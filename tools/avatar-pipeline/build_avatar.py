"""
STYLEAI avatar asset build (Blender 5.x + MPFB2 + MakeHuman CC0 system assets).

Run (isolated Blender profile with MPFB installed):
  normally run through build_all.sh (see frontend/public/models/README.md);
  blender -b -P build_avatar.py -- <output_dir> <female|male>   (with MPFB installed, see setup.sh)

For one gender this script:
  * creates a realistic MakeHuman character (textured skin, eyes, brows, lashes, teeth),
  * fits every hair / eyebrow / clothing / shoe / hat asset to it and poses the arms down,
  * captures each body-type and face configuration as morph targets on *every* mesh
    (garments and hair are re-fitted per configuration, so they deform with the body),
  * bakes per-garment "skin under garment" masks into body vertex attributes,
  * computes accessory anchor points per configuration,
  * exports every item as its own glTF (+ shared textures) and renders option thumbnails.
"""
import importlib, sys, os, math, json, hashlib
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion, kdtree
from mathutils.bvhtree import BVHTree


def di(p, k):
    for m in list(sys.modules):
        if m.endswith(p):
            return getattr(importlib.import_module(m), k)
    raise ValueError(p)


HumanService = di("mpfb.services.humanservice", "HumanService")
AssetService = di("mpfb.services.assetservice", "AssetService")
TargetService = di("mpfb.services.targetservice", "TargetService")
LocationService = di("mpfb.services.locationservice", "LocationService")
HOP = di("mpfb.entities.objectproperties", "HumanObjectProperties")

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(argv[0])
GENDER = argv[1]
GDIR = os.path.join(OUT, GENDER)
TEX = os.path.join(OUT, "tex")
THUMBS = os.path.join(OUT, "thumbs")
for d in (GDIR, TEX, THUMBS):
    os.makedirs(d, exist_ok=True)
TARGETS = LocationService.get_mpfb_data("targets")
IS_F = GENDER == "female"
IS_M = GENDER == "male"
GENDER_MACRO = {"female": 0.0, "male": 1.0, "neutral": 0.5}[GENDER]  # "neutral" = MakeHuman androgynous mid-point

# --------------------------------------------------------------------------------------
# Catalogue (ids are the stable asset identifiers used by the frontend)
# --------------------------------------------------------------------------------------
BASE_MACROS = {"gender": GENDER_MACRO, "age": 0.5, "muscle": 0.5, "weight": 0.5,
               # Modest bust (MakeHuman's average is 0.5): the avatar is shown in a professional context.
               "proportions": 0.5, "height": 0.5, "cupsize": 0.3, "firmness": 0.5,
               "african": 0.0, "asian": 0.0, "caucasian": 1.0}

# Body types: basis is "average". Each entry -> (macro overrides, [(target, weight)]).
# Presets differ per model so each one stays anatomically plausible for that body.
_BODY_ALL = {
    "slim": ({"weight": 0.1, "muscle": 0.4, "proportions": 0.6}, [("torso/measure-waist-circ-decr", 0.35)]),
    "athletic": ({"weight": 0.4, "muscle": 0.95}, [("torso/torso-vshape-incr", 0.25 if IS_F else 0.55)]),
    "curvy": ({"weight": 0.72, "muscle": 0.4, "cupsize": 0.4},
              [("hip/hip-scale-horiz-incr", 0.6), ("torso/measure-waist-circ-decr", 0.3)]),
    "full": ({"weight": 0.9, "muscle": 0.45, "cupsize": 0.4}, [("hip/hip-scale-horiz-incr", 0.3)]),
    "broad": ({"weight": 0.7, "muscle": 0.75}, [("torso/measure-shoulder-dist-incr", 0.7), ("torso/torso-vshape-incr", 0.2)]),
    "heavy": ({"weight": 0.95, "muscle": 0.55}, [("torso/torso-scale-horiz-incr", 0.2)]),
}
_BODY_FOR = {"female": ["slim", "athletic", "curvy", "full"], "male": ["slim", "athletic", "broad", "heavy"], "neutral": ["slim", "athletic", "curvy", "broad"]}
BODY = {k: _BODY_ALL[k] for k in _BODY_FOR[GENDER]}

# Age: MakeHuman's age macro, piecewise linear: 1 year = 0, 11 = 0.1875, 25 = 0.5, 90 = 1.0.
# Baked at a few ages; the app blends neighbouring configurations, so age changes are continuous.
def age_macro(years):
    if years <= 11:
        return (years - 1) / 10 * 0.1875
    if years <= 25:
        return 0.1875 + (years - 11) / 14 * 0.3125
    return 0.5 + (years - 25) / 65 * 0.5


AGE = {f"age_{y}": {"age": age_macro(y)} for y in (14, 18, 45, 65, 85)}

# Height: MakeHuman's height macro (0 = shortest, 1 = tallest), which changes proportions (leg length,
# torso, head size) the way the human model is built to. The app blends these towards the profile
# height and calibrates the exact stature with a small uniform scale.
HEIGHT = {"height_short": {"height": 0.0}, "height_tall": {"height": 1.0}}

