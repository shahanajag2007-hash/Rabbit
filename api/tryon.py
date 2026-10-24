"""Virtual try-on service: the selected outfit on the user's validated photo.

The frontend only talks to the endpoints in api/main.py; which model produces the image is decided
here by ``STYLEAI_TRYON_PROVIDER`` (a comma-separated fallback chain, e.g. ``worker,gradio``):

- ``worker``  : the open-source try-on worker in tools/tryon-worker (CatVTON), reachable at
                ``STYLEAI_TRYON_WORKER_URL``. Runs on your own hardware (or any GPU machine you point it
                to), so there is no per-image fee or hosted quota. Renders the top and the bottom wear.
- ``gradio``  : an IDM-VTON-compatible Gradio app — by default the public Hugging Face Space
                ``yisol/IDM-VTON`` (shared free GPU with a small daily quota; ``HF_TOKEN`` raises it), or
                any URL set in ``STYLEAI_TRYON_SPACE``. Renders the top only.
- ``fashn``   : FASHN API (paid, ``FASHN_API_KEY``). Renders the top and the bottom wear.
- ``none``    : disabled.

Both the photo and the product images go to the provider, so the frontend asks for consent and the
request is refused without it. Results are cached by a hash of the photo *content*, the garments,
the provider/model and its parameters (``var/tryon-cache``, private, never served directly): the same
photo and outfit never run the model twice, even after re-uploading the photo. Identical requests in
flight share one job. Failures are reported as failures — there is no placeholder image.
"""
from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import io
import json
import logging
import os
import shutil
import tempfile
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import requests
from PIL import Image

logger = logging.getLogger("styleai.tryon")

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "var" / "tryon-cache"
TIMEOUT_SECONDS = float(os.environ.get("STYLEAI_TRYON_TIMEOUT", "420"))
# Garment images are only downloaded from the brands' own CDNs (never arbitrary URLs from the client).
ALLOWED_IMAGE_HOSTS = {"cdn.shopify.com"}
HF_SPACE = os.environ.get("STYLEAI_TRYON_SPACE", "yisol/IDM-VTON")
WORKER_URL = os.environ.get("STYLEAI_TRYON_WORKER_URL", "http://127.0.0.1:8100").rstrip("/")
FASHN_API_URL = os.environ.get("FASHN_API_URL", "https://api.fashn.ai/v1").rstrip("/")


class TryOnError(Exception):
    pass


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class Provider:
    name = "none"
    label = "Disabled"
    garments: List[str] = []
    model_version = ""

    def missing(self) -> Optional[str]:
        """Why the provider cannot run (None when it can)."""
        return "Virtual try-on is disabled (STYLEAI_TRYON_PROVIDER=none)."

    def params(self) -> Dict:
        return {}

    def run(self, photo: Path, garments: Dict[str, Path], descriptions: Dict[str, str], workdir: Path) -> Path:
        raise TryOnError(self.missing() or "Not available.")


class WorkerProvider(Provider):
    name = "worker"
    label = "Open-source try-on worker (CatVTON)"
    garments = ["Top", "Bottom"]

    def __init__(self) -> None:
        self._health: Tuple[float, Optional[Dict]] = (0.0, None)

    def health(self) -> Optional[Dict]:
        checked, info = self._health
        if time.time() - checked < 30:
            return info
        try:
            response = requests.get(f"{WORKER_URL}/health", timeout=5)
            info = response.json() if response.status_code == 200 else None
        except (requests.RequestException, ValueError):
            info = None
        self._health = (time.time(), info)
        return info

    @property
    def model_version(self) -> str:  # type: ignore[override]
        info = self.health() or {}
        return str(info.get("model", "catvton"))

    def missing(self) -> Optional[str]:
        info = self.health()
        if info is None:
            return (f"The try-on worker is not running at {WORKER_URL}. Start it with tools/tryon-worker "
                    "(see its README) or set STYLEAI_TRYON_WORKER_URL.")
        if not info.get("ready"):
            return f"The try-on worker is starting or failed to load its model: {info.get('error') or 'loading…'}"
        return None

    def params(self) -> Dict:
        info = self.health() or {}
        return {"steps": info.get("steps"), "size": info.get("size"), "device": info.get("device")}

    def run(self, photo, garments, descriptions, workdir):
        current = photo
        for category in ("Full", "Top", "Bottom"):
            if category not in garments:
                continue
            with open(current, "rb") as person, open(garments[category], "rb") as cloth:
                response = requests.post(
                    f"{WORKER_URL}/tryon",
                    files={"person": ("person.jpg", person, "image/jpeg"), "garment": ("garment.jpg", cloth, "image/jpeg")},
                    data={"category": {"Full": "overall", "Top": "upper", "Bottom": "lower"}[category]},
                    timeout=TIMEOUT_SECONDS,
                )
            if response.status_code != 200:
                try:
                    detail = response.json().get("detail")
                except ValueError:
                    detail = None
                raise TryOnError(f"The try-on worker could not render the {category.lower()}: {detail or f'HTTP {response.status_code}'}")
            step = workdir / f"step_{category.lower()}.png"
            step.write_bytes(response.content)
            current = step
        if current == photo:
            raise TryOnError("The outfit has no top or bottom wear to try on.")
        return current


