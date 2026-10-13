"""Post-process the Blender build (AVATAR_WORK/out) into web-ready assets: usage  python postprocess.py <frontend/public/models/avatar>"""
import json, os, shutil, glob, sys
from PIL import Image, ImageOps
import numpy as np

WORK = os.environ.get("AVATAR_WORK", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".work"))
SRC = os.path.join(WORK, "out")
PACK = os.path.join(WORK, "blender_profile", "extensions", ".user", "user_default", "mpfb", "data")
DST = sys.argv[1]
DROP = {"top_graphic_tee_2", "top_printed_tee", "top_work_tee", "bottom_jeans_mid", "bottom_jeans_dark",
        "bottom_jeans_classic", "bottom_jeans_black", "bottom_jeans_stone"}

# Only the generated folders are replaced; thumbs/ (rendered separately) is kept.
for sub in ("female", "male", "neutral", "tex"):
    if os.path.isdir(os.path.join(DST, sub)):
        shutil.rmtree(os.path.join(DST, sub))
os.makedirs(os.path.join(DST, "tex"))

used = set()
# Textures that get the hair treatment (alpha kept, neutral grey for tinting): the facial hair meshes
# from the CC0 beard pack have generic texture names, so they are taken from meta.json.
facial_tex = set()
# Base-colour texture of each garment (from its glTF material), used for the tintable neutral version.
base_color = {}
for gender in ("female", "male", "neutral"):
    m = json.load(open(os.path.join(SRC, gender, "meta.json")))
    for fid in m.get("facialHair", []):
        g = json.load(open(os.path.join(SRC, gender, fid + ".gltf")))
        facial_tex.update(os.path.splitext(os.path.basename(i["uri"]))[0] for i in g.get("images", []))

for gender in ("female", "male", "neutral"):
    gsrc, gdst = os.path.join(SRC, gender), os.path.join(DST, gender)
    os.makedirs(gdst)
    meta = json.load(open(os.path.join(gsrc, "meta.json")))
    for gid in DROP:
        meta["garments"].pop(gid, None)
        meta["textures"].pop(gid, None)
    json.dump(meta, open(os.path.join(gdst, "meta.json"), "w"), indent=1)
    for f in glob.glob(os.path.join(gsrc, "*.gltf")):
        name = os.path.basename(f)[:-5]
        if name in DROP:
            continue
        g = json.load(open(f))
        for img in g.get("images", []):
            base = os.path.basename(img["uri"])
            used.add(base)
            stem = os.path.splitext(base)[0]
            alpha = stem in facial_tex or any(k in stem for k in ("hair", "afro", "bob", "braid", "long01", "ponytail", "short0", "eyebrow", "eyelash", "_eye"))
            new = stem + (".png" if alpha else ".jpg")
            img["uri"] = "../tex/" + new
            img["mimeType"] = "image/png" if alpha else "image/jpeg"
        shutil.copy(f.replace(".gltf", ".bin"), gdst)
        json.dump(g, open(os.path.join(gdst, name + ".gltf"), "w"))
        if name in meta["garments"]:
            for mat in g.get("materials", []):
                t = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture")
                if t is not None:
                    uri = g["images"][g["textures"][t["index"]]["source"]]["uri"]
                    base_color[name] = os.path.splitext(os.path.basename(uri))[0]
                    break
    meta["baseColor"] = {gid: base_color[gid] + "_neutral.jpg" for gid in meta["garments"] if gid in base_color}
    json.dump(meta, open(os.path.join(gdst, "meta.json"), "w"), indent=1)


def is_hair(stem):
    return stem in facial_tex or any(k in stem for k in ("afro", "bob0", "braid", "long01", "ponytail", "short0"))