FACE = {
    "face_oval": [("head/head-oval", 1.0)],
    "face_round": [("head/head-round", 1.0), ("head/head-fat-incr", 0.45)],
    "face_square": [("head/head-square", 1.0), ("chin/chin-width-incr", 0.6)],
    "face_heart": [("head/head-invertedtriangular", 1.0), ("chin/chin-width-decr", 0.5)],
    "face_long": [("head/head-rectangular", 0.7), ("head/head-scale-vert-incr", 0.6)],
    "nose_narrow": [("nose/nose-scale-horiz-decr", 0.8), ("nose/nose-nostrils-width-decr", 0.6)],
    "nose_wide": [("nose/nose-scale-horiz-incr", 0.8), ("nose/nose-nostrils-width-incr", 0.7)],
    "nose_upturned": [("nose/nose-point-up", 1.0)],
    "lips_full": [("mouth/mouth-upperlip-volume-incr", 1.0), ("mouth/mouth-lowerlip-volume-incr", 1.0)],
    "lips_thin": [("mouth/mouth-upperlip-volume-decr", 0.9), ("mouth/mouth-lowerlip-volume-decr", 0.9)],
    "lips_wide": [("mouth/mouth-scale-horiz-incr", 0.85)],
    "eyes_large": [("eyes/l-eye-scale-incr", 0.75), ("eyes/r-eye-scale-incr", 0.75)],
    "eyes_almond": [("eyes/l-eye-eyefold-angle-up", 0.7), ("eyes/r-eye-eyefold-angle-up", 0.7),
                    ("eyes/l-eye-corner1-up", 0.5), ("eyes/r-eye-corner1-up", 0.5)],
    "eyes_round": [("eyes/l-eye-height2-incr", 0.6), ("eyes/r-eye-height2-incr", 0.6)],
}

HAIR = ["long01", "ponytail01", "braid01", "bob01", "bob02", "afro01", "short01", "short02", "short03", "short04"]
EYEBROWS = [f"eyebrow{i:03d}" for i in range(1, 13)]
# (garment id, source mhclo, piece selector, slot)
GARMENTS = [
    ("top_white_tee", "male_casualsuit06", "upper", "top"),
    ("top_graphic_tee", "female_casualsuit01", "upper", "top"),
    ("top_graphic_tee_2", "female_casualsuit02", "upper", "top"),
    ("top_sport_crop", "female_sportsuit01", "upper", "top"),
    ("top_striped_blouse", "female_elegantsuit01", "upper", "top"),
    ("top_longsleeve_tee", "male_casualsuit02", "upper", "top"),
    ("top_striped_shirt", "male_casualsuit03", "upper", "top"),
    ("top_printed_tee", "male_casualsuit04", "upper", "top"),
    ("top_work_tee", "male_worksuit01", "upper", "top"),
    ("outer_casual_jacket", "male_casualsuit05", "upper", "outerwear"),
    ("outer_suit_blazer", "male_elegantsuit01", "upper", "outerwear"),
    ("bottom_jeans_light", "female_casualsuit01", "lower", "bottom"),
    ("bottom_jeans_mid", "male_casualsuit02", "lower", "bottom"),
    ("bottom_jeans_dark", "male_casualsuit03", "lower", "bottom"),
    ("bottom_jeans_classic", "male_casualsuit04", "lower", "bottom"),
    ("bottom_jeans_black", "male_casualsuit05", "lower", "bottom"),
    ("bottom_jeans_stone", "male_casualsuit06", "lower", "bottom"),
    ("bottom_leggings", "female_sportsuit01", "lower", "bottom"),
    ("bottom_denim_shorts", "female_casualsuit02", "lower", "bottom"),
    ("bottom_pencil_skirt", "female_elegantsuit01", "lower", "bottom"),
    ("bottom_suit_trousers", "male_elegantsuit01", "lower", "bottom"),
    ("bottom_overalls", "male_worksuit01", "lower", "bottom"),
    ("shoes_brown_leather", "shoes01", "all", "footwear"),
    ("shoes_grey_trainers", "shoes02", "all", "footwear"),
    ("shoes_black_boots", "shoes03", "all", "footwear"),
    ("shoes_black_formal", "shoes04", "all", "footwear"),
    ("shoes_white_sneakers", "shoes05", "all", "footwear"),
    ("shoes_navy_sneakers", "shoes06", "all", "footwear"),
    ("hat_fedora", "fedora01", "all", "hat"),
    # MakeHuman system assets: the button-up shirt + belted jeans suit (both pieces, for the skin masks)
    ("top_formal_shirt", "male_casualsuit01", "upper", "top"),
    ("bottom_jeans_belted", "male_casualsuit01", "lower", "bottom"),
    # MakeHuman CC0 asset packs (static.makehumancommunity.org/assets/assetpacks.html)
    ("top_polo", "namuhekam_male_polo_shirt", "all", "top"),
    ("top_sweater", "toigo_fisherman_sweater", "all", "top"),
    ("top_tucked_tee", "toigo_basic_tucked_t-shirt", "all", "top"),
    ("top_camisole", "toigo_camisole_top", "all", "top"),
    ("top_tank", "toigo_keyhole_tank_top", "all", "top"),
    ("top_tunic", "wdg_mycenaean_tunic", "all", "top"),
    ("dress_shift", "toigo_shift_dress", "all", "full"),
    ("dress_halter_midi", "toigo_halter_dress_midi", "all", "full"),
    ("dress_full_skirt", "toigo_camisole_dress_with_full_skirt", "all", "full"),
    ("dress_kimono", "mindfront_kimono", "all", "full"),
    ("full_skirt_suit", "toigo_female_suit", "all", "full"),
    ("full_trouser_suit_f", "toigo_female_double-breasted_suit", "all", "full"),
    ("full_suit_double_breasted", "toigo_male_double-breasted_suit", "all", "full"),
    ("full_dinner_suit", "toigo_suit_with_dinner_jacket", "all", "full"),
    ("bottom_wool_trousers", "toigo_wool_pants", "all", "bottom"),
    ("bottom_cargo", "cortu_cargo_pants", "all", "bottom"),
    ("bottom_harem", "toigo_harem_pants", "all", "bottom"),
    ("bottom_long_skirt", "toigo_long_full_skirt", "all", "bottom"),
    ("shoes_flats", "toigo_ballet_flats", "all", "footwear"),
    ("shoes_ankle_boots", "toigo_ankle_boots_male", "all", "footwear"),
]
# Facial hair (MakeHuman CC0 pack "bodyparts05"); fitted like hair, tinted with the hair colour.
FACIAL = {
    "facial_beard_short": "wdg_scruffy_beard",
    "facial_beard_full": "grinsegold_beard_sigmund_wip",
    "facial_beard_long": "rehmanpolanski_beard_viking",
    "facial_moustache": "rehmanpolanski_moustache_viking",
}
# Which asset pack each clothing source comes from (all CC0); written to meta.json.
PACK_OF = {
    "namuhekam_male_polo_shirt": "shirts01", "toigo_fisherman_sweater": "shirts01", "toigo_basic_tucked_t-shirt": "shirts01",
    "toigo_camisole_top": "shirts01", "toigo_keyhole_tank_top": "shirts01",
    "wdg_mycenaean_tunic": "dress01", "toigo_shift_dress": "dress01", "toigo_halter_dress_midi": "dress01",
    "toigo_camisole_dress_with_full_skirt": "dress01", "mindfront_kimono": "dress01",
    "toigo_wool_pants": "pants01", "cortu_cargo_pants": "pants01", "toigo_harem_pants": "pants01",
    "toigo_long_full_skirt": "skirts01",
    "toigo_female_suit": "suits01", "toigo_female_double-breasted_suit": "suits01",
    "toigo_male_double-breasted_suit": "suits01", "toigo_suit_with_dinner_jacket": "suits01", "toigo_ballet_flats": "shoes01", "toigo_ankle_boots_male": "shoes01",
}

