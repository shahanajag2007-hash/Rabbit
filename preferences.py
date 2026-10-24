"""Rule-based parser for the free-text styling request on the Recommendations page.

"Suggest a formal outfit in navy blue under 2500, no black" ->
    {"styles": ["Formal"], "colours": ["Navy"], "avoid_colours": ["Black"], "budget": 2500, ...}

No LLM is involved: every rule below is a keyword pattern, and ``understood`` lists, in plain
words, what was picked up, so the UI can show exactly what the recommender is acting on.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from live_catalog.normalize import COLOURS

# Longest synonyms first so "navy blue" wins over "blue".
_COLOUR_SYNONYMS = sorted(((syn, name) for name, (_, syns) in COLOURS.items() for syn in syns), key=lambda p: -len(p[0]))
_COLOUR_GROUPS = {
    "neutral": ["Beige", "White", "Black", "Grey", "Navy", "Cream", "Off-White", "Charcoal"],
    "earthy": ["Olive", "Rust", "Brown", "Camel", "Khaki", "Beige"],
    "pastel": ["Lavender", "Sage", "Coral", "Pink", "Cream"],
    "dark": ["Black", "Navy", "Charcoal", "Maroon", "Forest Green", "Chocolate"],
    "bright": ["Red", "Yellow", "Orange", "Cobalt Blue", "Pink"],
    "monochrome": ["Black", "White", "Grey"],
}
_NEGATION = re.compile(r"\b(no|not|avoid|without|except|never|hate|dislike|don'?t (?:want|like))\b")

_STYLE_WORDS = [
    (r"smart[- ]casual|semi[- ]formal", "Smart Casual"),
    (r"formal|professional|corporate|business|office wear", "Formal"),
    (r"street ?wear|street style|urban", "Streetwear"),
    (r"trendy|fashionable|stylish|bold|statement|edgy", "Trendy"),
    (r"minimal\w*|simple|clean|basic|understated", "Minimal"),
    (r"traditional|ethnic|desi|indian wear|kurta", "Traditional"),
    (r"elegant|classy|chic|sophisticated|graceful", "Elegant"),
    (r"casual|relaxed|laid[- ]back|comfortable|comfy|everyday", "Casual"),
]
_OCCASION_WORDS = [
    (r"interview", "Interview"),
    (r"office|work(?:place)?|meeting|corporate", "Office"),
    (r"college|campus|class(?:es)?|university|school|lecture", "College"),
    (r"party|night ?out|club|date night|celebration", "Party"),
    (r"wedding|festival|festive|diwali|eid|puja|pooja|traditional event|ceremony", "Traditional Event"),
    (r"brunch|outing|weekend|hang ?out|coffee|travel|vacation|trip", "Casual Outing"),
    (r"gala|award|special event|reception|dinner", "Special Event"),
]
_FIT_WORDS = [
    (r"oversized?|loose|baggy|relaxed[- ]fit|boxy|wide[- ]leg", "Loose / Oversized"),
    (r"slim|skinny|fitted|tailored|body[- ]hugging", "Slim / Fitted"),
    (r"regular[- ]fit|straight[- ]fit|classic fit", "Regular Fit"),
]
_FABRIC_WORDS = [
    (r"linen", "Linen"), (r"denim", "Denim"), (r"silk|satin", "Silk Satin"),
    (r"rayon|viscose", "Rayon"), (r"khadi|handloom", "Khadi Cotton"), (r"wool", "Wool Blend"),
    (r"cotton|breathable", "Cotton Blend"),
]
# Garment words per recommender category (used to prefer items whose name contains them).
_GARMENTS = {
    "Top": r"t-?shirts?|tees?|shirts?|polos?|kurtas?|kurtis?|tops?|blouses?|sweaters?|sweatshirts?|hoodies?|jackets?|blazers?|cardigans?|tunics?|henleys?",
    "Bottom": r"jeans|trousers?|pants?|chinos?|joggers?|cargos?|shorts|skirts?|palazzos?|salwars?|leggings",
    "Shoes": r"sneakers?|shoes?|loafers?|boots?|sandals?|sliders?|heels?|juttis?|mojaris?|flats|trainers?",
    "Accessory": r"watch(?:es)?|bags?|backpacks?|totes?|wallets?|belts?|caps?|hats?|sunglasses|earrings?|necklaces?|chains?|bracelets?|scarf|scarves|stoles?|dupattas?",
}
_QUALIFIERS = {"crop", "cropped", "high", "block", "skinny", "ripped", "short", "sleeveless", "graphic", "printed", "western"}
# Not garment nouns, but things people rule out ("no sleeveless", "avoid sequins").
_EXTRA_EXCLUSIONS = ["crop", "cropped", "sleeveless", "sequins?", "ripped", "distressed", "graphic", "western", "transparent", "sheer"]
_STRICT = re.compile(r"\b(only|strictly|must|exclusively|nothing but)\b")
_CHEAP = re.compile(r"\b(affordable|cheap|budget[- ]friendly|inexpensive|low[- ]cost|economical|value)\b")
_BUDGET = re.compile(r"(?:under|below|within|less than|max(?:imum)?|upto|up to|budget(?: of)?|around|about)\s*(?:rs\.?|inr|₹)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k)?\b")
_BUDGET_PLAIN = re.compile(r"(?:rs\.?|inr|₹)\s*(\d[\d,]*)\s*(k)?\b")


def _clause_negated(text: str, start: int) -> bool:
    """True when the word at ``start`` sits after a negation in the same clause ("no black", "avoid red and orange")."""
    clause_start = max(text.rfind(sep, 0, start) for sep in (",", ".", ";", " but ", " and i ", " with "))
    window = text[clause_start + 1 if clause_start >= 0 else 0:start]
    return bool(_NEGATION.search(window))


def _amount(number: str, k: Optional[str]) -> Optional[float]:
    try:
        value = float(number.replace(",", ""))
    except ValueError:
        return None
    value = value * 1000 if k else value
    return value if 100 <= value <= 200000 else None


def parse_preferences(text: str) -> Dict:
    raw = str(text or "").strip()
    lowered = " " + raw.lower() + " "
    result: Dict = {
        "colours": [], "avoid_colours": [], "styles": [], "occasion": None, "fit": None,
        "fit_by_category": {}, "fabrics": [], "garments": {}, "budget": None, "prefer_cheaper": False,
        "exclude": [], "strict": False, "required_colours": [], "understood": [],
    }
    if not raw:
        return result

    taken: List[tuple[int, int]] = []
    for synonym, name in _COLOUR_SYNONYMS:
        for match in re.finditer(rf"\b{re.escape(synonym)}\b", lowered):
            if any(a <= match.start() < b for a, b in taken):
                continue
            taken.append((match.start(), match.end()))
            target = result["avoid_colours"] if _clause_negated(lowered, match.start()) else result["colours"]
            if name not in target:
                target.append(name)
    for group, names in _COLOUR_GROUPS.items():
        for match in re.finditer(rf"\b{group}s?\b", lowered):
            target = result["avoid_colours"] if _clause_negated(lowered, match.start()) else result["colours"]
            target.extend(n for n in names if n not in target)
    result["colours"] = [c for c in result["colours"] if c not in result["avoid_colours"]]

    for pattern, style in _STYLE_WORDS:
        if re.search(rf"\b(?:{pattern})\b", lowered) and style not in result["styles"]:
            if not (style == "Casual" and "Smart Casual" in result["styles"] and "smart" in lowered):
                result["styles"].append(style)
    for pattern, occasion in _OCCASION_WORDS:
        if re.search(rf"\b(?:{pattern})\b", lowered):
            result["occasion"] = occasion
            break
    for pattern, fabric in _FABRIC_WORDS:
        if re.search(rf"\b(?:{pattern})\b", lowered) and fabric not in result["fabrics"]:
            result["fabrics"].append(fabric)

    # Garments, with a fit word just before them ("oversized tops", "straight-fit jeans").
    for category, pattern in _GARMENTS.items():
        for match in re.finditer(rf"\b({pattern})\b", lowered):
            word = match.group(1)
            if _clause_negated(lowered, match.start()):
                # "no heels", "do not recommend crop tops": a hard exclusion (the word plus its qualifier).
                before = lowered[max(0, match.start() - 14):match.start()].split()
                qualifier = before[-1] if before and before[-1] in _QUALIFIERS else ""
                phrase = f"{qualifier} {word}".strip()
                if phrase not in result["exclude"]:
                    result["exclude"].append(phrase)
                continue
            result["garments"].setdefault(category, [])
            stem = re.sub(r"(es|s)$", "", word) if word not in ("jeans", "shorts", "leggings", "sunglasses") else word
            if stem not in result["garments"][category]:
                result["garments"][category].append(stem)
            before = lowered[max(0, match.start() - 22):match.start()]
            for fit_pattern, fit in _FIT_WORDS:
                if re.search(rf"(?:{fit_pattern})[\s-]*$", before.strip() + " ", re.I) or re.search(rf"\b(?:{fit_pattern})\b", before):
                    result["fit_by_category"][category] = fit
                    break
    for fit_pattern, fit in _FIT_WORDS:
        if re.search(rf"\b(?:{fit_pattern})\b", lowered):
            result["fit"] = fit
            break

    for word in _EXTRA_EXCLUSIONS:
        for match in re.finditer(rf"\b{word}\b", lowered):
            label = word.replace("s?", "")  # "sequins?" -> "sequin" (also matches "sequinned")
            if _clause_negated(lowered, match.start()) and label not in result["exclude"]:
                result["exclude"].append(label)
    # "only", "must", "strictly": the named style / colours become requirements, not preferences.
    result["strict"] = bool(_STRICT.search(lowered))
    if result["strict"] and result["colours"]:
        result["required_colours"] = list(result["colours"])

    budget_match = _BUDGET.search(lowered) or _BUDGET_PLAIN.search(lowered)
    if budget_match:
        result["budget"] = _amount(budget_match.group(1), budget_match.group(2))
    result["prefer_cheaper"] = bool(_CHEAP.search(lowered))

    understood = result["understood"]
    if result["styles"]:
        understood.append("Style: " + ", ".join(result["styles"]))
    if result["occasion"]:
        understood.append(f"Occasion: {result['occasion']}")
    if result["colours"]:
        understood.append("Colours: " + ", ".join(result["colours"]))
    if result["avoid_colours"]:
        understood.append("Avoid: " + ", ".join(result["avoid_colours"]))
    if result["fit_by_category"]:
        understood.extend(f"{cat} fit: {fit}" for cat, fit in result["fit_by_category"].items())
    elif result["fit"]:
        understood.append(f"Fit: {result['fit']}")
    if result["garments"]:
        understood.append("Pieces: " + ", ".join(w for words in result["garments"].values() for w in words))
    if result["fabrics"]:
        understood.append("Fabric: " + ", ".join(result["fabrics"]))
    if result["exclude"]:
        understood.append("Excluded: " + ", ".join(result["exclude"]))
    if result["strict"]:
        understood.append("Treated as a requirement (\"only\")")
    if result["budget"]:
        understood.append(f"Budget: up to ₹{result['budget']:,.0f}")
    if result["prefer_cheaper"]:
        understood.append("Prefers lower prices")
    return result