for base in sorted(used):
    src = os.path.join(SRC, "tex", base)
    stem = os.path.splitext(base)[0]
    im = Image.open(src)
    if stem.endswith("_eye"):
        im.convert("RGBA").resize((512, 512), Image.LANCZOS).save(os.path.join(DST, "tex", stem + ".png"), optimize=True)
    elif "eyebrow" in stem or "eyelash" in stem:
        im = im.convert("RGBA").resize((512, 512) if im.width > 512 else im.size, Image.LANCZOS)
        if "eyebrow" in stem:
            # neutral brow texture so the hair colour can tint it
            a = np.asarray(im).astype(np.float32)
            lum = (a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11)
            ref = np.percentile(lum[a[..., 3] > 40], 90) if np.any(a[..., 3] > 40) else 255
            v = np.clip(lum / max(ref, 1) * 200, 0, 255)
            a[..., 0] = a[..., 1] = a[..., 2] = v
            im = Image.fromarray(a.astype(np.uint8), "RGBA")
        im.save(os.path.join(DST, "tex", stem + ".png"), optimize=True)
    elif is_hair(stem):
        im = im.convert("RGBA")
        im = im.resize((1024, 1024), Image.LANCZOS) if im.width > 1024 else im
        a = np.asarray(im).astype(np.float32)
        lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
        mask = a[..., 3] > 40
        ref = np.percentile(lum[mask], 92) if mask.any() else 255
        # keep strand contrast, normalise brightness to a light neutral grey for tinting
        v = np.clip(lum / max(ref, 1) * 235, 0, 255)
        a[..., 0] = a[..., 1] = a[..., 2] = v
        Image.fromarray(a.astype(np.uint8), "RGBA").save(os.path.join(DST, "tex", stem + ".png"), optimize=True)
    else:
        size = 2048 if "skinned" in stem else (512 if "_eye" in stem else 1024)
        im = im.convert("RGB")
        if im.width > size:
            im = im.resize((size, size), Image.LANCZOS)
        im.save(os.path.join(DST, "tex", stem + ".jpg"), quality=88, optimize=True)

# extra skin tones (medium / deep) and eye colours from the asset pack
for d in ("young_asian_female", "young_african_female", "young_asian_male", "young_african_male"):
    for p in glob.glob(os.path.join(PACK, "skins", d, "*_diffuse*.png")):
        stem = os.path.splitext(os.path.basename(p))[0]
        Image.open(p).convert("RGB").resize((2048, 2048), Image.LANCZOS).save(os.path.join(DST, "tex", stem + ".jpg"), quality=88, optimize=True)
        print("SKIN", d, stem)
for p in glob.glob(os.path.join(PACK, "eyes", "materials", "*_eye.png")):
    stem = os.path.splitext(os.path.basename(p))[0]
    Image.open(p).convert("RGBA").resize((512, 512), Image.LANCZOS).save(os.path.join(DST, "tex", stem + ".png"), optimize=True)

total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(DST) for f in fs)
print("TOTAL MB", round(total / 1e6, 1), "textures", len(os.listdir(os.path.join(DST, "tex"))))

# Neutral (luminance-only) garment textures so garments can be genuinely re-coloured by tinting.
neutral = []
for stem in sorted(set(base_color.values())):
    p = os.path.join(DST, "tex", stem + ".jpg")
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)
    lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    ref = np.percentile(lum, 97)
    v = np.clip(lum / max(ref, 1) * 245, 0, 255).astype(np.uint8)
    Image.fromarray(v, "L").convert("RGB").save(os.path.join(DST, "tex", stem + "_neutral.jpg"), quality=86, optimize=True)
    neutral.append(stem)
print("NEUTRAL", len(neutral))

# Average skin colour of each skin texture (face/torso region) for honest swatches.
avg = {}
for p in glob.glob(os.path.join(DST, "tex", "*skinned*_diffuse*.jpg")):
    a = np.asarray(Image.open(p).convert("RGB").resize((256, 256))).astype(np.float32)
    region = a[40:200, 40:200].reshape(-1, 3)
    bright = region[region.sum(axis=1) > 60]
    avg[os.path.basename(p)] = [int(x) for x in np.median(bright, axis=0)]
json.dump(avg, open(os.path.join(DST, "skin_average.json"), "w"), indent=1)
print("SKIN AVG", avg)
