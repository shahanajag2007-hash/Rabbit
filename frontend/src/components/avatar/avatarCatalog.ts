/**
 * Avatar asset registry.
 *
 *  - AVATAR_MODELS: the three base models (female-, male-presenting and androgynous), each built
 *    separately in Blender with its own body presets and defaults.
 *  - Customisation assets (hair, garments, ...) are keyed by stable IDs that map to real glTF files
 *    per model (public/models/avatar/<model>/<id>.gltf), morph targets baked into those files, or
 *    material settings. Compatibility is checked against the model's meta.json (what was actually
 *    built for it). `collections` only orders the catalogue ("for this model" / "more styles"); it
 *    never restricts what a user may wear.
 *  - Options with `available: false` have no asset and are shown disabled.
 *
 * Assets: MakeHuman system assets (CC0), built with MPFB2 — see public/models/README.md.
 */

import { DEFAULT_HAIRSTYLE } from './hairStyles'

/** Avatar model id (= asset folder). */
export type Presentation = 'female' | 'male' | 'neutral'
export type StyleCollection = 'feminine' | 'masculine'
/** 'full' = a one-piece outfit (dress, suit, kimono) worn instead of top + bottom. */
export type GarmentSlot = 'top' | 'outerwear' | 'bottom' | 'full' | 'footwear' | 'hat'

export type BodyTypeId = 'average' | 'slim' | 'athletic' | 'curvy' | 'full' | 'broad' | 'heavy'
export type FaceShapeId = 'natural' | 'face_oval' | 'face_round' | 'face_square' | 'face_heart' | 'face_long'
export type NoseId = 'natural' | 'nose_narrow' | 'nose_wide' | 'nose_upturned'
export type LipsId = 'natural' | 'lips_full' | 'lips_thin' | 'lips_wide'
export type EyeShapeId = 'natural' | 'eyes_large' | 'eyes_almond' | 'eyes_round'
export type AccessoryId = 'earrings' | 'necklace' | 'bracelet' | 'glasses' | 'sunglasses' | 'watch' | 'handbag' | 'tote' | 'belt'
export type FacialHairId = 'none' | 'stubble' | 'short_beard' | 'full_beard' | 'long_beard' | 'mustache'

/** Structured, serialisable avatar configuration (asset IDs, not labels). */
export interface AvatarConfig {
  /** null = follow the gender chosen on the Profile page. */
  presentation: Presentation | null
  /**
   * The model these settings were initialised for. When the model actually shown changes (profile
   * gender or an explicit model switch), model-dependent settings are re-initialised for the new
   * model (see initAvatarForModel), so hair and clothes from the previous model never carry over.
   */
  modelKey: Presentation | null
  /** Apply the profile age to the avatar (conservative MakeHuman age morph, adults 25+ only). */
  useProfileAge: boolean
  facePreset: FaceShapeId
  nose: NoseId
  lips: LipsId
  eyeShape: EyeShapeId
  eyebrows: string | null // null = default for presentation
  eyeColor: string
  hairstyle: string | null // null = default for presentation (ids from hairStyles.ts)
  hairColor: string
  /** Highlight streaks colour id (HAIR_HIGHLIGHTS); null = none. */
  hairHighlight: string | null
  facialHair: FacialHairId
  /** null = suggested from profile height & weight. (Skin tone is NOT stored here: it lives in the profile.) */
  bodyType: BodyTypeId | null
  top: string | null
  topColor: string | null
  outerwear: string | null
  outerwearColor: string | null
  bottom: string | null
  bottomColor: string | null
  /** One-piece outfit (dress / suit / kimono); when set it is worn instead of top, outerwear and bottom. */
  full: string | null
  fullColor: string | null
  footwear: string | null
  footwearColor: string | null
  hat: string | null
  accessories: AccessoryId[]
  pose: 'front' | 'three_quarter'
}

type OutfitDefaults = Pick<AvatarConfig, 'top' | 'topColor' | 'outerwear' | 'outerwearColor' | 'bottom' | 'bottomColor' | 'full' | 'fullColor' | 'footwear' | 'footwearColor' | 'hat'>

/**
 * Casual starter outfit per model, shown before any recommendation. Every garment here was fitted to
 * that model in the Blender build (each model folder has its own copy), so nothing is stretched across
 * bodies. These are starting points only: every compatible garment stays selectable on every model.
 *  - female:  long kurta-style tunic in teal over salwar-style harem pants in cream, ballet flats
 *  - male:    regular-fit crew tee (male casual suit) in navy, beige chinos (tinted trousers), white sneakers
 *  - neutral: long-sleeve tee in olive, light jeans, grey trainers
 */
