"""Map scraped Shopify products onto the recommender's dataset schema.

The recommender expects the columns of data/fashion_dataset.csv
(item_id, category, item_name, colour, shade, style, occasion, price, image).
Extra columns (brand, product_url, gender, fabric, ...) ride along unchanged.
"""
from __future__ import annotations

import html
import re
from typing import Dict, Iterable, List, Optional

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

# Not representable as a single Top/Bottom/Shoes/Accessory slot, or not outfit pieces.
SKIP = re.compile(
    r"\b(sets?|co-?ords?|combo|pack of|dress(es)?|jumpsuits?|playsuits?|rompers?|sarees?|lehengas?|gowns?|"
    r"kaftans?|nightwear|night ?suits?|pyjamas?|pajamas?|loungewear|boxers?|briefs?|trunks?|vests? ?innerwear|"
    r"innerwear|bras?|bralettes?|lingerie|camisoles?|crop|tube top|halter|backless|bodycon|bikini|swim\w*|socks?|perfumes?|fragrances?|"
    r"deodorants?|gift ?cards?|masks?|kids?|boys?|girls?|infant|test|cleaner|laces|insoles?|phone|cover|"
    r"stickers?|posters?|mugs?|bottles?|candles?|keychains?|sample)\b"
)

CATEGORY_RULES: List[tuple[str, re.Pattern]] = [
    ("Shoes", re.compile(r"\b(sneakers?|shoes?|loafers?|boots?|sandals?|sliders?|slides|flip ?flops?|heels?|juttis?|"
                         r"mojaris?|derby|derbies|brogues?|oxfords? shoes?|trainers?|slip-?ons?|floaters?|clogs?|mules?|"
                         r"espadrilles?|footwear|kolhapuris?|wedges?|ballerinas?|flats)\b")),
    ("Accessory", re.compile(r"\b(watch(es)?|bags?|backpacks?|totes?|wallets?|belts?|caps?|hats?|beanies?|sunglass(es)?|"
                             r"eyewear|earrings?|jhumkas?|necklaces?|chains?|bracelets?|kadas?|bangles?|pendants?|"
                             r"scarf|scarves|stoles?|dupattas?|ties|tie|pocket squares?|cufflinks?|handbags?|clutch(es)?|"
                             r"sling|duffle|rings?|anklets?|brooch(es)?)\b")),
    ("Bottom", re.compile(r"\b(jeans|trousers?|pants?|chinos?|joggers?|cargos?|shorts|skirts?|palazzos?|"
                          r"salwars?|churidars?|leggings|dhotis?|track ?pants?|culottes?)\b")),
    ("Top", re.compile(r"\b(shirts?|t-?shirts?|tees?|polos?|kurtas?|kurtis?|tops?|blouses?|sweaters?|sweatshirts?|"
                       r"hoodies?|jackets?|blazers?|cardigans?|tunics?|henleys?|shackets?|overshirts?|pullovers?|"
                       r"tanks?|waistcoats?|bandhgalas?|nehru|coats?|jumpers?|knits?|vests?)\b")),
]


def _prepare(text: str) -> str:
    # "tie-dye" is a print, not a tie.
    return re.sub(r"tie[- ]?dye", "tiedye", text.lower())


def classify_category(title: str, product_type: str) -> Optional[str]:
    if SKIP.search(_prepare(f"{title} {product_type}")):
        return None
    # The product type is the more reliable signal. Within a text the head noun comes last, so the
    # latest garment word wins ("Denim Jacket" -> Top, "Cap Sleeve Top" -> Top, "Leather Belt" -> Accessory).
    for source in (_prepare(product_type), _prepare(title)):
        best: Optional[tuple[int, str]] = None
        for category, pattern in CATEGORY_RULES:
            for match in pattern.finditer(source):
                if best is None or match.end() > best[0]:
                    best = (match.end(), category)
        if best:
            return best[1]
    return None


# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------

