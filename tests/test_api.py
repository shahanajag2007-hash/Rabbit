"""API tests: the FastAPI layer must return exactly what the existing recommender returns."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import recommender  # noqa: E402
from api.main import app, to_jsonable  # noqa: E402

client = TestClient(app)

PROFILE_A = {
    "gender": "Female",
    "height": 160,
    "weight": 55,
    "skin_tone": "Medium",
    "style": "Casual",
    "occasion": "College",
    "budget": 3500,
    "favorite_colours": ["Navy", "White"],
    "avoid_colours": ["Orange"],
}

PROFILE_B = {
    "gender": "Male",
    "height": 175,
    "weight": 70,
    "skin_tone": "Medium",
    "style": "Formal",
    "occasion": "Office",
    "budget": 5000,
    "favorite_colours": ["Black", "Navy"],
    "avoid_colours": ["Yellow"],
}


def _direct(profile, **kwargs):
    return recommender.recommend_outfits(recommender.load_dataset(), profile, **kwargs)


def _recommend(profile, **kwargs):
    response = client.post("/api/recommendations", json={"profile": profile, **kwargs})
    assert response.status_code == 200, response.text
    return response.json()["outfits"]


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["dataset_items"] == 50


def test_cors_allows_credentials_from_configured_frontend():
    response = client.options(
        "/api/photos",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize("profile", [PROFILE_A, PROFILE_B])
def test_recommendations_match_recommender_exactly(profile):
    api_outfits = _recommend(profile)
    direct = _direct(profile, limit=3)
    assert len(api_outfits) == len(direct) == 3
    for api_outfit, direct_outfit in zip(api_outfits, direct):
        assert api_outfit["score"] == direct_outfit["score"]
        assert api_outfit["total_price"] == direct_outfit["total_price"]
        assert api_outfit["breakdown"] == direct_outfit["breakdown"]
        assert api_outfit["signature"] == list(direct_outfit["signature"])
        for category in recommender.CATEGORIES:
            assert str(api_outfit["items"][category]["item_id"]) == str(direct_outfit["items"][category]["item_id"])
            assert api_outfit["items"][category]["image_url"]


def test_budget_is_respected():
    for outfit in _recommend({**PROFILE_A, "budget": 3000}):
        assert outfit["total_price"] <= 3000


def test_score_matches_score_single_outfit():
    outfit = _recommend(PROFILE_A)[0]
    response = client.post("/api/outfits/score", json={"outfit": {"items": outfit["items"]}, "profile": PROFILE_A})
    assert response.status_code == 200
    direct = recommender.score_single_outfit(_direct(PROFILE_A, limit=3)[0], PROFILE_A)
    assert response.json() == to_jsonable(direct)


def test_locked_items_stay_fixed_on_regenerate():
    outfit = _recommend(PROFILE_A)[0]
    response = client.post(
        "/api/outfits/regenerate",
        json={"outfit": {"items": outfit["items"]}, "profile": PROFILE_A, "locked_categories": ["Top", "Shoes"]},
    )
    assert response.status_code == 200
    new = response.json()["outfit"]
    assert new["items"]["Top"]["item_id"] == outfit["items"]["Top"]["item_id"]
    assert new["items"]["Shoes"]["item_id"] == outfit["items"]["Shoes"]["item_id"]


def test_replacements_exclude_current_item():
    outfit = _recommend(PROFILE_A)[0]
    response = client.post(
        "/api/outfits/replacements",
        json={"category": "Top", "outfit": {"items": outfit["items"]}, "profile": PROFILE_A},
    )
    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert candidates
    direct = recommender.get_replacement_candidates(recommender.load_dataset(), "Top", _direct(PROFILE_A, limit=3)[0], PROFILE_A)
    assert [c["item_id"] for c in candidates] == [int(c["items"]["Top"]["item_id"]) for c in direct[:3]]
    assert all(c["item_id"] != outfit["items"]["Top"]["item_id"] for c in candidates)


def test_cheaper_alternative():
    frame = recommender.load_dataset()
    expensive_top = to_jsonable(frame[(frame["category"] == "Top") & (frame["price"] > 1000)].iloc[0].to_dict())
    response = client.post("/api/outfits/cheaper", json={"item": expensive_top})
    assert response.status_code == 200
    assert response.json()["item"]["item_name"] == "Teal Casual Shirt"


def test_invalid_inputs_are_rejected():
    assert client.post("/api/recommendations", json={"profile": {**PROFILE_A, "budget": -5}}).status_code == 422
    assert client.post("/api/outfits/replacements", json={"category": "Hat", "outfit": {"items": {}}, "profile": PROFILE_A}).status_code == 422
    assert client.post("/api/outfits/score", json={"outfit": {"items": {}}, "profile": PROFILE_A}).status_code == 422


def test_shopping_alternatives_within_budget_returns_nothing():
    outfit = _recommend(PROFILE_A)[0]
    response = client.post("/api/shopping/alternatives", json={"outfit": {"items": outfit["items"]}, "budget": 100000})
    assert response.status_code == 200
    assert response.json()["alternatives"] == {}


def test_skin_tone_analysis():
    buffer = io.BytesIO()
    Image.new("RGB", (120, 200), (200, 160, 130)).save(buffer, format="PNG")
    response = client.post("/api/skin-tone/analyze", files={"file": ("me.png", buffer.getvalue(), "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["skin_tone"] == "Medium"
    assert body["palette"]


def test_skin_tone_rejects_non_image():
    response = client.post("/api/skin-tone/analyze", files={"file": ("x.png", b"not an image", "image/png")})
    assert response.status_code == 422


def test_avatar_svg_fallback():
    response = client.post("/api/avatar/svg", json={"params": {"gender": "Female"}})
    assert response.status_code == 200
    assert "<svg" in response.json()["svg"]


def test_missing_image_404():
    assert client.get("/api/images/does_not_exist.jpg").status_code == 404
    assert client.get("/api/images/app.py").status_code == 404