# --------------------------------------------------------------------------------------
# Build the character
# --------------------------------------------------------------------------------------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

human = HumanService.create_human()
for k, v in BASE_MACROS.items():
    HOP.set_value(k, v, entity_reference=human)
TargetService.reapply_macro_details(human)
skin_name = "young_caucasian_male" if IS_M else "young_caucasian_female"
HumanService.set_character_skin(AssetService.find_asset_absolute_path(skin_name + ".mhmat", asset_subdir="skins"), human, skin_type="GAMEENGINE")
rig = HumanService.add_builtin_rig(human, "game_engine")


def add(sub, name, atype):
    p = AssetService.find_asset_absolute_path(name + ".mhclo", asset_subdir=sub)
    if p is None:
        raise RuntimeError(f"missing asset {sub}/{name}")
    return HumanService.add_mhclo_asset(p, human, asset_type=atype, material_type="GAMEENGINE", subdiv_levels=0)


items = {}  # id -> blender object (source, before splitting)
items["eyes"] = add("eyes", "high-poly", "Eyes")
items["eyelashes"] = add("eyelashes", "eyelashes01", "Eyelashes")
items["teeth"] = add("teeth", "teeth_base", "Teeth")
for hname in HAIR:
    items["hair_" + hname] = add("hair", hname, "Hair")
for b in EYEBROWS:
    items["brows_" + b] = add("eyebrows", b, "Eyebrows")
for fid, src in FACIAL.items():
    items[fid] = add("clothes", src, "Clothes")
source_clothes = {}
for gid, src, sel, slot in GARMENTS:
    if src not in source_clothes:
        source_clothes[src] = add("clothes", src, "Clothes")

# Delete-groups (skin hidden under each clothing source) before we drop the mask modifiers.
delete_groups = {}
for mod in list(human.modifiers):
    if mod.type == "MASK":
        vg = mod.vertex_group
        for src, obj in source_clothes.items():
            if src in vg or src in mod.name:
                delete_groups[src] = vg
        human.modifiers.remove(mod)
print("DELETE GROUPS", delete_groups)

# Natural relaxed standing pose (replaces MakeHuman's A-pose). Bones are aimed in world space, so
# the pose is anatomically the same for every body type; it is re-applied after each refit.
def _wpos(name, tail=False):
    pb = rig.pose.bones[name]
    return rig.matrix_world @ (pb.tail if tail else pb.head)


def _rotate_world(name, q):
    """Rotate a pose bone about its head by a world-space rotation (children follow)."""
    pb = rig.pose.bones[name]
    mw = rig.matrix_world.to_3x3().normalized()
    r = (mw.inverted() @ q.to_matrix() @ mw).to_4x4()
    m = pb.matrix.copy()
    t = m.translation.copy()
    pb.matrix = Matrix.Translation(t) @ r @ Matrix.Translation(-t) @ m
    bpy.context.view_layer.update()


def _aim(name, direction):
    cur = (_wpos(name, True) - _wpos(name)).normalized()
    _rotate_world(name, cur.rotation_difference(direction.normalized()))


def _keep_orientation(name, saved):
    pb = rig.pose.bones[name]
    pb.matrix = Matrix.Translation(pb.matrix.translation) @ saved.to_3x3().to_4x4()
    bpy.context.view_layer.update()


