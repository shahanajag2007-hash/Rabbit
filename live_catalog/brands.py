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
    # Ethnic / traditional wear (robots.txt allows the public feed on each; checked 2026-10-24).
    Brand("janasya", "Janasya", "www.janasya.com", gender="Women", max_pages=2),
    Brand("bunaai", "Bunaai", "www.bunaai.com", gender="Women", max_pages=2),
    Brand("suta", "Suta", "www.suta.in", gender="Women", max_pages=1),
    Brand("okhai", "Okhai", "www.okhai.org", max_pages=1),
    Brand("vastramay", "Vastramay", "www.vastramay.com", max_pages=2),
    Brand("kisah", "Kisah", "www.kisah.in", gender="Men", max_pages=1),
    Brand("sojanya", "Sojanya", "www.sojanya.com", gender="Men", max_pages=1),
    # Traditional footwear and jewellery.
    Brand("fizzygoblet", "Fizzy Goblet", "www.fizzygoblet.com", gender="Women", max_pages=1),
    Brand("needledust", "Needledust", "www.needledust.com", gender="Women", max_pages=1),
    Brand("giva", "Giva", "www.giva.co", gender="Women", max_pages=1),
)
