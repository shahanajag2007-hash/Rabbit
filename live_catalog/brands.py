"""Brand storefronts scraped for the live product catalogue.

Every brand here runs on Shopify, which publishes the public storefront feed
``/products.json`` (no API key, no headless browser). robots.txt is checked before
each fetch, so a brand that disallows it is skipped automatically.

``gender`` is the brand's default audience, used when a product's own title/tags
don't say ("Men", "Women" or "Unisex"). ``None`` means: infer from the product.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Brand:
    key: str
    name: str
    domain: str
    gender: Optional[str] = None
    max_pages: int = 3  # 250 products per page


BRANDS: tuple[Brand, ...] = (
    Brand("snitch", "Snitch", "www.snitch.co.in", gender="Men"),
    Brand("powerlook", "Powerlook", "www.powerlook.in", gender="Men"),
    Brand("rare", "Rare Rabbit", "www.thehouseofrare.com"),
    Brand("libas", "Libas", "www.libas.in", gender="Women"),
    Brand("offduty", "Offduty", "www.offduty.in"),
    Brand("bonkers", "Bonkers Corner", "www.bonkerscorner.com", gender="Unisex"),
    Brand("urbanmonkey", "Urban Monkey", "www.urbanmonkey.com", gender="Unisex", max_pages=2),
    Brand("campus", "Campus", "www.campusshoes.com", max_pages=2),
    Brand("redtape", "Red Tape", "www.redtape.com", max_pages=2),
)