# canonical name -> (shade, synonyms). Canonical names match the palettes in skin_tone.py, the
# favourite-colour options and the avatar's colour table (frontend garmentMapping.ts).
COLOURS: Dict[str, tuple[str, tuple[str, ...]]] = {
    "Off-White": ("Light", ("off white", "off-white", "ecru")),
    "White": ("Light", ("white", "optic white")),
    "Ivory": ("Light", ("ivory",)),
    "Cream": ("Light", ("cream", "natural", "vanilla", "butter")),
    "Beige": ("Light", ("beige", "stone", "oatmeal", "taupe", "nude", "fawn")),
    "Sand": ("Light", ("sand",)),
    "Khaki": ("Medium", ("khaki",)),
    "Tan": ("Medium", ("tan",)),
    "Camel": ("Medium", ("camel",)),
    "Chocolate": ("Dark", ("chocolate", "dark brown", "coffee")),
    "Brown": ("Medium", ("brown", "mocha", "cognac", "walnut", "chestnut")),
    "Charcoal": ("Dark", ("charcoal", "dark grey", "dark gray", "anthracite", "graphite")),
    "Black": ("Dark", ("black", "jet black", "onyx")),
    "Grey": ("Medium", ("grey", "gray", "melange", "ash", "slate")),
    "Silver": ("Light", ("silver",)),
    "Rose Gold": ("Light", ("rose gold",)),
    "Gold": ("Light", ("gold", "golden")),
    "Navy": ("Dark", ("navy", "navy blue", "midnight blue", "midnight")),
    "Cobalt Blue": ("Dark", ("cobalt", "cobalt blue", "royal blue")),
    "Teal": ("Medium", ("teal", "turquoise", "aqua", "petrol", "peacock")),
    "Blue": ("Medium", ("blue", "sky blue", "powder blue", "light blue", "ice blue", "denim", "indigo", "steel blue")),
    "Emerald": ("Dark", ("emerald", "bottle green")),
    "Forest Green": ("Dark", ("forest green", "dark green", "hunter green")),
    "Olive": ("Medium", ("olive", "olive green", "army", "military")),
    "Sage": ("Light", ("sage", "mint", "pista", "pistachio")),
    "Green": ("Medium", ("green", "lime", "kelly green")),
    "Mustard": ("Medium", ("mustard", "ochre")),
    "Yellow": ("Light", ("yellow", "lemon")),
    "Rust": ("Medium", ("rust", "terracotta", "brick", "copper")),
    "Orange": ("Medium", ("orange", "tangerine")),
    "Coral": ("Light", ("coral", "peach", "salmon", "apricot")),
    "Burgundy": ("Dark", ("burgundy", "oxblood", "wine")),
    "Maroon": ("Dark", ("maroon",)),
    "Red": ("Medium", ("red", "cherry", "crimson")),
    "Pink": ("Light", ("pink", "rose", "fuchsia", "magenta", "blush", "dusty pink", "baby pink")),
    "Lavender": ("Light", ("lavender", "lilac", "mauve")),
    "Purple": ("Dark", ("purple", "violet", "aubergine", "plum")),
    "Multi": ("Medium", ("multi", "multicolour", "multicolor", "multi-colour", "multi-color")),
}

_SYNONYMS = sorted(
    ((syn, name) for name, (_, syns) in COLOURS.items() for syn in syns),
    key=lambda pair: -len(pair[0]),
)
_COLOUR_PATTERNS = [(re.compile(rf"\b{re.escape(syn)}\b"), name) for syn, name in _SYNONYMS]


def canonical_colour(text: str) -> Optional[str]:
    """First (longest-synonym) colour named in ``text``."""
    lowered = str(text or "").lower()
    best: Optional[tuple[int, str]] = None
    for pattern, name in _COLOUR_PATTERNS:
        match = pattern.search(lowered)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), name)
    return best[1] if best else None


def shade_for(colour: str) -> str:
    return COLOURS.get(colour, ("Medium", ()))[0]


