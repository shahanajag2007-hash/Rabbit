/**
 * Hairstyle registry.
 *
 * The CC0 MakeHuman pack ships 10 hair meshes (fitted to every model and every body/face/age morph
 * in the Blender build). Every hairstyle below is built from those real meshes:
 *
 *  - `layers`: one or two real hair meshes. A layer can be modified in its shader (HairMod):
 *      keep 'scalp'  - removes ponytail01's tail, leaving its slicked-back scalp section
 *      keep 'fringe' - keeps only the front section (a fringe / side sweep laid over another layer)
 *      trim          - cuts the hair at a height (shoulder-length, jaw-length, ear-length)
 *      fade          - removes hair below a line, dithered (fade) or hard (undercut), so the
 *                      shorter layer underneath (or skin) shows on the sides and back
 *      wave          - displaces strands into waves / curls with extra volume
 *      volume        - spreads the lengths out (A-line body and bounce)
 *      spike         - pushes clumps on the top up and out (spiky / faux hawk)
 *      lift          - raises the front-top section (quiff, pompadour)
 *      crop          - pulls the strands onto the scalp (clipper-cut sides under fades)
 *      part          - moves a centre parting to the side (rotates the top within the scalp shape)
 *      mirror        - mirrors the mesh (moves a side part to the other side)
 *  - `parts`: procedural strands modelled in three.js (ProceduralHair.tsx) and attached to head
 *    anchors measured on the model: braids (three-strand, fishtail, French, crown), ponytails, buns
 *    (coiled, braided, smooth, messy) and gajra (jasmine strings). They are tinted with the same
 *    hair colour.
 *
 * Every style works on every model (all three models carry all 10 meshes), so gender only decides
 * the default style and which collection is listed first. Thumbnails are rendered from the actual
 * result with scripts/render-avatar-thumbnails.mjs.
 */
import type { Presentation } from './avatarCatalog'

export type HairCollection = 'feminine' | 'masculine' | 'flexible'
export type HairGroup = 'Braids' | 'Ponytails' | 'Buns & updos' | 'Open & long' | 'Medium & bobs' | 'Short' | 'Fades & undercuts' | 'Curly & textured'
export const HAIR_GROUP_ORDER: HairGroup[] = ['Braids', 'Ponytails', 'Buns & updos', 'Open & long', 'Medium & bobs', 'Short', 'Fades & undercuts', 'Curly & textured']
export const HAIR_GROUPS: HairGroup[] = HAIR_GROUP_ORDER

/** The real hair meshes (glTF per model). */
export type HairMesh = 'hair_long01' | 'hair_ponytail01' | 'hair_braid01' | 'hair_bob01' | 'hair_bob02' | 'hair_afro01' | 'hair_short01' | 'hair_short02' | 'hair_short03' | 'hair_short04'
export const HAIR_MESHES: HairMesh[] = ['hair_long01', 'hair_ponytail01', 'hair_braid01', 'hair_bob01', 'hair_bob02', 'hair_afro01', 'hair_short01', 'hair_short02', 'hair_short03', 'hair_short04']

/** Heights used by trim / fade, resolved from the model's anchors in ProceduralHair.ts. */
export type HairLevel = 'shoulder' | 'collarbone' | 'jaw' | 'ear' | 'chest' | 'brow'

export interface HairMod {
  keep?: 'scalp' | 'fringe'
  trim?: HairLevel
  /** 0 = ear line, 1 = crown. Hair below `from` is removed; between from..to it thins out (dithered). */
  fade?: { from: number; to: number }
  wave?: { amp: number; freq: number }
  /** Extra body in the lengths (metres of outward spread at chest level). */
  volume?: number
  /** Textured spikes on the top; centre 1 = a central strip (faux hawk). */
  spike?: { amount: number; centre?: number }
  lift?: number
  /** 0..1: how far strands are pulled onto the scalp (1 = skin-tight clipper cut). */
  crop?: number
  /** Moves a centre parting sideways: rotation (radians) of the top of the head, + = to the model's left. */
  part?: number
  mirror?: boolean
}

export interface HairLayer {
  mesh: HairMesh
  mod?: HairMod
}

