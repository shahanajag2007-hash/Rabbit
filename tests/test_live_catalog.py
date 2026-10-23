"""Offline tests for the live brand-store catalogue (no network: the fetcher is faked)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import recommender  # noqa: E402
from live_catalog import Brand, LiveCatalog, normalize_product  # noqa: E402
from live_catalog.fetcher import FetchError  # noqa: E402
from live_catalog.normalize import canonical_colour, classify_category  # noqa: E402
from shopping import ShoppingService  # noqa: E402


def product(pid, title, product_type="", tags=(), variants=None, options=None, body=""):
    return {
        "id": pid,
        "title": title,
        "handle": f"p-{pid}",
        "product_type": product_type,
        "tags": list(tags),
        "body_html": body,
        "options": options or [{"name": "Size", "position": 1}],
        "variants": variants or [{"id": pid * 10, "price": "999.00", "available": True, "option1": "M"}],
        "images": [{"src": f"https://cdn.shopify.com/{pid}.jpg", "variant_ids": []}],
        "updated_at": "2026-10-23T10:00:00+05:30",
    }


CATALOG_PRODUCTS = [
    product(1, "Navy Oxford Shirt", "Shirts", ["Men", "Formal"], body="<b>Material</b>: 100% Cotton"),
    product(2, "Black Slim Chinos", "Trousers", ["Men"]),
    product(3, "White Leather Sneakers", "Sneakers", ["Men"]),
    product(4, "Brown Leather Belt", "Belts", ["Men"]),
    product(5, "Teal Kurta For Women", "Kurta", ["Women"]),
    product(6, "Cream Palazzo Pants", "Bottoms", ["Women"]),
    product(7, "Tan Block Heels", "Heels", ["Women"]),
    product(8, "Gold Jhumka Earrings", "Jewellery", ["Women"]),
    product(9, "White Cotton Shirt", "Shirts", ["Men"]),
    product(10, "Grey Linen Trousers", "Trousers", ["Men"], body="Fabric - Pure Linen"),
]


class FakeFetcher:
    calls = 0

    def __init__(self):
        pass

    def get_json(self, domain, path):
        FakeFetcher.calls += 1
        if domain == "down.example.com":
            raise FetchError("HTTP 429 after 4 attempts")
        return {"products": CATALOG_PRODUCTS if "page=1" in path else []}


def make_catalog(tmp_path, brands=None, fallback=recommender.load_dataset):
    brands = brands or [Brand("demo", "Demo", "demo.example.com")]
    catalog = LiveCatalog(snapshot_path=tmp_path / "snap.json", brands=brands, ttl_hours=6,
                          fallback_loader=fallback, fetcher_factory=FakeFetcher)
    return catalog


def test_category_uses_head_noun_and_skips_non_outfit_items():
    assert classify_category("Denim Jacket", "") == "Top"
    assert classify_category("Tie-Dye Oversized T-Shirt", "") == "Top"
    assert classify_category("Leather Belt", "") == "Accessory"
    assert classify_category("Relaxed Fit Cargo Pants", "") == "Bottom"
    assert classify_category("Chunky Sneakers", "Footwear") == "Shoes"
    assert classify_category("Floral Maxi Dress", "Dresses") is None
    assert classify_category("Kurta Set With Dupatta", "Kurta Sets") is None
    assert classify_category("Cotton Trunks Pack of 3", "Innerwear") is None


def test_colour_normalisation():
    assert canonical_colour("Navy Blue") == "Navy"
    assert canonical_colour("Off White / M") == "Off-White"
    assert canonical_colour("Wine") == "Burgundy"
    assert canonical_colour("Sky Blue") == "Blue"
    assert canonical_colour("Size M") is None


def test_normalize_splits_colours_and_skips_out_of_stock():
    raw = product(
        42, "Classic Polo T-Shirt", "Polos", ["Men", "Casual Wear"],
        options=[{"name": "Color", "position": 1}, {"name": "Size", "position": 2}],
        variants=[
            {"id": 1, "price": "899.00", "compare_at_price": "1299.00", "available": True, "option1": "Navy Blue", "option2": "M"},
            {"id": 2, "price": "899.00", "available": True, "option1": "Navy Blue", "option2": "L"},
            {"id": 3, "price": "799.00", "available": True, "option1": "Olive", "option2": "M"},
            {"id": 4, "price": "799.00", "available": False, "option1": "Red", "option2": "M"},
        ],
    )
    rows = normalize_product(raw, "demo", "Demo", "demo.example.com", None)
    assert {row["colour"] for row in rows} == {"Navy", "Olive"}
    navy = next(row for row in rows if row["colour"] == "Navy")
    assert navy["category"] == "Top"
    assert navy["price"] == 899.0 and navy["mrp"] == 1299.0
    assert navy["shade"] == "Dark"
    assert navy["gender"] == "Men"
    assert navy["item_name"].startswith("Demo Classic Polo")
    assert navy["product_url"].startswith("https://demo.example.com/products/p-42")
    assert navy["image"].startswith("https://") and "width=" in navy["image"]
    assert "Smart Casual" in navy["style"].split("|")
    assert set(recommender.load_dataset().columns) <= set(navy)  # same schema as the CSV


def test_fabric_maps_to_fabric_note_keys():
    rows = normalize_product(CATALOG_PRODUCTS[9], "demo", "Demo", "demo.example.com", "Men")
    assert rows[0]["fabric"] == "Linen" and rows[0]["fabric_tag"] == "Pure Linen"


def test_static_fallback_until_first_scrape(tmp_path):
    catalog = make_catalog(tmp_path)
    assert catalog.source() == "static-fallback"
    assert len(catalog.frame()) == 50
    catalog.refresh()
    assert catalog.source() == "live"
    frame = catalog.frame()
    assert set(frame["category"]) == {"Top", "Bottom", "Shoes", "Accessory"}
    assert (tmp_path / "snap.json").exists()
    # A new instance loads the saved snapshot without scraping.
    assert make_catalog(tmp_path).source() == "live"


def test_failed_brand_keeps_previous_items(tmp_path):
    good = Brand("demo", "Demo", "demo.example.com")
    catalog = make_catalog(tmp_path, brands=[good])
    catalog.refresh()
    before = len(catalog.frame())
    flaky = LiveCatalog(snapshot_path=tmp_path / "snap.json",
                        brands=[Brand("demo", "Demo", "down.example.com")],
                        fallback_loader=recommender.load_dataset, fetcher_factory=FakeFetcher)
    status = flaky.refresh()
    assert status["brands"]["demo"]["error"].startswith("HTTP 429")
    assert len(flaky.frame()) == before


def test_gender_filter(tmp_path):
    catalog = make_catalog(tmp_path)
    catalog.refresh()
    women = catalog.frame_for("Female")
    men = catalog.frame_for("Male")
    assert set(women["gender"]) <= {"Women", "Unisex"}
    assert set(men["gender"]) <= {"Men", "Unisex"}
    assert len(catalog.frame_for("Non-binary")) == len(catalog.frame())


def test_recommender_runs_on_live_rows(tmp_path):
    catalog = make_catalog(tmp_path)
    catalog.refresh()
    profile = {"gender": "Male", "skin_tone": "Medium", "style": "Formal", "occasion": "Office", "budget": 6000}
    outfits = recommender.recommend_outfits(catalog.frame_for("Male"), profile, limit=2)
    assert outfits
    assert outfits[0]["items"]["Top"]["brand"] == "Demo"
    assert outfits[0]["items"]["Top"]["product_url"]


def test_brand_store_cheaper_alternative(tmp_path):
    catalog = make_catalog(tmp_path)
    catalog.refresh()
    expensive_shirt = {"category": "Top", "item_name": "White Formal Shirt", "colour": "White",
                       "style": "Formal", "occasion": "Office", "price": 2500, "gender": "Men"}
    outfit = {"items": {"Top": expensive_shirt}}
    alternatives = ShoppingService(catalog_frame=catalog.frame).find_cheaper_alternatives(outfit, 1500, [])
    top = alternatives["Top"]
    assert top["platform"] == "Demo"
    assert top["price"] < 2500 and top["url"].startswith("https://demo.example.com/products/")
    assert "Shirt" in top["product_name"]


def test_fabric_ignores_non_fibre_text():
    from live_catalog.normalize import extract_fabric

    assert extract_fabric("<p>Material: 60% Cotton 40% Polyester</p>", [], "Tee") == ("Cotton Blend", "60% Cotton 40% Polyester")
    assert extract_fabric("<p>Material: Sole - EVA</p>", ["5% All"], "Sliders") == (None, None)
    assert extract_fabric("<p>Fabric: Thoughtfully selected to balance comfort, structure and flexibility</p>", [], "Jacket") == (None, None)


def test_title_gender_beats_tags_and_taglines_are_trimmed():
    raw = product(77, "AZURA Navy Women's Sneakers | Lightweight Everyday Comfort", "Sneakers", ["Men", "Women"])
    row = normalize_product(raw, "demo", "Demo", "demo.example.com", None)[0]
    assert row["gender"] == "Women"
    assert row["item_name"] == "Demo AZURA Navy Women's Sneakers"


def test_revealing_tops_are_skipped():
    assert classify_category("Red Halter Knit Top", "Tops") is None


def test_product_type_added_when_title_has_no_garment_word():
    row = normalize_product(product(88, "Utopia", "Caps", ["Black"]), "demo", "Demo", "demo.example.com", None)[0]
    assert row["item_name"] == "Demo Utopia Cap"


def test_only_due_brands_are_refreshed(tmp_path):
    from live_catalog import catalog as catalog_module

    good, down = Brand("demo", "Demo", "demo.example.com"), Brand("down", "Down", "down.example.com")
    catalog = make_catalog(tmp_path, brands=[good, down])
    assert catalog.due_brands() == [good, down]  # never scraped
    catalog.refresh()
    assert catalog.due_brands() == []  # demo is fresh; down failed just now (retried after RETRY_MINUTES)
    catalog._snapshot["brands"]["down"]["failed_at"] = "2000-01-01T00:00:00+00:00"
    assert catalog.due_brands() == [down]
    catalog._snapshot["brands"]["demo"]["fetched_at"] = "2000-01-01T00:00:00+00:00"
    assert catalog.due_brands() == [good, down]
    assert catalog_module.RETRY_MINUTES > 0
