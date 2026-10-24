"""Photo upload: validation, privacy and deletion (Tests O and P). Runs offline with synthetic images."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import photos  # noqa: E402
from api.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def private_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOAD_ROOT", tmp_path / "uploads")
    return tmp_path / "uploads"


def png(width, height, colour=(200, 160, 130), noise=False) -> bytes:
    if noise:
        data = np.random.default_rng(1).integers(0, 255, (height, width, 3), dtype=np.uint8)
        image = Image.fromarray(data)
    else:
        image = Image.new("RGB", (width, height), colour)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def upload(client, data, name="me.png", mime="image/png"):
    return client.post("/api/photos", files={"file": (name, data, mime)})


def test_corrupted_and_unsupported_files_are_rejected():
    client = TestClient(app)
    assert upload(client, b"definitely not an image").status_code == 422
    gif = io.BytesIO()
    Image.new("RGB", (800, 1200)).save(gif, format="GIF")
    response = upload(client, gif.getvalue(), "me.gif", "image/gif")
    assert response.status_code == 415
    assert "JPG, PNG or WebP" in response.json()["detail"]


def test_unsuitable_photos_are_not_accepted():
    client = TestClient(app)
    small = upload(client, png(120, 160, noise=True)).json()
    assert small["accepted"] is False
    assert any("too small" in p for p in small["problems"])
    flat = upload(client, png(800, 1200)).json()
    assert flat["accepted"] is False
    assert any("blurry" in p for p in flat["problems"])
    assert any("No person" in p or "unavailable" in p for p in flat["problems"])


def test_metadata_is_stripped(private_dir):
    client = TestClient(app)
    image = Image.new("RGB", (800, 1200), (120, 90, 70))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # camera make
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    photo_id = upload(client, buffer.getvalue(), "me.jpg", "image/jpeg").json()["photo_id"]
    stored = next(private_dir.rglob(f"{photo_id}.jpg"))
    assert not Image.open(stored).getexif()


def test_photos_are_private_to_their_session_and_deletable(private_dir):
    me, other = TestClient(app), TestClient(app)
    photo_id = upload(me, png(800, 1200, noise=True)).json()["photo_id"]
    assert me.get(f"/api/photos/{photo_id}/image").status_code == 200
    assert me.get(f"/api/photos/{photo_id}/image").headers["cache-control"] == "private, no-store"
    assert other.get(f"/api/photos/{photo_id}").status_code == 404
    assert other.get(f"/api/photos/{photo_id}/image").status_code == 404
    assert other.delete(f"/api/photos/{photo_id}").status_code == 404
    assert TestClient(app).get(f"/api/photos/{photo_id}/image").status_code == 404  # no cookie at all
    # Not reachable through the public product-image route either.
    assert me.get(f"/api/images/{photo_id}.jpg").status_code == 404
    assert me.delete(f"/api/photos/{photo_id}").json() == {"deleted": True}
    assert me.get(f"/api/photos/{photo_id}").status_code == 404
    assert not list(private_dir.rglob(f"{photo_id}*"))


def test_photo_session_cookie_is_http_only(private_dir):
    client = TestClient(app)
    response = upload(client, png(800, 1200, noise=True))
    cookie = response.headers["set-cookie"].lower()
    assert "styleai_sid=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_tryon_requires_consent_and_an_accepted_photo():
    client = TestClient(app)
    photo_id = upload(client, png(800, 1200, noise=True)).json()["photo_id"]
    items = {"Top": {"item_id": "x", "category": "Top", "item_name": "Shirt", "price": 100, "colour": "Blue", "image": "https://cdn.shopify.com/x.jpg"}}
    assert client.post("/api/tryon", json={"photo_id": photo_id, "items": items}).status_code == 400
    response = client.post("/api/tryon", json={"photo_id": photo_id, "items": items, "consent": True})
    assert response.status_code == 422  # random noise is not a full-body person
    assert client.post("/api/tryon", json={"photo_id": "0" * 32, "items": items, "consent": True}).status_code == 404
