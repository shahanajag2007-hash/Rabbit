"""Try-on caching and failure handling (Tests 8 and 9), offline with a fake provider."""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import photos, tryon  # noqa: E402
from api.main import app  # noqa: E402


class CountingProvider(tryon.Provider):
    name = "fake"
    label = "Fake test provider"
    garments = ["Top", "Bottom"]
    model_version = "fake-1"
    calls = 0
    fail = False

    def missing(self):
        return None

    def run(self, photo, garments, descriptions, workdir):
        CountingProvider.calls += 1
        if CountingProvider.fail:
            raise tryon.TryOnError("The fake provider is down.")
        out = workdir / "result.png"
        Image.new("RGB", (64, 96), (10, 120, 200)).save(out)
        return out


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(tryon, "CACHE_DIR", tmp_path / "cache")
    # Accept the synthetic photo as a valid full-body photo; validation itself is tested in test_photos.py.
    monkeypatch.setattr(photos, "validate", lambda image: ([{"name": "test", "ok": True, "message": "ok"}], [], {}))
    monkeypatch.setattr(tryon, "_garment_image", lambda item, workdir, name: _write(workdir / f"{name}.jpg"))
    monkeypatch.setitem(tryon.PROVIDERS, "fake", CountingProvider)
    monkeypatch.setenv("STYLEAI_TRYON_PROVIDER", "fake")
    tryon._instances.clear()
    CountingProvider.calls = 0
    CountingProvider.fail = False


def _write(path: Path) -> Path:
    Image.new("RGB", (32, 32), (200, 20, 20)).save(path)
    return path


PHOTO = io.BytesIO()
Image.fromarray(np.random.default_rng(3).integers(0, 255, (1200, 800, 3), dtype=np.uint8)).save(PHOTO, format="PNG")
ITEM_A = {"item_id": "top-a", "category": "Top", "item_name": "Shirt A", "price": 999, "colour": "Navy", "image": "https://cdn.shopify.com/a.jpg"}
ITEM_B = {**ITEM_A, "item_id": "top-b", "item_name": "Shirt B", "image": "https://cdn.shopify.com/b.jpg"}


def upload(client) -> str:
    response = client.post("/api/photos", files={"file": ("me.png", PHOTO.getvalue(), "image/png")})
    assert response.status_code == 200, response.text
    return response.json()["photo_id"]


def wait(client, photo_id, job_id):
    for _ in range(100):
        job = client.get(f"/api/tryon/{photo_id}/{job_id}").json()
        if job["status"] not in ("queued", "running"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def tryon_request(client, photo_id, item):
    return client.post("/api/tryon", json={"photo_id": photo_id, "items": {"Top": item}, "consent": True})


def test_same_request_reuses_the_result_and_new_garment_generates():
    client = TestClient(app)
    photo_id = upload(client)
    first = wait(client, photo_id, tryon_request(client, photo_id, ITEM_A).json()["job_id"])
    assert first["status"] == "done" and CountingProvider.calls == 1
    assert client.get(f"/api/tryon/{photo_id}/{first['job_id']}/image").status_code == 200
    again = tryon_request(client, photo_id, ITEM_A).json()
    assert again["job_id"] == first["job_id"] and again["status"] == "done"
    assert CountingProvider.calls == 1  # no second inference
    # Re-uploading the same photo (new photo id) hits the content-hash cache.
    second_photo = upload(client)
    cached = tryon_request(client, second_photo, ITEM_A).json()
    assert cached["status"] == "done" and cached["cached"] is True and CountingProvider.calls == 1
    # A different garment is a new generation.
    other = wait(client, photo_id, tryon_request(client, photo_id, ITEM_B).json()["job_id"])
    assert other["status"] == "done" and CountingProvider.calls == 2


def test_tryon_cache_key_includes_provider_text_inputs():
    provider = CountingProvider()
    original = tryon.cache_key("photo", {"Top": ITEM_A}, provider)
    renamed = tryon.cache_key("photo", {"Top": {**ITEM_A, "item_name": "Different shirt"}}, provider)
    recoloured = tryon.cache_key("photo", {"Top": {**ITEM_A, "colour": "Red"}}, provider)
    assert original != renamed
    assert original != recoloured


def test_provider_failure_is_reported_and_retry_works():
    client = TestClient(app)
    photo_id = upload(client)
    CountingProvider.fail = True
    failed = wait(client, photo_id, tryon_request(client, photo_id, ITEM_A).json()["job_id"])
    assert failed["status"] == "failed" and "down" in failed["error"]
    assert client.get(f"/api/tryon/{photo_id}/{failed['job_id']}/image").status_code == 404  # no fake image
    CountingProvider.fail = False
    retried = wait(client, photo_id, tryon_request(client, photo_id, ITEM_A).json()["job_id"])
    assert retried["status"] == "done"


def test_unavailable_provider_explains_what_to_configure(monkeypatch):
    monkeypatch.setenv("STYLEAI_TRYON_PROVIDER", "worker")
    monkeypatch.setattr(tryon, "WORKER_URL", "http://127.0.0.1:9")  # nothing listens there
    tryon._instances.clear()
    client = TestClient(app)
    info = client.get("/api/tryon/provider").json()
    assert info["configured"] is False and "not running" in info["missing"]
    photo_id = upload(client)
    response = tryon_request(client, photo_id, ITEM_A)
    assert response.status_code == 503 and "tryon-worker" in response.json()["detail"]


def test_deleting_the_photo_removes_cached_results(tmp_path):
    client = TestClient(app)
    photo_id = upload(client)
    wait(client, photo_id, tryon_request(client, photo_id, ITEM_A).json()["job_id"])
    assert list((tmp_path / "cache").rglob("*.png"))
    client.delete(f"/api/photos/{photo_id}")
    assert not list((tmp_path / "cache").rglob("*.png"))
