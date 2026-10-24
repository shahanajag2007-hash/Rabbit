"""Garment types and which types each style allows (shared by the scraper and the recommender).

``garment_type`` names what a product is (kurta, palazzo, juttis, jeans, sneakers, cap, ...) from
its title and the brand's product type. ``STYLE_RULES`` then says, for the strict styles, which types
an outfit may contain. This is what keeps a Traditional request from returning crop tops and sneakers:
style is a filter there, not just a score.
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Set

# Ordered most specific first; the head noun (last match in the text) wins, like the category rules.
_TYPES: Dict[str, list] = {
    "Top": [
        ("kurta", r"kurta|kurtis?|kurtas"), ("tunic", r"tunics?"), ("ethnic_top", r"anarkali|angrakha|kaftan top|choli"),
        ("nehru_jacket", r"nehru|bandhgala|modi jacket"), ("blazer", r"blazers?|suit jacket"), ("waistcoat", r"waistcoats?"),
        ("jacket", r"jackets?|bombers?|coats?|shackets?|overshirts?"), ("hoodie", r"hoodies?"), ("sweatshirt", r"sweatshirts?|pullovers?|jumpers?"),
        ("sweater", r"sweaters?|cardigans?|knit(?:ted)? tops?"), ("polo", r"polos?"), ("tshirt", r"t-?shirts?|tees?|henleys?"),
        ("blouse", r"blouses?"), ("shirt", r"shirts?"), ("tank", r"tanks?|vests?|camis?"), ("top", r"tops?"),
    ],
    "Bottom": [
        ("salwar", r"salwars?|patialas?"), ("churidar", r"churidars?|pyjamas?|pajamas?"), ("dhoti", r"dhotis?"),
        ("sharara", r"shararas?|ghararas?"), ("palazzo", r"palazzos?"), ("ethnic_skirt", r"lehenga skirts?|ethnic skirts?"),
        ("leggings", r"leggings|jeggings"), ("jeans", r"jeans|denims?"), ("joggers", r"joggers?|track ?pants?|trackpants?|sweatpants?"),
        ("cargo", r"cargos?"), ("shorts", r"shorts"), ("chinos", r"chinos?"), ("skirt", r"skirts?"),
        ("trousers", r"trousers?|pants?|culottes?"),
    ],
    "Shoes": [
        ("juttis", r"juttis?|mojaris?|nagras?|kolhapuris?"), ("formal_shoes", r"derby|derbies|oxfords?|brogues?|formal shoes?|monk"),
        ("loafers", r"loafers?|moccasins?"), ("heels", r"heels?|stilettos?|wedges?|pumps?"), ("boots", r"boots?"),
        ("flats", r"flats|ballerinas?|ballet"),
        ("sports_shoes", r"running|sports?|training|trainers?|walking|hiking|athleisure|trekking"),
        ("sliders", r"sliders?|slides|flip ?flops?|clogs?|floaters?"), ("sandals", r"sandals?"),
        ("sneakers", r"sneakers?|canvas|casual shoes?|slip-?ons?|shoes?"),
    ],
    "Accessory": [
        ("earrings", r"jhumkas?|earrings?|studs|chandbalis?"), ("bangles", r"bangles?|kadas?|bracelets?|cuffs?"),
        ("necklace", r"necklaces?|chains?|pendants?|mangalsutras?|chokers?"), ("ring", r"rings?"),
        ("dupatta", r"dupattas?|stoles?|scarf|scarves|shawls?"), ("clutch", r"clutch(?:es)?|potlis?|batuas?"),
        ("tie", r"ties?|pocket squares?|cufflinks?"), ("watch", r"watch(?:es)?"), ("belt", r"belts?"),
        ("wallet", r"wallets?|card holders?"), ("cap", r"caps?|hats?|beanies?"), ("sunglasses", r"sunglass(?:es)?|eyewear"),
        ("backpack", r"backpacks?|duffle|duffel|laptop bags?"), ("bag", r"handbags?|totes?|sling|bags?"),
    ],
}
_COMPILED = {cat: [(name, re.compile(rf"\b(?:{pattern})\b")) for name, pattern in rules] for cat, rules in _TYPES.items()}


def garment_type(category: str, title: str, product_type: str = "") -> Optional[str]:
    """The most specific garment type named in the title or the brand's product type.

    Rules are ordered most specific first within a category, so "Palazzo Pants" is a palazzo,
    "Kurta Shirt" a kurta and "Polo T-Shirt" a polo.
    """
    text = re.sub(r"tie[- ]?dye", "tiedye", f"{title} {product_type}".lower())
    for name, pattern in _COMPILED.get(category, []):
        if pattern.search(text):
            return name
    return None


ETHNIC_TYPES = {"kurta", "tunic", "ethnic_top", "nehru_jacket", "salwar", "churidar", "dhoti", "sharara", "palazzo",
                "ethnic_skirt", "juttis", "earrings", "bangles", "dupatta", "clutch", "ethnic_set", "saree", "lehenga"}
# Types that only make sense in an ethnic outfit (excluded from western styles).
ETHNIC_ONLY = {"kurta", "ethnic_top", "nehru_jacket", "salwar", "churidar", "dhoti", "sharara", "ethnic_skirt", "juttis",
               "ethnic_set", "saree", "lehenga"}
# Full outfits (fill the Top slot, cover Bottom) — see normalize.FULL_OUTFIT.
FULL_TYPES = {"ethnic_set", "saree", "lehenga", "suit", "coord", "jumpsuit", "dress"}
# Casual details that do not belong in a Formal outfit even when the garment type would.
FORMAL_EXCLUDED_WORDS = re.compile(r"\b(graphic|printed|print|hawaiian|cuban|resort|ripped|distressed|oversized|tie-?dye|tiedye|"
                                   r"denim|cargo|washed|varsity|camo)\b", re.I)

# For each strict style: allowed garment types per category. A product whose own style tags include
# the style is always allowed (e.g. an ethnic-tagged top of an unknown type).
STYLE_RULES: Dict[str, Dict[str, Set[str]]] = {
    "Traditional": {
        "Top": {"kurta", "tunic", "ethnic_top", "nehru_jacket", "ethnic_set", "saree", "lehenga"},
        "Bottom": {"salwar", "churidar", "dhoti", "sharara", "palazzo", "ethnic_skirt", "leggings"},
        "Shoes": {"juttis", "sandals", "flats", "heels", "loafers"},
        "Accessory": {"earrings", "bangles", "necklace", "ring", "dupatta", "clutch", "bag", "watch"},
    },
    "Formal": {
        "Top": {"shirt", "blouse", "blazer", "waistcoat", "sweater", "suit", "dress"},
        "Bottom": {"trousers", "chinos", "skirt"},
        "Shoes": {"formal_shoes", "loafers", "heels", "flats", "boots"},
        "Accessory": {"watch", "belt", "tie", "bag", "earrings", "bangles", "necklace", "ring", "wallet"},
    },
}
STYLE_RULES["Ethnic"] = STYLE_RULES["Traditional"]
# Western styles never get ethnic-only pieces; Smart Casual also drops the most casual ones.
WESTERN_STYLES = {"Casual", "Smart Casual", "Trendy", "Streetwear", "Minimal", "Elegant"}
SMART_EXCLUDED = {"hoodie", "joggers", "sliders", "shorts", "cap", "backpack", "sports_shoes"}
# Occasions that imply a strict style when the user has not picked a conflicting one.
OCCASION_RULES = {"Interview": "Formal"}


# Plain trousers in these colours are worn with kurtas (e.g. white straight pants), so Traditional allows them.
KURTA_TROUSER_COLOURS = {"white", "off-white", "ivory", "cream", "beige", "black"}
PLAIN_TROUSER_EXCLUDED = re.compile(r"\b(cargo|jogger|track|denim|jeans|baggy|wide|flared?|parachute|ripped|printed)\b", re.I)


def allowed_for_style(style: str, category: str, gtype: Optional[str], item_styles: Set[str], name: str = "", colour: str = "") -> bool:
    """Whether a product of this garment type may appear in an outfit of ``style``.

    Traditional / Formal allow only their listed garment types (an ethnic-tagged accessory of an
    unlisted type is still fine for Traditional). Western styles exclude ethnic-only pieces, and
    Smart Casual / Elegant also drop the most casual ones. Other styles allow everything.
    """
    rules = STYLE_RULES.get(style)
    if rules is not None:
        tagged = style.lower() in item_styles or (style in ("Traditional", "Ethnic") and bool({"ethnic", "traditional"} & item_styles))
        if gtype in rules.get(category, set()):
            return not (style == "Formal" and category in ("Top", "Bottom") and FORMAL_EXCLUDED_WORDS.search(name))
        if style in ("Traditional", "Ethnic") and category == "Bottom" and gtype in ("trousers", "chinos"):
            return colour.lower() in KURTA_TROUSER_COLOURS and not PLAIN_TROUSER_EXCLUDED.search(name)
        return tagged and category == "Accessory" and gtype is None
    if style in WESTERN_STYLES:
        if gtype in ETHNIC_ONLY:
            return False
        if style in ("Smart Casual", "Elegant") and gtype in SMART_EXCLUDED:
            return False
    return True