export const MODEL_DEFAULT_OUTFIT: Record<Presentation, OutfitDefaults> = {
  female: { top: 'top_tunic', topColor: '#3d7d84', outerwear: null, outerwearColor: null, bottom: 'bottom_harem', bottomColor: '#f1e9db', full: null, fullColor: null, footwear: 'shoes_flats', footwearColor: null, hat: null },
  male: { top: 'top_white_tee', topColor: '#1f2c4a', outerwear: null, outerwearColor: null, bottom: 'bottom_suit_trousers', bottomColor: '#d9c4a3', full: null, fullColor: null, footwear: 'shoes_white_sneakers', footwearColor: null, hat: null },
  neutral: { top: 'top_longsleeve_tee', topColor: '#5b6236', outerwear: null, outerwearColor: null, bottom: 'bottom_jeans_light', bottomColor: null, full: null, fullColor: null, footwear: 'shoes_grey_trainers', footwearColor: null, hat: null },
}

/** @deprecated kept for older imports: the female starter outfit. Use MODEL_DEFAULT_OUTFIT. */
export const DEFAULT_OUTFIT = { top: 'top_white_tee', bottom: 'bottom_jeans_light', footwear: 'shoes_white_sneakers' } as const

export const DEFAULT_AVATAR_CONFIG: AvatarConfig = {
  presentation: null,
  modelKey: null,
  useProfileAge: true,
  facePreset: 'natural',
  nose: 'natural',
  lips: 'natural',
  eyeShape: 'natural',
  eyebrows: null,
  eyeColor: 'brown',
  hairstyle: null,
  hairColor: 'dark_brown',
  hairHighlight: null,
  facialHair: 'none',
  bodyType: null,
  top: DEFAULT_OUTFIT.top,
  topColor: null,
  outerwear: null,
  outerwearColor: null,
  bottom: DEFAULT_OUTFIT.bottom,
  bottomColor: null,
  full: null,
  fullColor: null,
  footwear: DEFAULT_OUTFIT.footwear,
  footwearColor: null,
  hat: null,
  accessories: [],
  pose: 'front',
}

export interface AvatarModel {
  id: Presentation
  label: string
  description: string
  /** Body presets baked for this model (must match meta.json configs.body; 'average' is the basis). */
  bodyPresets: BodyTypeId[]
  defaultHair: string
  defaultBrows: string
  /** Style collection listed first for this model (null = all collections equally). */
  collection: StyleCollection | null
}

export const AVATAR_MODELS: Record<Presentation, AvatarModel> = {
  female: {
    id: 'female',
    label: 'Female-presenting',
    description: 'MakeHuman female base model',
    bodyPresets: ['average', 'slim', 'athletic', 'curvy', 'full'],
    defaultHair: DEFAULT_HAIRSTYLE.female,
    defaultBrows: 'brows_eyebrow010',
    collection: 'feminine',
  },
  male: {
    id: 'male',
    label: 'Male-presenting',
    description: 'MakeHuman male base model',
    bodyPresets: ['average', 'slim', 'athletic', 'broad', 'heavy'],
    defaultHair: DEFAULT_HAIRSTYLE.male,
    defaultBrows: 'brows_eyebrow001',
    collection: 'masculine',
  },
  neutral: {
    id: 'neutral',
    label: 'Androgynous',
    description: 'MakeHuman gender mid-point (0.5) base model',
    bodyPresets: ['average', 'slim', 'athletic', 'curvy', 'broad'],
    defaultHair: DEFAULT_HAIRSTYLE.neutral,
    defaultBrows: 'brows_eyebrow006',
    collection: null,
  },
}

export const DEFAULT_HAIR: Record<Presentation, string> = DEFAULT_HAIRSTYLE
export const DEFAULT_BROWS: Record<Presentation, string> = { female: 'brows_eyebrow010', male: 'brows_eyebrow001', neutral: 'brows_eyebrow006' }

export interface Option<Id extends string = string> {
  id: Id
  label: string
  available?: boolean // default true
  note?: string
  group?: string
}

export const BODY_TYPES: Option<BodyTypeId>[] = [
  { id: 'average', label: 'Average' },
  { id: 'slim', label: 'Slim' },
  { id: 'athletic', label: 'Athletic' },
  { id: 'curvy', label: 'Curvy' },
  { id: 'full', label: 'Full figure' },
  { id: 'broad', label: 'Broad' },
  { id: 'heavy', label: 'Heavy-set' },
]

/** Closest preset on another model when the chosen one was not built for it. */
const BODY_FALLBACK: Record<BodyTypeId, BodyTypeId[]> = {
  average: [], slim: [], athletic: [],
  curvy: ['full', 'broad'], full: ['curvy', 'heavy'], broad: ['athletic', 'heavy'], heavy: ['full', 'broad'],
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))

/**
 * Weight-for-height (kg/m²) that each model's basis body stands for. The basis is MakeHuman's
 * mid "weight" macro (0.5); the `slim` preset is weight 0.1 and the heaviest preset ~0.9-0.95
 * (see BODY in tools/avatar-pipeline/build_avatar.py).
 */
const BASIS_MASS_INDEX = 22
const LIGHTER_SPAN = 5.5 // 16.5 kg/m² -> the full lighter preset
const HEAVIER_SPAN = 11 // 33 kg/m² -> the full heavier preset

/**
 * Morph targets that move each model along MakeHuman's weight axis (lighter <-> heavier).
 * They are mixed fractionally, and every garment/hair mesh carries the same morphs, so clothes follow.
 */