_HIP_IDX = None


def _hip_vertex_indices():
    """Body vertices weighted to the pelvis/thighs (used to keep the hands clear of the hips)."""
    global _HIP_IDX
    if _HIP_IDX is None:
        groups = {vg.index for vg in human.vertex_groups if vg.name in ("pelvis", "thigh_l", "thigh_r", "spine_01")}
        # MakeHuman's hidden helper geometry (tights/skirt helpers, joint cubes) is not real body surface.
        helpers = {vg.index for vg in human.vertex_groups if vg.name.lower().startswith(("helper", "joint"))}
        _HIP_IDX = np.array(
            [v.index for v in human.data.vertices
             if any(g.group in groups and g.weight > 0.4 for g in v.groups) and not any(g.group in helpers and g.weight > 0 for g in v.groups)],
            dtype=np.int64)
    return _HIP_IDX


def _body_world_coords():
    dg = bpy.context.evaluated_depsgraph_get()
    oe = human.evaluated_get(dg)
    me = oe.to_mesh()
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) @ np.array(oe.matrix_world)[:3, :3].T + np.array(oe.matrix_world)[:3, 3]
    oe.to_mesh_clear()
    return co


def _reset(names):
    for n in names:
        pb = rig.pose.bones.get(n)
        if pb:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()


