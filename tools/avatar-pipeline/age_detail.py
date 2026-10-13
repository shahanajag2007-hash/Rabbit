"""Age-detail maps for the avatar skin shader (frontend/src/components/avatar/skinShader.ts).

usage:  python age_detail.py <mpfb data dir> <frontend/public/models/avatar/tex>

MakeHuman ships young, middle-aged and old skin textures with the same UV layout. For each sex this
writes tex/age_detail_<sex>.png where
    R = middle-aged detail ratio, G = old detail ratio, stored as (ratio - 0.6) / 0.8
    ratio = highpass(aged luminance) / highpass(young luminance)
High-pass removes overall colour (so the user's skin tone is kept); dividing by the young texture's
own high-pass cancels features present in both (eyelids, lips, pores) and leaves what ageing adds:
forehead lines, crow's feet, nasolabial folds, finer skin texture.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

DATA, OUT = sys.argv[1], sys.argv[2]
SKINS = os.path.join(DATA, "skins")
SETS = {
    "female": ("young_caucasian_female/young_lightskinned_female_diffuse.png",
               "middleage_caucasian_female/middleage_lightskinned_female_diffuse.png",
               "old_caucasian_female/old_lightskinned_female_diffuse.png"),
    "male": ("young_caucasian_male/young_lightskinned_male_diffuse.png",
             "middleage_caucasian_male/middleage_lightskinned_male_diffuse.png",
             "old_caucasian_male/old_lightskinned_male_diffuse.png"),
}


def lum(path):
    a = np.asarray(Image.open(os.path.join(SKINS, path)).convert("RGB")).astype(np.float64) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def highpass(l, sigma=14.0):
    return (l + 0.02) / (gaussian_filter(l, sigma) + 0.02)


for sex, (young, mid, old) in SETS.items():
    y = highpass(lum(young))
    out = []
    for aged in (mid, old):
        r = highpass(lum(aged)) / y
        # Eye openings, nostrils and ear folds are deep features that do not line up exactly between the
        # textures; leave them unchanged. Ageing mostly adds creases (darker), so lightening is damped.
        feature = 1.0 - np.clip((y - 0.72) / 0.16, 0, 1)
        feature = gaussian_filter(feature, 6.0)
        r = 1.0 + (r - 1.0) * (1.0 - np.clip(feature * 2.5, 0, 1))
        r = np.where(r > 1.0, 1.0 + (r - 1.0) * 0.35, r)
        r = gaussian_filter(r, 0.8)  # drop single-pixel noise, keep line structure
        out.append(np.clip((r - 0.6) / 0.8, 0, 1))
    rgb = np.stack([out[0], out[1], np.full_like(out[0], 0.5)], axis=-1)
    img = Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), "RGB").resize((1024, 1024), Image.LANCZOS)
    dst = os.path.join(OUT, f"age_detail_{sex}.png")
    img.save(dst, optimize=True)
    print("wrote", dst, "mid ratio p1/p99", np.percentile(out[0] * 0.8 + 0.6, [1, 99]).round(3), "old", np.percentile(out[1] * 0.8 + 0.6, [1, 99]).round(3))