const MASS_AXIS: Record<Presentation, { lighter: Record<string, number>; heavier: Record<string, number> }> = {
  female: { lighter: { slim: 1 }, heavier: { full: 1 } },
  male: { lighter: { slim: 1 }, heavier: { heavy: 1 } },
  // The androgynous model has no single "heavy" preset; its two weight-0.7 presets are mixed evenly.
  neutral: { lighter: { slim: 1 }, heavier: { curvy: 0.5, broad: 0.5 } },
}

export interface ProfileBodyEstimate {
  /** Fractional morph weights applied to the model. */
  weights: Record<string, number>
  /** -1 (lightest preset) .. 0 (basis) .. 1 (heaviest preset). */
  build: number
  label: string
  /** Built preset closest to the estimate (used by the 2D fallback and for labels). */
  nearest: BodyTypeId
}

/**
 * Starting body estimate from the profile's height AND weight. It sets one continuous parameter,
 * overall build, by blending the model's lighter/heavier presets. Body shape (curvy, athletic, broad,
 * ...) is never inferred: those stay the user's own choice in Body Type. A rough visual starting
 * point, not a measurement of the user's body.
 */
export function estimateBodyFromProfile(model: Presentation, heightCm: number, weightKg: number): ProfileBodyEstimate {
  const h = clamp(Number(heightCm) || 168, 120, 230) / 100
  const w = clamp(Number(weightKg) || 60, 30, 200)
  const ratio = w / (h * h)
  const build = ratio < BASIS_MASS_INDEX ? -clamp((BASIS_MASS_INDEX - ratio) / LIGHTER_SPAN, 0, 1) : clamp((ratio - BASIS_MASS_INDEX) / HEAVIER_SPAN, 0, 1)
  const axis = build < 0 ? MASS_AXIS[model].lighter : MASS_AXIS[model].heavier
  const weights: Record<string, number> = {}
  if (Math.abs(build) > 0.01) for (const [k, v] of Object.entries(axis)) weights[k] = Math.round(v * Math.abs(build) * 1000) / 1000
  const label = build < -0.6 ? 'Lighter build' : build < -0.2 ? 'Slightly lighter build' : build <= 0.2 ? 'Mid build' : build <= 0.6 ? 'Fuller build' : 'Much fuller build'
  const presets = AVATAR_MODELS[model].bodyPresets
  const heavier = Object.keys(MASS_AXIS[model].heavier)[0] as BodyTypeId
  const nearest: BodyTypeId = build < -0.5 ? 'slim' : build > 0.5 && presets.includes(heavier) ? heavier : 'average'
  return { weights, build, label, nearest }
}

/** Nearest built preset to the profile estimate. */
export function suggestBodyType(model: Presentation, heightCm: number, weightKg: number): BodyTypeId {
  return estimateBodyFromProfile(model, heightCm, weightKg).nearest
}

export interface ResolvedBody {
  /** Preset shown (for a profile estimate: the nearest built preset). */
  id: BodyTypeId
  /** Body morph weights actually applied. */
  weights: Record<string, number>
  /** True when the body comes from the profile estimate (no preset chosen). */
  fromProfile: boolean
  estimate: ProfileBodyEstimate
  note: string | null
}

/** Body for a model: the user's chosen preset (mapped to the closest built one) or the profile estimate. */
export function resolveBody(model: Presentation, chosen: BodyTypeId | null, heightCm: number, weightKg: number): ResolvedBody {
  const estimate = estimateBodyFromProfile(model, heightCm, weightKg)
  if (!chosen) return { id: estimate.nearest, weights: estimate.weights, fromProfile: true, estimate, note: null }
  const presets = AVATAR_MODELS[model].bodyPresets
  const one = (id: BodyTypeId): Record<string, number> => (id === 'average' ? {} : { [id]: 1 })
  if (presets.includes(chosen)) return { id: chosen, weights: one(chosen), fromProfile: false, estimate, note: null }
  const alt = BODY_FALLBACK[chosen].find((b) => presets.includes(b)) ?? 'average'
  const label = (id: BodyTypeId) => BODY_TYPES.find((b) => b.id === id)?.label
  return { id: alt, weights: one(alt), fromProfile: false, estimate, note: `${label(chosen)} is not built for the ${AVATAR_MODELS[model].label.toLowerCase()} model, so ${label(alt)} is shown.` }
}

/** @deprecated Backwards-compat shim for older imports. */
export function resolveBodyType(model: Presentation, chosen: BodyTypeId | null, heightCm: number, weightKg: number): ResolvedBody {
  return resolveBody(model, chosen, heightCm, weightKg)
}

export interface AgeHandling {
  weights: Record<string, number>
  /** Short, honest description of what the profile age does to the avatar. */
  status: string
  applied: boolean
}

/**
 * Age handling within what the assets support. MakeHuman's age macro is baked at 14, 18, 45, 65 and
 * 85 (age_* morphs on body, garments and hair; the base model is 25). Neighbouring configurations are
 * blended linearly, so the face and body change gradually with no jumps at any age. Skin ageing
 * (fine lines, crow's feet, nasolabial folds) is added in the skin shader from 30 (skinShader.ts).
 */