export type BraidPath = 'back' | 'back_pair' | 'front_pair' | 'side' | 'french' | 'crown'
/** pair_high = two pigtails tied high behind the ears. */
export type TailPlace = 'high' | 'mid' | 'low' | 'side' | 'pair' | 'pair_high' | 'half_up'
/** pair_top = two buns on the top of the head (space buns). */
export type BunPlace = 'high' | 'low' | 'half_up' | 'pair_top'

export type HairPart =
  | { kind: 'braid'; path: BraidPath; style?: 'three' | 'fishtail'; length?: number; width?: number; gajra?: boolean }
  | { kind: 'tail'; place: TailPlace; length: number; width?: number; curl?: number; sleek?: boolean }
  | { kind: 'bun'; place: BunPlace; size: number; style: 'coil' | 'braided' | 'smooth' | 'messy'; gajra?: boolean }

export interface HairStyle {
  id: string
  label: string
  group: HairGroup
  collections: HairCollection[]
  /** Part of the Indian hairstyles collection. */
  indian?: boolean
  layers: HairLayer[]
  parts?: HairPart[]
  available?: boolean
  note?: string
  /** Thumbnail camera: back-of-head styles are shown from behind. */
  thumbView?: 'front' | 'back' | 'three_quarter' | 'back_three_quarter'
  /** Short description of how the style is built (shown as a tooltip). */
  build: string
}

const F: HairCollection[] = ['feminine']
const M: HairCollection[] = ['masculine']
const FX: HairCollection[] = ['feminine', 'flexible']
const MX: HairCollection[] = ['masculine', 'flexible']
const ALL: HairCollection[] = ['feminine', 'masculine', 'flexible']

const SCALP: HairLayer = { mesh: 'hair_ponytail01', mod: { keep: 'scalp' } }
/** Close-cropped sides under fades and undercuts (short04, itself fading out at the very bottom). */
const SIDES = (from = 0.05): HairLayer => ({ mesh: 'hair_short04', mod: { fade: { from: -0.25, to: from }, crop: 0.8 } })

