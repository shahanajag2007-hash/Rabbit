"""Brief tests 1-6: style / occasion / colour / budget are requirements, and the three outfits differ."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import recommender  # noqa: E402


def row(item_id, category, name, colour, style, occasion, price, product_type="", **extra):
    return {"item_id": item_id, "product_id": item_id, "category": category, "item_name": name, "colour": colour, "shade": "Medium",
            "style": style, "occasion": occasion, "price": price, "image": "", "product_type": product_type, "gender": "Women", **extra}


CATALOG = pd.DataFrame([
    # Traditional
    row("k1", "Top", "Maroon Cotton Kurta", "Maroon", "Ethnic|Traditional", "Festival|Traditional Event", 900),
    row("k2", "Top", "Navy Printed Kurti", "Navy", "Ethnic|Traditional", "Festival|Traditional Event", 800),
    row("k3", "Top", "Teal Anarkali Kurta", "Teal", "Ethnic|Traditional", "Festival|Traditional Event", 1100),
    row("s1", "Top", "Wine Straight Suit With Dupatta", "Burgundy", "Ethnic|Traditional", "Festival|Traditional Event", 1800, "Suit Set"),
    row("p1", "Bottom", "Cream Palazzo Pants", "Cream", "Ethnic|Traditional", "Festival|Traditional Event", 600),
    row("p2", "Bottom", "White Cotton Salwar", "White", "Ethnic|Traditional", "Festival|Traditional Event", 500),
    row("j1", "Shoes", "Gold Embroidered Juttis", "Gold", "Ethnic|Traditional", "Festival|Traditional Event", 700),
    row("j2", "Shoes", "Tan Kolhapuri Flats", "Tan", "Ethnic|Traditional", "Festival|Traditional Event", 650),
    row("a1", "Accessory", "Maroon Jhumka Earrings", "Maroon", "Ethnic|Traditional", "Festival|Traditional Event", 300),
    row("a2", "Accessory", "Gold Bangles Set", "Gold", "Ethnic|Traditional", "Festival|Traditional Event", 350),
    # Western, deliberately in the user's favourite colour
    row("w1", "Top", "Maroon Ribbed Top", "Maroon", "Trendy|Casual", "Party|College", 500),
    row("w2", "Top", "Maroon Graphic T-Shirt", "Maroon", "Casual", "College", 450),
    row("w3", "Bottom", "Maroon Mini Skirt", "Maroon", "Trendy", "Party", 600),
    row("w4", "Shoes", "Maroon Chunky Sneakers", "Maroon", "Casual|Trendy", "College", 900),
    row("w5", "Accessory", "Maroon Baseball Cap", "Maroon", "Casual", "College", 300),
    # Formal
    row("f1", "Top", "Navy Formal Shirt", "Navy", "Formal", "Office|Interview", 1200),
    row("f2", "Top", "White Oxford Shirt", "White", "Formal|Smart Casual", "Office|Interview", 1100),
    row("f3", "Top", "Navy Printed Resort Shirt", "Navy", "Casual|Trendy", "Party", 900),
    row("f4", "Bottom", "Charcoal Formal Trousers", "Charcoal", "Formal", "Office|Interview", 1400),
    row("f5", "Bottom", "Navy Slim Chinos", "Navy", "Smart Casual|Formal", "Office", 1300),
    row("f6", "Bottom", "Blue Ripped Jeans", "Blue", "Casual|Trendy", "College", 1000),
    row("f7", "Shoes", "Black Derby Formal Shoes", "Black", "Formal", "Office|Interview", 1800),
    row("f8", "Shoes", "Navy Block Heels", "Navy", "Formal|Elegant", "Office|Party", 1500),
    row("f9", "Accessory", "Silver Analog Watch", "Silver", "Formal|Minimal", "Office", 1200),
])
BASE = {"gender": "Female", "age": 24, "skin_tone": "Medium", "budget": 3000, "favorite_colours": [], "avoid_colours": []}
TRADITIONAL = {"Top": {"kurta", "ethnic_set"}, "Bottom": {"palazzo", "salwar"}, "Shoes": {"juttis", "flats", "sandals"}, "Accessory": {"earrings", "bangles"}}


def outfits(profile, limit=3):
    return recommender.recommend_with_notes(CATALOG, {**BASE, **profile}, limit=limit)


def test_1_traditional_festival_maroon_within_budget():
    result, notes = outfits({"style": "Traditional", "occasion": "Festival", "favorite_colours": ["Maroon"], "budget": 3000})
    assert result, notes
    for outfit in result:
        assert outfit["total_price"] <= 3000
        for category, item in outfit["items"].items():
            assert recommender.item_subcategory(item) in TRADITIONAL[category], item["item_name"]
            assert not item["item_id"].startswith("w"), f"western item {item['item_name']}"
    assert result[0]["items"]["Top"]["colour"] in ("Maroon", "Burgundy")  # favourite colour prioritised


def test_2_formal_office_navy_excludes_casual():
    result, _ = outfits({"style": "Formal", "occasion": "Office", "favorite_colours": ["Navy"], "budget": 6000})
    assert result
    for outfit in result:
        names = [i["item_name"] for i in outfit["items"].values()]
        assert not any(word in " ".join(names) for word in ("Resort", "Ripped", "Graphic", "Sneakers", "Cap")), names
    assert result[0]["items"]["Top"]["colour"] == "Navy"


def test_3_explicit_exclusion_in_text():
    result, _ = outfits({"style": "Casual", "occasion": "College", "preference_text": "Traditional clothing only. Do not recommend crop tops."})
    assert result
    for outfit in result:
        for item in outfit["items"].values():
            assert "crop" not in item["item_name"].lower()
            assert not item["item_id"].startswith(("w", "f"))


def test_4_colour_change_changes_results_but_keeps_style():
    maroon, _ = outfits({"style": "Traditional", "occasion": "Festival", "favorite_colours": ["Maroon"]})
    navy, _ = outfits({"style": "Traditional", "occasion": "Festival", "favorite_colours": ["Navy"]})
    assert maroon[0]["items"]["Top"]["item_id"] != navy[0]["items"]["Top"]["item_id"]
    assert navy[0]["items"]["Top"]["colour"] == "Navy"
    for outfit in navy:
        assert all(not i["item_id"].startswith("w") for i in outfit["items"].values())


def test_5_budget_reduction():
    roomy, _ = outfits({"style": "Traditional", "occasion": "Festival", "budget": 4000})
    tight, notes = outfits({"style": "Traditional", "occasion": "Festival", "budget": 2400})
    assert tight and all(o["total_price"] <= 2400 and not o.get("over_budget") for o in tight)
    assert max(o["total_price"] for o in tight) <= max(o["total_price"] for o in roomy)
    impossible, notes = outfits({"style": "Traditional", "occasion": "Festival", "budget": 1000})
    assert all(o.get("over_budget") for o in impossible) and any("budget" in n for n in notes)


def test_6_three_distinct_traditional_outfits():
    result, _ = outfits({"style": "Traditional", "occasion": "Festival", "budget": 4000})
    assert len(result) == 3
    keys = {frozenset(i["item_id"] for i in o["items"].values()) for o in result}
    assert len(keys) == 3
    tops = [o["items"]["Top"]["item_id"] for o in result]
    assert len(set(tops)) >= 2, tops  # meaningfully different, not just a different accessory


def test_missing_category_is_explained_not_relaxed():
    no_ethnic_shoes = CATALOG[~CATALOG["item_id"].isin(["j1", "j2", "f8"])]  # juttis, flats and the block heels
    result, notes = recommender.recommend_with_notes(no_ethnic_shoes, {**BASE, "style": "Traditional", "occasion": "Festival"})
    assert result == []
    assert any("no traditional shoes" in n for n in notes)


def test_full_outfit_sets_take_no_bottom():
    result, _ = outfits({"style": "Traditional", "occasion": "Festival", "budget": 4000, "favorite_colours": ["Burgundy"]})
    sets = [o for o in result if o["items"]["Top"]["item_id"] == "s1"]
    assert sets and all("Bottom" not in o["items"] for o in sets)