export function ageHandling(age: number, enabled: boolean): AgeHandling {
  const years = Math.round(Number(age) || 0)
  if (!years) return { weights: {}, applied: false, status: 'Age not set' }
  if (!enabled) return { weights: {}, applied: false, status: 'Age shaping turned off' }
  const weights = ageWeights(years)
  const status =
    years < 18 ? `Teen proportions for ${years} (youthful face and build)`
    : years < 25 ? `Young-adult proportions for ${years}`
    : years === 25 ? 'Base adult model (25)'
    : years < 30 ? `Adult proportions for ${years}`
    : `Gradual age shaping and skin detail for ${years}`
  return { weights, applied: Object.keys(weights).length > 0, status }
}

/** Age morph weights: linear blend between the baked ages (14, 18, 25 = base, 45, 65, 85). */
export function ageWeights(age: number): Record<string, number> {
  const a = Number(age) || 0
  if (!a) return {}
  const KEYS: [number, string | null][] = [[14, 'age_14'], [18, 'age_18'], [25, null], [45, 'age_45'], [65, 'age_65'], [85, 'age_85']]
  if (a <= KEYS[0][0]) return { age_14: 1 }
  if (a >= 85) return { age_85: 1 }
  for (let i = 0; i < KEYS.length - 1; i++) {
    const [y0, k0] = KEYS[i]
    const [y1, k1] = KEYS[i + 1]
    if (a >= y0 && a <= y1) {
      const t = (a - y0) / (y1 - y0)
      const w: Record<string, number> = {}
      if (k0 && t < 1) w[k0] = Math.round((1 - t) * 1000) / 1000
      if (k1 && t > 0) w[k1] = Math.round(t * 1000) / 1000
      return w
    }
  }
  return {}
}

/**
 * Height morph (MakeHuman's height macro, baked as height_short / height_tall): the blend that brings
 * the crown of the head, with every other active morph, to the profile height. The proportions change
 * the way the human model does (leg length, torso, head); RealisticAvatar then calibrates the exact
 * stature with a small uniform scale, only needed beyond the model's natural range.
 */
export function heightMorph(topY: (weights: Record<string, number>) => number | undefined, heightCm: number, weights: Record<string, number>): Record<string, number> {
  const base = topY(weights)
  const short = topY({ ...weights, height_short: 1 })
  const tall = topY({ ...weights, height_tall: 1 })
  if (base === undefined || short === undefined || tall === undefined) return {}
  const target = heightCm / 100
  if (target >= base && tall > base) return { height_tall: Math.round(Math.min(1, (target - base) / (tall - base)) * 1000) / 1000 }
  if (target < base && short < base) return { height_short: Math.round(Math.min(1, (base - target) / (base - short)) * 1000) / 1000 }
  return {}
}

export const FACE_SHAPES: Option<FaceShapeId>[] = [
  { id: 'natural', label: 'Natural' },
  { id: 'face_oval', label: 'Oval' },
  { id: 'face_round', label: 'Round' },
  { id: 'face_square', label: 'Square' },
  { id: 'face_heart', label: 'Heart' },
  { id: 'face_long', label: 'Long' },
]
export const NOSES: Option<NoseId>[] = [
  { id: 'natural', label: 'Natural' },
  { id: 'nose_narrow', label: 'Narrow' },
  { id: 'nose_wide', label: 'Wide' },
  { id: 'nose_upturned', label: 'Upturned' },
]
export const LIPS: Option<LipsId>[] = [
  { id: 'natural', label: 'Natural' },
  { id: 'lips_full', label: 'Full' },
  { id: 'lips_thin', label: 'Thin' },
  { id: 'lips_wide', label: 'Wide' },
]
export const EYE_SHAPES: Option<EyeShapeId>[] = [
  { id: 'natural', label: 'Natural' },
  { id: 'eyes_large', label: 'Large' },
  { id: 'eyes_almond', label: 'Almond' },
  { id: 'eyes_round', label: 'Round' },
]
// The 12 MakeHuman eyebrow meshes; the rendered thumbnail shows each style.
export const EYEBROWS: Option[] = Array.from({ length: 12 }, (_, i) => ({ id: `brows_eyebrow${String(i + 1).padStart(3, '0')}`, label: `Style ${i + 1}` }))
/**
 * Facial hair: real beard / moustache meshes from MakeHuman's CC0 "bodyparts05" pack, fitted to each
 * model like the hair (they follow face, body and age morphs) and tinted with the hair colour.
 */
export const FACIAL_HAIR: (Option<FacialHairId> & { mesh?: string })[] = [
  { id: 'none', label: 'Clean-shaven' },
  { id: 'short_beard', label: 'Short scruffy beard', mesh: 'facial_beard_short' },
  { id: 'full_beard', label: 'Full beard & moustache', mesh: 'facial_beard_full' },
  { id: 'long_beard', label: 'Long beard', mesh: 'facial_beard_long' },
  { id: 'mustache', label: 'Moustache', mesh: 'facial_moustache' },
  { id: 'stubble', label: 'Light stubble', available: false, note: 'No stubble asset in the CC0 packs' },
]

