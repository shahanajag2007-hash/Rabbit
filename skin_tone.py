from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


PALETTES: Dict[str, list[str]] = {
    "Light": ["Navy", "Burgundy", "Forest Green", "White", "Grey", "Lavender"],
    "Medium": ["Teal", "Olive", "Mustard", "Cream", "Maroon", "Navy"],
    "Tan": ["Rust", "Olive", "Camel", "Cream", "Teal", "Chocolate"],
    "Deep": ["White", "Cobalt Blue", "Emerald", "Coral", "Mustard", "Lavender"],
}


def _face_region(image: Image.Image) -> Image.Image:
    """Use the upper-center portion as a simple, non-professional face proxy."""
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    left = int(width * 0.25)
    right = int(width * 0.75)
    top = int(height * 0.08)
    bottom = int(height * 0.48)
    return rgb_image.crop((left, top, right, bottom))


def detect_skin_tone(image: Image.Image, clusters: int = 3) -> Tuple[str, Tuple[int, int, int]]:
    """Detect a broad tone label from a dominant RGB cluster."""
    region = _face_region(image).resize((80, 80))
    pixels = np.asarray(region, dtype=np.float32).reshape(-1, 3)
    cluster_count = max(1, min(clusters, len(pixels)))
    model = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
    labels = model.fit_predict(pixels)
    counts = np.bincount(labels)
    dominant = model.cluster_centers_[int(np.argmax(counts))]
    dominant_rgb = tuple(int(np.clip(value, 0, 255)) for value in dominant)
    brightness = float(np.mean(dominant))

    if brightness >= 190:
        tone = "Light"
    elif brightness >= 145:
        tone = "Medium"
    elif brightness >= 100:
        tone = "Tan"
    else:
        tone = "Deep"
    return tone, dominant_rgb


def estimate_skin_tone(image: Image.Image, clusters: int = 3) -> Tuple[str, Tuple[int, int, int], list[str]]:
    tone, dominant_rgb = detect_skin_tone(image, clusters)
    return tone, dominant_rgb, suggested_palette(tone)


def suggested_palette(tone: str) -> list[str]:
    return PALETTES.get(tone, PALETTES["Medium"])