# ---------------------------------------------------------------------------
# Style / occasion
# ---------------------------------------------------------------------------

# Style names include both the dataset's tags and the UI's option names, so either matches.
STYLE_RULES: List[tuple[str, re.Pattern]] = [
    ("Ethnic", re.compile(r"\b(kurtas?|kurtis?|ethnic|salwars?|churidars?|dhotis?|juttis?|mojaris?|jhumkas?|kadas?|"
                          r"bangles?|dupattas?|nehru|bandhgala|anarkali|festive|kolhapuris?|palazzos?|chikankari|"
                          r"block print|bandhani|ikat|zari)\b")),
    ("Formal", re.compile(r"\b(formal|blazers?|suits?|tuxedo|waistcoats?|oxfords?|derby|derbies|brogues?|ties?|"
                          r"pocket squares?|cufflinks?|office|work ?wear|pleated trousers?|business)\b")),
    ("Smart Casual", re.compile(r"\b(chinos?|linen|polos?|loafers?|knit|cardigans?|overshirts?|smart|cuban|"
                                r"resort|oxford shirt|trousers?)\b")),
    ("Trendy", re.compile(r"\b(oversized|graphic|cargos?|baggy|streetwear|street|printed|party|sequin\w*|satin|"
                          r"distressed|chunky|statement|varsity|bomber|y2k|relaxed fit|wide leg)\b")),
    ("Elegant", re.compile(r"\b(silk|satin|sequin\w*|embellished|velvet|luxe|premium|pearls?|organza)\b")),
    ("Minimal", re.compile(r"\b(solid|plain|basic|essential|classic|minimal)\b")),
    ("Casual", re.compile(r"\b(t-?shirts?|tees?|jeans|denims?|joggers?|shorts|sneakers?|sandals?|sliders?|caps?|"
                          r"backpacks?|hoodies?|sweatshirts?|casual|everyday|canvas|henleys?)\b")),
]
ALIASES = {"Ethnic": "Traditional", "Trendy": "Streetwear"}

# Same pairing as recommender.OCCASION_STYLES plus the UI's extra occasions.
STYLE_OCCASIONS = {
    "Formal": ["Office", "Interview"],
    "Smart Casual": ["Office", "Party", "Casual Outing"],
    "Casual": ["College", "Casual Outing"],
    "Trendy": ["Party", "College"],
    "Ethnic": ["Festival", "Traditional Event", "Party"],
    "Elegant": ["Party", "Special Event"],
    "Minimal": ["Office", "College"],
}
TAG_OCCASIONS = [
    (re.compile(r"\b(party|night ?out|evening)\b"), "Party"),
    (re.compile(r"\b(festive|festival|wedding|diwali|eid)\b"), "Festival"),
    (re.compile(r"\b(office|work ?wear|formal wear)\b"), "Office"),
    (re.compile(r"\b(casual wear|everyday|vacation|holiday)\b"), "Casual Outing"),
]


def classify_style(text: str) -> List[str]:
    lowered = _prepare(text)
    styles = [style for style, pattern in STYLE_RULES if pattern.search(lowered)]
    primary = styles[:2] or ["Casual"]
    if "Ethnic" in styles and "Ethnic" not in primary:
        primary = ["Ethnic", *primary[:1]]
    return primary + [ALIASES[s] for s in primary if s in ALIASES]


def classify_occasion(styles: Iterable[str], text: str) -> List[str]:
    occasions: List[str] = []
    for pattern, occasion in TAG_OCCASIONS:
        if pattern.search(text.lower()):
            occasions.append(occasion)
    for style in styles:
        occasions.extend(STYLE_OCCASIONS.get(style, []))
    if "Festival" in occasions and "Traditional Event" not in occasions:
        occasions.append("Traditional Event")
    return list(dict.fromkeys(occasions))[:4] or ["College", "Casual Outing"]


# ---------------------------------------------------------------------------
# Gender / fabric
# ---------------------------------------------------------------------------

