"""FastAPI layer exposing the existing STYLEAI Python backend to the React frontend.

This module only adapts the existing modules (recommender, skin_tone, avatar_engine,
demo_data, shopping) to HTTP. The recommendation/scoring logic itself is unchanged.

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
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import recommender  # noqa: E402
from avatar_engine import render_fashion_avatar_svg  # noqa: E402
from demo_data import DEMO_FABRIC_NOTES, DEMO_PALETTES, DEMO_SUGGESTION_CHIPS  # noqa: E402
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
)

# Same folders the Streamlit recommendations page searched for product images.
IMAGE_FOLDERS = [ROOT / "images", ROOT / "static", ROOT / "data", ROOT]
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

_dataset = None


def get_dataset():
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


def serialize_item(item: Dict) -> Dict:
    data = to_jsonable(item)
    data["image_url"] = image_url_for(data)
    return data


def serialize_outfit(outfit: Dict) -> Dict:
    data = to_jsonable({key: val for key, val in outfit.items() if key != "items"})
    data["items"] = {category: serialize_item(item) for category, item in outfit.get("items", {}).items()}
    return data


def _strip_client_fields(item: Dict) -> Dict:
    return {key: val for key, val in item.items() if key != "image_url"}


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


class RegenerateRequest(BaseModel):
    outfit: OutfitIn
    profile: UserProfile
    locked_categories: List[str] = Field(default_factory=list)


class ShoppingRequest(BaseModel):
    outfit: OutfitIn
    budget: float = Field(gt=0)
    locked_categories: List[str] = Field(default_factory=list)


class AvatarSvgRequest(BaseModel):
    params: Dict[str, Any]
    outfit_items: Optional[Dict[str, Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> Dict:
    frame = get_dataset()
    return {"status": "ok", "dataset_items": int(len(frame))}


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
    outfits = recommender.recommend_outfits(
        frame=get_dataset(),
        user_profile=request.profile.model_dump(),
        locked_items=locked or None,
        limit=request.limit,
    )
    return {"profile": request.profile.model_dump(), "outfits": [serialize_outfit(o) for o in outfits]}


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
        get_dataset(), request.category, outfit, request.profile.model_dump()
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
    alternative = recommender.get_cheaper_alternative(get_dataset(), _strip_client_fields(request.item))
    return {"item": serialize_item(alternative) if alternative else None}


@app.post("/api/outfits/regenerate")
def regenerate(request: RegenerateRequest) -> Dict:
    """Same behaviour as the 'Regenerate Unlocked Items' button: locked items stay fixed."""
    outfit = _outfit_from_client(request.outfit)
    locked = {cat: outfit["items"][cat] for cat in request.locked_categories if cat in outfit["items"]}
    new_outfits = recommender.recommend_outfits(get_dataset(), request.profile.model_dump(), locked_items=locked, limit=1)
    return {"outfit": serialize_outfit(new_outfits[0]) if new_outfits else None}


@app.post("/api/shopping/alternatives")
def shopping_alternatives(request: ShoppingRequest) -> Dict:
    service = ShoppingService()
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