class GradioProvider(Provider):
    name = "gradio"
    garments = ["Top"]
    model_version = "idm-vton"

    @property
    def label(self) -> str:  # type: ignore[override]
        return f"IDM-VTON on Hugging Face ({HF_SPACE})" if "/" in HF_SPACE and not HF_SPACE.startswith("http") else f"IDM-VTON at {HF_SPACE}"

    def missing(self):
        try:
            import gradio_client  # noqa: F401
        except ImportError:
            return "The gradio_client package is not installed on the server (pip install -r requirements.txt)."
        return None

    def params(self):
        return {"space": HF_SPACE, "steps": 30, "seed": 42, "crop": True}

    def run(self, photo, garments, descriptions, workdir):
        from gradio_client import Client, handle_file

        top = garments.get("Top") or garments.get("Full")
        if top is None:
            raise TryOnError("The outfit has no top to try on (this model renders upper-body garments only).")
        try:
            client = Client(HF_SPACE, hf_token=os.environ.get("HF_TOKEN") or None, verbose=False)
            output, _mask = client.predict(
                {"background": handle_file(str(photo)), "layers": [], "composite": None},
                handle_file(str(top)), descriptions.get("Top", ""), True, True, 30, 42, api_name="/tryon",
            )
        except Exception as exc:
            text = str(exc).lower()
            if "quota" in text or "exceeded" in text or "gpu" in text and "limit" in text:
                raise TryOnError("The free Hugging Face GPU quota is used up for now. It resets after a while; a free HF_TOKEN raises it, "
                                 "or run the open-source try-on worker (STYLEAI_TRYON_PROVIDER=worker).") from exc
            raise TryOnError("The hosted try-on service failed to generate an image. Please try again in a few minutes.") from exc
        result = workdir / "result.png"
        shutil.copy(output, result)
        return result


class FashnProvider(Provider):
    name = "fashn"
    label = "FASHN virtual try-on API"
    garments = ["Top", "Bottom"]
    model_version = "tryon-v1.6"

    def missing(self):
        return None if os.environ.get("FASHN_API_KEY") else "FASHN_API_KEY is not set on the server."

    def params(self):
        return {"model": self.model_version}

    def _call(self, model_image: str, garment: Path, category: str) -> str:
        headers = {"Authorization": f"Bearer {os.environ.get('FASHN_API_KEY')}", "Content-Type": "application/json"}
        garment_b64 = "data:image/jpeg;base64," + base64.b64encode(garment.read_bytes()).decode()
        response = requests.post(f"{FASHN_API_URL}/run", headers=headers, timeout=60, json={
            "model_name": self.model_version, "inputs": {"model_image": model_image, "garment_image": garment_b64, "category": category}})
        if response.status_code != 200:
            raise TryOnError(f"The FASHN try-on request was rejected (HTTP {response.status_code}).")
        job = response.json().get("id")
        deadline = time.time() + TIMEOUT_SECONDS
        while time.time() < deadline:
            time.sleep(3)
            status = requests.get(f"{FASHN_API_URL}/status/{job}", headers=headers, timeout=30).json()
            if status.get("status") == "completed" and status.get("output"):
                return status["output"][0]
            if status.get("status") in ("failed", "canceled"):
                raise TryOnError("The FASHN try-on job failed: " + str((status.get("error") or {}).get("message", "unknown error")))
        raise TryOnError("The try-on took too long and was stopped.")

    def run(self, photo, garments, descriptions, workdir):
        model_image = "data:image/jpeg;base64," + base64.b64encode(photo.read_bytes()).decode()
        rendered = False
        for category, fashn_category in (("Full", "one-pieces"), ("Top", "tops"), ("Bottom", "bottoms")):
            if category in garments:
                model_image = self._call(model_image, garments[category], fashn_category)
                rendered = True
        if not rendered:
            raise TryOnError("The outfit has no top or bottom wear to try on.")
        response = requests.get(model_image, timeout=60)
        if response.status_code != 200:
            raise TryOnError("Could not download the try-on result.")
        result = workdir / "result.png"
        Image.open(io.BytesIO(response.content)).save(result)
        return result


