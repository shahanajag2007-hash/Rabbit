"""Products imported from authorized feeds (affiliate exports, retailer feeds, partner CSVs).

Marketplaces such as Amazon, Flipkart, Myntra and AJIO do not allow scraping; their products can
only come in through their affiliate / partner programmes. Put such exports in ``data/imports/`` as
JSON or CSV in the schema below and they join the catalogue next to the scraped brand stores.

JSON: {"source": "Amazon Associates export", "retrieved_at": "2026-10-24T10:00:00+00:00", "products": [ ... ]}
CSV:  one product per row with the same column names (``source`` / ``retrieved_at`` columns optional).

Required per product: id, name, category (Top / Bottom / Shoes / Accessory), colour, price (INR),
image_url, product_url, retailer. Optional: gender (Men / Women / Unisex), style (e.g. "Ethnic|Casual"),
occasion, sizes ("S|M|L"), available_sizes, fabric, link_type ("product" for a verified product page,
"search" for a retailer search page), mrp.

Rows with a missing field, a non-positive price or a non-https link are skipped (and counted), never
guessed. Nothing here is fetched from the network.
"""
from __future__ import annotations

import csv
import json
import logging
import urllib.parse
from pathlib import Path
from typing import Dict, List, Tuple

from .normalize import canonical_colour, shade_for

logger = logging.getLogger("styleai.live_catalog")

REQUIRED = ("id", "name", "category", "colour", "price", "image_url", "product_url", "retailer")
CATEGORIES = {"top": "Top", "bottom": "Bottom", "shoes": "Shoes", "accessory": "Accessory"}


def _https(url: str) -> bool:
    parsed = urllib.parse.urlparse(str(url or ""))
    return parsed.scheme == "https" and bool(parsed.hostname)


def _split(value) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value or "").replace(",", "|").split("|") if part.strip()]


def normalize_import(product: Dict, source: str, retrieved_at: str | None) -> Dict | None:
    if any(not str(product.get(key) or "").strip() for key in REQUIRED):
        return None
    category = CATEGORIES.get(str(product["category"]).strip().lower())
    try:
        price = float(product["price"])
    except (TypeError, ValueError):
        return None
    if not category or price <= 0 or not _https(product["product_url"]) or not _https(product["image_url"]):
        return None
    colour = canonical_colour(str(product["colour"])) or str(product["colour"]).title()
    sizes = _split(product.get("sizes"))
    retailer = str(product["retailer"]).strip()
    link_type = str(product.get("link_type") or "product").lower()
    return {
        "item_id": f"import-{str(product['id']).strip()}",
        "product_id": f"import-{str(product['id']).strip()}",
        "category": category,
        "item_name": str(product["name"]).strip(),
        "colour": colour,
        "colour_label": str(product["colour"]).strip().title(),
        "shade": shade_for(colour),
        "style": "|".join(_split(product.get("style"))) or "Casual",
        "occasion": "|".join(_split(product.get("occasion"))) or "Casual Outing",
        "price": round(price, 2),
        "mrp": float(product["mrp"]) if str(product.get("mrp") or "").strip() else None,
        "image": str(product["image_url"]).strip(),
        "brand": retailer,
        "gender": str(product.get("gender") or "Unisex").strip().title(),
        "product_url": str(product["product_url"]).strip(),
        "link_type": "search" if link_type == "search" else "product",
        "sizes": sizes,
        "available_sizes": _split(product.get("available_sizes")) or sizes,
        "fabric": str(product.get("fabric") or "").strip() or None,
        "fabric_tag": str(product.get("fabric") or "").strip() or None,
        "product_type": str(product.get("subcategory") or "").strip(),
        "source": source,
        "price_checked_at": retrieved_at,
    }


def load_imports(directory: Path) -> Tuple[List[Dict], Dict[str, Dict]]:
    """(rows, per-file report) for every JSON / CSV file in ``directory``."""
    rows: List[Dict] = []
    report: Dict[str, Dict] = {}
    if not directory.is_dir():
        return rows, report
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in (".json", ".csv"):
            continue
        try:
            if path.suffix.lower() == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                source, retrieved, products = data.get("source") or path.stem, data.get("retrieved_at"), data.get("products", [])
            else:
                with path.open(encoding="utf-8", newline="") as handle:
                    products = list(csv.DictReader(handle))
                source = (products[0].get("source") if products else None) or path.stem
                retrieved = products[0].get("retrieved_at") if products else None
        except (OSError, ValueError) as exc:
            report[path.name] = {"error": str(exc), "imported": 0, "skipped": 0}
            continue
        kept = [r for r in (normalize_import(p, source, retrieved) for p in products) if r is not None]
        rows.extend(kept)
        report[path.name] = {"source": source, "imported": len(kept), "skipped": len(products) - len(kept)}
        if len(kept) < len(products):
            logger.warning("%s: skipped %d products with missing or invalid fields", path.name, len(products) - len(kept))
    return rows, report