def _pose_arm(side, xs, abduction_deg):
    finger_bones = [f"{f}_{s}_{side}" for f in ("index", "middle", "ring", "pinky", "thumb") for s in ("01", "02", "03")]
    _reset([f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"] + finger_bones)
    a = math.radians(abduction_deg)
    _aim(f"upperarm_{side}", Vector((xs * math.sin(a), 0.02, -math.cos(a))))
    _aim(f"lowerarm_{side}", Vector((xs * math.sin(math.radians(3)), -math.sin(math.radians(10)), -1.0)))
    _aim(f"hand_{side}", _wpos(f"lowerarm_{side}", True) - _wpos(f"lowerarm_{side}"))  # wrist in line with the forearm
    # Forearm twist so the palm faces the thigh (thumb pointing forward).
    axis = (_wpos(f"lowerarm_{side}", True) - _wpos(f"lowerarm_{side}")).normalized()
    across = _wpos(f"index_01_{side}") - _wpos(f"pinky_01_{side}")
    across_p = (across - axis * across.dot(axis)).normalized()
    forward = Vector((0, -1, 0))
    forward_p = (forward - axis * forward.dot(axis)).normalized()
    _rotate_world(f"lowerarm_{side}", across_p.rotation_difference(forward_p))
    # Relaxed fingers: curl each segment towards the palm.
    palm_axis = (_wpos(f"index_01_{side}") - _wpos(f"pinky_01_{side}")).normalized()
    inward = Vector((-xs, 0, 0))
    for finger, angles in (("index", (6, 12, 8)), ("middle", (8, 13, 8)), ("ring", (9, 14, 9)), ("pinky", (10, 15, 9)), ("thumb", (3, 6, 4))):
        for seg, deg in zip(("01", "02", "03"), angles):
            name = f"{finger}_{seg}_{side}"
            if name not in rig.pose.bones:
                continue
            d = (_wpos(name, True) - _wpos(name)).normalized()
            best = None
            for sign in (1, -1):
                q = Quaternion(palm_axis, sign * math.radians(deg))
                score = (q @ d).dot(inward)
                if best is None or score > best[0]:
                    best = (score, q)
            _rotate_world(name, best[1])


def _hand_clearance(side, xs, co):
    """Gap (m) between the hand and the hip surface at hand height (negative = intersecting)."""
    wrist = _wpos(f"hand_{side}")
    tip = _wpos(f"middle_01_{side}")  # knuckles: relaxed fingertips may rest lightly against the thigh
    hip = co[_hip_vertex_indices()]
    zlo, zhi = min(wrist.z, tip.z) - 0.02, max(wrist.z, tip.z) + 0.02
    band = hip[(hip[:, 2] > zlo) & (hip[:, 2] < zhi) & (xs * hip[:, 0] > 0)]
    if not len(band):
        return 1.0
    hip_out = float(np.max(xs * band[:, 0]))
    hand_in = min(xs * wrist.x, xs * tip.x) - 0.03  # approx. half hand thickness
    if os.environ.get("POSE_DEBUG"):
        print(f"DBG side={side} xs={xs} wrist={tuple(round(c, 3) for c in wrist)} tip={tuple(round(c, 3) for c in tip)} band={len(band)} hip_out={hip_out:.3f} "
              f"hip_z=({band[:, 2].min():.2f},{band[:, 2].max():.2f}) hipidx={len(_hip_vertex_indices())}")
    return hand_in - hip_out


def apply_pose():
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    for side in ("l", "r"):
        xs = 1 if _wpos(f"upperarm_{side}", True).x > _wpos(f"upperarm_{side}").x else -1
        # Legs: feet under the hips (no wide A-stance), feet kept flat on the ground.
        foot_saved = rig.pose.bones[f"foot_{side}"].matrix.copy()
        _aim(f"thigh_{side}", Vector((xs * 0.012, 0.0, -1.0)))
        _aim(f"calf_{side}", Vector((xs * 0.01, 0.02, -1.0)))
        _keep_orientation(f"foot_{side}", foot_saved)
        # Arms relaxed at the sides; open the arm just enough for the hand to clear the hip of
        # this particular body (wider presets get a slightly wider arm angle, not a scaled body).
        angle = 8.0
        _pose_arm(side, xs, angle)
        for _ in range(8):
            gap = _hand_clearance(side, xs, _body_world_coords())
            if gap >= 0.008 or angle >= 22:
                break
            angle += 2.0
            _pose_arm(side, xs, angle)
        print(f"POSE {side} arm angle {angle:.0f} deg gap {gap * 100:.1f} cm")


apply_pose()
if os.environ.get("POSE_DEBUG"):
    sys.exit(0)

mesh_objects = [human] + list(items.values()) + list(source_clothes.values())


def capture():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    res = {}
    for o in mesh_objects:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(oe.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        res[o.name] = co.astype(np.float32)
        oe.to_mesh_clear()
    # ground the configuration: lowest point of the body at z = 0
    zmin = float(res[human.name][:, 2].min())
    for k in res:
        res[k] = res[k] - np.array([0, 0, zmin], dtype=np.float32)
    return res


def bone_world(name, tail=False):
    pb = rig.pose.bones[name]
    return rig.matrix_world @ (pb.tail if tail else pb.head)


def anchors_from(co_body, zshift):
    """Accessory anchor points for the current pose/config (Blender world coords, grounded)."""
    def b(name, tail=False):
        v = bone_world(name, tail)
        return [v.x, v.y, v.z - zshift]

    def ring(center, axis_pts, band=0.012):
        # radius of body cross-section around 'center' (horizontal ring)
        c = np.array(center)
        m = (np.abs(co_body[:, 2] - c[2]) < band) & (np.abs(co_body[:, 0] - c[0]) < 0.25) & (np.abs(co_body[:, 1] - c[1]) < 0.25)
        pts = co_body[m]
        if len(pts) == 0:
            return [0.06, 0.06]
        return [float(np.percentile(np.abs(pts[:, 0] - c[0]), 95)), float(np.percentile(np.abs(pts[:, 1] - c[1]), 95))]

    a = {}
    a["head"] = b("head")
    a["head_top"] = [a["head"][0], a["head"][1], float(co_body[:, 2].max())]
    for side in ("l", "r"):
        wrist = b(f"hand_{side}")
        elbow = b(f"lowerarm_{side}")
        a[f"wrist_{side}"] = wrist
        a[f"forearm_dir_{side}"] = list((np.array(wrist) - np.array(elbow)) / (np.linalg.norm(np.array(wrist) - np.array(elbow)) + 1e-9))
        a[f"hand_{side}"] = b(f"hand_{side}", tail=True)
        # wrist radius: body verts near the wrist point
        w = np.array(wrist)
        d = np.linalg.norm(co_body - w, axis=1)
        a[f"wrist_radius_{side}"] = float(np.percentile(d[d < 0.06], 60)) if np.any(d < 0.06) else 0.03
    neck = b("neck_01")
    a["neck"] = neck
    a["neck_radii"] = ring([neck[0], neck[1], neck[2] + 0.02], None)
    waist = b("spine_01")
    a["waist"] = waist
    a["waist_radii"] = ring(waist, None, band=0.015)
    return a


# Eye centers / ear lobes are taken from mesh vertices (stable indices across configs).
def landmark_indices(co_body, co_eyes):
    eyes = co_eyes
    left = eyes[eyes[:, 0] > 0]
    right = eyes[eyes[:, 0] < 0]
    eye_l, eye_r = left.mean(axis=0), right.mean(axis=0)
    eye_z = (eye_l[2] + eye_r[2]) / 2
    idx = {}
    for side, sign in (("l", 1), ("r", -1)):
        m = (np.abs(co_body[:, 2] - (eye_z - 0.045)) < 0.012) & (np.abs(co_body[:, 1] - (eye_l[1] + 0.085)) < 0.03) & (sign * co_body[:, 0] > 0.04) & (sign * co_body[:, 0] < 0.11)
        cand = np.where(m)[0]
        if len(cand) == 0:
            raise RuntimeError("ear landmark not found")
        idx[f"ear_{side}"] = int(cand[np.argmax(sign * co_body[cand, 0])])
    return idx


def eye_centers(co_eyes):
    left = co_eyes[co_eyes[:, 0] > 0].mean(axis=0)
    right = co_eyes[co_eyes[:, 0] < 0].mean(axis=0)
    front = float(co_eyes[:, 1].min())
    return left, right, front


def apply_config(macros, targets):
    for k, v in BASE_MACROS.items():
        HOP.set_value(k, macros.get(k, v), entity_reference=human)
    TargetService.reapply_macro_details(human)
    keys = human.data.shape_keys.key_blocks if human.data.shape_keys else []
    loaded = {kb.name for kb in keys}
    for tname, w in targets:
        sk = "cfg_" + tname.replace("/", "_")
        if sk not in loaded:
            TargetService.load_target(human, os.path.join(TARGETS, tname + ".target.gz"), weight=0.0, name=sk)
    for kb in human.data.shape_keys.key_blocks:
        if kb.name.startswith("cfg_"):
            kb.value = 0.0
    for tname, w in targets:
        human.data.shape_keys.key_blocks["cfg_" + tname.replace("/", "_")].value = w
    HumanService.refit(human)
    apply_pose()
    bpy.context.view_layer.update()


# --------------------------------------------------------------------------------------
# Capture configurations
# --------------------------------------------------------------------------------------
configs = {}
anchors = {}
apply_config({}, [])
base = capture()
configs["basis"] = base
zshift = 0.0
dg = bpy.context.evaluated_depsgraph_get()
body_raw_min = None


def body_zmin_uncorrected():
    dg = bpy.context.evaluated_depsgraph_get()
    oe = human.evaluated_get(dg)
    me = oe.to_mesh()
    z = min((oe.matrix_world @ v.co).z for v in me.vertices)
    oe.to_mesh_clear()
    return z


anchors["basis"] = anchors_from(base[human.name], body_zmin_uncorrected())
lm = landmark_indices(base[human.name], base[items["eyes"].name])
print("LANDMARKS", lm)

for name, (macros, targets) in BODY.items():
    apply_config(macros, targets)
    configs[name] = capture()
    anchors[name] = anchors_from(configs[name][human.name], body_zmin_uncorrected())
    print("CONFIG", name)
for name, macros in list(AGE.items()) + list(HEIGHT.items()):
    apply_config(macros, [])
    configs[name] = capture()
    anchors[name] = anchors_from(configs[name][human.name], body_zmin_uncorrected())
    print("CONFIG", name)
for name, targets in FACE.items():
    apply_config({}, targets)
    configs[name] = capture()
    anchors[name] = anchors_from(configs[name][human.name], body_zmin_uncorrected())
    print("CONFIG", name)
apply_config({}, [])


def add_landmarks(cfg_name):
    co = configs[cfg_name]
    a = anchors[cfg_name]
    el, er, front = eye_centers(co[items["eyes"].name])
    a["eye_l"], a["eye_r"] = el.tolist(), er.tolist()
    a["eyes_front"] = front
    for k, i in lm.items():
        a[k] = co[human.name][i].tolist()


for c in configs:
    add_landmarks(c)

# --------------------------------------------------------------------------------------
# Build static export meshes with morph targets
# --------------------------------------------------------------------------------------
export_col = bpy.data.collections.new("export")
bpy.context.scene.collection.children.link(export_col)
dg = bpy.context.evaluated_depsgraph_get()


def static_copy(src, name, vert_idx=None):
    oe = src.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(oe, preserve_all_data_layers=True, depsgraph=dg)
    me.name = name
    ob = bpy.data.objects.new(name, me)
    export_col.objects.link(ob)
    ob.matrix_world = Matrix.Identity(4)
    me.vertices.foreach_set("co", configs["basis"][src.name].reshape(-1))
    me.update()
    keep = None
    if vert_idx is not None:
        keep = np.zeros(len(me.vertices), dtype=bool)
        keep[vert_idx] = True
    ob.shape_key_add(name="Basis", from_mix=False)
    for cname, co in configs.items():
        if cname == "basis":
            continue
        delta = np.abs(co[src.name] - configs["basis"][src.name])
        if keep is not None:
            delta = delta[keep]
        if float(delta.max()) < 2e-4:
            continue
        sk = ob.shape_key_add(name=cname, from_mix=False)
        sk.data.foreach_set("co", co[src.name].reshape(-1))
        sk.value = 0.0  # default glTF weight 0: morphs are applied by the app
    if keep is not None:
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep[v.index]], context="VERTS")
        bm.to_mesh(me)
        bm.free()
    for vg in list(ob.vertex_groups):
        ob.vertex_groups.remove(vg)
    for mod in list(ob.modifiers):
        ob.modifiers.remove(mod)
    return ob


def loose_parts(obj):
    me = obj.data
    n = len(me.vertices)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


exports = {}  # id -> object
# body: remove helper geometry later (after masks are computed)
body = static_copy(human, "body")
exports["body"] = body
exports["eyes"] = static_copy(items["eyes"], "eyes")
exports["eyelashes"] = static_copy(items["eyelashes"], "eyelashes")
exports["teeth"] = static_copy(items["teeth"], "teeth")
for hname in HAIR:
    exports["hair_" + hname] = static_copy(items["hair_" + hname], "hair_" + hname)
for b in EYEBROWS:
    exports["brows_" + b] = static_copy(items["brows_" + b], "brows_" + b)
for fid in FACIAL:
    exports[fid] = static_copy(items[fid], fid)

garment_vertidx = {}
for gid, src, sel, slot in GARMENTS:
    sobj = source_clothes[src]
    if sel == "all":
        idx = None
    else:
        parts = loose_parts(sobj)
        co = configs["basis"][sobj.name]
        # pieces centred above 60% of body height are the upper garment (tops/jackets), the rest the lower one
        split_z = 0.6 * float(configs["basis"][human.name][:, 2].max())
        upper = [p for p in parts if co[p, 2].mean() > split_z]
        lower = [p for p in parts if p not in upper]
        chosen = upper if sel == "upper" else lower
        idx = np.array(sorted(i for p in chosen for i in p), dtype=np.int64)
        if not len(idx):
            # One connected mesh (e.g. a shirt tucked into belted jeans): split at the belt line instead.
            # The tucked-in shirt below the belt is hidden inside the trousers anyway.
            belt_z = float(bone_world("pelvis").z) + 0.06
            idx = np.where(co[:, 2] > belt_z if sel == "upper" else co[:, 2] <= belt_z)[0].astype(np.int64)
            print("SPLIT BY HEIGHT", gid, src, "parts", len(parts), "belt z", round(belt_z, 3), "verts", len(idx))
    garment_vertidx[gid] = (src, idx)
    exports[gid] = static_copy(sobj, gid, vert_idx=idx)
    print("GARMENT", gid, len(exports[gid].data.vertices))

# Skin masks: body vertices hidden by each garment (delete-group verts nearest to that piece).
human_co = configs["basis"][human.name]
mask_bits = {}
bit = 0
MASK_ATTRS = ("_HIDEA", "_HIDEB", "_HIDEC")  # 24 bits each (exactly representable as float32)
masks = np.zeros((len(human_co), len(MASK_ATTRS)), dtype=np.int64)


def covered_by_geometry(src):
    """Skin under a garment that ships without delete-groups: a body vertex is covered when a ray along
    its outward normal hits the garment within 3 cm. One erosion ring keeps openings (neck, cuffs, hems)
    from showing holes."""
    bm = bmesh.new()
    bm.from_mesh(human.data)
    bm.verts.ensure_lookup_table()
    for v, co in zip(bm.verts, human_co):
        v.co = Vector(co)
    bm.normal_update()
    gco = configs["basis"][source_clothes[src].name]
    tree = BVHTree.FromPolygons([Vector(c) for c in gco], [tuple(p.vertices) for p in source_clothes[src].data.polygons])
    hit = np.zeros(len(human_co), dtype=bool)
    for v in bm.verts:
        h = tree.ray_cast(v.co + v.normal * -0.002, v.normal, 0.03)
        hit[v.index] = h[0] is not None
    eroded = hit.copy()
    for e in bm.edges:
        a, b = e.verts[0].index, e.verts[1].index
        if hit[a] != hit[b]:
            eroded[a] = eroded[b] = False
    bm.free()
    return [int(i) for i in np.where(eroded)[0]]


mask_members = {}
for src, vg_name in delete_groups.items():
    vg = human.vertex_groups.get(vg_name)
    if vg is not None:
        gi = vg.index
        mask_members[src] = [v.index for v in human.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
for src in source_clothes:
    if src not in mask_members:
        mask_members[src] = covered_by_geometry(src)
        print("GEOMETRIC MASK", src, len(mask_members[src]))

for src, members in mask_members.items():
    pieces = [(gid, idx) for gid, (s, idx) in garment_vertidx.items() if s == src]
    trees = []
    for gid, idx in pieces:
        pco = configs["basis"][source_clothes[src].name]
        pco = pco if idx is None else pco[idx]
        t = kdtree.KDTree(len(pco))
        for i, p in enumerate(pco):
            t.insert(p, i)
        t.balance()
        trees.append((gid, t))
    for gid, _ in pieces:
        mask_bits[gid] = bit
        bit += 1
    for vi in members:
        p = human_co[vi]
        best = min(trees, key=lambda gt: gt[1].find(p)[2])[0] if len(trees) > 1 else trees[0][0]
        b_ = mask_bits[best]
        masks[vi, b_ // 24] |= (1 << (b_ % 24))
print("MASK BITS", mask_bits)
assert bit <= 24 * len(MASK_ATTRS), f"too many garment pieces for the skin masks: {bit}"

# Write masks as float point attributes (exported as _HIDEA/_HIDEB/_HIDEC custom glTF attributes).
for col, name in enumerate(MASK_ATTRS):
    attr = body.data.attributes.new(name, "FLOAT", "POINT")
    attr.data.foreach_set("value", masks[:, col].astype(np.float32))

# Remove helper geometry (joint cubes, helper tights/skirt/hair) from the body.
helper_groups = [vg.index for vg in human.vertex_groups if vg.name.lower().startswith(("helper", "joint"))]
helper = np.zeros(len(human_co), dtype=bool)
for v in human.data.vertices:
    if any(g.group in helper_groups and g.weight > 0.0 for g in v.groups):
        helper[v.index] = True
print("HELPER VERTS", int(helper.sum()), "of", len(helper))
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if helper[v.index]], context="VERTS")
bm.to_mesh(body.data)
bm.free()

# Hide originals from the scene before export / thumbnails.
for o in bpy.data.objects:
    if o.users_collection and export_col not in o.users_collection:
        o.hide_render = True
        o.hide_set(True)

# --------------------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------------------
def export(ob, filename):
    bpy.ops.object.select_all(action="DESELECT")
    ob.hide_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(GDIR, filename + ".gltf"),
        export_format="GLTF_SEPARATE",
        export_texture_dir="../tex",
        use_selection=True,
        export_apply=False,
        export_yup=True,
        export_morph=True,
        export_morph_normal=True,
        export_skins=False,
        export_animations=False,
        export_attributes=True,
        export_cameras=False,
        export_lights=False,
        export_extras=False,
    )