PROVIDERS: Dict[str, Callable[[], Provider]] = {
    "worker": WorkerProvider, "local": WorkerProvider,
    "gradio": GradioProvider, "huggingface": GradioProvider,
    "fashn": FashnProvider, "none": Provider,
}
_instances: Dict[str, Provider] = {}


def provider_chain() -> List[Provider]:
    names = [n.strip().lower() for n in os.environ.get("STYLEAI_TRYON_PROVIDER", "worker,huggingface").split(",") if n.strip()]
    chain = []
    for name in names or ["none"]:
        factory = PROVIDERS.get(name)
        if factory is None:
            continue
        key = factory.__name__
        _instances.setdefault(key, factory())
        chain.append(_instances[key])
    return chain or [Provider()]


def active_provider() -> Tuple[Provider, List[str]]:
    """The first provider in the chain that can run, and why the earlier ones cannot."""
    reasons = []
    chain = provider_chain()
    for provider in chain:
        problem = provider.missing()
        if problem is None:
            return provider, reasons
        reasons.append(f"{provider.label}: {problem}")
    return chain[0], reasons


def provider_info() -> Dict:
    provider, skipped = active_provider()
    problem = provider.missing()
    return {"provider": provider.name, "configured": problem is None, "label": provider.label,
            "garments": provider.garments, "missing": problem if problem else None, "skipped": skipped,
            "chain": [p.name for p in provider_chain()]}


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def _garment_image(item: Dict, workdir: Path, name: str) -> Path:
    url = str(item.get("image") or item.get("image_url") or "")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
        raise TryOnError(f"{item.get('item_name', 'This item')} has no product photo from the brand, so it cannot be tried on.")
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        raise TryOnError(f"Could not download the product photo for {item.get('item_name')} (HTTP {response.status_code}).")
    try:
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as exc:
        raise TryOnError(f"The product photo for {item.get('item_name')} could not be read.") from exc
    path = workdir / f"{name}.jpg"
    image.save(path, format="JPEG", quality=95)
    return path


def _describe(item: Dict) -> str:
    name = str(item.get("item_name") or "garment")
    brand = str(item.get("brand") or "")
    if brand and name.lower().startswith(brand.lower()):
        name = name[len(brand):].strip()
    return f"{item.get('colour', '')} {name}".strip()[:120]


def photo_hash(photo_path: Path) -> str:
    return hashlib.sha256(photo_path.read_bytes()).hexdigest()


def cache_path(photo_digest: str, key: str) -> Path:
    """Results are grouped per photo content, so deleting a photo can delete its cached try-ons."""
    return CACHE_DIR / photo_digest[:32] / f"{key}.png"


def forget_photo(photo_path: Path) -> None:
    """Delete every cached try-on made from this photo (called when the user deletes the photo)."""
    if photo_path.exists():
        shutil.rmtree(CACHE_DIR / photo_hash(photo_path)[:32], ignore_errors=True)


def cache_key(photo_digest: str, garments: Dict[str, Dict], provider: Provider) -> str:
    """Stable key: every provider input, plus the provider/model and its generation parameters."""
    parts = [photo_digest, provider.name, provider.model_version, json.dumps(provider.params(), sort_keys=True)]
    for category in sorted(garments):
        if category in provider.garments:
            g = garments[category]
            parts.append(json.dumps({
                "category": category,
                "item_id": g.get("item_id"),
                "image": g.get("image") or g.get("image_url"),
                "description": _describe(g),
                "covers_bottom": bool(g.get("covers_bottom")),
            }, sort_keys=True))
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Jobs (per photo, private to the session folder)
# ---------------------------------------------------------------------------

_inflight: Dict[str, threading.Event] = {}
_inflight_lock = threading.Lock()
_cancelled: set = set()


def job_dir(folder: Path, photo_id: str, job_id: str) -> Path:
    return folder / "tryon" / photo_id / job_id


def read_job(folder: Path, photo_id: str, job_id: str) -> Optional[Dict]:
    path = job_dir(folder, photo_id, job_id) / "job.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _write_job(folder: Path, photo_id: str, job: Dict) -> None:
    path = job_dir(folder, photo_id, job["job_id"])
    path.mkdir(parents=True, exist_ok=True)
    (path / "job.json").write_text(json.dumps(job), encoding="utf-8")


