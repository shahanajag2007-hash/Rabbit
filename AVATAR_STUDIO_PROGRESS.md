# Avatar Studio personalisation — progress checkpoint

This is a checkpoint, not a substitute for reading the code. Last updated 2026-10-13 (session 3).

## Session 1
- Model switching re-initialises model-dependent settings in the store (`reconcileAvatar`), store v4.
- Continuous height+weight body estimate applied to morphs.
- Hairstyle system wired up (`hairShader.ts`, `ProceduralHair.tsx`), ~52 styles, thumbnails.

## Session 2 (hair realism, clothing, height, weight, age)

Root causes found
- Height "did nothing": the camera distance was proportional to the avatar's height, so every height
  filled the frame identically. Also, stature was measured to the shoe-grounded floor, not the foot.
- Hair looked like a wig: alpha-tested hair wrote its texture alpha into the transparent canvas, so
  the page background showed through every strand edge; bare skin ran up to a hard hairline.
- Garments fitted independently poked through each other where a top overlaps a bottom.
- Crash when changing garments: offsets computed for the new mesh were written into the previous one.

Done
- [x] Hair: alpha-preserving blending; scalp/root shading (`scalpCoverage.ts`, `skinShader.ts`).
- [x] Age: morphs at 14/18/45/65/85 blended continuously; skin wrinkle detail from MakeHuman's aged
      skins (`tools/avatar-pipeline/age_detail.py` -> `tex/age_detail_*.png`).
- [x] Height: MakeHuman height morphs + barefoot-stature calibration, fixed-reference framing, height
      scale and tag, grounding on the actual shoe soles (`Grounding`).
- [x] Clothing: CC0 packs integrated through the Blender build (polo, sweater, formal shirt, dresses,
      suits, kimono, tunic, harem pants, long skirt, cargo/wool trousers, flats, ankle boots, beards);
      `full` slot; men's/women's categories; layer fit (`layerFit.ts`); geometric skin masks.
- [x] Thumbnails re-rendered (468).
- [x] `npm run build` passes; backend `pytest` 14 passed.
- [x] Full `node scripts/verify-avatar.mjs` run: every avatar check passed (54 hairstyles, 43 garments x 3 models).

## Known limitations
- No CC0 hoodie, long coat, saree, sherwani, sandals or stubble: listed as unavailable.
- Small layering specks remain for very baggy bottoms under fitted tops (harem pants + sweater).
- Each model folder is ~80 MB (morph targets on every mesh); only worn parts load (~15 MB first view).

## Session 3
- Female starter outfit was a blush-tinted graphic tee (rendered muddy brown with a large logo) and skinny
  jeans. Replaced with a teal kurta-style tunic, cream salwar-style harem pants and ballet flats
  (`MODEL_DEFAULT_OUTFIT.female`). Store v5 migration swaps the old starter outfit only if untouched.
- `verify-avatar.mjs` now also checks the rendered female starter outfit.
- Scratch helper scripts removed from `frontend/node_modules/`.
- Full beard reads as heavy, with hard edges, in the thumbnail (CC0 mesh); left as-is for now.
- Hair, from user reference images (styles only, no images copied):
  - New styles (67 total): big glam waves, side-parted glam waves, waves with fringe, wavy lob, long
    voluminous curls, curly shoulder-length, space buns, half-up space buns, high pigtails, curly
    pigtails, spiky textured top, textured fringe, faux hawk.
  - Shader mods `volume` (A-line body) and `spike` (clumped spikes; centre=1 for a faux hawk);
    procedural placements `pair_top` (space buns) and `pair_high` (pigtails, `hangSide` path).
  - Highlights (`hairHighlight`, HAIR_HIGHLIGHTS): balayage ribbons + face-framing pieces from forehead
    height down, on hair meshes and procedural parts. Every hair layer now gets the head frame
    (`shaderMod(l.mod ?? {})`), which the highlights need.
  - Colours: honey blonde, rose pink, pastel pink, lavender, purple, blue.
  - Thumbnails rendered for the new keys (`render-avatar-thumbnails.mjs --keys=...`).
  - `verify-avatar.mjs`: highlight checks; navigation timeout 120 s (leaving /avatar takes ~30 s
    under SwiftShader).
- Dev note: editing a module in the store's import chain while Vite runs makes the verify/shot scripts
  drive an orphaned store instance (HMR `?t=` URLs). Restart the dev server before running them.
- Rejected: afro01 as a curly crown over long hair (looked like a knitted cap).
- Professional look (user feedback, same day):
  - Removed from the catalogue (assets kept): fitted graphic tee (logo), camisole top, keyhole tank,
    sport crop top, denim shorts. "Shorts" recommendations show cargo trousers. Store v6 migration swaps
    them for the model's starter piece.
  - Sleeveless dresses get a fitted long-sleeve layer underneath (`underlayer`, drawn in plain colour, no
    print; LayerFit keeps it inside the dress) and are lengthened below the hips (`lengthen`, `Lengthen`
    writes the dress's `aLayer`). Renamed: long-sleeve shift / maxi / A-line dress.
  - Wide lehenga-style skirt (`overTop`): the top is tucked inside the skirt (LayerFit reversed), which
    stops the skirt bursting through the tunic.
  - Bust reduced in the Blender build (`cupsize` 0.5 -> 0.3; curvy/full 0.8/0.75 -> 0.4). Previous
    assets backed up in C:/Users/shaha/avatar-build/backup_models_2026-10-13. Pipeline work dir:
    AVATAR_WORK=/c/Users/shaha/avatar-build.
  - Could not reproduce the reported navy-top-with-beige-patches back view (tried tee/sweater/polo/
    tunic/jacket/overalls on all models and heavier bodies).