export const EYE_COLORS: (Option & { hex: string })[] = [
  { id: 'brown', label: 'Brown', hex: '#5a3a22' },
  { id: 'brownlight', label: 'Hazel', hex: '#8a6234' },
  { id: 'green', label: 'Green', hex: '#4f7a3c' },
  { id: 'bluegreen', label: 'Blue-green', hex: '#3f7c78' },
  { id: 'blue', label: 'Blue', hex: '#3d6aa8' },
  { id: 'lightblue', label: 'Light blue', hex: '#7fa6cf' },
  { id: 'deepblue', label: 'Deep blue', hex: '#26467e' },
  { id: 'grey', label: 'Grey', hex: '#7c858d' },
  { id: 'ice', label: 'Ice', hex: '#a9c4d6' },
]

const F: StyleCollection[] = ['feminine']
const M: StyleCollection[] = ['masculine']
const FM: StyleCollection[] = ['feminine', 'masculine']

// Hairstyles live in hairStyles.ts (real hair meshes + hairstyle presets built on them).

/** Hair colours. Every hairstyle (meshes and procedural parts) is tinted through its material, so all colours work on all styles. */
export const HAIR_COLORS: (Option & { hex: string })[] = [
  { id: 'black', label: 'Black', hex: '#141110' },
  { id: 'dark_brown', label: 'Natural dark brown', hex: '#3b271c' },
  { id: 'brown', label: 'Medium brown', hex: '#6a4630' },
  { id: 'light_brown', label: 'Light brown', hex: '#94704f' },
  { id: 'blonde', label: 'Blonde', hex: '#d2b07a' },
  { id: 'platinum', label: 'Platinum', hex: '#e6dcc8' },
  { id: 'auburn', label: 'Auburn', hex: '#7e3a22' },
  { id: 'dark_auburn', label: 'Dark auburn', hex: '#4e2117' },
  { id: 'red', label: 'Copper red', hex: '#a4462a' },
  { id: 'burgundy', label: 'Burgundy', hex: '#4a1626' },
  { id: 'grey', label: 'Grey', hex: '#8f8b86' },
  { id: 'silver', label: 'Silver', hex: '#c9c8c6' },
  { id: 'honey', label: 'Honey blonde', hex: '#b98a4e' },
  { id: 'rose_pink', label: 'Rose pink', hex: '#c2577a' },
  { id: 'pastel_pink', label: 'Pastel pink', hex: '#eaa6bc' },
  { id: 'lavender', label: 'Lavender', hex: '#a68cc8' },
  { id: 'purple', label: 'Purple', hex: '#5e3a8c' },
  { id: 'blue', label: 'Blue', hex: '#2f5fa8' },
]

/** Highlight streaks over the base colour (face-framing pieces + fine streaks; roots stay natural). */
export const HAIR_HIGHLIGHTS: (Option & { hex: string })[] = [
  { id: 'caramel', label: 'Caramel', hex: '#b07a45' },
  { id: 'honey', label: 'Honey', hex: '#d9ab6a' },
  { id: 'platinum', label: 'Platinum', hex: '#efe6d6' },
  { id: 'copper', label: 'Copper', hex: '#c0602e' },
  { id: 'pink', label: 'Pink', hex: '#e86d9a' },
  { id: 'purple', label: 'Purple', hex: '#8d5bc9' },
  { id: 'blue', label: 'Blue', hex: '#3f7fd6' },
]

/** Skin tones: real skin textures from the pack, with a multiplicative tint that keeps texture detail. */
export interface SkinTone extends Option {
  texture: 'light' | 'medium' | 'deep'
  tint: [number, number, number]
  swatch: string
  /** The broad tone used by the recommendation engine (recommender.py palettes). */
  recommenderTone: 'Light' | 'Medium' | 'Tan' | 'Deep'
}
const BASE_AVG = { light: [210, 164, 137], medium: [210, 163, 130], deep: [106, 62, 44] } as const
function tone(id: string, label: string, texture: SkinTone['texture'], tint: [number, number, number], recommenderTone: SkinTone['recommenderTone']): SkinTone {
  const c = BASE_AVG[texture].map((v, i) => Math.max(0, Math.min(255, Math.round(v * tint[i]))))
  return { id, label, texture, tint, recommenderTone, swatch: `rgb(${c.join(',')})` }
}
export const SKIN_TONES: SkinTone[] = [
  tone('porcelain', 'Porcelain', 'light', [1.13, 1.12, 1.12], 'Light'),
  tone('fair', 'Fair', 'light', [1.04, 1.03, 1.02], 'Light'),
  tone('light', 'Light', 'medium', [1.0, 0.98, 0.95], 'Medium'),
  tone('medium', 'Medium', 'medium', [0.9, 0.82, 0.74], 'Medium'),
  tone('olive', 'Olive', 'medium', [0.82, 0.76, 0.6], 'Tan'),
  tone('tan', 'Tan', 'medium', [0.72, 0.58, 0.47], 'Tan'),
  tone('brown', 'Brown', 'deep', [1.28, 1.26, 1.22], 'Deep'),
  tone('deep', 'Deep', 'deep', [1.0, 1.0, 1.0], 'Deep'),
  tone('espresso', 'Espresso', 'deep', [0.78, 0.76, 0.76], 'Deep'),
]

