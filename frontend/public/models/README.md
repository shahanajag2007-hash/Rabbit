# Avatar assets

`avatar/` contains the realistic 3D avatar used by the Avatar Studio, Complete Look and Final Look pages.

## Source and licence

Everything is CC0 (public domain); no attribution is legally required, credit is given here anyway.

* **MakeHuman system assets** (CC0 1.0): base meshes, skin textures (young, middle-aged and old),
  eyes, eyebrows, eyelashes, teeth, 10 hairstyles, casual/elegant/work suits and shoes.
* **MakeHuman CC0 asset packs** (<https://static.makehumancommunity.org/assets/assetpacks.html>):
  * `shirts01`: polo shirt (namuhekam), fisherman sweater, basic tee, camisole, keyhole tank (toigo)
  * `dress01`: shift dress, halter midi dress, camisole dress with full skirt (toigo), kimono
    (mindfront), long tunic (wdg)
  * `pants01`: wool trousers, harem pants (toigo), cargo pants (cortu)
  * `skirts01`: long full skirt (toigo)
  * `shoes01`: ballet flats, ankle boots (toigo)
  * `suits01`: skirt suit, double-breasted trouser suit, double-breasted suit, dinner-jacket suit (toigo)
  * `bodyparts05`: scruffy beard (wdg), full beard (grinsegold), long beard and moustache (rehmanpolanski)
* Generated with **MPFB2 2.0.18** for Blender (code GPL-3.0; generated characters are CC0).
* Only the MakeHuman logo was removed from the plain white T-shirt texture.
* `tex/age_detail_*.png` are derived from the MakeHuman middle-aged / old skins (`age_detail.py`).
* Accessories (glasses, sunglasses, earrings, necklace, bracelet, watch, belt, handbag, tote) are
  simple meshes modelled in code (`src/components/avatar/Accessories.tsx`).

## Layout

```
avatar/
  female/ male/ neutral/   one folder per base model (MakeHuman gender 0 / 1 / 0.5), each with
                           one glTF (+ .bin) per item and meta.json (anchors, skin masks, configs)
    body.gltf          textured body with morph targets (see below)
    eyes / eyelashes / teeth / brows_eyebrow001-012 / hair_* / facial_* .gltf
    top_* / outer_* / bottom_* / full_* / dress_* / shoes_* / hat_fedora .gltf   garments, each fitted to the body
  tex/                shared textures (skins, eyes, hair, garments, *_neutral tintable textures, age detail maps)
  thumbs/             option thumbnails rendered with the app's own three.js avatar
  skin_average.json   average colour per skin texture (for honest skin-tone swatches)
```

Every garment, hair and beard mesh carries the same morph targets as the body, each re-fitted in MPFB
for that configuration so clothes and hair follow the body exactly:

* body presets (female `slim athletic curvy full`, male `slim athletic broad heavy`, neutral `slim athletic curvy broad`)
* `height_short` / `height_tall`: MakeHuman's height macro (proportions change, not just size)
* `age_14`, `age_18`, `age_45`, `age_65`, `age_85`: MakeHuman's age macro (the basis is 25)
* `face_*`, `nose_*`, `lips_*`, `eyes_*`

The body also stores `_HIDEA/_HIDEB/_HIDEC` vertex attributes: bit masks of the skin covered by each
garment piece (from the asset's delete-groups, or measured by ray casting when an asset has none),
used to stop skin poking through clothes. Loading is lazy: only the parts being worn are fetched.

## How the app uses them

* **Height**: the height morph is blended until the crown of the morphed head reaches the profile
  height; a small uniform scale calibrates the rest (`heightMorph`, `RealisticAvatar.tsx`).
* **Weight**: height and weight together blend the lighter / heavier body presets (`estimateBodyFromProfile`).
* **Age**: neighbouring age morphs are blended linearly; from 30 the skin shader adds the age detail
  maps (forehead lines, crow's feet, nasolabial folds) without changing the chosen skin tone.
* **Hair**: alpha-tested hair never lowers the canvas alpha (no see-through strands); the scalp under
  the hair and beards gets a darker root tone with a soft hairline (`scalpCoverage.ts`, `skinShader.ts`).
* **Layering**: where an untucked top or jacket covers a bottom, the bottom is pulled just inside it
  (`layerFit.ts`), so garments fitted independently do not poke through each other.

## Pose and proportions

MakeHuman's rest pose is an A-pose with a wide stance. The build re-poses every configuration
in Blender (`apply_pose` in `build_avatar.py`): legs brought under the hips with flat feet, arms
hanging naturally with a slight elbow bend, forearms turned so the palms face the thighs, and
relaxed fingers. The arm angle is chosen per body preset by measuring the hip surface at hand
height, so hands never sink into wider hips.

## Rebuilding

The pipeline lives in `tools/avatar-pipeline/` (repository root):

1. Install Blender 4.2+ (tested with 5.2).
2. `tools/avatar-pipeline/setup.sh` downloads MPFB2, the CC0 system assets and the CC0 packs above, and
   installs MPFB into an isolated Blender profile (your normal Blender setup is untouched).
3. `tools/avatar-pipeline/build_all.sh frontend/public/models/avatar` builds the three models, removes the logo,
   post-processes textures and writes the age detail maps (about 10 minutes).
4. With `npm run dev` running in `frontend/`, run `node scripts/render-avatar-thumbnails.mjs` to re-render the thumbnails.

## Hairstyles beyond the 10 meshes

`src/components/avatar/hairStyles.ts` builds ~50 styles from the 10 real hair meshes. A shader
(`hairShader.ts`) can trim, fade, wave, lift, crop or re-part a mesh, or keep only its scalp or fringe.
Braids, ponytails, buns and gajra are modelled in three.js (`ProceduralHair.tsx`) on head anchors and on
the measured body surface.

## Not available in any CC0 pack (shown disabled in the studio)

Hoodie, long coat, saree, sherwani, sandals, light stubble. To add one, export a MakeHuman-compatible
`.mhclo` asset, add it to `GARMENTS` in `build_avatar.py` and to `avatarCatalog.ts`, then rebuild.