def start_job(folder: Path, photo_id: str, photo_path: Path, garments: Dict[str, Dict]) -> Dict:
    provider, skipped = active_provider()
    problem = provider.missing()
    if problem:
        raise TryOnError(" ".join([*skipped, problem]) if skipped else problem)
    digest = photo_hash(photo_path)
    key = cache_key(digest, garments, provider)
    job_id = key[:24]
    existing = read_job(folder, photo_id, job_id)
    if existing and existing["status"] in ("queued", "running", "done"):
        return existing  # same photo + outfit in this session: nothing to do
    job = {
        "job_id": job_id, "photo_id": photo_id, "status": "queued", "provider": provider.name, "label": provider.label,
        "garments": {cat: {"item_id": g.get("item_id"), "item_name": g.get("item_name")} for cat, g in garments.items()},
        "rendered": [cat for cat in provider.garments if cat in garments],
        "not_rendered": [cat for cat in ("Top", "Bottom", "Shoes", "Accessory") if cat in garments and cat not in provider.garments],
        "error": None, "cached": False, "started_at": time.time(), "finished_at": None,
    }
    cached = cache_path(digest, key)
    if cached.exists():
        # Same photo content and garments seen before (e.g. the photo was re-uploaded): no new inference.
        target = job_dir(folder, photo_id, job_id)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy(cached, target / "result.png")
        job.update(status="done", cached=True, finished_at=time.time())
        _write_job(folder, photo_id, job)
        return job
    _write_job(folder, photo_id, job)
    threading.Thread(target=_run_job, args=(folder, photo_id, photo_path, garments, job, provider, key, cached), daemon=True,
                     name=f"tryon-{job_id}").start()
    return job


def cancel_job(folder: Path, photo_id: str, job_id: str) -> Optional[Dict]:
    job = read_job(folder, photo_id, job_id)
    if job and job["status"] in ("queued", "running"):
        _cancelled.add((str(folder), photo_id, job_id))
        job.update(status="cancelled", error="Cancelled.", finished_at=time.time())
        _write_job(folder, photo_id, job)
    return job


def _run_job(folder: Path, photo_id: str, photo_path: Path, garments: Dict[str, Dict], job: Dict, provider: Provider, key: str,
             cached: Path) -> None:
    token = (str(folder), photo_id, job["job_id"])
    with _inflight_lock:
        waiting = _inflight.get(key)
        mine = waiting is None
        if mine:
            _inflight[key] = threading.Event()
    if not mine:
        # Another session is already generating exactly this image: wait for it instead of running again.
        waiting.wait(TIMEOUT_SECONDS)
    job = {**job, "status": "running"}
    if token not in _cancelled:
        _write_job(folder, photo_id, job)
    workdir = Path(tempfile.mkdtemp(prefix="styleai-tryon-"))
    try:
        if not cached.exists():
            images = {}
            for cat, g in garments.items():
                if cat not in provider.garments:
                    continue
                full = cat == "Top" and bool(g.get("covers_bottom"))
                images["Full" if full else cat] = _garment_image(g, workdir, "full" if full else cat.lower())
            if not images:
                raise TryOnError(f"Nothing in this outfit can be rendered by {provider.label} (it renders: {', '.join(provider.garments)}).")
            descriptions = {cat: _describe(g) for cat, g in garments.items()}
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(provider.run, photo_path, images, descriptions, workdir)
                try:
                    result = future.result(timeout=TIMEOUT_SECONDS)
                except concurrent.futures.TimeoutError as exc:
                    raise TryOnError(f"The try-on took longer than {TIMEOUT_SECONDS / 60:.0f} minutes and was stopped. Please try again.") from exc
            cached.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(result, cached)
        else:
            job["cached"] = True
        if token in _cancelled:
            return  # the result stays in the cache for next time; the cancelled job is not updated
        shutil.copy(cached, job_dir(folder, photo_id, job["job_id"]) / "result.png")
        job.update(status="done")
    except TryOnError as exc:
        job.update(status="failed", error=str(exc))
    except Exception:  # never leak internals to the browser
        logger.exception("Try-on job %s failed", job["job_id"])
        job.update(status="failed", error="The virtual try-on failed unexpectedly. Please try again.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        if mine:
            with _inflight_lock:
                _inflight.pop(key, None).set()
        if token not in _cancelled:
            job["finished_at"] = time.time()
            _write_job(folder, photo_id, job)