export const HAIRSTYLES: HairStyle[] = [
  // ------------------------------------------------------------------ Braids (Indian collection)
  { id: 'in_single_braid', label: 'Single traditional braid', group: 'Braids', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'braid', path: 'back', length: 0.62 }], thumbView: 'back_three_quarter', build: 'Slicked scalp mesh + long three-strand braid (choti) down the back' },
  { id: 'in_double_braids', label: 'Double braids', group: 'Braids', collections: FX, indian: true, layers: [SCALP], parts: [{ kind: 'braid', path: 'front_pair', length: 0.4 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + two braids worn over the shoulders' },
  { id: 'in_two_long_braids', label: 'Two long braids', group: 'Braids', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'braid', path: 'back_pair', length: 0.6 }], thumbView: 'back_three_quarter', build: 'Slicked scalp mesh + two long braids down the back' },
  { id: 'in_side_braid', label: 'Side braid', group: 'Braids', collections: FX, indian: true, layers: [SCALP], parts: [{ kind: 'braid', path: 'side', length: 0.44 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + one braid over the shoulder' },
  { id: 'in_french_braid', label: 'French braid', group: 'Braids', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'braid', path: 'french', length: 0.5 }], thumbView: 'back', build: 'Slicked scalp mesh + braid woven from the crown down the back' },
  { id: 'in_fishtail_braid', label: 'Fishtail braid', group: 'Braids', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'braid', path: 'back', style: 'fishtail', length: 0.5 }], thumbView: 'back_three_quarter', build: 'Slicked scalp mesh + fine-weave fishtail braid' },
  { id: 'in_crown_braid', label: 'Crown braid', group: 'Braids', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'braid', path: 'crown', width: 0.032 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + braid wrapped around the crown' },
  { id: 'in_flower_braid', label: 'Braid with gajra', group: 'Braids', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'braid', path: 'back', length: 0.6, gajra: true }], thumbView: 'back_three_quarter', build: 'Traditional braid adorned with a jasmine string (gajra)' },
  { id: 'hair_braid01', label: 'Braid with side fringe', group: 'Braids', collections: F, layers: [{ mesh: 'hair_braid01' }], thumbView: 'three_quarter', build: 'MakeHuman braid01 mesh' },

  // ------------------------------------------------------------------ Ponytails
  { id: 'in_high_ponytail', label: 'High ponytail', group: 'Ponytails', collections: FX, indian: true, layers: [SCALP], parts: [{ kind: 'tail', place: 'high', length: 0.36 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + ponytail tied at the crown' },
  { id: 'hair_ponytail01', label: 'Low ponytail', group: 'Ponytails', collections: ALL, indian: true, layers: [{ mesh: 'hair_ponytail01' }], thumbView: 'back_three_quarter', build: 'MakeHuman ponytail01 mesh (also the tied-back style)' },
  { id: 'in_double_ponytail', label: 'Double ponytail', group: 'Ponytails', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'tail', place: 'pair', length: 0.26 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + two low ponytails' },
  { id: 'in_side_ponytail', label: 'Side ponytail', group: 'Ponytails', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'tail', place: 'side', length: 0.34 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + ponytail over one shoulder' },
  { id: 'in_sleek_ponytail', label: 'Sleek ponytail', group: 'Ponytails', collections: FX, indian: true, layers: [SCALP], parts: [{ kind: 'tail', place: 'mid', length: 0.46, width: 0.022, sleek: true }], thumbView: 'back_three_quarter', build: 'Slicked scalp mesh + long smooth ponytail' },
  { id: 'in_curly_ponytail', label: 'Curly ponytail', group: 'Ponytails', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'tail', place: 'high', length: 0.3, width: 0.034, curl: 1 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + voluminous curly ponytail' },
  { id: 'in_high_pigtails', label: 'High pigtails', group: 'Ponytails', collections: F, layers: [SCALP], parts: [{ kind: 'tail', place: 'pair_high', length: 0.3, width: 0.022 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + two pigtails tied high behind the ears' },
  { id: 'in_curly_pigtails', label: 'Curly pigtails', group: 'Ponytails', collections: F, layers: [SCALP], parts: [{ kind: 'tail', place: 'pair_high', length: 0.26, width: 0.026, curl: 1 }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + two curly pigtails tied high' },
  { id: 'in_half_up_ponytail', label: 'Half-up ponytail', group: 'Ponytails', collections: F, indian: true, layers: [{ mesh: 'hair_long01' }], parts: [{ kind: 'tail', place: 'half_up', length: 0.2, width: 0.018 }], thumbView: 'back_three_quarter', build: 'Long hair mesh + small ponytail tied from the top section' },

  // ------------------------------------------------------------------ Buns & updos
  { id: 'in_low_bun', label: 'Traditional low bun', group: 'Buns & updos', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'bun', place: 'low', size: 0.05, style: 'coil' }], thumbView: 'back_three_quarter', build: 'Slicked scalp mesh + coiled bun (juda) at the nape' },
  { id: 'in_flower_bun', label: 'Bun with gajra', group: 'Buns & updos', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'bun', place: 'low', size: 0.05, style: 'coil', gajra: true }], thumbView: 'back_three_quarter', build: 'Coiled bun encircled by a jasmine string (gajra)' },
  { id: 'in_braided_bun', label: 'Braided bun', group: 'Buns & updos', collections: F, indian: true, layers: [SCALP], parts: [{ kind: 'bun', place: 'low', size: 0.052, style: 'braided' }], thumbView: 'back_three_quarter', build: 'Slicked scalp mesh + braid coiled into a bun' },
  { id: 'in_high_bun', label: 'High bun', group: 'Buns & updos', collections: FX, indian: true, layers: [SCALP], parts: [{ kind: 'bun', place: 'high', size: 0.046, style: 'smooth' }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + smooth top bun' },
  { id: 'in_messy_bun', label: 'Messy bun', group: 'Buns & updos', collections: FX, indian: true, layers: [SCALP], parts: [{ kind: 'bun', place: 'high', size: 0.05, style: 'messy' }], thumbView: 'three_quarter', build: 'Slicked scalp mesh + loose, textured bun' },
  { id: 'in_smooth_low_bun', label: 'Low bun', group: 'Buns & updos', collections: FX, indian: true, layers: [SCALP], parts: [{ kind: 'bun', place: 'low', size: 0.046, style: 'smooth' }], thumbView: 'back_three_quarter', build: 'Slicked scalp mesh + smooth round bun at the nape' },
  { id: 'in_space_buns', label: 'Space buns', group: 'Buns & updos', collections: F, layers: [SCALP], parts: [{ kind: 'bun', place: 'pair_top', size: 0.036, style: 'coil' }], thumbView: 'front', build: 'Slicked scalp mesh + two coiled buns on top of the head' },
  { id: 'in_half_up_space_buns', label: 'Half-up space buns', group: 'Buns & updos', collections: F, layers: [{ mesh: 'hair_long01', mod: { wave: { amp: 0.008, freq: 36 } } }], parts: [{ kind: 'bun', place: 'pair_top', size: 0.03, style: 'coil' }], thumbView: 'front', build: 'Long wavy hair left open + two small coiled buns on top' },
  { id: 'in_half_up', label: 'Half-up, half-down', group: 'Buns & updos', collections: F, indian: true, layers: [{ mesh: 'hair_long01' }], parts: [{ kind: 'bun', place: 'half_up', size: 0.03, style: 'coil' }], thumbView: 'back_three_quarter', build: 'Long hair mesh + top section twisted into a small bun' },

  // ------------------------------------------------------------------ Open & long
  { id: 'hair_long01', label: 'Long straight, centre-parted', group: 'Open & long', collections: ALL, indian: true, layers: [{ mesh: 'hair_long01' }], build: 'MakeHuman long01 mesh' },
  { id: 'in_long_wavy', label: 'Long wavy', group: 'Open & long', collections: FX, indian: true, layers: [{ mesh: 'hair_long01', mod: { wave: { amp: 0.011, freq: 42 } } }], build: 'Long hair mesh with wave displacement' },
  { id: 'in_long_curly', label: 'Long curly', group: 'Open & long', collections: F, indian: true, layers: [{ mesh: 'hair_long01', mod: { wave: { amp: 0.02, freq: 85 } } }], build: 'Long hair mesh with tight curl displacement and volume' },
  { id: 'in_glam_waves', label: 'Big glam waves', group: 'Open & long', collections: FX, layers: [{ mesh: 'hair_long01', mod: { wave: { amp: 0.014, freq: 30 }, volume: 0.03 } }], build: 'Long hair mesh with loose S-waves and extra body through the lengths' },
  { id: 'in_side_glam_waves', label: 'Side-parted glam waves', group: 'Open & long', collections: F, layers: [SCALP, { mesh: 'hair_long01', mod: { part: 0.32, wave: { amp: 0.014, freq: 30 }, volume: 0.03 } }], build: 'Deep side part with voluminous waves' },
  { id: 'in_waves_curtain_bangs', label: 'Waves with fringe', group: 'Open & long', collections: F, layers: [{ mesh: 'hair_long01', mod: { wave: { amp: 0.01, freq: 38 }, volume: 0.02 } }, { mesh: 'hair_short02', mod: { keep: 'fringe' } }], build: 'Soft waves with body + a swept fringe' },
  { id: 'in_long_side_part', label: 'Long, side-parted', group: 'Open & long', collections: F, indian: true, layers: [SCALP, { mesh: 'hair_long01', mod: { part: 0.32 } }], build: 'Long hair mesh with the parting moved to the side (scalp layer underneath)' },
  { id: 'in_long_bangs', label: 'Long with bangs', group: 'Open & long', collections: F, indian: true, layers: [{ mesh: 'hair_long01' }, { mesh: 'hair_short02', mod: { keep: 'fringe' } }], build: 'Long hair mesh + fringe from short02' },

  // ------------------------------------------------------------------ Medium & bobs
  { id: 'in_shoulder_middle_part', label: 'Shoulder-length, middle-parted', group: 'Medium & bobs', collections: FX, indian: true, layers: [{ mesh: 'hair_long01', mod: { trim: 'shoulder' } }], build: 'Long hair mesh trimmed at the shoulders' },
  { id: 'in_shoulder_side_part', label: 'Shoulder-length, side-parted', group: 'Medium & bobs', collections: FX, indian: true, layers: [SCALP, { mesh: 'hair_long01', mod: { trim: 'shoulder', part: 0.32 } }], build: 'Long hair mesh trimmed at the shoulders, parting moved to the side' },
  { id: 'in_medium_layered', label: 'Medium layered waves', group: 'Medium & bobs', collections: F, indian: true, layers: [{ mesh: 'hair_long01', mod: { trim: 'chest', wave: { amp: 0.008, freq: 36 } } }], build: 'Long hair mesh trimmed to collarbone-chest length with soft waves' },
  { id: 'in_wavy_lob', label: 'Wavy lob', group: 'Medium & bobs', collections: FX, layers: [{ mesh: 'hair_long01', mod: { trim: 'collarbone', wave: { amp: 0.012, freq: 40 }, volume: 0.02 } }], build: 'Long hair mesh cut at the collarbone with tousled waves and body' },
  { id: 'hair_bob02', label: 'Short bob', group: 'Medium & bobs', collections: FX, indian: true, layers: [{ mesh: 'hair_bob02' }], build: 'MakeHuman bob02 mesh' },
  { id: 'hair_bob01', label: 'Side-parted bob', group: 'Medium & bobs', collections: FX, indian: true, layers: [{ mesh: 'hair_bob01' }], build: 'MakeHuman bob01 mesh' },
  { id: 'mx_medium_wavy', label: 'Medium wavy', group: 'Medium & bobs', collections: ALL, layers: [{ mesh: 'hair_bob02', mod: { wave: { amp: 0.007, freq: 55 } } }], build: 'Bob mesh with wave displacement' },
  { id: 'mx_long_centre_part', label: 'Longer centre-parted', group: 'Medium & bobs', collections: MX, indian: true, layers: [{ mesh: 'hair_long01', mod: { trim: 'jaw' } }], build: 'Long hair mesh trimmed at the jaw' },

  // ------------------------------------------------------------------ Short
  { id: 'hair_short04', label: 'Classic side-part', group: 'Short', collections: MX, indian: true, layers: [{ mesh: 'hair_short04' }], build: 'MakeHuman short04 mesh' },
  { id: 'mx_traditional_combed', label: 'Traditional neatly combed', group: 'Short', collections: M, indian: true, layers: [{ mesh: 'hair_short04', mod: { mirror: true } }], build: 'short04 mesh, parted on the other side' },
  { id: 'hair_short03', label: 'Deep side-part sweep', group: 'Short', collections: ALL, indian: true, layers: [{ mesh: 'hair_short03' }], build: 'MakeHuman short03 mesh' },
  { id: 'hair_short02', label: 'Side-swept fringe', group: 'Short', collections: MX, indian: true, layers: [{ mesh: 'hair_short02' }], build: 'MakeHuman short02 mesh' },
  { id: 'mx_middle_part', label: 'Middle-part (curtain)', group: 'Short', collections: MX, indian: true, layers: [{ mesh: 'hair_long01', mod: { trim: 'ear' } }], build: 'Long hair mesh cut at ear length' },
  { id: 'hair_short01', label: 'Short textured crop', group: 'Short', collections: ALL, indian: true, layers: [{ mesh: 'hair_short01' }], build: 'MakeHuman short01 mesh' },
  { id: 'mx_crew_cut', label: 'Crew cut', group: 'Short', collections: MX, layers: [{ mesh: 'hair_short04', mod: { fade: { from: 0.0, to: 0.3 } } }], build: 'short04 tapered to skin on the sides' },
  { id: 'mx_quiff', label: 'Quiff', group: 'Short', collections: M, indian: true, layers: [{ mesh: 'hair_short01', mod: { lift: 0.024, fade: { from: 0.28, to: 0.46 } } }, SIDES()], build: 'Textured top lifted at the front, tapered sides' },
  { id: 'mx_pompadour', label: 'Pompadour', group: 'Short', collections: M, layers: [{ mesh: 'hair_short02', mod: { lift: 0.034, fade: { from: 0.3, to: 0.44 } } }, SIDES()], build: 'Front swept up and back with volume, short sides' },
  { id: 'mx_spiky', label: 'Spiky textured top', group: 'Short', collections: MX, layers: [{ mesh: 'hair_short01', mod: { spike: { amount: 0.012 }, fade: { from: 0.22, to: 0.4 } } }, SIDES(0.05)], build: 'Textured crop with gelled spikes on top, tapered sides' },
  { id: 'mx_textured_fringe', label: 'Textured fringe', group: 'Short', collections: MX, layers: [{ mesh: 'hair_short02', mod: { wave: { amp: 0.004, freq: 120 } } }], build: 'Forward fringe with piecey texture' },
  { id: 'mx_slicked_back', label: 'Slicked-back', group: 'Short', collections: ALL, layers: [SCALP], build: 'Scalp section of ponytail01 (combed straight back)' },

  // ------------------------------------------------------------------ Fades & undercuts
  { id: 'mx_low_fade', label: 'Low fade', group: 'Fades & undercuts', collections: M, indian: true, layers: [{ mesh: 'hair_short01', mod: { fade: { from: 0.12, to: 0.3 } } }, SIDES(0.0)], build: 'Textured top fading into close-cropped sides low down' },
  { id: 'mx_mid_fade', label: 'Mid fade', group: 'Fades & undercuts', collections: M, indian: true, layers: [{ mesh: 'hair_short01', mod: { fade: { from: 0.3, to: 0.48 } } }, SIDES(0.1)], build: 'Fade starting at temple height' },
  { id: 'mx_high_fade', label: 'High fade', group: 'Fades & undercuts', collections: M, indian: true, layers: [{ mesh: 'hair_short01', mod: { fade: { from: 0.5, to: 0.64 } } }, SIDES(0.25)], build: 'Fade starting high on the head' },
  { id: 'mx_fade', label: 'Fade haircut', group: 'Fades & undercuts', collections: M, indian: true, layers: [{ mesh: 'hair_short02', mod: { fade: { from: 0.26, to: 0.44 } } }, SIDES(0.08)], build: 'Classic top with faded sides' },
  { id: 'mx_undercut', label: 'Undercut', group: 'Fades & undercuts', collections: ALL, layers: [{ mesh: 'hair_short02', mod: { fade: { from: 0.42, to: 0.425 } } }, SIDES(0.15)], build: 'Longer top with a hard line over short sides' },
  { id: 'mx_faux_hawk', label: 'Faux hawk', group: 'Fades & undercuts', collections: M, layers: [{ mesh: 'hair_short01', mod: { spike: { amount: 0.022, centre: 1 }, lift: 0.01, fade: { from: 0.42, to: 0.56 } } }, SIDES(0.2)], build: 'Spiked central strip over short faded sides' },
  { id: 'mx_side_swept_undercut', label: 'Side-swept', group: 'Fades & undercuts', collections: MX, indian: true, layers: [{ mesh: 'hair_short03', mod: { fade: { from: 0.32, to: 0.46 } } }, SIDES(0.1)], build: 'Swept top with tapered sides' },

  // ------------------------------------------------------------------ Curly & textured
  { id: 'hair_afro01', label: 'Short curly', group: 'Curly & textured', collections: ALL, indian: true, layers: [{ mesh: 'hair_afro01' }], build: 'MakeHuman afro01 mesh' },
  { id: 'in_voluminous_curls', label: 'Long voluminous curls', group: 'Curly & textured', collections: FX, layers: [{ mesh: 'hair_long01', mod: { wave: { amp: 0.022, freq: 72 }, volume: 0.045 } }], build: 'Long hair mesh with tight curls and big volume' },
  { id: 'in_curly_shoulder', label: 'Curly shoulder-length', group: 'Curly & textured', collections: FX, layers: [{ mesh: 'hair_long01', mod: { trim: 'shoulder', wave: { amp: 0.02, freq: 80 }, volume: 0.035 } }], build: 'Shoulder-length ringlets with volume' },
  { id: 'mx_curly_top', label: 'Curly top, short sides', group: 'Curly & textured', collections: M, layers: [{ mesh: 'hair_afro01', mod: { fade: { from: 0.34, to: 0.5 } } }, SIDES(0.1)], build: 'Curly top with faded sides' },
  { id: 'mx_messy_textured', label: 'Messy textured', group: 'Curly & textured', collections: MX, indian: true, layers: [{ mesh: 'hair_short01', mod: { wave: { amp: 0.005, freq: 140 }, lift: 0.01 } }], build: 'Textured crop with tousled displacement' },
]

export function hairStyle(id: string | null | undefined): HairStyle | undefined {
  return id ? HAIRSTYLES.find((h) => h.id === id) : undefined
}

/** Default hairstyle per model. */
export const DEFAULT_HAIRSTYLE: Record<Presentation, string> = { female: 'hair_long01', male: 'hair_short04', neutral: 'hair_short03' }

/** Collection listed first for each model. */
export const MODEL_HAIR_COLLECTION: Record<Presentation, HairCollection> = { female: 'feminine', male: 'masculine', neutral: 'flexible' }

/** Real meshes a style needs (used for compatibility checks and preloading). */
export function hairMeshes(style: HairStyle): HairMesh[] {
  return style.layers.map((l) => l.mesh)
}
