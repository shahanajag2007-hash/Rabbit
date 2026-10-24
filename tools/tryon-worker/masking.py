"""Garment-area masks for try-on, made with MediaPipe (no detectron2 / DensePose needed).

MediaPipe's multiclass selfie segmenter labels each pixel as background, hair, body skin, face skin,
clothes or other. The pose landmarker gives the shoulder / hip / ankle lines. The mask is the clothes and
body-skin pixels in the band of the body the new garment covers:

- upper   : shoulders to just below the hips (plus the arms, so sleeves can change)
- lower   : waist to ankles
- overall : shoulders to ankles (sets, dresses, sarees)

The face, hair and hands are never masked, so they come out unchanged. The mask is dilated and its
holes filled so a looser or longer garment has room.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SEGMENTER = HERE / "models" / "selfie_multiclass_256x256.tflite"
POSE = HERE.parent.parent / "models" / "pose_landmarker_lite.task"  # shared with the main app

BACKGROUND, HAIR, BODY_SKIN, FACE_SKIN, CLOTHES, OTHER = range(6)
L_SHOULDER, R_SHOULDER, L_WRIST, R_WRIST, L_HIP, R_HIP, L_ANKLE, R_ANKLE = 11, 12, 15, 16, 23, 24, 27, 28

_segmenter = None
_pose = None


def _models():
    global _segmenter, _pose
    if _segmenter is None:
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision

        _segmenter = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=str(SEGMENTER)), output_category_mask=True))
        _pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=str(POSE)), num_poses=1))
    return _segmenter, _pose


def garment_mask(person: Image.Image, category: str) -> Image.Image:
    """White = area the new garment may repaint. ``category``: upper | lower | overall."""
    import mediapipe as mp

    segmenter, pose = _models()
    rgb = np.asarray(person.convert("RGB"))
    h, w = rgb.shape[:2]
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    labels = segmenter.segment(image).category_mask.numpy_view().squeeze()
    if labels.shape != (h, w):
        labels = cv2.resize(labels.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
    poses = pose.detect(image).pose_landmarks
    if not poses:
        raise ValueError("No person found in the photo.")
    lm = poses[0]
    y = lambda i: lm[i].y * h  # noqa: E731
    shoulders = min(y(L_SHOULDER), y(R_SHOULDER))
    hips = (y(L_HIP) + y(R_HIP)) / 2
    ankles = max(y(L_ANKLE), y(R_ANKLE))
    torso = max(hips - shoulders, 1.0)

    if category == "upper":
        top, bottom = shoulders - 0.12 * torso, hips + 0.30 * torso
    elif category == "lower":
        top, bottom = hips - 0.15 * torso, ankles + 0.04 * torso
    else:
        top, bottom = shoulders - 0.12 * torso, ankles + 0.04 * torso

    wearable = np.isin(labels, (CLOTHES, BODY_SKIN, OTHER))
    band = np.zeros((h, w), dtype=bool)
    band[int(max(0, top)):int(min(h, bottom)), :] = True
    mask = (wearable & band).astype(np.uint8) * 255

    # Room for a looser / longer garment, then fill holes.
    k = max(3, int(0.035 * h)) | 1
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 2 + 1, k * 2 + 1)))
    # Keep the face, hair and hands as they are.
    keep = np.isin(labels, (FACE_SKIN, HAIR)).astype(np.uint8)
    for wrist in (L_WRIST, R_WRIST):
        if lm[wrist].visibility > 0.5 and category != "lower":
            cx, cy = int(lm[wrist].x * w), int(lm[wrist].y * h)
            cv2.circle(keep, (cx, cy + int(0.03 * h)), int(0.035 * h), 1, -1)
    keep = cv2.dilate(keep, np.ones((5, 5), np.uint8))
    mask[keep > 0] = 0
    return Image.fromarray(mask, mode="L")


def pad_to_ratio(image: Image.Image, ratio: float = 3 / 4, fill=(255, 255, 255)) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Pad (not crop) to width/height = ``ratio`` so the head and feet are never cut off.
    Returns the padded image and the box of the original inside it."""
    w, h = image.size
    if abs(w / h - ratio) < 1e-3:
        return image, (0, 0, w, h)
    if w / h < ratio:
        new_w, new_h = round(h * ratio), h
    else:
        new_w, new_h = w, round(w / ratio)
    canvas = Image.new(image.mode, (new_w, new_h), fill if image.mode == "RGB" else 0)
    left, top = (new_w - w) // 2, (new_h - h) // 2
    canvas.paste(image, (left, top))
    return canvas, (left, top, left + w, top + h)


def blend_back(original: Image.Image, result: Image.Image, mask: Optional[Image.Image]) -> Image.Image:
    """Keep every pixel outside the (softened) mask from the original photo."""
    if mask is None:
        return result
    soft = mask.resize(original.size).filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(4))
    return Image.composite(result.resize(original.size, Image.LANCZOS), original, soft)