material_textures = {}
for key, ob in exports.items():
    texs = []
    for slot in ob.material_slots:
        if slot.material and slot.material.node_tree:
            for n in slot.material.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    texs.append(os.path.basename(n.image.filepath or n.image.name))
    material_textures[key] = sorted(set(texs))
    export(ob, key)
    print("EXPORTED", key, len(ob.data.vertices), "morphs", len(ob.data.shape_keys.key_blocks) - 1 if ob.data.shape_keys else 0)


def to_yup(v):
    return [float(v[0]), float(v[2]), float(-v[1])]


def anchors_yup(a):
    out = {}
    for k, v in a.items():
        if isinstance(v, list) and len(v) == 3 and k not in ("neck_radii", "waist_radii"):
            out[k] = to_yup(v)
        else:
            out[k] = v
    return out


meta = {
    "gender": GENDER,
    "assetSource": "MakeHuman system assets (CC0) via MPFB2 " + "2.0.18",
    "configs": {"body": list(BODY.keys()), "face": list(FACE.keys()), "age": list(AGE.keys()), "height": list(HEIGHT.keys())},
    "anchors": {k: anchors_yup(v) for k, v in anchors.items()},
    "maskBits": mask_bits,
    "garments": {gid: {"source": src, "slot": slot, "pack": PACK_OF.get(src, "makehuman_system_assets"), "license": "CC0"} for gid, src, sel, slot in GARMENTS},
    "hair": ["hair_" + h for h in HAIR],
    "eyebrows": ["brows_" + b for b in EYEBROWS],
    "facialHair": list(FACIAL.keys()),
    "textures": material_textures,
    "skin": skin_name,
}
with open(os.path.join(GDIR, "meta.json"), "w") as f:
    json.dump(meta, f, indent=1)