_WOMEN = re.compile(r"\b(women'?s?|womens|woman|ladies|female|her)\b")
_MEN = re.compile(r"\b(men'?s?|mens|man|male|gents|him)\b")
_WOMEN_ITEMS = re.compile(r"\b(kurtis?|blouses?|skirts?|heels?|earrings?|jhumkas?|handbags?|clutch(es)?|dupattas?|"
                          r"palazzos?|leggings|bangles?|ballerinas?)\b")


def classify_gender(text: str, default: Optional[str]) -> str:
    lowered = text.lower()
    if "unisex" in lowered:
        return "Unisex"
    women, men = bool(_WOMEN.search(lowered)), bool(_MEN.search(lowered))
    if women and not men:
        return "Women"
    if men and not women:
        return "Men"
    if _WOMEN_ITEMS.search(lowered):
        return "Women"
    return default or "Unisex"


# Keys match demo_data.DEMO_FABRIC_NOTES so the Fabric panel shows the matching note.
FABRIC_KEYS = [
    (re.compile(r"linen"), "Linen"),
    (re.compile(r"denim"), "Denim"),
    (re.compile(r"silk|satin"), "Silk Satin"),
    (re.compile(r"rayon|viscose|modal"), "Rayon"),
    (re.compile(r"khadi|handloom"), "Khadi Cotton"),
    (re.compile(r"wool|merino"), "Wool Blend"),
    (re.compile(r"cotton"), "Cotton Blend"),
]
_MATERIAL_LINE = re.compile(r"(?:material|fabric|composition)\s*[:\-–]\s*([^\n|]{2,60})", re.I)
_FIBRES = (r"linen|denim|silk|satin|rayon|viscose|modal|khadi|wool|merino|cotton|polyester|nylon|lycra|spandex|"
           r"elastane|leather|suede|canvas|mesh|knit|fleece|corduroy|georgette|chiffon|crepe|velvet|jacquard|"
           r"chambray|twill|terry|acrylic|organza")
_FABRIC_WORD = re.compile(rf"\b((?:\d{{1,3}}\s?%\s?)?(?:{_FIBRES}))\b", re.I)


def extract_fabric(body_html: str, tags: Iterable[str], title: str) -> tuple[Optional[str], Optional[str]]:
    """(fabric, fabric_tag): a DEMO_FABRIC_NOTES key when one fits, plus the raw material text."""
    text = BeautifulSoup(body_html or "", "html.parser").get_text("\n") if body_html else ""
    raw = None
    match = _MATERIAL_LINE.search(text)
    line = re.sub(r"\s+", " ", match.group(1)).strip(" .,;") if match else ""
    if line and _FABRIC_WORD.search(line) and len(line) <= 40:
        raw = line  # e.g. "100% Cotton", "60% Cotton 40% Polyester"
    else:
        # Only real fibre/material words count (not "Sole - EVA", marketing copy or "5% off").
        for source in (line, " ".join(tags), title, text):
            words = list(dict.fromkeys(m.group(1).strip() for m in _FABRIC_WORD.finditer(source or "")))
            if words:
                raw = " ".join(words[:3])
                break
    if not raw:
        return None, None
    raw = html.unescape(raw).title()
    for pattern, key in FABRIC_KEYS:
        if pattern.search(raw.lower()):
            return key, raw
    return raw, raw


# ---------------------------------------------------------------------------
# Product -> rows
# ---------------------------------------------------------------------------

def _image(src: str, width: int = 480) -> str:
    if not src:
        return ""
    src = f"https:{src}" if src.startswith("//") else src
    return f"{src}{'&' if '?' in src else '?'}width={width}"


def _colour_option_index(product: Dict) -> Optional[int]:
    for option in product.get("options") or []:
        if isinstance(option, dict) and re.search(r"colou?r|shade", str(option.get("name", "")), re.I):
            position = option.get("position")
            if isinstance(position, int) and 1 <= position <= 3:
                return position
    return None


