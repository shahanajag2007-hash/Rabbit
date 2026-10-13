from __future__ import annotations

from itertools import product
from pathlib import Path
import re
from typing import Dict, Iterable, Optional

import pandas as pd

from skin_tone import suggested_palette


CATEGORIES = ("Top", "Bottom", "Shoes", "Accessory")
WEIGHTS = {"colour": 30, "style": 20, "occasion": 20, "compatibility": 15, "budget": 15}
OCCASION_STYLES = {
    "College": {"Casual", "Smart Casual"},
    "Office": {"Formal", "Smart Casual"},
    "Interview": {"Formal"},
    "Party": {"Trendy", "Smart Casual"},
    "Festival": {"Ethnic"},
}


def load_dataset(path: Optional[Path] = None) -> pd.DataFrame:
    csv_path = path or Path(__file__).parent / "data" / "fashion_dataset.csv"
    frame = pd.read_csv(csv_path)
    frame["price"] = pd.to_numeric(frame["price"], errors="raise")
    required = {"item_id", "category", "item_name", "colour", "shade", "style", "occasion", "price", "image"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    return frame


def _matches(value: str, requested: str) -> bool:
    return requested.lower() in {part.strip().lower() for part in re.split(r"[|,]", str(value))}


def _style_matches_occasion(item: pd.Series, style: str, occasion: str) -> bool:
    allowed_styles = OCCASION_STYLES.get(occasion, {style})
    return any(_matches(item["style"], allowed_style) for allowed_style in allowed_styles)


def _colour_score(item: pd.Series, palette: Iterable[str], favorite: Iterable[str] = None, avoid: Iterable[str] = None) -> float:
    colours = {str(item["colour"]).lower(), str(item["shade"]).lower()}
    preferred = {colour.lower() for colour in palette}
    favorite_set = {colour.lower() for colour in (favorite or [])}
    avoid_set = {colour.lower() for colour in (avoid or [])}
    
    if colours & avoid_set:
        return 0.0 # Strongly penalize avoided colours
    
    score = 16.0
    if colours & preferred:
        score += 14.0
    if colours & favorite_set:
        score += 5.0
    return min(30.0, score)


def _item_score(item: pd.Series, style: str, occasion: str, palette: Iterable[str], budget_share: float, favorite: Iterable[str] = None, avoid: Iterable[str] = None) -> Dict[str, float]:
    colour = _colour_score(item, palette, favorite, avoid)
    style_score = 20.0 if _matches(item["style"], style) and _style_matches_occasion(item, style, occasion) else 9.0
    occasion_score = 20.0 if _matches(item["occasion"], occasion) else 8.0
    budget_score = 15.0 if float(item["price"]) <= budget_share else max(0.0, 15.0 - (float(item["price"]) - budget_share) / max(budget_share, 1) * 15)
    return {"colour": colour, "style": style_score, "occasion": occasion_score, "budget": budget_score}


def _compatibility_score(items: Dict[str, pd.Series], palette: Iterable[str]) -> float:
    colours = [str(item["colour"]).lower() for item in items.values()]
    palette_lower = {colour.lower() for colour in palette}
    preferred_count = sum(colour in palette_lower for colour in colours)
    unique_count = len(set(colours))
    return min(15.0, 7.0 + preferred_count * 2.0 + (2.0 if unique_count >= 2 else 0.0))


def _score_outfit(items: Dict[str, pd.Series], style: str, occasion: str, budget: float, palette: Iterable[str], favorite: Iterable[str] = None, avoid: Iterable[str] = None) -> tuple[float, Dict[str, float]]:
    share = budget / 4
    component_totals = {key: 0.0 for key in WEIGHTS}
    for item in items.values():
        scores = _item_score(item, style, occasion, palette, share, favorite, avoid)
        for key, value in scores.items():
            component_totals[key] += value / 4
    component_totals["compatibility"] = _compatibility_score(items, palette)
    total_price = sum(float(item["price"]) for item in items.values())
    component_totals["budget"] = 15.0 if total_price <= budget else max(0.0, 15.0 - (total_price - budget) / max(budget, 1) * 15)
    total = sum(component_totals.values())
    return round(total, 2), {key: round(value, 2) for key, value in component_totals.items()}


def score_single_outfit(outfit: Dict, user_profile: Dict) -> Dict:
    style = user_profile.get("style", "Casual")
    occasion = user_profile.get("occasion", "College")
    budget = float(user_profile.get("budget", 3500.0))
    tone = user_profile.get("skin_tone")
    favorite = user_profile.get("favorite_colours", [])
    avoid = user_profile.get("avoid_colours", [])
    items = _as_item_map(outfit)
    score, breakdown = _score_outfit(items, style, occasion, budget, suggested_palette(tone) if tone else [], favorite, avoid)
    total_price = sum(float(item["price"]) for item in items.values())
    return {"score": score, "breakdown": breakdown, "total_price": round(total_price, 2)}


def _as_item_map(outfit: Optional[Dict]) -> Dict[str, pd.Series]:
    if not outfit:
        return {}
    return {category: pd.Series(item) for category, item in outfit.get("items", {}).items()}


def recommend_outfits(
    frame: pd.DataFrame,
    user_profile: Dict,
    locked_items: Optional[Dict[str, Dict]] = None,
    exclude_signatures: Optional[set[tuple]] = None,
    limit: int = 3,
) -> list[Dict]:
    style = user_profile.get("style", "Casual")
    occasion = user_profile.get("occasion", "College")
    budget = float(user_profile.get("budget", 3500.0))
    tone = user_profile.get("skin_tone")
    favorite = user_profile.get("favorite_colours", [])
    avoid = user_profile.get("avoid_colours", [])

    palette = suggested_palette(tone) if tone else []
    locked_items = locked_items or {}
    exclude_signatures = exclude_signatures or set()
    choices = {}
    for category in CATEGORIES:
        if category in locked_items:
            choices[category] = [pd.Series(locked_items[category])]
        else:
            category_rows = frame[frame["category"].str.lower() == category.lower()].copy()
            if category_rows.empty:
                # Fallback if category missing
                choices[category] = [pd.Series({"item_id": f"missing_{category}", "category": category, "price": 0, "colour": "", "style": "", "occasion": "", "item_name": "Placeholder"})]
                continue
                
            category_rows["preference"] = category_rows.apply(
                lambda row: _item_score(row, style, occasion, palette, budget / 4, favorite, avoid)["colour"]
                + _item_score(row, style, occasion, palette, budget / 4, favorite, avoid)["style"], axis=1
            )
            choices[category] = [row for _, row in category_rows.sort_values("preference", ascending=False).head(12).iterrows()]

    results = []
    for selected in product(*(choices[category] for category in CATEGORIES)):
        items = dict(zip(CATEGORIES, selected))
        total_price = sum(float(item["price"]) for item in items.values())
        if total_price > budget:
            continue
        signature = tuple(str(items[category]["item_id"]) for category in CATEGORIES)
        if signature in exclude_signatures:
            continue
        score, breakdown = _score_outfit(items, style, occasion, budget, palette, favorite, avoid)
        results.append({
            "signature": signature,
            "items": {category: item.to_dict() for category, item in items.items()},
            "score": score,
            "total_price": round(total_price, 2),
            "breakdown": breakdown,
            "palette": palette,
        })
    results.sort(key=lambda outfit: (-outfit["score"], outfit["total_price"]))
    
    # Filter for diversity: ensure successive outfits differ by at least 2 items if possible
    diverse_results = []
    for outfit in results:
        if not diverse_results:
            diverse_results.append(outfit)
            continue
        
        # Check against already selected diverse outfits
        is_diverse = True
        for selected_outfit in diverse_results:
            diff_count = sum(1 for a, b in zip(outfit["signature"], selected_outfit["signature"]) if a != b)
            # Require at least 2 items to be different (unless locked items force otherwise)
            min_diff = max(1, min(2, len(CATEGORIES) - len(locked_items)))
            if diff_count < min_diff:
                is_diverse = False
                break
                
        if is_diverse:
            diverse_results.append(outfit)
            if len(diverse_results) >= limit:
                break
                
    # Fallback if we filtered out too many and don't have enough
    if len(diverse_results) < limit:
        for outfit in results:
            if outfit not in diverse_results:
                diverse_results.append(outfit)
            if len(diverse_results) >= limit:
                break
    
    # Fallback if all over budget
    if not diverse_results:
        # Return cheapest possible combinations ignoring budget
        fallback_results = []
        for selected in product(*(choices[category][:2] for category in CATEGORIES)):
            items = dict(zip(CATEGORIES, selected))
            total_price = sum(float(item["price"]) for item in items.values())
            signature = tuple(str(items[category]["item_id"]) for category in CATEGORIES)
            score, breakdown = _score_outfit(items, style, occasion, budget, palette, favorite, avoid)
            fallback_results.append({
                "signature": signature,
                "items": {category: item.to_dict() for category, item in items.items()},
                "score": score,
                "total_price": round(total_price, 2),
                "breakdown": breakdown,
                "palette": palette,
            })
        fallback_results.sort(key=lambda outfit: outfit["total_price"])
        diverse_results = fallback_results[:limit]

    return diverse_results


def replacement_candidates(
    frame: pd.DataFrame,
    category: str,
    outfit: Dict,
    user_profile: Dict,
) -> list[Dict]:
    current = _as_item_map(outfit)
    locked = current.copy()
    locked.pop(category, None)
    current_item = current.get(category, {})
    if isinstance(current_item, pd.Series):
        current_item_id = str(current_item.get("item_id", ""))
    elif isinstance(current_item, dict):
        current_item_id = str(current_item.get("item_id", ""))
    else:
        current_item_id = ""
    candidates = recommend_outfits(frame, user_profile, locked_items={key: item.to_dict() for key, item in locked.items()}, limit=60)
    return [candidate for candidate in candidates if str(candidate["items"][category]["item_id"]) != current_item_id]


def cheaper_alternative(frame: pd.DataFrame, item: Dict) -> Optional[Dict]:
    candidates = frame[(frame["category"] == item["category"]) & (frame["price"] < float(item["price"]))].copy()
    if candidates.empty:
        return None
    same_colour = candidates[candidates["colour"].str.lower() == str(item["colour"]).lower()]
    chosen = (same_colour if not same_colour.empty else candidates).sort_values("price", ascending=False).iloc[0]
    return chosen.to_dict()


def get_replacement_candidates(frame: pd.DataFrame, category: str, outfit: Dict, user_profile: Dict) -> list[Dict]:
    return replacement_candidates(frame, category, outfit, user_profile)


def get_cheaper_alternative(frame: pd.DataFrame, item: Dict) -> Optional[Dict]:
    return cheaper_alternative(frame, item)