import sys as _sys
print("BUILD DONE", GENDER)
_sys.exit(0)
# --------------------------------------------------------------------------------------
# Thumbnails (legacy Blender renders; superseded by frontend/scripts/render-avatar-thumbnails.mjs)
# --------------------------------------------------------------------------------------
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = 256
try:
    sc.eevee.taa_render_samples = 16
except Exception:
    pass
sc.view_settings.view_transform = "Standard"
bpy.ops.object.light_add(type="AREA", location=(1.5, -3, 3))
key = bpy.context.object
key.data.energy = 600
key.data.size = 4
bpy.ops.object.light_add(type="AREA", location=(-2, -2, 1.5))
bpy.context.object.data.energy = 300
bpy.context.object.data.size = 4
bpy.ops.object.light_add(type="AREA", location=(0, 3, 2))
bpy.context.object.data.energy = 250
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.data.type = "ORTHO"
sc.camera = cam


def frame(objs, pad=1.15, view="front"):
    pts = []
    for o in objs:
        for v in o.data.vertices:
            pts.append(o.matrix_world @ v.co)
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
    size = max(max(xs) - min(xs), max(zs) - min(zs)) * pad
    if view == "three_quarter":
        cam.location = (cx - 2.2, cy - 2.6, cz + 0.15)
        cam.rotation_euler = (math.radians(87), 0, math.radians(-40))
    else:
        cam.location = (cx, cy - 4, cz)
        cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.ortho_scale = size


