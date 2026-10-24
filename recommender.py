"""STYLEAI outfit recommender: one rule-based engine used by every page (no machine learning).

Pipeline (``recommend_with_notes``):
  1. hard filters   - avoided colours, age-appropriateness, a price that fits the budget at all;
  2. item scores    - colour, style and occasion components (see ``_item_scores``), computed once per item;
  3. candidates     - the best-matching items per category, plus some cheaper well-matching ones;
  4. outfits        - every combination of candidates within the budget, scored with the outfit-level
                      compatibility and budget components (``WEIGHTS``, total 100);
  5. diversity      - successive outfits differ by at least two items where possible;
  6. explanations   - per-outfit reasons and page-level notes (e.g. why nothing fits the budget).

Inputs come from the profile (age, gender filter applied by the caller, budget), the four Appearance
steps (skin tone, favourite colours, style, occasion), the optional fine-tune signals (fit, fabrics,
styles/tones to avoid, brands), the free-text request (``preferences.parse_preferences``) and a colour
picked from the palette. Height and weight only drive the size guide (``size_hint``), never fit claims.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional

import pandas as pd

from live_catalog.garments import ETHNIC_TYPES, STYLE_RULES, allowed_for_style, garment_type
from live_catalog.normalize import full_outfit_type
from preferences import parse_preferences
from skin_tone import suggested_palette


CATEGORIES = ("Top", "Bottom", "Shoes", "Accessory")
WEIGHTS = {"colour": 30, "style": 20, "occasion": 20, "compatibility": 15, "budget": 15}
OCCASION_STYLES = {
    "College": {"Casual", "Smart Casual", "Streetwear", "Minimal"},
    "Office": {"Formal", "Smart Casual", "Minimal"},
    "Interview": {"Formal"},
    "Party": {"Trendy", "Smart Casual", "Elegant", "Streetwear"},
    "Festival": {"Ethnic", "Traditional"},
    "Casual Outing": {"Casual", "Smart Casual", "Minimal", "Streetwear", "Trendy"},
    "Traditional Event": {"Ethnic", "Traditional"},
    "Special Event": {"Elegant", "Formal", "Trendy"},
}
# UI style names that the original dataset spells differently (partial matches).
STYLE_ALIASES = {
    "Traditional": {"Ethnic"}, "Ethnic": {"Traditional"}, "Streetwear": {"Trendy"}, "Trendy": {"Streetwear"},
    "Elegant": {"Formal", "Smart Casual"}, "Minimal": {"Smart Casual", "Casual"},
}
OCCASION_ALIASES = {
    "Traditional Event": {"Festival"}, "Festival": {"Traditional Event"},
    "Casual Outing": {"College"}, "Special Event": {"Party"},
}
NEUTRALS = {"black", "white", "off-white", "ivory", "cream", "beige", "grey", "charcoal", "navy", "khaki", "tan", "camel", "silver", "brown"}
BRIGHT = {"red", "yellow", "orange", "cobalt blue", "pink", "green"}
PASTELS = {"lavender", "sage", "coral", "pink", "yellow"}
CLASHES = [{"red", "green"}, {"red", "pink"}, {"orange", "pink"}, {"red", "orange"}, {"purple", "orange"}, {"yellow", "pink"}, {"maroon", "red"}]
LAYER_WORDS = re.compile(r"\b(jacket|hoodie|overshirt|shacket|cardigan|blazer|coat|sweater|sweatshirt|pullover)\b", re.I)
NEON_WORDS = re.compile(r"\b(neon|fluorescent|highlighter)\b", re.I)
# Not shown to users under 18 (the scraper already skips lingerie, crop/halter/backless tops).
ADULT_WORDS = re.compile(r"\b(sexy|lingerie|bodycon|plunge|deep[- ]neck|backless|halter|mini ?skirt|crop|bralette|thong|beer|whisk(e)?y|vodka|wine glass|vape|smok\w*|hookah)\b", re.I)
# Gentle age affinity (never a filter; the user's own style choice always outweighs it).
AGE_AFFINITY = [
    (0, 18, {"Casual", "Trendy", "Streetwear", "Minimal"}, {"Formal", "Elegant"}),
    (18, 26, {"Trendy", "Streetwear", "Casual"}, set()),
    (26, 41, {"Smart Casual", "Minimal", "Formal"}, set()),
    (41, 200, {"Minimal", "Smart Casual", "Elegant", "Formal"}, set()),
]
AVOID_OPTIONS = {"neon / flashy", "overly bright", "pastels", "clashing tones", "dense layering"}


def load_dataset(path: Optional[Path] = None) -> pd.DataFrame:
    csv_path = path or Path(__file__).parent / "data" / "fashion_dataset.csv"
    frame = pd.read_csv(csv_path)
    frame["price"] = pd.to_numeric(frame["price"], errors="raise")
    required = {"item_id", "category", "item_name", "colour", "shade", "style", "occasion", "price", "image"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    return frame


def _split(value) -> set[str]:
    return {part.strip().lower() for part in re.split(r"[|,]", str(value)) if part.strip()}


def _matches(value: str, requested: str) -> bool:
    return requested.lower() in _split(value)


def _style_matches_occasion(item, style: str, occasion: str) -> bool:
    allowed_styles = OCCASION_STYLES.get(occasion, {style})
    return any(_matches(item["style"], allowed_style) for allowed_style in allowed_styles)


def _text(value) -> str:
    return "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)


# ---------------------------------------------------------------------------
# Context: everything the user told us, in one place
# ---------------------------------------------------------------------------

@dataclass
class Context:
    style: str
    occasion: str
    budget: float
    palette: List[str]
    styles: List[str] = field(default_factory=list)
    favorite: set = field(default_factory=set)
    strong: set = field(default_factory=set)       # palette pick + colours named in the text request
    picked: Optional[str] = None                   # colour clicked in the palette (the latest explicit choice)
    avoid_hard: set = field(default_factory=set)   # explicitly avoided colours: excluded
    avoid_soft: set = field(default_factory=set)   # "Overly Bright" / "Pastels": ranked lower
    no_neon: bool = False
    clash_sensitive: bool = False
    avoid_layering: bool = False
    age: Optional[int] = None
    fit: Optional[str] = None
    fit_by_category: Dict[str, str] = field(default_factory=dict)
    fabrics: set = field(default_factory=set)
    brands: set = field(default_factory=set)
    garments: Dict[str, List[str]] = field(default_factory=dict)
    prefer_cheaper: bool = False
    parsed: Dict = field(default_factory=dict)
    profile_budget: float = 0.0
    exclude: List[str] = field(default_factory=list)          # "no heels", "do not recommend crop tops"
    required_colours: set = field(default_factory=set)       # "only black": clothing must be these colours


FABRIC_PREFS = {
    "breathable linen": "linen", "crisp cotton blend": "cotton", "classic denim": "denim",
    "silk & satin": "silk", "soft supima cotton": "cotton", "handloom khadi": "khadi",
}


def build_context(user_profile: Dict) -> Context:
    parsed = parse_preferences(user_profile.get("preference_text") or "")
    # A style named in the text request is the user's current intent: it replaces the profile style.
    style = (parsed.get("styles") or [None])[0] or user_profile.get("style") or "Casual"
    occasion = parsed.get("occasion") or user_profile.get("occasion") or "College"
    profile_budget = float(user_profile.get("budget", 3500.0))
    budget = min(profile_budget, parsed["budget"]) if parsed.get("budget") else profile_budget
    tone = user_profile.get("skin_tone")
    avoid_raw = [str(c) for c in (user_profile.get("avoid_colours") or [])]
    avoid_options = {c.lower() for c in avoid_raw if c.lower() in AVOID_OPTIONS}
    avoid_soft = set()
    if "overly bright" in avoid_options or "neon / flashy" in avoid_options:
        avoid_soft |= BRIGHT
    if "pastels" in avoid_options:
        avoid_soft |= PASTELS
    palette_pick = [c for c in [user_profile.get("palette_colour")] if c]
    age = user_profile.get("age")
    try:
        age = int(age) if age is not None else None
    except (TypeError, ValueError):
        age = None
    return Context(
        style=style,
        occasion=occasion,
        budget=budget,
        profile_budget=profile_budget,
        palette=suggested_palette(tone) if tone else [],
        styles=list(dict.fromkeys([style, *parsed.get("styles", [])])) if parsed.get("styles") else [style],
        favorite={c.lower() for c in user_profile.get("favorite_colours") or []},
        strong={c.lower() for c in [*palette_pick, *parsed.get("colours", [])]},
        picked=palette_pick[0].lower() if palette_pick else None,
        avoid_hard={c.lower() for c in avoid_raw if c.lower() not in AVOID_OPTIONS} | {c.lower() for c in parsed.get("avoid_colours", [])},
        avoid_soft=avoid_soft - {c.lower() for c in user_profile.get("favorite_colours") or []},
        no_neon="neon / flashy" in avoid_options,
        clash_sensitive="clashing tones" in avoid_options,
        avoid_layering="dense layering" in avoid_options,
        age=age,
        fit=parsed.get("fit") or user_profile.get("preferred_fit"),
        fit_by_category=parsed.get("fit_by_category", {}),
        fabrics={FABRIC_PREFS.get(f.lower(), f.lower()) for f in user_profile.get("preferred_fabrics") or []}
        | {f.lower().split()[0] for f in parsed.get("fabrics", [])},
        brands={b.lower() for b in user_profile.get("preferred_brands") or []},
        garments=parsed.get("garments", {}),
        prefer_cheaper=bool(parsed.get("prefer_cheaper")),
        parsed=parsed,
        exclude=[w.lower() for w in parsed.get("exclude", [])],
        required_colours={c.lower() for c in parsed.get("required_colours", [])},
    )


# ---------------------------------------------------------------------------
# Hard filters and item scores
# ---------------------------------------------------------------------------

def _item_colours(item) -> set[str]:
    return {_text(item.get("colour")).lower(), _text(item.get("shade")).lower()} - {""}


def item_subcategory(item) -> Optional[str]:
    """Garment type of a catalogue row (stored for live items, derived for the original CSV)."""
    stored = _text(item.get("subcategory"))
    if stored:
        return stored
    full = full_outfit_type(_text(item.get("item_name")), _text(item.get("product_type")))
    return full or garment_type(_text(item.get("category")), _text(item.get("item_name")), _text(item.get("product_type")))


def covers_bottom(item) -> bool:
    value = item.get("covers_bottom") if item is not None else None
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return bool(item is not None and full_outfit_type(_text(item.get("item_name")), _text(item.get("product_type"))))
    return bool(value)


def _allowed(item, ctx: Context) -> bool:
    if _item_colours(item) & ctx.avoid_hard:
        return False
    name = _text(item.get("item_name"))
    lowered = name.lower()
    if ctx.no_neon and NEON_WORDS.search(name):
        return False
    if ctx.age is not None and ctx.age < 18 and ADULT_WORDS.search(f"{name} {_text(item.get('product_type'))}"):
        return False
    category = _text(item.get("category"))
    subcategory = item_subcategory(item)
    # The chosen style is a requirement: e.g. Traditional only allows ethnic garment types.
    if not allowed_for_style(ctx.style, category, subcategory, _split(item.get("style")), name, _text(item.get("colour"))):
        return False
    # Explicit exclusions from the text request ("no heels", "do not recommend crop tops").
    for word in ctx.exclude:
        stem = word.rstrip("s") if len(word) > 4 else word
        if stem in lowered or (subcategory and stem in subcategory) or word == "western" and subcategory not in ETHNIC_TYPES:
            return False
    if ctx.required_colours and category in ("Top", "Bottom") and not _item_colours(item) & ctx.required_colours:
        return False
    return True


def apply_hard_filters(frame: pd.DataFrame, ctx: Context) -> pd.DataFrame:
    if frame.empty:
        return frame
    mask = frame.apply(lambda row: _allowed(row, ctx), axis=1)
    return frame[mask & frame["price"].notna() & (frame["price"] > 0)]


# Related shades. Exact matches score higher than family matches, so Navy and Blue, or Cream and Beige,
# stay distinguishable while still helping each other.
COLOUR_FAMILIES = {
    "blue": {"navy", "blue", "cobalt blue", "teal"}, "red": {"maroon", "burgundy", "red", "rust"},
    "pink": {"pink", "coral", "lavender"}, "green": {"green", "forest green", "emerald", "olive", "sage"},
    "light neutral": {"white", "off-white", "ivory", "cream", "beige", "sand"}, "brown": {"brown", "chocolate", "tan", "camel", "khaki"},
    "dark neutral": {"black", "charcoal", "grey"}, "yellow": {"yellow", "mustard", "gold", "orange"}, "purple": {"purple", "lavender"},
}


def _families(colours) -> set:
    return {family for family, members in COLOUR_FAMILIES.items() if set(colours) & members}


def _colour_score(item, ctx: Context) -> float:
    colours = _item_colours(item)
    if colours & ctx.avoid_hard:
        return 0.0
    score = 12.0
    # Colours the user chose outweigh the palette inferred from skin tone.
    if colours & {c.lower() for c in ctx.palette}:
        score += 6.0
    if colours & ctx.favorite:
        score += 9.0
    elif _families(colours) & _families(ctx.favorite):
        score += 4.0  # a related shade (e.g. Burgundy for a Maroon favourite) counts, but less
    if colours & ctx.strong:
        score += 10.0
    elif _families(colours) & _families(ctx.strong):
        score += 4.0
    if ctx.picked and ctx.picked in colours:
        score += 8.0
    if colours & ctx.avoid_soft:
        score -= 8.0
    if colours & NEUTRALS and not colours & (ctx.favorite | ctx.strong):
        score += 2.0
    return max(0.0, min(30.0, score))


def _style_score(item, category: str, ctx: Context) -> float:
    item_styles = _split(item.get("style"))
    wanted = [s.lower() for s in ctx.styles]
    if item_styles & set(wanted):
        points = 15.0
    elif any(item_styles & {a.lower() for a in STYLE_ALIASES.get(s, set())} for s in ctx.styles):
        points = 11.0
    else:
        points = 5.0
    if _style_matches_occasion(item, ctx.style, ctx.occasion):
        points += 4.0
    wanted_fit = ctx.fit_by_category.get(category) or ctx.fit
    item_fit = _text(item.get("fit"))
    if wanted_fit and item_fit:
        points += 2.0 if item_fit == wanted_fit else -1.0
    text = f"{_text(item.get('item_name'))} {_text(item.get('fabric'))} {_text(item.get('fabric_tag'))}".lower()
    if ctx.fabrics and any(f in text for f in ctx.fabrics):
        points += 1.5
    if ctx.brands and _text(item.get("brand")).lower() in ctx.brands:
        points += 1.5
    if any(word in _text(item.get("item_name")).lower() for word in ctx.garments.get(category, [])):
        points += 4.0
    if ctx.age is not None:
        for low, high, liked, disliked in AGE_AFFINITY:
            if low <= ctx.age < high:
                if item_styles & {s.lower() for s in liked}:
                    points += 1.0
                if item_styles & {s.lower() for s in disliked} and ctx.style not in disliked and ctx.occasion not in ("Office", "Interview"):
                    points -= 1.5
    return max(0.0, min(20.0, points))


def _occasion_score(item, ctx: Context) -> float:
    occasions = _split(item.get("occasion"))
    if ctx.occasion.lower() in occasions:
        return 20.0
    if occasions & {a.lower() for a in OCCASION_ALIASES.get(ctx.occasion, set())}:
        return 14.0
    return 8.0


def _item_scores(item, category: str, ctx: Context) -> Dict[str, float]:
    return {"colour": _colour_score(item, ctx), "style": _style_score(item, category, ctx), "occasion": _occasion_score(item, ctx)}


def _compatibility_score(items: Dict[str, Dict], ctx: Context) -> float:
    colours = [_text(item.get("colour")).lower() for item in items.values()]
    liked = {c.lower() for c in ctx.palette} | ctx.favorite | ctx.strong
    score = 7.0 + sum(c in liked for c in colours) * 2.0
    unique = set(colours)
    if len(unique) >= 2:
        score += 2.0
    if unique & NEUTRALS:
        score += 2.0
    clashes = sum(1 for pair in CLASHES if pair <= unique)
    score -= clashes * (6.0 if ctx.clash_sensitive else 4.0)
    if len(items) >= 3 and len(unique) == 1 and not unique & NEUTRALS:
        score -= 3.0
    top, bottom = items.get("Top"), items.get("Bottom")
    if top is not None and bottom is not None and _split(top.get("style")) & _split(bottom.get("style")):
        score += 1.0
    if ctx.avoid_layering and top is not None and LAYER_WORDS.search(_text(top.get("item_name"))):
        score -= 3.0
    if ctx.picked and ctx.picked in unique:
        score += 4.0
    return max(0.0, min(15.0, score))


def _budget_score(total: float, ctx: Context) -> float:
    budget = max(ctx.budget, 1)
    if total > budget:
        return max(0.0, 15.0 - (total - budget) / budget * 15)
    if ctx.prefer_cheaper:
        return 15.0 if total <= 0.6 * budget else 15.0 - (total / budget - 0.6) / 0.4 * 6.0
    return 15.0


def _outfit_breakdown(items: Dict[str, Dict], item_scores: Dict[str, Dict[str, float]], ctx: Context) -> tuple[float, Dict[str, float], float]:
    n = max(len(items), 1)
    totals = {key: 0.0 for key in WEIGHTS}
    for category in items:
        for key, value in item_scores[category].items():
            totals[key] += value / n
    totals["compatibility"] = _compatibility_score(items, ctx)
    total_price = sum(float(item["price"]) for item in items.values())
    totals["budget"] = _budget_score(total_price, ctx)
    return round(sum(totals.values()), 2), {key: round(value, 2) for key, value in totals.items()}, round(total_price, 2)


def _reasons(items: Dict[str, Dict], ctx: Context, total: float) -> List[str]:
    reasons: List[str] = []
    if ctx.style in STYLE_RULES:
        kinds = [str(item_subcategory(item) or cat).replace("_", " ") for cat, item in items.items()]
        reasons.append(f"Every piece is a {ctx.style.lower()} garment type ({', '.join(kinds)})")
    else:
        styled = [cat for cat, item in items.items() if _split(item.get("style")) & {s.lower() for s in ctx.styles}]
        if styled:
            reasons.append(f"{', '.join(styled)} match your {' / '.join(ctx.styles)} style")
    occasion = [cat for cat, item in items.items() if ctx.occasion.lower() in _split(item.get("occasion"))]
    if occasion:
        reasons.append(f"{', '.join(occasion)} suit {ctx.occasion}")
    picked = sorted({_text(item.get("colour")) for item in items.values() if _item_colours(item) & ctx.strong})
    if picked:
        reasons.append(f"In your requested colour{'s' if len(picked) > 1 else ''}: {', '.join(picked)}")
    palette = sorted({_text(item.get("colour")) for item in items.values() if _item_colours(item) & {c.lower() for c in ctx.palette}})
    if palette:
        reasons.append(f"{', '.join(palette)} {'is' if len(palette) == 1 else 'are'} in the suggested palette for the skin tone you selected")
    favourite = sorted({_text(item.get("colour")) for item in items.values() if _item_colours(item) & ctx.favorite})
    if favourite:
        reasons.append(f"Favourite colour{'s' if len(favourite) > 1 else ''}: {', '.join(favourite)}")
    related = sorted({_text(item.get("colour")) for item in items.values()
                      if not _item_colours(item) & ctx.favorite and _families(_item_colours(item)) & _families(ctx.favorite)})
    if related:
        reasons.append(f"{', '.join(related)}: close to your favourite colours")
    for cat, item in items.items():
        wanted_fit = ctx.fit_by_category.get(cat)
        if wanted_fit and _text(item.get("fit")) == wanted_fit:
            reasons.append(f"{cat} is {wanted_fit.lower()} as requested")
    if total <= ctx.budget:
        reasons.append(f"Within budget: ₹{ctx.budget - total:,.0f} to spare")
    return reasons


# ---------------------------------------------------------------------------
# Outfits
# ---------------------------------------------------------------------------

def _as_item_map(outfit: Optional[Dict]) -> Dict[str, pd.Series]:
    if not outfit:
        return {}
    return {category: pd.Series(item) for category, item in outfit.get("items", {}).items()}


def _candidates(rows: pd.DataFrame, category: str, ctx: Context, top_n: int = 10, cheap_n: int = 4) -> List[tuple]:
    """(item dict, scores) for the best-matching items plus a few well-matching cheaper ones."""
    scored = []
    for _, row in rows.iterrows():
        item = row.to_dict()
        scores = _item_scores(item, category, ctx)
        scored.append((item, scores, scores["colour"] + scores["style"] + scores["occasion"]))
    scored.sort(key=lambda entry: -entry[2])
    best = scored[:top_n]
    if len(scored) > top_n:
        median = sorted(entry[2] for entry in scored)[len(scored) // 2]
        cheap = sorted((e for e in scored[top_n:] if e[2] >= median), key=lambda e: float(e[0]["price"]))[:cheap_n]
        best += cheap
    if ctx.picked:
        # The palette pick always gets a chance to compete at outfit level.
        best += [e for e in scored if e not in best and ctx.picked in _item_colours(e[0])][:2]
    return [(item, scores) for item, scores, _ in best]


def _build(selected: Dict[str, tuple], ctx: Context) -> Dict:
    """An outfit from {category: (item, scores)}; categories may be absent (covered by a set, or no accessory)."""
    items = {category: item for category, (item, _) in selected.items()}
    item_scores = {category: scores for category, (_, scores) in selected.items()}
    score, breakdown, total = _outfit_breakdown(items, item_scores, ctx)
    return {
        "signature": tuple(str(items[category]["item_id"]) if category in items else "" for category in CATEGORIES),
        "items": items,
        "score": score,
        "total_price": total,
        "breakdown": breakdown,
        "palette": ctx.palette,
    }


def _group(item: Dict) -> str:
    """Product identity across colour variants (so two colours of one kurta count as the same product)."""
    return _text(item.get("product_id")) or _text(item.get("item_id"))


# Diversity: how much each shared piece makes two outfits "the same", and the penalty per unit.
SLOT_SIMILARITY = {"Top": 1.0, "Bottom": 0.7, "Shoes": 0.5, "Accessory": 0.3}
DIVERSITY_PENALTY = 9.0


def _similarity(a: Dict, b: Dict) -> float:
    sim = 0.0
    for category, weight in SLOT_SIMILARITY.items():
        x, y = a["items"].get(category), b["items"].get(category)
        if x is not None and y is not None and _group(x) == _group(y):
            sim += weight
    top_a, top_b = a["items"].get("Top"), b["items"].get("Top")
    if top_a is not None and top_b is not None and _group(top_a) != _group(top_b):
        if item_subcategory(top_a) == item_subcategory(top_b) and _text(top_a.get("colour")) == _text(top_b.get("colour")):
            sim += 0.4  # same kind of top in the same colour reads as a near-duplicate
    return sim


def select_diverse(results: List[Dict], limit: int, locked: int = 0) -> List[Dict]:
    """Greedy diversity-aware selection (maximal-marginal-relevance style).

    Each pick maximises ``score - DIVERSITY_PENALTY * max similarity to the outfits already picked``.
    Identical product sets are never picked twice. Locked pieces are shared by every outfit, so they
    are not penalised.
    """
    chosen: List[Dict] = []
    seen_sets = set()
    pool = results[:400]
    while pool and len(chosen) < limit:
        best, best_value = None, None
        for outfit in pool:
            key = frozenset(_group(item) for item in outfit["items"].values())
            if key in seen_sets:
                continue
            penalty = max((_similarity(outfit, c) for c in chosen), default=0.0)
            if locked:
                penalty = max(0.0, penalty - sum(list(SLOT_SIMILARITY.values())[:locked]))
            value = outfit["score"] - DIVERSITY_PENALTY * penalty
            if best_value is None or value > best_value:
                best, best_value = outfit, value
        if best is None:
            break
        chosen.append(best)
        seen_sets.add(frozenset(_group(item) for item in best["items"].values()))
        pool = [o for o in pool if o is not best]
    return chosen


def _combinations(choices: Dict[str, List[tuple]], locked_items: Dict[str, Dict]):
    """All outfits from the candidate lists. A full-outfit top (set, saree, dress) takes no bottom;
    a category with no candidates (only Accessory may be empty) is left out."""
    tops = choices.get("Top", [])
    bottoms = choices.get("Bottom", [])
    rest = [c for c in ("Shoes", "Accessory") if choices.get(c)]
    for top in tops:
        if covers_bottom(top[0]):
            if "Bottom" in locked_items:
                continue  # a locked bottom cannot be combined with a set that already includes one
            bottom_options = [None]
        else:
            bottom_options = bottoms
            if not bottom_options:
                continue
        for bottom in bottom_options:
            for others in product(*(choices[c] for c in rest)):
                selected = {"Top": top}
                if bottom is not None:
                    selected["Bottom"] = bottom
                selected.update(dict(zip(rest, others)))
                yield selected


def recommend_with_notes(
    frame: pd.DataFrame,
    user_profile: Dict,
    locked_items: Optional[Dict[str, Dict]] = None,
    exclude_signatures: Optional[set[tuple]] = None,
    limit: int = 3,
) -> tuple[List[Dict], List[str]]:
    ctx = build_context(user_profile)
    notes: List[str] = []
    locked_items = locked_items or {}
    exclude_signatures = exclude_signatures or set()
    if ctx.budget < ctx.profile_budget:
        notes.append(f"Using the budget from your request: ₹{ctx.budget:,.0f}.")

    filtered = apply_hard_filters(frame, ctx)
    locked_total = sum(float(item.get("price") or 0) for item in locked_items.values())
    choices: Dict[str, List[tuple]] = {}
    missing: List[str] = []
    for category in CATEGORIES:
        if category in locked_items:
            item = dict(locked_items[category])
            choices[category] = [(item, _item_scores(item, category, ctx))]
            continue
        rows = filtered[filtered["category"].str.lower() == category.lower()]
        affordable = rows[rows["price"] <= max(ctx.budget - locked_total, 0)] if not rows.empty else rows
        rows = affordable if not affordable.empty else rows
        if rows.empty:
            choices[category] = []
            missing.append(category)
            continue
        choices[category] = _candidates(rows, category, ctx)

    style_label = ctx.style.lower()
    has_full_top = any(covers_bottom(item) for item, _ in choices.get("Top", []))
    blocking = [c for c in missing if c in ("Top", "Shoes") or (c == "Bottom" and not has_full_top)]
    if blocking:
        notes.append(
            f"The catalogue has no {style_label} {', '.join(c.lower() for c in blocking)} that match your choices right now, "
            f"so no complete {style_label} outfit can be built. More {style_label} products are needed (see the catalogue status); "
            f"your style preference was not relaxed."
        )
        return [], notes
    if "Accessory" in missing:
        notes.append(f"No {style_label} accessories match your choices, so these outfits have no accessory.")

    for colour in sorted(ctx.strong):
        if not any(colour in _item_colours(item) for options in choices.values() for item, _ in options):
            notes.append(f"No products in {colour.title()} are available for your other choices right now; showing the closest matches.")

    results = []
    for selected in _combinations(choices, locked_items):
        total_price = sum(float(item["price"]) for item, _ in selected.values())
        if total_price > ctx.budget:
            continue
        outfit = _build(selected, ctx)
        if outfit["signature"] in exclude_signatures:
            continue
        results.append(outfit)
    results.sort(key=lambda outfit: (-outfit["score"], outfit["total_price"]))
    diverse = select_diverse(results, limit, locked=len(locked_items))

    if not diverse:
        # Nothing fits the budget: show the cheapest real combinations (still in the chosen style) and say so.
        cheapest: Dict[str, List[tuple]] = {}
        for category in CATEGORIES:
            if category in locked_items or not choices.get(category):
                cheapest[category] = choices.get(category, [])
                continue
            rows = filtered[filtered["category"].str.lower() == category.lower()]
            cheapest[category] = [(row.to_dict(), _item_scores(row.to_dict(), category, ctx)) for _, row in rows.nsmallest(3, "price").iterrows()]
        fallback = [_build(selected, ctx) for selected in _combinations(cheapest, locked_items)]
        fallback = [o for o in fallback if o["signature"] not in exclude_signatures]
        fallback.sort(key=lambda outfit: (outfit["total_price"], -outfit["score"]))
        diverse = select_diverse(fallback, limit, locked=len(locked_items))
        for outfit in diverse:
            outfit["over_budget"] = True
        if diverse:
            locked_note = " including your locked items" if locked_items else ""
            notes.append(
                f"No complete outfit{locked_note} fits your ₹{ctx.budget:,.0f} budget with the available products. "
                f"The closest options start at ₹{diverse[0]['total_price']:,.0f}."
            )

    for outfit in diverse:
        outfit["reasons"] = _reasons(outfit["items"], ctx, outfit["total_price"])
    if ctx.picked and diverse and not any(ctx.picked in _item_colours(item) for o in diverse for item in o["items"].values()):
        notes.append(
            f"{ctx.picked.title()} items are available, but none of them suit your {style_label} / {ctx.occasion} choices "
            f"within budget, so they rank below the outfits shown."
        )
    if 0 < len(diverse) < limit:
        notes.append(
            f"Only {len(diverse)} distinct {style_label} outfit{'s' if len(diverse) > 1 else ''} could be built from the products that "
            f"match; the catalogue needs more {style_label} items for more variety."
        )
    return diverse, notes


def effective_context(user_profile: Dict) -> Dict:
    """The style / occasion / budget actually used after applying the text request (for the UI)."""
    ctx = build_context(user_profile)
    return {"style": ctx.style, "styles": ctx.styles, "occasion": ctx.occasion, "budget": ctx.budget}


def recommend_outfits(
    frame: pd.DataFrame,
    user_profile: Dict,
    locked_items: Optional[Dict[str, Dict]] = None,
    exclude_signatures: Optional[set[tuple]] = None,
    limit: int = 3,
) -> list[Dict]:
    return recommend_with_notes(frame, user_profile, locked_items, exclude_signatures, limit)[0]


def score_single_outfit(outfit: Dict, user_profile: Dict) -> Dict:
    ctx = build_context(user_profile)
    items = {category: dict(item) for category, item in (outfit or {}).get("items", {}).items()}
    item_scores = {category: _item_scores(item, category, ctx) for category, item in items.items()}
    score, breakdown, total = _outfit_breakdown(items, item_scores, ctx)
    return {"score": score, "breakdown": breakdown, "total_price": total}


def replacement_candidates(frame: pd.DataFrame, category: str, outfit: Dict, user_profile: Dict) -> list[Dict]:
    current = _as_item_map(outfit)
    locked = current.copy()
    current_item = locked.pop(category, None)
    current_item_id = str(current_item.get("item_id", "")) if current_item is not None else ""
    candidates = recommend_outfits(frame, user_profile, locked_items={key: item.to_dict() for key, item in locked.items()}, limit=60)
    seen, unique = set(), []
    for candidate in candidates:
        item_id = str(candidate["items"][category]["item_id"])
        if item_id != current_item_id and item_id not in seen:
            seen.add(item_id)
            unique.append(candidate)
    return unique


def cheaper_alternative(frame: pd.DataFrame, item: Dict, user_profile: Optional[Dict] = None, outfit: Optional[Dict] = None) -> Optional[Dict]:
    """A strictly cheaper real product in the same category.

    Without a profile: same colour if possible, else the most expensive cheaper item (original behaviour).
    With a profile: avoided colours are excluded and the best-scoring cheaper item that goes with the
    rest of the outfit wins (ties: the closer price).
    """
    price = float(item["price"])
    candidates = frame[(frame["category"] == item["category"]) & (frame["price"] < price)].copy()
    candidates = candidates[candidates["item_id"].astype(str) != str(item.get("item_id"))]
    if candidates.empty:
        return None
    if user_profile is None:
        same_colour = candidates[candidates["colour"].str.lower() == str(item["colour"]).lower()]
        chosen = (same_colour if not same_colour.empty else candidates).sort_values("price", ascending=False).iloc[0]
        return chosen.to_dict()
    ctx = build_context(user_profile)
    candidates = apply_hard_filters(candidates, ctx)
    if candidates.empty:
        return None
    others = {cat: dict(other) for cat, other in (outfit or {}).get("items", {}).items() if cat != item["category"]}
    best, best_key = None, None
    for _, row in candidates.iterrows():
        cand = row.to_dict()
        scores = _item_scores(cand, item["category"], ctx)
        compat = _compatibility_score({**others, item["category"]: cand}, ctx)
        same_colour = 3.0 if str(cand.get("colour")).lower() == str(item.get("colour")).lower() else 0.0
        key = (sum(scores.values()) + compat + same_colour, float(cand["price"]))
        if best_key is None or key > best_key:
            best, best_key = cand, key
    return best


def builder_options(frame: pd.DataFrame, user_profile: Dict, category: str, selected: Dict[str, Dict], limit: int = 8, offset: int = 0) -> Dict:
    """Ranked products for one step of the manual outfit builder, given what is already picked."""
    ctx = build_context(user_profile)
    others = {cat: dict(item) for cat, item in selected.items() if cat != category and item}
    spent = sum(float(item.get("price") or 0) for item in others.values())
    remaining = ctx.budget - spent
    rows = apply_hard_filters(frame[frame["category"].str.lower() == category.lower()], ctx)
    notes: List[str] = []
    within = rows[rows["price"] <= remaining] if remaining > 0 else rows.iloc[0:0]
    if within.empty and not rows.empty:
        notes.append(f"Nothing in {category.lower()} fits the ₹{max(remaining, 0):,.0f} left in your budget; showing the cheapest options.")
        within = rows.nsmallest(limit, "price")
    ranked = []
    for _, row in within.iterrows():
        item = row.to_dict()
        scores = _item_scores(item, category, ctx)
        compat = _compatibility_score({**others, category: item}, ctx) if others else 7.5
        ranked.append((sum(scores.values()) + compat, -float(item["price"]), item))
    ranked.sort(key=lambda entry: (-entry[0], -entry[1]))
    return {
        "category": category,
        "items": [item for _, _, item in ranked[offset:offset + limit]],
        "total": len(ranked),
        "remaining_budget": round(remaining, 2),
        "notes": notes,
    }


COLOUR_HEX = {
    "White": "#f4f4f1", "Off-White": "#efe9dc", "Ivory": "#f3eedf", "Cream": "#efe4cc", "Beige": "#d8c3a0", "Sand": "#d6c19a",
    "Khaki": "#b8a07a", "Tan": "#b98a5c", "Camel": "#c19a6b", "Brown": "#6b4428", "Chocolate": "#3e251a", "Black": "#1c1c1f",
    "Charcoal": "#36383d", "Grey": "#7d8086", "Silver": "#c9ccd2", "Gold": "#c9a54a", "Rose Gold": "#c98f7a", "Navy": "#1f2a44",
    "Blue": "#3b5fa8", "Cobalt Blue": "#1f4bb0", "Teal": "#11605f", "Green": "#2f6b3a", "Forest Green": "#1e4731",
    "Olive": "#5b6234", "Sage": "#8a9a78", "Emerald": "#0d6646", "Mustard": "#c9971f", "Yellow": "#e2c044", "Rust": "#a84b26",
    "Orange": "#d9772b", "Coral": "#e2735e", "Red": "#b3282d", "Maroon": "#6b1d27", "Burgundy": "#6b1d2f", "Pink": "#e48aa6",
    "Lavender": "#b5a7d8", "Purple": "#5b3f8c", "Multi": "#8b8794",
}
STYLE_COLOURS = {
    "Formal": ["Navy", "White", "Black", "Grey", "Charcoal"], "Smart Casual": ["Navy", "Beige", "Olive", "White", "Brown"],
    "Minimal": ["White", "Black", "Beige", "Grey", "Navy"], "Traditional": ["Maroon", "Mustard", "Teal", "Cream", "Gold"],
    "Ethnic": ["Maroon", "Mustard", "Teal", "Cream", "Gold"], "Elegant": ["Black", "Burgundy", "Emerald", "Ivory", "Navy"],
    "Streetwear": ["Black", "Olive", "Grey", "White", "Beige"], "Trendy": ["Black", "Olive", "Lavender", "Rust", "White"],
    "Casual": ["Blue", "White", "Olive", "Grey", "Beige"],
}


def colour_palette(frame: pd.DataFrame, user_profile: Dict, limit: int = 8) -> Dict:
    """Clickable palette: skin-tone, favourite and style colours that real products are available in."""
    ctx = build_context({**user_profile, "palette_colour": None})
    available = apply_hard_filters(frame, ctx)
    counts = available["colour"].astype(str).value_counts().to_dict() if not available.empty else {}
    candidates = []
    for colour in ctx.palette:
        candidates.append((colour, f"Suits your {user_profile.get('skin_tone', 'Medium')} skin tone"))
    for colour in user_profile.get("favorite_colours") or []:
        candidates.append((colour, "One of your favourite colours"))
    for colour in STYLE_COLOURS.get(ctx.style, []):
        candidates.append((colour, f"Works for a {ctx.style} look"))
    swatches, unavailable, seen = [], [], set()
    for colour, reason in candidates:
        if colour.lower() in seen or colour.lower() in ctx.avoid_hard:
            continue
        seen.add(colour.lower())
        count = int(sum(n for name, n in counts.items() if name.lower() == colour.lower()))
        entry = {"name": colour, "hex": COLOUR_HEX.get(colour, "#8b8794"), "count": count, "reason": reason}
        (swatches if count else unavailable).append(entry)
    return {"swatches": swatches[:limit], "unavailable": unavailable}


SIZE_ORDER = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL", "XXXL", "4XL", "5XL"]


def size_hint(gender: Optional[str], height: Optional[float], weight: Optional[float]) -> Optional[Dict]:
    """A rough letter-size starting point from height and weight. Not a fit guarantee: brand size charts differ."""
    try:
        h, w = float(height), float(weight)
    except (TypeError, ValueError):
        return None
    if str(gender).lower() in ("female", "woman", "women"):
        steps = [(45, "XS"), (52, "S"), (60, "M"), (68, "L"), (78, "XL")]
        size = next((s for limit, s in steps if w <= limit), "XXL")
    else:
        steps = [(55, "S"), (65, "M"), (76, "L"), (87, "XL")]
        size = next((s for limit, s in steps if w <= limit), "XXL")
        if size == "S" and w < 50:
            size = "XS"
    index = SIZE_ORDER.index(size)
    if h >= 185 and index < len(SIZE_ORDER) - 1:
        size = SIZE_ORDER[index + 1]
    return {
        "size": size,
        "note": f"Rough starting point for {h:.0f} cm / {w:.0f} kg. Brand size charts differ — check the brand's chart before buying.",
    }


def get_replacement_candidates(frame: pd.DataFrame, category: str, outfit: Dict, user_profile: Dict) -> list[Dict]:
    return replacement_candidates(frame, category, outfit, user_profile)


def get_cheaper_alternative(frame: pd.DataFrame, item: Dict, user_profile: Optional[Dict] = None, outfit: Optional[Dict] = None) -> Optional[Dict]:
    return cheaper_alternative(frame, item, user_profile, outfit)