/** Default avatar shade for each profile skin tone (the four tones the recommender uses). */
export const DEFAULT_SHADE: Record<SkinTone['recommenderTone'], string> = { Light: 'fair', Medium: 'medium', Tan: 'tan', Deep: 'deep' }

/**
 * The avatar's skin shade, derived from the profile (the single source of truth).
 * `profileShade` is the finer shade picked in the Avatar Studio; it only applies while it still
 * belongs to the profile's skin tone, so changing the tone on the Appearance page always wins.
 */
export function shadeForProfile(profileTone: string, profileShade: string | null): string {
  const tone = (['Light', 'Medium', 'Tan', 'Deep'] as const).find((t) => t === profileTone)
  const shade = SKIN_TONES.find((t) => t.id === profileShade)
  if (tone && shade && shade.recommenderTone === tone) return shade.id
  return tone ? DEFAULT_SHADE[tone] : 'medium'
}

export const SKIN_TEXTURES: Record<Presentation, Record<SkinTone['texture'], string>> = {
  female: {
    light: 'young_lightskinned_female_diffuse.jpg',
    medium: 'young_lightskinned_female_diffuse3.jpg',
    deep: 'young_darkskinned_female_diffuse.jpg',
  },
  male: {
    light: 'young_lightskinned_male_diffuse.jpg',
    medium: 'young_lightskinned_male_diffuse3.jpg',
    deep: 'young_darkskinned_male_diffuse.jpg',
  },
  // The androgynous model uses the female skin set (no stubble shading in the texture).
  neutral: {
    light: 'young_lightskinned_female_diffuse.jpg',
    medium: 'young_lightskinned_female_diffuse3.jpg',
    deep: 'young_darkskinned_female_diffuse.jpg',
  },
}

export interface GarmentOption extends Option {
  slot: GarmentSlot
  group: string
  /** Style collections the garment is listed under first (unisex = both). */
  collections: StyleCollection[]
  /** Colours the garment can be re-tinted to (applied to a neutral version of its texture). */
  tintable?: boolean
  /** Sleeveless dress: a fitted long-sleeve layer worn underneath (gives it sleeves, fills the neckline). */
  underlayer?: string
  /** Colour of that layer while the dress keeps its original print (otherwise the dress colour). */
  underlayerColor?: string
  /** Lengthens the skirt: stretch factor for everything below the hips (1 = as modelled). */
  lengthen?: number
  /** Wide skirt worn over the top (the top is tucked in) instead of under it. */
  overTop?: boolean
}

/**
 * Every available garment is a real MakeHuman mesh fitted to each model in the Blender build (system
 * assets + CC0 asset packs, see public/models/README.md). Items without a mesh are listed disabled.
 * `collections` decides which model lists the item first (men's / women's); everything stays selectable.
 */
