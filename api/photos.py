"""Private photo uploads: validation, derived features and deletion.

Privacy model (there is no login in this app):
- each browser gets a random session id in an HttpOnly cookie (``styleai_sid``);
- photos are stored under ``var/uploads/<hash of the session id>/`` — outside every folder the API
  serves publicly — with random ids, re-encoded as JPEG without EXIF/GPS metadata;
- a photo (and its try-on results) can only be read or deleted with the cookie that uploaded it;
- image contents are never logged. Anyone with the same browser profile shares the session.

Validation (``validate``) runs locally: decodability, size, blur, exposure, and — with MediaPipe Pose —
exactly one person, visible from head to feet. Checks that cannot run are reported as unknown and the
photo is not accepted for try-on, rather than pretending they passed.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import shutil
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from fastapi import HTTPException, Request, Response
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_ROOT = ROOT / "var" / "uploads"
POSE_MODEL = ROOT / "models" / "pose_landmarker_lite.task"
COOKIE = "styleai_sid"
COOKIE_SAMESITE = os.environ.get("STYLEAI_COOKIE_SAMESITE", "lax").strip().lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    raise ValueError("STYLEAI_COOKIE_SAMESITE must be lax, strict or none.")
_secure_setting = os.environ.get("STYLEAI_COOKIE_SECURE", "false").strip().lower()
if _secure_setting not in {"1", "true", "yes", "on", "0", "false", "no", "off"}:
    raise ValueError("STYLEAI_COOKIE_SECURE must be a boolean value.")
COOKIE_SECURE = _secure_setting in {"1", "true", "yes", "on"}
if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
    raise ValueError("STYLEAI_COOKIE_SECURE=true is required when STYLEAI_COOKIE_SAMESITE=none.")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_SIDE = 2000
MIN_SHORT_SIDE, MIN_LONG_SIDE = 400, 600
BLUR_THRESHOLD = 40.0  # variance of the Laplacian on a 512px greyscale copy
PHOTO_ID = re.compile(r"^[0-9a-f]{32}$")
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

# MediaPipe pose landmark indices.
NOSE, L_EAR, R_EAR = 0, 7, 8
L_SHOULDER, R_SHOULDER, L_HIP, R_HIP = 11, 12, 23, 24
L_ANKLE, R_ANKLE, L_HEEL, R_HEEL = 27, 28, 29, 30


# ---------------------------------------------------------------------------
# Session and storage
# ---------------------------------------------------------------------------

def session_dir(request: Request, response: Optional[Response] = None, create: bool = False) -> Path:
    sid = request.cookies.get(COOKIE)
    if not sid or not re.fullmatch(r"[A-Za-z0-9_-]{32,64}", sid):
        if not create or response is None:
            raise HTTPException(status_code=404, detail="Photo not found.")
        sid = secrets.token_urlsafe(32)
        response.set_cookie(
            COOKIE,
            sid,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=60 * 60 * 24 * 7,
            path="/api",
        )
    folder = UPLOAD_ROOT / hashlib.sha256(sid.encode()).hexdigest()[:32]
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def photo_paths(folder: Path, photo_id: str) -> Tuple[Path, Path]:
    if not PHOTO_ID.fullmatch(photo_id or ""):
        raise HTTPException(status_code=404, detail="Photo not found.")
    return folder / f"{photo_id}.jpg", folder / f"{photo_id}.json"


def load_record(folder: Path, photo_id: str) -> Dict:
    image, meta = photo_paths(folder, photo_id)
    if not image.exists() or not meta.exists():
        raise HTTPException(status_code=404, detail="Photo not found. It may have been deleted — please upload it again.")
    return json.loads(meta.read_text(encoding="utf-8"))


def delete_photo(folder: Path, photo_id: str) -> None:
    from api.tryon import forget_photo

    image, meta = photo_paths(folder, photo_id)
    forget_photo(image)  # cached try-on results made from this photo
    for path in (image, meta):
        path.unlink(missing_ok=True)
    tryon_dir = folder / "tryon" / photo_id
    if tryon_dir.exists():
        shutil.rmtree(tryon_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------

def decode_upload(data: bytes) -> Image.Image:
    """Decode and sanity-check an upload; returns an EXIF-free, upright RGB image."""
    if not data:
        raise HTTPException(status_code=422, detail="The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 10 MB.")
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        probe.verify()  # structural check; the image must be reopened afterwards
        image = Image.open(io.BytesIO(data))
        if image.width * image.height > MAX_PIXELS:
            raise HTTPException(status_code=422, detail="The image has too many pixels to process (over 40 megapixels).")
        image.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=422, detail="The file is not a readable image or is corrupted. Please upload a JPG, PNG or WebP photo.")
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(status_code=415, detail="Please upload a JPG, PNG or WebP photo.")
    image = ImageOps.exif_transpose(image).convert("RGB")
    if max(image.size) > MAX_SIDE:
        image.thumbnail((MAX_SIDE, MAX_SIDE))
    return image


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_landmarker = None
_landmarker_error: Optional[str] = None
_landmarker_lock = threading.Lock()


def _pose_landmarker():
    global _landmarker, _landmarker_error
    with _landmarker_lock:
        if _landmarker is None and _landmarker_error is None:
            try:
                from mediapipe.tasks import python as mp_tasks
                from mediapipe.tasks.python import vision

                options = vision.PoseLandmarkerOptions(
                    base_options=mp_tasks.BaseOptions(model_asset_path=str(POSE_MODEL)),
                    running_mode=vision.RunningMode.IMAGE,
                    num_poses=3,
                    min_pose_detection_confidence=0.5,
                )
                _landmarker = vision.PoseLandmarker.create_from_options(options)
            except Exception as exc:  # missing package or model file
                _landmarker_error = f"{type(exc).__name__}: {exc}"
        return _landmarker


def _quality(image: Image.Image) -> Dict:
    grey = image.convert("L")
    grey.thumbnail((512, 512))
    g = np.asarray(grey, dtype=np.float32)
    lap = g[1:-1, 1:-1] * -4 + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return {"sharpness": float(lap.var()), "brightness": float(g.mean()), "contrast": float(g.std())}


def _detect_people(image: Image.Image) -> Optional[List[List[Tuple[float, float, float]]]]:
    landmarker = _pose_landmarker()
    if landmarker is None:
        return None
    import mediapipe as mp

    small = image.copy()
    small.thumbnail((1024, 1024))
    result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(small)))
    return [[(lm.x, lm.y, getattr(lm, "visibility", 1.0) or 0.0) for lm in pose] for pose in result.pose_landmarks]


def _visible(point: Tuple[float, float, float], margin: float = 0.0) -> bool:
    x, y, vis = point
    return vis >= 0.5 and -margin <= x <= 1 + margin and -margin <= y <= 1 + margin


def validate(image: Image.Image) -> Tuple[List[Dict], List[str], Dict]:
    """(checks, problems, features). A photo is usable for full-body try-on when ``problems`` is empty."""
    checks: List[Dict] = []
    problems: List[str] = []

    def check(name: str, ok: Optional[bool], message: str) -> None:
        checks.append({"name": name, "ok": ok, "message": message})
        if ok is False or ok is None:
            problems.append(message)

    w, h = image.size
    check("resolution", min(w, h) >= MIN_SHORT_SIDE and max(w, h) >= MIN_LONG_SIDE,
          f"Resolution {w}×{h}px" if min(w, h) >= MIN_SHORT_SIDE and max(w, h) >= MIN_LONG_SIDE
          else f"The photo is too small ({w}×{h}px). Please upload one at least {MIN_SHORT_SIDE}×{MIN_LONG_SIDE}px.")
    q = _quality(image)
    check("sharpness", q["sharpness"] >= BLUR_THRESHOLD,
          "Image is sharp enough" if q["sharpness"] >= BLUR_THRESHOLD
          else "The image is too blurry for a reliable virtual try-on. Please upload a clearer photograph.")
    lit = 45 <= q["brightness"] <= 225 and q["contrast"] >= 20
    check("lighting", lit, "Lighting looks fine" if lit else
          "The photo is too dark, too bright or too flat. Please upload a photo taken in even, natural light.")

    features: Dict = {"quality": {k: round(v, 1) for k, v in q.items()}}
    people = _detect_people(image)
    if people is None:
        check("person", None, "Person detection is unavailable on this server (MediaPipe pose model not installed), "
              "so the photo could not be checked for a full-body try-on.")
        return checks, problems, features

    features["people_detected"] = len(people)
    if not people:
        check("person", False, "No person could be detected. Please upload a clear, full-body photograph of yourself.")
        return checks, problems, features
    if len(people) > 1:
        check("single person", False, "Only one clearly visible person should be present in the photograph.")
        return checks, problems, features
    check("single person", True, "One person detected")

    pose = people[0]
    head = any(_visible(pose[i]) for i in (NOSE, L_EAR, R_EAR))
    feet = any(_visible(pose[i], margin=0.01) for i in (L_ANKLE, R_ANKLE, L_HEEL, R_HEEL))
    torso = all(_visible(pose[i]) for i in (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP))
    full = head and feet and torso
    check("full body", full, "Head to feet visible" if full else
          "Please upload a clear, full-body photograph with your head and feet visible.")

    xs = [p[0] for p in pose if p[2] >= 0.5]
    ys = [p[1] for p in pose if p[2] >= 0.5]
    if xs and ys:
        features["bbox"] = [round(max(0.0, min(xs)), 4), round(max(0.0, min(ys)), 4), round(min(1.0, max(xs)), 4), round(min(1.0, max(ys)), 4)]
        person_height = max(ys) - min(ys)
        check("framing", person_height >= 0.5, "Person fills enough of the frame" if person_height >= 0.5 else
              "You appear quite small in the photo. Please stand closer so your body fills most of the frame.")
    features["keypoints"] = [[round(x, 4), round(y, 4), round(v, 3)] for x, y, v in pose]
    shoulder = abs(pose[L_SHOULDER][0] - pose[R_SHOULDER][0])
    hip = abs(pose[L_HIP][0] - pose[R_HIP][0])
    if hip > 0.01:
        # Proportion only (2D, pose-dependent); never converted into body measurements.
        features["shoulder_to_hip_ratio"] = round(shoulder / hip, 3)
    features["face_box"] = _face_box(pose, image.size)
    return checks, problems, features


def _face_box(pose, size) -> Optional[List[int]]:
    w, h = size
    nose = pose[NOSE]
    if nose[2] < 0.5:
        return None
    shoulder = abs(pose[L_SHOULDER][0] - pose[R_SHOULDER][0]) * w
    half = max(int(shoulder * 0.35), 12)
    cx, cy = int(nose[0] * w), int(nose[1] * h)
    return [max(cx - half, 0), max(cy - int(half * 1.3), 0), min(cx + half, w), min(cy + int(half * 0.9), h)]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def store_upload(folder: Path, image: Image.Image) -> Dict:
    from skin_tone import estimate_skin_tone

    checks, problems, features = validate(image)
    photo_id = secrets.token_hex(16)
    image_path, meta_path = photo_paths(folder, photo_id)
    image.save(image_path, format="JPEG", quality=92)  # re-encoded: no EXIF / GPS metadata

    skin = None
    box = features.get("face_box")
    if box and box[2] - box[0] > 8 and box[3] - box[1] > 8:
        # The face crop's upper-centre (forehead/cheeks) is what skin_tone samples.
        tone, rgb, palette = estimate_skin_tone(image.crop(tuple(box)))
        skin = {"skin_tone": tone, "skin_rgb": list(rgb), "palette": palette, "source": "face region"}

    record = {
        "photo_id": photo_id,
        "accepted": not problems,
        "checks": checks,
        "problems": problems,
        "width": image.width,
        "height": image.height,
        "features": features,
        "skin": skin,
        "processing": {"validator": "styleai-photo-1", "pose_model": POSE_MODEL.name if _landmarker else None},
        "created_at": time.time(),
    }
    meta_path.write_text(json.dumps(record), encoding="utf-8")
    return record


def public_record(record: Dict) -> Dict:
    """What the browser gets back: validation results, no keypoints or file paths."""
    skin = record.get("skin") or {}
    return {
        "photo_id": record["photo_id"],
        "accepted": record["accepted"],
        "checks": record["checks"],
        "problems": record["problems"],
        "width": record["width"],
        "height": record["height"],
        "skin_tone": skin.get("skin_tone"),
        "skin_rgb": skin.get("skin_rgb"),
        "palette": skin.get("palette"),
    }