def _clean_title(title: str) -> str:
    # "Jackets for Men in Olive | Solid Regular Fit Jacket" -> the part before the tagline.
    title = html.unescape(title).replace("’", "'").split(" | ")[0]
    return re.sub(r"\s+", " ", title).strip()


def normalize_product(product: Dict, brand_key: str, brand_name: str, domain: str, brand_gender: Optional[str]) -> List[Dict]:
    """One row per colour of a Shopify product (only in-stock colours); [] when not usable."""
    title = _clean_title(str(product.get("title") or ""))
    product_type = str(product.get("product_type") or "")
    tags = [str(tag) for tag in (product.get("tags") or [])]
    if isinstance(product.get("tags"), str):
        tags = [tag.strip() for tag in product["tags"].split(",")]
    category = classify_category(title, product_type)
    if not title or not category:
        return []

    signal = " ".join([title, product_type, " ".join(tags)])
    styles = classify_style(signal)
    occasions = classify_occasion(styles, signal)
    # The title is the most specific signal ("AZURA Women's Sneakers" is tagged both Men and Women).
    title_gender = classify_gender(title, None)
    gender = title_gender if title_gender != "Unisex" else classify_gender(signal, brand_gender)
    fabric, fabric_tag = extract_fabric(str(product.get("body_html") or ""), tags, title)

    images = product.get("images") or []
    image_by_variant = {vid: img.get("src", "") for img in images for vid in (img.get("variant_ids") or [])}
    default_image = images[0].get("src", "") if images else ""
    colour_index = _colour_option_index(product)
    fallback_colour = canonical_colour(title) or canonical_colour(" ".join(tags))

    groups: Dict[str, List[Dict]] = {}
    for variant in product.get("variants") or []:
        if not variant.get("available", True):
            continue
        try:
            price = float(variant.get("price") or 0)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        raw_colour = str(variant.get(f"option{colour_index}") or "") if colour_index else ""
        colour = canonical_colour(raw_colour) or fallback_colour
        if not colour:
            continue
        groups.setdefault(colour, []).append({**variant, "_price": price})

    handle = product.get("handle", "")
    rows = []
    for colour, variants in groups.items():
        cheapest = min(variants, key=lambda v: v["_price"])
        compare = max(float(v.get("compare_at_price") or 0) for v in variants)
        featured = cheapest.get("featured_image") or {}
        image = featured.get("src") or next(
            (image_by_variant[v["id"]] for v in variants if v.get("id") in image_by_variant), default_image
        )
        name = title if brand_name.lower() in title.lower() else f"{brand_name} {title}"
        if product_type and not any(pattern.search(_prepare(title)) for _, pattern in CATEGORY_RULES):
            # "Urban Monkey Utopia" -> "Urban Monkey Utopia Cap": the avatar maps items by their name.
            noun = product_type.strip()
            noun = noun[:-1] if noun.lower().endswith("s") and not noun.lower().endswith("ss") else noun
            name = f"{name} {noun.title()}"
        if len(groups) > 1 and colour.lower() not in name.lower():
            name = f"{name} - {colour}"
        rows.append({
            "item_id": f"{brand_key}-{product.get('id')}-{colour.lower().replace(' ', '-')}",
            "category": category,
            "item_name": name,
            "colour": colour,
            "shade": shade_for(colour),
            "style": "|".join(styles),
            "occasion": "|".join(occasions),
            "price": round(cheapest["_price"], 2),
            "image": _image(image),
            "brand": brand_name,
            "gender": gender,
            "product_url": f"https://{domain}/products/{handle}" + (f"?variant={cheapest['id']}" if cheapest.get("id") else ""),
            "mrp": round(compare, 2) if compare > cheapest["_price"] else None,
            "fabric": fabric,
            "fabric_tag": fabric_tag,
            "product_type": product_type,
            "updated_at": product.get("updated_at"),
        })
    return rows