export const GARMENTS: GarmentOption[] = [
  // Tops
  { id: 'top_white_tee', label: 'Crew-neck T-shirt', slot: 'top', group: 'T-shirts', collections: FM, tintable: true },
  { id: 'top_tucked_tee', label: 'Boxy cropped tee', slot: 'top', group: 'T-shirts', collections: FM, tintable: true },
  { id: 'top_longsleeve_tee', label: 'Long-sleeve tee', slot: 'top', group: 'T-shirts', collections: M, tintable: true },
  { id: 'top_polo', label: 'Polo shirt', slot: 'top', group: 'Polo shirts', collections: M, tintable: true },
  { id: 'top_formal_shirt', label: 'Button-up formal shirt', slot: 'top', group: 'Formal shirts & blouses', collections: FM, tintable: true },
  { id: 'top_striped_blouse', label: 'Striped blouse', slot: 'top', group: 'Formal shirts & blouses', collections: F, tintable: true },
  { id: 'top_striped_shirt', label: 'Striped shirt', slot: 'top', group: 'Striped shirts', collections: M, tintable: true },
  { id: 'top_sweater', label: 'Knit sweater', slot: 'top', group: 'Sweaters & hoodies', collections: FM, tintable: true },
  { id: 'top_hoodie', label: 'Hoodie', slot: 'top', group: 'Sweaters & hoodies', collections: FM, available: false, note: 'No hoodie mesh in the CC0 packs' },
  { id: 'top_tunic', label: 'Long tunic (kurta-style)', slot: 'top', group: 'Traditional', collections: FM, tintable: true },
  // Outerwear
  { id: 'outer_casual_jacket', label: 'Casual jacket', slot: 'outerwear', group: 'Jackets', collections: FM, tintable: true },
  { id: 'outer_suit_blazer', label: 'Suit blazer & tie', slot: 'outerwear', group: 'Blazers', collections: M, tintable: true },
  { id: 'outer_coat', label: 'Long coat', slot: 'outerwear', group: 'Coats', collections: FM, available: false, note: 'No coat mesh in the CC0 packs' },
  // One-piece outfits (worn instead of top + bottom)
  { id: 'dress_shift', label: 'Long-sleeve shift dress', slot: 'full', group: 'Dresses', collections: F, tintable: true, underlayer: 'top_longsleeve_tee', underlayerColor: '#2e2e33', lengthen: 1.7 },
  { id: 'dress_halter_midi', label: 'Long-sleeve maxi dress', slot: 'full', group: 'Dresses', collections: F, tintable: true, underlayer: 'top_longsleeve_tee', underlayerColor: '#5a2230', lengthen: 1.3 },
  { id: 'dress_full_skirt', label: 'Long-sleeve A-line dress', slot: 'full', group: 'Dresses', collections: F, tintable: true, underlayer: 'top_longsleeve_tee', underlayerColor: '#7d6aa8', lengthen: 1.6 },
  { id: 'full_skirt_suit', label: 'Skirt suit', slot: 'full', group: 'Suits', collections: F },
  { id: 'full_trouser_suit_f', label: 'Double-breasted trouser suit', slot: 'full', group: 'Suits', collections: F },
  { id: 'full_suit_double_breasted', label: 'Double-breasted suit', slot: 'full', group: 'Suits', collections: M },
  { id: 'full_dinner_suit', label: 'Dinner-jacket suit', slot: 'full', group: 'Suits', collections: M },
  { id: 'dress_kimono', label: 'Kimono robe', slot: 'full', group: 'Traditional', collections: F, tintable: true },
  { id: 'full_saree', label: 'Saree', slot: 'full', group: 'Traditional', collections: F, available: false, note: 'No saree mesh in the CC0 packs' },
  { id: 'full_sherwani', label: 'Sherwani', slot: 'full', group: 'Traditional', collections: M, available: false, note: 'No sherwani mesh in the CC0 packs' },
  // Bottoms
  { id: 'bottom_jeans_light', label: 'Jeans', slot: 'bottom', group: 'Jeans', collections: FM, tintable: true },
  { id: 'bottom_jeans_belted', label: 'Belted dark jeans', slot: 'bottom', group: 'Jeans', collections: M, tintable: true },
  { id: 'bottom_suit_trousers', label: 'Tailored trousers', slot: 'bottom', group: 'Formal trousers', collections: FM, tintable: true },
  { id: 'bottom_wool_trousers', label: 'Wool trousers', slot: 'bottom', group: 'Formal trousers', collections: FM, tintable: true },
  { id: 'bottom_cargo', label: 'Cargo pants', slot: 'bottom', group: 'Casual trousers', collections: M, tintable: true },
  { id: 'bottom_overalls', label: 'Denim overalls', slot: 'bottom', group: 'Casual trousers', collections: FM, tintable: true },
  { id: 'bottom_leggings', label: 'Leggings', slot: 'bottom', group: 'Casual trousers', collections: F, tintable: true },
  { id: 'bottom_pencil_skirt', label: 'Pencil skirt', slot: 'bottom', group: 'Skirts', collections: F, tintable: true },
  { id: 'bottom_long_skirt', label: 'Long full skirt (lehenga-style)', slot: 'bottom', group: 'Traditional', collections: F, tintable: true, overTop: true },
  { id: 'bottom_harem', label: 'Harem pants (salwar-style)', slot: 'bottom', group: 'Traditional', collections: FM, tintable: true },
  // Footwear
  { id: 'shoes_white_sneakers', label: 'White sneakers', slot: 'footwear', group: 'Sneakers', collections: FM, tintable: true },
  { id: 'shoes_navy_sneakers', label: 'Navy sneakers', slot: 'footwear', group: 'Sneakers', collections: FM, tintable: true },
  { id: 'shoes_grey_trainers', label: 'Grey trainers', slot: 'footwear', group: 'Sneakers', collections: FM, tintable: true },
  { id: 'shoes_black_formal', label: 'Black formal shoes', slot: 'footwear', group: 'Formal shoes', collections: M, tintable: true },
  { id: 'shoes_brown_leather', label: 'Brown leather shoes', slot: 'footwear', group: 'Formal shoes', collections: FM, tintable: true },
  { id: 'shoes_flats', label: 'Ballet flats', slot: 'footwear', group: 'Flats', collections: F, tintable: true },
  { id: 'shoes_ankle_boots', label: 'Ankle boots', slot: 'footwear', group: 'Boots', collections: FM, tintable: true },
  { id: 'shoes_black_boots', label: 'Black boots', slot: 'footwear', group: 'Boots', collections: FM, tintable: true },
  { id: 'shoes_sandals', label: 'Sandals', slot: 'footwear', group: 'Sandals', collections: FM, available: false, note: 'No sandal mesh in the CC0 packs' },
  // Hat (accessory category)
  { id: 'hat_fedora', label: 'Fedora', slot: 'hat', group: 'Hats', collections: FM, tintable: true },
]

export function garment(id: string | null | undefined): GarmentOption | undefined {
  return id ? GARMENTS.find((g) => g.id === id) : undefined
}

