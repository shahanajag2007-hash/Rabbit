"""Acceptance tests for personalisation: every profile / Appearance / text input changes the results.

A small controlled catalogue is used so each test can show a specific input making a difference.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import recommender  # noqa: E402
from preferences import parse_preferences  # noqa: E402


def row(item_id, category, name, colour, style, occasion, price, **extra):
    return {"item_id": item_id, "category": category, "item_name": name, "colour": colour,
            "shade": recommender.COLOUR_HEX and "Medium", "style": style, "occasion": occasion,
            "price": price, "image": "", **extra}


CATALOG = pd.DataFrame([
    row("t-navy-formal", "Top", "Navy Formal Shirt", "Navy", "Formal|Smart Casual", "Office|Interview", 1400, fit="Slim / Fitted"),
    row("t-white-formal", "Top", "White Formal Shirt", "White", "Formal", "Office|Interview", 1200, fit="Regular Fit"),
    row("t-olive-tee", "Top", "Olive Oversized T-Shirt", "Olive", "Casual|Trendy|Streetwear", "College|Party|Casual Outing", 700, fit="Loose / Oversized"),
    row("t-teal-kurta", "Top", "Teal Cotton Kurta", "Teal", "Ethnic|Traditional", "Festival|Traditional Event", 1100, fabric="Cotton Blend"),
    row("t-pink-crop", "Top", "Pink Crop Top", "Pink", "Trendy", "Party", 600),
    row("t-black-tee", "Top", "Black Basic Tee", "Black", "Casual|Minimal", "College|Casual Outing", 500, fit="Regular Fit"),
    row("t-red-tee", "Top", "Red Graphic Tee", "Red", "Casual|Trendy", "College|Party", 650),
    row("b-black-trousers", "Bottom", "Black Formal Trousers", "Black", "Formal", "Office|Interview", 1500),
    row("b-blue-jeans", "Bottom", "Blue Straight Fit Jeans", "Blue", "Casual|Trendy", "College|Party", 1300, fit="Regular Fit"),
    row("b-beige-chinos", "Bottom", "Beige Chinos", "Beige", "Smart Casual", "Office|Party", 1200),
    row("b-cream-palazzo", "Bottom", "Cream Palazzo Pants", "Cream", "Ethnic|Traditional", "Festival|Traditional Event", 900),
    row("b-green-joggers", "Bottom", "Green Joggers", "Green", "Casual", "College", 600),
    row("s-black-formal", "Shoes", "Black Formal Derby Shoes", "Black", "Formal", "Office|Interview", 2000),
    row("s-white-sneakers", "Shoes", "White Sneakers", "White", "Casual|Trendy", "College|Party", 1000),
    row("s-tan-juttis", "Shoes", "Tan Juttis", "Tan", "Ethnic|Traditional", "Festival|Traditional Event", 800),
    row("s-grey-slides", "Shoes", "Grey Sliders", "Grey", "Casual", "College", 300),
    row("a-silver-watch", "Accessory", "Silver Watch", "Silver", "Formal|Minimal", "Office|Interview", 1500),
    row("a-black-cap", "Accessory", "Black Cap", "Black", "Casual|Streetwear", "College|Casual Outing", 400),
    row("a-gold-earrings", "Accessory", "Gold Jhumka Earrings", "Gold", "Ethnic|Traditional", "Festival|Traditional Event", 500),
    row("a-navy-tie", "Accessory", "Navy Tie", "Navy", "Formal", "Office|Interview", 350),
])

BASE = {"gender": "Female", "age": 22, "height": 165, "weight": 58, "skin_tone": "Medium", "style": "Casual",
        "occasion": "College", "budget": 5000, "favorite_colours": [], "avoid_colours": []}


def top_items(profile, limit=3):
    outfits, notes = recommender.recommend_with_notes(CATALOG, {**BASE, **profile}, limit=limit)
    return outfits, notes


def first(profile, category="Top"):
    return top_items(profile)[0][0]["items"][category]["item_id"]


# Test A - age
def test_minors_never_get_adult_items_and_age_changes_ranking():
    teen = [o["items"]["Top"]["item_id"] for o in top_items({"age": 14, "style": "Trendy", "occasion": "Party"}, limit=10)[0]]
    adult = [o["items"]["Top"]["item_id"] for o in top_items({"age": 30, "style": "Trendy", "occasion": "Party"}, limit=10)[0]]
    assert "t-pink-crop" not in teen
    assert "t-pink-crop" in adult


# Test B - budget and profile
def test_budget_is_a_hard_limit_and_explained_when_impossible():
    outfits, _ = top_items({"budget": 2500})
    assert outfits and all(o["total_price"] <= 2500 for o in outfits)
    outfits, notes = top_items({"budget": 1000})
    assert outfits[0].get("over_budget") is True
    assert any("fits your ₹1,000 budget" in n for n in notes)


# Test C - the four Appearance fields
def test_each_appearance_field_changes_results():
    assert first({"style": "Formal", "occasion": "Office"}) in {"t-navy-formal", "t-white-formal"}
    assert first({"style": "Traditional", "occasion": "Traditional Event"}) == "t-teal-kurta"
    assert first({"style": "Casual", "occasion": "College"}) != first({"style": "Formal", "occasion": "Office"})
    # Favourite colours
    assert first({"favorite_colours": ["Red"]}) == "t-red-tee"
    # Skin tone palette (Medium palette has Olive, Tan palette has Olive too, Deep palette has White/Coral)
    medium = recommender.score_single_outfit({"items": {"Top": CATALOG.iloc[2].to_dict()}}, {**BASE, "skin_tone": "Medium"})
    deep = recommender.score_single_outfit({"items": {"Top": CATALOG.iloc[2].to_dict()}}, {**BASE, "skin_tone": "Deep"})
    assert medium["breakdown"]["colour"] > deep["breakdown"]["colour"]
    # Occasion alone
    assert first({"occasion": "Office"}) != first({"occasion": "Traditional Event"})


def test_fine_tune_signals_are_used():
    loose = recommender.score_single_outfit({"items": {"Top": CATALOG.iloc[2].to_dict()}}, {**BASE, "preferred_fit": "Loose / Oversized"})
    slim = recommender.score_single_outfit({"items": {"Top": CATALOG.iloc[2].to_dict()}}, {**BASE, "preferred_fit": "Slim / Fitted"})
    assert loose["breakdown"]["style"] > slim["breakdown"]["style"]
    bright = recommender.score_single_outfit({"items": {"Top": CATALOG.iloc[6].to_dict()}}, {**BASE, "avoid_colours": ["Overly Bright"]})
    plain = recommender.score_single_outfit({"items": {"Top": CATALOG.iloc[6].to_dict()}}, BASE)
    assert bright["breakdown"]["colour"] < plain["breakdown"]["colour"]


# Test D - manual text
def test_formal_navy_request():
    outfits, _ = top_items({"preference_text": "Suggest a formal outfit in navy blue for the office"})
    items = outfits[0]["items"]
    assert items["Top"]["item_id"] == "t-navy-formal"
    assert any("Navy" in r for r in outfits[0]["reasons"])


def test_text_negation_and_budget():
    outfits, notes = top_items({"preference_text": "casual college look, no black, under 3000"})
    for outfit in outfits:
        assert all(item["colour"] != "Black" for item in outfit["items"].values())
        assert outfit["total_price"] <= 3000
    assert any("₹3,000" in n for n in notes)


def test_parser_examples():
    assert parse_preferences("I like oversized tops with straight-fit jeans.")["fit_by_category"] == {"Top": "Loose / Oversized", "Bottom": "Regular Fit"}
    assert parse_preferences("Show me an affordable party outfit.")["prefer_cheaper"] is True
    assert parse_preferences("Give me a traditional outfit within my budget.")["styles"] == ["Traditional"]


# Test E - palette pick
def test_palette_colour_changes_recommendations():
    assert first({"palette_colour": "Olive"}) == "t-olive-tee"
    palette = recommender.colour_palette(CATALOG, BASE)
    assert palette["swatches"] and all(s["count"] > 0 for s in palette["swatches"])


# Test F - builder
def test_builder_respects_remaining_budget_and_matches_top():
    picked = CATALOG.set_index("item_id").loc["t-navy-formal"].to_dict() | {"item_id": "t-navy-formal"}
    step = recommender.builder_options(CATALOG, {**BASE, "budget": 3000, "style": "Formal", "occasion": "Office"}, "Bottom", {"Top": picked})
    assert step["remaining_budget"] == 1600
    assert all(item["price"] <= 1600 for item in step["items"])
    assert step["items"][0]["item_id"] in {"b-black-trousers", "b-beige-chinos"}


# Tests I, J, K - replace, cheaper, lock
def test_replace_keeps_other_items_and_lock_survives_regeneration():
    outfit = top_items({})[0][0]
    candidates = recommender.replacement_candidates(CATALOG, "Top", outfit, {**BASE})
    assert candidates
    for candidate in candidates:
        for category in ("Bottom", "Shoes", "Accessory"):
            assert candidate["items"][category]["item_id"] == outfit["items"][category]["item_id"]
        assert candidate["items"]["Top"]["item_id"] != outfit["items"]["Top"]["item_id"]
    locked = {"Shoes": outfit["items"]["Shoes"]}
    for regenerated in recommender.recommend_outfits(CATALOG, BASE, locked_items=locked, limit=3):
        assert regenerated["items"]["Shoes"]["item_id"] == outfit["items"]["Shoes"]["item_id"]


def test_cheaper_option_is_strictly_cheaper():
    item = CATALOG.set_index("item_id").loc["s-black-formal"].to_dict() | {"item_id": "s-black-formal"}
    cheaper = recommender.cheaper_alternative(CATALOG, item, BASE, {"items": {"Shoes": item}})
    assert cheaper is not None and cheaper["price"] < item["price"]
    cheapest = CATALOG.set_index("item_id").loc["s-grey-slides"].to_dict() | {"item_id": "s-grey-slides"}
    assert recommender.cheaper_alternative(CATALOG, cheapest, BASE) is None


def test_size_hint_is_labelled_approximate():
    hint = recommender.size_hint("Female", 165, 58)
    assert hint["size"] == "M" and "Brand size charts differ" in hint["note"]
