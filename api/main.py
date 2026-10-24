"""FastAPI layer exposing the existing STYLEAI Python backend to the React frontend.

This module only adapts the existing modules (recommender, skin_tone, avatar_engine,
demo_data, shopping) to HTTP. The recommendation/scoring logic itself is unchanged.

Products come from the live brand-store catalogue (live_catalog/, scraped and refreshed in the
background). STYLEAI_CATALOG_SOURCE=static uses the bundled data/fashion_dataset.csv instead.

Run from the repository root:
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import io
import logging
import math
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if os.environ.get("STYLEAI_SKIP_DOTENV") != "1":  # tests run without the developer's .env
    from api.settings import load_env  # noqa: E402

    load_env()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import recommender  # noqa: E402
from avatar_engine import render_fashion_avatar_svg  # noqa: E402
from demo_data import DEMO_FABRIC_NOTES, DEMO_PALETTES, DEMO_SUGGESTION_CHIPS  # noqa: E402
from live_catalog import BRANDS, LiveCatalog  # noqa: E402
from preferences import parse_preferences  # noqa: E402
from api import photos, tryon  # noqa: E402
from shopping import ShoppingService  # noqa: E402
from skin_tone import PALETTES, estimate_skin_tone  # noqa: E402

logger = logging.getLogger("styleai.api")

app = FastAPI(title="STYLEAI API", version="1.0.0")

_origins = os.environ.get("STYLEAI_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Same folders the Streamlit recommendations page searched for product images.
IMAGE_FOLDERS = [ROOT / "images", ROOT / "static", ROOT / "data", ROOT]
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

_dataset = None
CATALOG_SOURCE = os.environ.get("STYLEAI_CATALOG_SOURCE", "live").strip().lower()
live_catalog: Optional[LiveCatalog] = None
if CATALOG_SOURCE != "static":
    live_catalog = LiveCatalog(fallback_loader=recommender.load_dataset)


@app.on_event("startup")
def _start_catalog_refresh() -> None:
    if live_catalog is not None:
        live_catalog.refresh_async()


def get_dataset(gender: Optional[str] = None):
    """Current products: the live catalogue (filtered to the profile's gender) or the static CSV."""
    if live_catalog is not None:
        live_catalog.refresh_async()  # no-op unless the snapshot is stale
        return live_catalog.frame_for(gender)
    global _dataset
    if _dataset is None:
        _dataset = recommender.load_dataset()
    return _dataset


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def to_jsonable(value: Any) -> Any:
    """Convert pandas/numpy values coming out of the recommender into JSON-safe values."""
    if isinstance(value, dict):
        return {str(key): to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(val) for val in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _find_local_image(filename: str) -> Optional[Path]:
    if not filename or Path(filename).name != filename:
        return None
    for folder in IMAGE_FOLDERS:
        path = folder / filename
        if path.is_file():
            return path
    return None


def image_url_for(item: Dict) -> str:
    """Mirror of the Streamlit page's image lookup: local file if present, else a placeholder."""
    filename = str(item.get("image") or "")
    if filename.startswith("http://") or filename.startswith("https://"):
        return filename
    if filename and _find_local_image(filename):
        return f"/api/images/{urllib.parse.quote(filename)}"
    return f"https://placehold.co/400x500/e6e4eb/1d1528?text={urllib.parse.quote(str(item.get('item_name', '')))}"


LINK_DOMAINS = {brand.domain for brand in BRANDS}


def verified_product_url(url: Any) -> Optional[str]:
    """Only https links on a scraped brand's own domain are shown as product links."""
    if not isinstance(url, str):
        return None
    parsed = urllib.parse.urlparse(url)
    return url if parsed.scheme == "https" and parsed.hostname in LINK_DOMAINS else None


def serialize_item(item: Dict) -> Dict:
    data = to_jsonable(item)
    data["image_url"] = image_url_for(data)
    if "product_url" in data or "variants" in data:
        data["product_url"] = verified_product_url(data.get("product_url"))
        for variant in data.get("variants") or []:
            variant["url"] = verified_product_url(variant.get("url"))
    return data


def serialize_outfit(outfit: Dict) -> Dict:
    data = to_jsonable({key: val for key, val in outfit.items() if key != "items"})
    data["items"] = {category: serialize_item(item) for category, item in outfit.get("items", {}).items()}
    return data


def _strip_client_fields(item: Dict) -> Dict:
    return {key: val for key, val in item.items() if key != "image_url"}


def _gender_of(item: Dict) -> Optional[str]:
    """Live items carry Men/Women/Unisex; map to the profile's wording for frame_for()."""
    return {"Men": "Male", "Women": "Female"}.get(str(item.get("gender") or ""))


def _outfit_from_client(outfit: "OutfitIn") -> Dict:
    return {"items": {category: _strip_client_fields(item) for category, item in outfit.items.items()}}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class UserProfile(BaseModel):
    """Same keys the Streamlit app placed in st.session_state['user_profile']."""

    gender: Optional[str] = "Female"
    height: Optional[float] = 168
    weight: Optional[float] = 58
    skin_tone: Optional[str] = "Medium"
    style: Optional[str] = "Casual"
    occasion: Optional[str] = "College"
    budget: float = Field(3500.0, gt=0)
    favorite_colours: List[str] = Field(default_factory=list)
    avoid_colours: List[str] = Field(default_factory=list)
    # Added for personalisation (all optional, so older clients keep working).
    age: Optional[int] = Field(None, ge=5, le=120)
    preferred_fit: Optional[str] = None
    preferred_fabrics: List[str] = Field(default_factory=list)
    preferred_brands: List[str] = Field(default_factory=list)
    preference_text: Optional[str] = Field(None, max_length=500)
    palette_colour: Optional[str] = Field(None, max_length=40)


class OutfitIn(BaseModel):
    items: Dict[str, Dict[str, Any]]


class RecommendRequest(BaseModel):
    profile: UserProfile
    locked_items: Optional[Dict[str, Dict[str, Any]]] = None
    limit: int = Field(3, ge=1, le=60)


class ScoreRequest(BaseModel):
    outfit: OutfitIn
    profile: UserProfile


class ReplacementRequest(BaseModel):
    category: str
    outfit: OutfitIn
    profile: UserProfile
    limit: int = Field(3, ge=1, le=60)


class CheaperRequest(BaseModel):
    item: Dict[str, Any]
    # Optional context: with them the cheaper item also respects preferences and suits the rest of the outfit.
    profile: Optional[UserProfile] = None
    outfit: Optional[OutfitIn] = None


class PreferenceRequest(BaseModel):
    text: str = Field("", max_length=500)


class PaletteRequest(BaseModel):
    profile: UserProfile


class BuilderRequest(BaseModel):
    profile: UserProfile
    category: str
    selected: Dict[str, Optional[Dict[str, Any]]] = Field(default_factory=dict)
    limit: int = Field(8, ge=1, le=40)
    offset: int = Field(0, ge=0)


class RegenerateRequest(BaseModel):
    outfit: OutfitIn
    profile: UserProfile
    locked_categories: List[str] = Field(default_factory=list)


class ShoppingRequest(BaseModel):
    outfit: OutfitIn
    budget: float = Field(gt=0)
    locked_categories: List[str] = Field(default_factory=list)


class TryOnRequest(BaseModel):
    photo_id: str = Field(min_length=32, max_length=32)
    items: Dict[str, Dict[str, Any]]
    consent: bool = False


class AvatarSvgRequest(BaseModel):
    params: Dict[str, Any]
    outfit_items: Optional[Dict[str, Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> Dict:
    frame = get_dataset()
    source = live_catalog.source() if live_catalog is not None else "static"
    return {"status": "ok", "dataset_items": int(len(frame)), "catalog_source": source}


@app.get("/api/catalog/status")
def catalog_status() -> Dict:
    """Where products come from, when each brand was last scraped, and any scrape errors."""
    if live_catalog is None:
        return {"source": "static", "items": int(len(get_dataset())), "brands": {}}
    return to_jsonable(live_catalog.status())


@app.post("/api/catalog/refresh")
def catalog_refresh(brand: Optional[str] = None) -> Dict:
    """Start a background re-scrape of the brand stores (all, or one brand key; returns immediately)."""
    if live_catalog is None:
        raise HTTPException(status_code=409, detail="Live catalogue is disabled (STYLEAI_CATALOG_SOURCE=static).")
    if brand and brand not in {b.key for b in live_catalog.brands}:
        raise HTTPException(status_code=404, detail=f"Unknown brand '{brand}'.")
    started = live_catalog.refresh_async(force=True, only=[brand] if brand else None)
    return {"started": started, "status": to_jsonable(live_catalog.status())}


@app.get("/api/meta")
def meta() -> Dict:
    """Static reference data used by the UI (palettes, chips, fabric notes)."""
    return {
        "categories": list(recommender.CATEGORIES),
        "score_weights": recommender.WEIGHTS,
        "skin_tone_palettes": PALETTES,
        "demo_palettes": DEMO_PALETTES,
        "suggestion_chips": DEMO_SUGGESTION_CHIPS,
        "fabric_notes": DEMO_FABRIC_NOTES,
    }


@app.get("/api/catalog")
def catalog() -> Dict:
    frame = get_dataset()
    return {"items": [serialize_item(row) for row in frame.to_dict(orient="records")]}


@app.post("/api/recommendations")
def recommendations(request: RecommendRequest) -> Dict:
    locked = {cat: _strip_client_fields(item) for cat, item in (request.locked_items or {}).items()}
    profile = request.profile.model_dump()
    outfits, notes = recommender.recommend_with_notes(
        frame=get_dataset(request.profile.gender),
        user_profile=profile,
        locked_items=locked or None,
        limit=request.limit,
    )
    return {
        "profile": profile,
        "outfits": [serialize_outfit(o) for o in outfits],
        "notes": notes,
        "understood": parse_preferences(profile.get("preference_text") or "")["understood"],
        "context": recommender.effective_context(profile),
    }


@app.post("/api/preferences/parse")
def preferences_parse(request: PreferenceRequest) -> Dict:
    """What the recommender will act on from the free-text request (rule-based, no LLM)."""
    return parse_preferences(request.text)


@app.post("/api/palette")
def palette(request: PaletteRequest) -> Dict:
    """Recommended colours for this profile that real products are available in (with counts)."""
    return to_jsonable(recommender.colour_palette(get_dataset(request.profile.gender), request.profile.model_dump()))


@app.post("/api/builder/options")
def builder_options(request: BuilderRequest) -> Dict:
    """One step of the manual outfit builder: ranked products for a category, given the picks so far."""
    if request.category not in recommender.CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Unknown category '{request.category}'.")
    selected = {cat: _strip_client_fields(item) for cat, item in request.selected.items() if item and cat in recommender.CATEGORIES}
    result = recommender.builder_options(get_dataset(request.profile.gender), request.profile.model_dump(),
                                         request.category, selected, request.limit, request.offset)
    result["items"] = [serialize_item(item) for item in result["items"]]
    return to_jsonable(result)


@app.get("/api/products/{item_id}")
def product_detail(item_id: str) -> Dict:
    """A catalogue item with its real variants (sizes, prices, links) and in-stock colours."""
    if live_catalog is not None:
        item = live_catalog.item(item_id)
    else:
        frame = get_dataset()
        match = frame[frame["item_id"].astype(str) == item_id]
        item = match.iloc[0].to_dict() if not match.empty else None
    if item is None:
        raise HTTPException(status_code=404, detail="This product is no longer in the catalogue.")
    return {"item": serialize_item(item)}


@app.get("/api/size-hint")
def size_hint(gender: Optional[str] = None, height: Optional[float] = None, weight: Optional[float] = None) -> Dict:
    return {"hint": recommender.size_hint(gender, height, weight)}


@app.post("/api/outfits/score")
def score_outfit(request: ScoreRequest) -> Dict:
    outfit = _outfit_from_client(request.outfit)
    if not outfit["items"]:
        raise HTTPException(status_code=422, detail="Outfit has no items to score.")
    return to_jsonable(recommender.score_single_outfit(outfit, request.profile.model_dump()))


@app.post("/api/outfits/replacements")
def replacements(request: ReplacementRequest) -> Dict:
    if request.category not in recommender.CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Unknown category '{request.category}'.")
    outfit = _outfit_from_client(request.outfit)
    candidates = recommender.get_replacement_candidates(
        get_dataset(request.profile.gender), request.category, outfit, request.profile.model_dump()
    )
    return {
        "category": request.category,
        "candidates": [serialize_item(c["items"][request.category]) for c in candidates[: request.limit]],
    }


@app.post("/api/outfits/cheaper")
def cheaper(request: CheaperRequest) -> Dict:
    required = {"category", "price", "colour"}
    if not required.issubset(request.item):
        raise HTTPException(status_code=422, detail=f"Item must include {sorted(required)}.")
    item = _strip_client_fields(request.item)
    profile = request.profile.model_dump() if request.profile else None
    outfit = _outfit_from_client(request.outfit) if request.outfit else None
    gender = request.profile.gender if request.profile else _gender_of(item)
    alternative = recommender.get_cheaper_alternative(get_dataset(gender), item, profile, outfit)
    if alternative is not None and float(alternative["price"]) >= float(item["price"]):  # never call a pricier item "cheaper"
        alternative = None
    return {"item": serialize_item(alternative) if alternative else None}


@app.post("/api/outfits/regenerate")
def regenerate(request: RegenerateRequest) -> Dict:
    """Same behaviour as the 'Regenerate Unlocked Items' button: locked items stay fixed."""
    outfit = _outfit_from_client(request.outfit)
    locked = {cat: outfit["items"][cat] for cat in request.locked_categories if cat in outfit["items"]}
    current = tuple(str(outfit["items"].get(cat, {}).get("item_id", "")) for cat in recommender.CATEGORIES)
    new_outfits, notes = recommender.recommend_with_notes(get_dataset(request.profile.gender), request.profile.model_dump(),
                                                          locked_items=locked, exclude_signatures={current}, limit=1)
    return {"outfit": serialize_outfit(new_outfits[0]) if new_outfits else None, "notes": notes}


@app.post("/api/shopping/alternatives")
def shopping_alternatives(request: ShoppingRequest) -> Dict:
    service = ShoppingService(catalog_frame=live_catalog.frame if live_catalog is not None else None)
    alternatives = service.find_cheaper_alternatives(_outfit_from_client(request.outfit), request.budget, request.locked_categories)
    configured = [provider.name for provider in service.providers if provider.is_configured()]
    return {
        "alternatives": to_jsonable(alternatives),
        "configured_providers": configured,
        "mock_mode": os.environ.get("USE_MOCK_SHOPPING_DATA", "False").lower() == "true",
    }


@app.post("/api/skin-tone/analyze")
async def analyze_skin_tone(file: UploadFile = File(...)) -> Dict:
    if file.content_type not in {"image/jpeg", "image/png", "image/jpg"}:
        raise HTTPException(status_code=415, detail="Please upload a JPG or PNG image.")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 10 MB.")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="The uploaded file is not a readable image.")
    tone, dominant_rgb, palette = estimate_skin_tone(image)
    return {"skin_tone": tone, "dominant_rgb": list(dominant_rgb), "palette": palette}


@app.post("/api/avatar/svg")
def avatar_svg(request: AvatarSvgRequest) -> Dict:
    """2D SVG avatar from the original avatar_engine (used as a non-WebGL fallback)."""
    return {"svg": render_fashion_avatar_svg(request.params, outfit_items=request.outfit_items)}


@app.get("/api/images/{filename}")
def product_image(filename: str):
    path = _find_local_image(filename)
    if not path or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(path)


# ---------------------------------------------------------------------------
# Private photos and virtual try-on (see api/photos.py and api/tryon.py)
# ---------------------------------------------------------------------------

PRIVATE_HEADERS = {"Cache-Control": "private, no-store"}


@app.post("/api/photos")
async def upload_photo(request: Request, response: Response, file: UploadFile = File(...)) -> Dict:
    """Validate and privately store a full-body photo; returns the validation result (no image data)."""
    data = await file.read(photos.MAX_UPLOAD_BYTES + 1)
    image = photos.decode_upload(data)
    folder = photos.session_dir(request, response, create=True)
    record = photos.store_upload(folder, image)
    response.headers.update(PRIVATE_HEADERS)
    return photos.public_record(record)


@app.get("/api/photos/{photo_id}")
def photo_status(photo_id: str, request: Request) -> Dict:
    return photos.public_record(photos.load_record(photos.session_dir(request), photo_id))


@app.get("/api/photos/{photo_id}/image")
def photo_image(photo_id: str, request: Request):
    folder = photos.session_dir(request)
    photos.load_record(folder, photo_id)
    image_path, _ = photos.photo_paths(folder, photo_id)
    return FileResponse(image_path, media_type="image/jpeg", headers=PRIVATE_HEADERS)


@app.delete("/api/photos/{photo_id}")
def remove_photo(photo_id: str, request: Request) -> Dict:
    """Delete the photo, its derived data (pose, skin tone) and its try-on results."""
    folder = photos.session_dir(request)
    photos.load_record(folder, photo_id)
    photos.delete_photo(folder, photo_id)
    return {"deleted": True}


@app.get("/api/tryon/provider")
def tryon_provider() -> Dict:
    return tryon.provider_info()


@app.post("/api/tryon")
def start_tryon(body: TryOnRequest, request: Request) -> Dict:
    if not body.consent:
        raise HTTPException(status_code=400, detail="Please agree to send your photo to the try-on service first.")
    folder = photos.session_dir(request)
    record = photos.load_record(folder, body.photo_id)
    if not record.get("accepted"):
        raise HTTPException(status_code=422, detail="This photo did not pass the full-body checks, so it cannot be used for try-on.")
    garments = {cat: _strip_client_fields(item) for cat, item in body.items.items() if cat in recommender.CATEGORIES and item}
    if not garments:
        raise HTTPException(status_code=422, detail="Select an outfit first.")
    image_path, _ = photos.photo_paths(folder, body.photo_id)
    try:
        return tryon.start_job(folder, body.photo_id, image_path, garments)
    except tryon.TryOnError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/tryon/{photo_id}/{job_id}")
def tryon_status(photo_id: str, job_id: str, request: Request) -> Dict:
    folder = photos.session_dir(request)
    photos.load_record(folder, photo_id)
    job = tryon.read_job(folder, photo_id, job_id) if job_id.isalnum() else None
    if job is None:
        raise HTTPException(status_code=404, detail="Try-on not found.")
    return job


@app.delete("/api/tryon/{photo_id}/{job_id}")
def tryon_cancel(photo_id: str, job_id: str, request: Request) -> Dict:
    """Stop waiting for a running try-on (a result that still arrives is kept in the private cache)."""
    folder = photos.session_dir(request)
    photos.load_record(folder, photo_id)
    job = tryon.cancel_job(folder, photo_id, job_id) if job_id.isalnum() else None
    if job is None:
        raise HTTPException(status_code=404, detail="Try-on not found.")
    return job


@app.get("/api/tryon/{photo_id}/{job_id}/image")
def tryon_image(photo_id: str, job_id: str, request: Request):
    folder = photos.session_dir(request)
    photos.load_record(folder, photo_id)
    path = tryon.job_dir(folder, photo_id, job_id) / "result.png" if job_id.isalnum() else None
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Try-on image not found.")
    return FileResponse(path, media_type="image/png", headers=PRIVATE_HEADERS)