export const GARMENT_COLORS: { id: string; label: string; hex: string }[] = [
  { id: 'white', label: 'White', hex: '#f4f2ee' },
  { id: 'beige', label: 'Beige', hex: '#d9c4a3' },
  { id: 'charcoal', label: 'Charcoal', hex: '#3c3e44' },
  { id: 'black', label: 'Black', hex: '#1f1f22' },
  { id: 'navy', label: 'Navy', hex: '#1f2c4a' },
  { id: 'muted_blue', label: 'Muted blue', hex: '#5d7ea8' },
  { id: 'olive', label: 'Olive', hex: '#5b6236' },
  { id: 'burgundy', label: 'Burgundy', hex: '#6b1d2f' },
  { id: 'blush', label: 'Blush', hex: '#e2b4ae' },
  { id: 'mustard', label: 'Mustard', hex: '#c9971f' },
]

export interface AccessoryOption extends Option<AccessoryId> {
  group: 'Jewellery' | 'Eyewear' | 'Other'
}
export const ACCESSORIES: AccessoryOption[] = [
  { id: 'earrings', label: 'Earrings', group: 'Jewellery' },
  { id: 'necklace', label: 'Necklace', group: 'Jewellery' },
  { id: 'bracelet', label: 'Bracelet', group: 'Jewellery' },
  { id: 'glasses', label: 'Glasses', group: 'Eyewear' },
  { id: 'sunglasses', label: 'Sunglasses', group: 'Eyewear' },
  { id: 'watch', label: 'Watch', group: 'Other' },
  { id: 'handbag', label: 'Handbag', group: 'Other' },
  { id: 'tote', label: 'Canvas tote', group: 'Other' },
  { id: 'belt', label: 'Belt', group: 'Other' },
]
/** Accessories that cannot be worn together (same body location). */
export const ACCESSORY_CONFLICTS: Partial<Record<AccessoryId, AccessoryId[]>> = {
  glasses: ['sunglasses'],
  sunglasses: ['glasses'],
  handbag: ['tote'],
  tote: ['handbag'],
}

export const AVATAR_ASSET_ROOT = `${import.meta.env.BASE_URL}models/avatar`

export function thumbUrl(presentation: Presentation, key: string): string {
  return `${AVATAR_ASSET_ROOT}/thumbs/${presentation}_${key}.png`
}

/** Model from the profile gender. Non-binary starts on the androgynous model and is offered a choice. */
export function resolvePresentation(config: AvatarConfig, profileGender: string): { presentation: Presentation; needsChoice: boolean } {
  if (config.presentation) return { presentation: config.presentation, needsChoice: false }
  if (profileGender === 'Male') return { presentation: 'male', needsChoice: false }
  if (profileGender === 'Female') return { presentation: 'female', needsChoice: false }
  return { presentation: 'neutral', needsChoice: true }
}

/** Is an item listed first for this model? (Everything stays selectable; this only orders the catalogue.) */
export function inCollection(model: Presentation, collections: ReadonlyArray<string>): boolean {
  const c = AVATAR_MODELS[model].collection
  return c === null || collections.includes(c)
}

/** Profile gender -> model (Non-binary starts on the androgynous model). */
export function profileModel(profileGender: string): Presentation {
  return profileGender === 'Male' ? 'male' : profileGender === 'Female' ? 'female' : 'neutral'
}

/**
 * Keep the avatar config consistent with the model actually shown. When that model differs from the
 * one the settings were initialised for (`modelKey`), the model-dependent settings are re-initialised.
 * Pure and synchronous: it runs inside the store update, never after an asset load, so a model that
 * finishes loading late can never bring back an older avatar.
 */
export function reconcileAvatar(config: AvatarConfig, profileGender: string): AvatarConfig {
  const { presentation } = resolvePresentation(config, profileGender)
  return config.modelKey === presentation ? config : initAvatarForModel(presentation, config.presentation, config)
}

/**
 * Model-dependent settings for a freshly selected model: default hairstyle and brows, body from the
 * profile estimate, natural face, no facial hair, the model's starter outfit. Kept from `prev`:
 * eye colour, hair colour and highlights (all colours work on all hair), pose, the age toggle and the code-modelled
 * accessories (anchored per model, so compatible with every model). Profile data is not part of the
 * avatar config, so it is never touched here.
 */
export function initAvatarForModel(model: Presentation, explicit: Presentation | null, prev: AvatarConfig = DEFAULT_AVATAR_CONFIG): AvatarConfig {
  return {
    ...DEFAULT_AVATAR_CONFIG,
    eyeColor: prev.eyeColor,
    hairColor: HAIR_COLORS.some((c) => c.id === prev.hairColor) ? prev.hairColor : DEFAULT_AVATAR_CONFIG.hairColor,
    hairHighlight: HAIR_HIGHLIGHTS.some((c) => c.id === prev.hairHighlight) ? prev.hairHighlight : null,
    pose: prev.pose,
    useProfileAge: prev.useProfileAge,
    accessories: [...prev.accessories],
    ...MODEL_DEFAULT_OUTFIT[model],
    presentation: explicit,
    modelKey: model,
  }
}