def show_only(objs):
    for o in export_col.objects:
        vis = o in objs
        o.hide_render = not vis
        o.hide_set(not vis)


def set_shape(objs, name, value):
    for o in objs:
        if o.data.shape_keys and name in o.data.shape_keys.key_blocks:
            o.data.shape_keys.key_blocks[name].value = value


def render(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


g = GENDER
head_set = [exports["body"], exports["eyes"], exports["eyelashes"]]
default_brows = exports["brows_eyebrow001"]
default_hair = exports["hair_long01" if IS_F else "hair_short02"]
outfit = [exports["top_white_tee"], exports["bottom_jeans_light"], exports["shoes_white_sneakers"]]


def head_frame():
    hb = anchors["basis"]["head"]
    cam.location = (0, -4, hb[2] + 0.08)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.ortho_scale = 0.36


# garments, shoes, hat: the item alone
for gid, src, sel, slot in GARMENTS:
    ob = exports[gid]
    show_only([ob])
    frame([ob], view="three_quarter" if slot == "footwear" else "front")
    render(os.path.join(THUMBS, f"{g}_{gid}.png"))
# hair on head
for hname in HAIR:
    show_only(head_set + [default_brows, exports["hair_" + hname]])
    head_frame()
    cam.data.ortho_scale = 0.5
    cam.location = (0, -4, anchors["basis"]["head"][2] + 0.04)
    render(os.path.join(THUMBS, f"{g}_hair_{hname}.png"))
# eyebrows on face (close-up)
for b in EYEBROWS:
    show_only(head_set + [exports["brows_" + b], default_hair])
    el = anchors["basis"]["eye_l"] if "eye_l" in anchors["basis"] else None
    cam.location = (0, -4, configs["basis"][items["eyes"].name][:, 2].mean() + 0.01)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.ortho_scale = 0.16
    render(os.path.join(THUMBS, f"{g}_brows_{b}.png"))
# face presets
face_objs = head_set + [default_brows, default_hair]
for fname in ["basis"] + list(FACE.keys()):
    show_only(face_objs)
    if fname != "basis":
        set_shape(face_objs, fname, 1.0)
    head_frame()
    render(os.path.join(THUMBS, f"{g}_face_{fname}.png"))
    if fname != "basis":
        set_shape(face_objs, fname, 0.0)
# body types (full figure in the default outfit)
body_objs = head_set + [default_brows, default_hair] + outfit
for bname in ["basis"] + list(BODY.keys()):
    show_only(body_objs)
    if bname != "basis":
        set_shape(body_objs, bname, 1.0)
    frame(body_objs, pad=1.05)
    render(os.path.join(THUMBS, f"{g}_body_{bname}.png"))
    if bname != "basis":
        set_shape(body_objs, bname, 0.0)
# full preview
show_only(body_objs)
sc.render.resolution_x, sc.render.resolution_y = 600, 900
frame(body_objs, pad=1.05)
cam.data.ortho_scale = 2.0
render(os.path.join(OUT, f"preview_{g}.png"))
print("BUILD DONE", GENDER)
