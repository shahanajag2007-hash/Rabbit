import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import {
  DEFAULT_AVATAR_CONFIG,
  initAvatarForModel,
  MODEL_DEFAULT_OUTFIT,
  profileModel,
  reconcileAvatar,
  resolvePresentation,
  SKIN_TONES,
  type AvatarConfig,
} from '../components/avatar/avatarCatalog'
import type { Category, Outfit, OutfitItem, ShoppingResponse, UserProfile } from '../types'

/**
 * Client-side session state. Mirrors the keys of the Streamlit app's st.session_state
 * (see ui_theme.ensure_session_defaults) so navigation never resets the user's choices.
 * The backend stays the source of truth for recommendations and scores.
 *
 * Four separate groups of state, connected only by the explicit actions below:
 *  1. Profile          — user_name … preferred_brands, skin_tone / skin_shade / skin_tone_detected
 *  2. Avatar           — avatar_config, saved_avatar_looks (appearance + visualisation-only clothes)
 *  3. Recommendation   — recommended_outfits (from the backend recommender)
 *  4. Final outfit     — selected_outfit, locked_items, shopping_results, garment_colour_overrides
 * The profile feeds the avatar (gender picks the model, height/weight/age/skin tone shape it); the
 * only write-back is skin tone (setSkinShade). Avatar clothing never writes to the recommendation or
 * final-outfit state. Whenever the model shown changes (profile gender or an explicit model choice),
 * the avatar's model-dependent settings are re-initialised in the same update (reconcileAvatar).
 */
export interface StyleState {
  // 1. Profile
  user_name: string
  age: number
  gender: string
  height: number
  weight: number
  budget: number
  // Appearance & preferences
  appearance_substep: number
  /** Profile skin tone used by the recommender: Light | Medium | Tan | Deep. Single source of truth. */
  skin_tone: string
  /** Finer avatar shade within skin_tone (set in the Avatar Studio); null = default shade for the tone. */
  skin_shade: string | null
  /** Tone detected from an uploaded photo (kept separate from the user's manual choice). */
  skin_tone_detected: string | null
  favorite_colours: string[]
  style: string
  occasion: string
  avoid_colours: string[]
  preferred_fit: string
  preferred_fabrics: string[]
  preferred_brands: string[]
  // 2. Avatar
  visual_mode: 'avatar' | 'photo'
  /** Structured avatar appearance (asset IDs). Kept separate from the recommended outfit. */
  avatar_config: AvatarConfig
  saved_avatar_looks: Record<string, AvatarConfig>
  selected_avatar_key: string | null
  active_avatar_tab: string
  // Preference analysis
  preference_text: string
  style_analyzed: boolean
  // 3. Recommendation
  recommended_outfits: Outfit[]
  // 4. Final outfit (selected recommendation + edits)
  selected_outfit: Outfit | null
  locked_items: Record<Category, boolean>
  shopping_results: ShoppingResponse | null
  shopping_signature: string | null
  /** Per-category colour override for the 3D viewer only (does not change the recommended item). */
  garment_colour_overrides: Partial<Record<Category, string>>

  set: (patch: Partial<StyleState>) => void
  /** Profile skin tone (Appearance page / photo): keeps the avatar shade inside the new tone. */
  setSkinTone: (tone: string) => void
  /** Avatar Studio shade: also updates the profile skin tone it belongs to. */
  setSkinShade: (shade: string) => void
  updateAvatar: (patch: Partial<AvatarConfig>) => void
  selectOutfit: (outfit: Outfit) => void
  updateOutfitItems: (items: Outfit['items']) => void
  setOutfitItem: (category: Category, item: OutfitItem) => void
  removeOutfitItem: (category: Category) => void
  toggleLock: (category: Category) => void
  resetAvatarAppearance: () => void
  saveAvatarLook: (name: string) => void
  loadAvatarLook: (name: string) => void
  restartJourney: () => void
}


const DEFAULT_GENDER = 'Female'

const defaults = {
  user_name: 'Alex',
  age: 22,
  gender: DEFAULT_GENDER,
  height: 168,
  weight: 58,
  budget: 3500,
  appearance_substep: 1,
  skin_tone: 'Medium',
  skin_shade: null as string | null,
  skin_tone_detected: null as string | null,
  favorite_colours: ['Navy', 'Beige', 'White'],
  style: 'Casual',
  occasion: 'College',
  avoid_colours: ['Neon / Flashy', 'Clashing Tones'],
  preferred_fit: 'Regular Fit',
  preferred_fabrics: ['Breathable Linen', 'Crisp Cotton Blend'],
  preferred_brands: ['ZARA', 'UNIQLO', 'Myntra'],
  visual_mode: 'avatar' as const,
  avatar_config: initAvatarForModel(profileModel(DEFAULT_GENDER), null),
  saved_avatar_looks: {} as Record<string, AvatarConfig>,
  selected_avatar_key: null as string | null,
  active_avatar_tab: 'appearance',
  preference_text: '',
  style_analyzed: false,
  recommended_outfits: [] as Outfit[],
  selected_outfit: null,
  locked_items: { Top: false, Bottom: false, Shoes: false, Accessory: false },
  shopping_results: null,
  shopping_signature: null,
  garment_colour_overrides: {},
}

export const useStyleStore = create<StyleState>()(
  persist(
    (set, get) => ({
      ...defaults,
      set: (patch) => {
        // A profile gender change can switch the model: re-initialise the avatar in the same update.
        if ('gender' in patch || 'avatar_config' in patch) {
          const gender = patch.gender ?? get().gender
          set({ ...patch, avatar_config: reconcileAvatar(patch.avatar_config ?? get().avatar_config, gender) })
        } else set(patch)
      },
      setSkinTone: (tone) => {
        const shade = SKIN_TONES.find((t) => t.id === get().skin_shade)
        set({ skin_tone: tone, skin_shade: shade && shade.recommenderTone === tone ? shade.id : null })
      },
      setSkinShade: (shadeId) => {
        const shade = SKIN_TONES.find((t) => t.id === shadeId)
        if (shade) set({ skin_shade: shade.id, skin_tone: shade.recommenderTone })
      },
      updateAvatar: (patch) => set({ avatar_config: reconcileAvatar({ ...get().avatar_config, ...patch }, get().gender) }),
      selectOutfit: (outfit) =>
        set({ selected_outfit: { ...outfit, items: { ...outfit.items } }, garment_colour_overrides: {}, shopping_results: null }),
      updateOutfitItems: (items) => {
        const current = get().selected_outfit
        set({ selected_outfit: { ...(current ?? {}), items }, shopping_results: null })
      },
      setOutfitItem: (category, item) => {
        const current = get().selected_outfit
        if (!current) return
        const overrides = { ...get().garment_colour_overrides }
        delete overrides[category]
        set({
          selected_outfit: { ...current, items: { ...current.items, [category]: item } },
          garment_colour_overrides: overrides,
          shopping_results: null,
        })
      },
      removeOutfitItem: (category) => {
        const current = get().selected_outfit
        if (!current) return
        const items = { ...current.items }
        delete items[category]
        set({ selected_outfit: { ...current, items }, shopping_results: null })
      },
      toggleLock: (category) =>
        set({ locked_items: { ...get().locked_items, [category]: !get().locked_items[category] }, shopping_results: null }),
      resetAvatarAppearance: () => {
        // Back to the model's default look and casual outfit; keeps the chosen body model and all profile data.
        const explicit = get().avatar_config.presentation
        const model = resolvePresentation({ ...DEFAULT_AVATAR_CONFIG, presentation: explicit }, get().gender).presentation
        set({ avatar_config: initAvatarForModel(model, explicit) })
      },
      saveAvatarLook: (name) =>
        set({ saved_avatar_looks: { ...get().saved_avatar_looks, [name]: { ...get().avatar_config } }, selected_avatar_key: name }),
      loadAvatarLook: (name) => {
        const look = get().saved_avatar_looks[name]
        if (!look) return
        // A saved look restores its own model; if the profile now points elsewhere, pin the look's model.
        const cfg = { ...DEFAULT_AVATAR_CONFIG, ...look }
        if (cfg.modelKey && !cfg.presentation && resolvePresentation(cfg, get().gender).presentation !== cfg.modelKey) cfg.presentation = cfg.modelKey
        set({ avatar_config: reconcileAvatar(cfg, get().gender), selected_avatar_key: name })
      },
      restartJourney: () => set({ appearance_substep: 1 }),
    }),
    {
      name: 'styleai-session',
      version: 6,
      // v1 stored the old mannequin builder; keep everything else and start the new avatar from defaults.
      migrate: (persisted, version) => {
        const state = (persisted ?? {}) as Record<string, unknown>
        if (version < 3) {
          // v2 kept a separate avatar skin tone; it is now part of the profile (skin_shade).
          const cfg = (state.avatar_config ?? {}) as Record<string, unknown>
          const old = SKIN_TONES.find((t) => t.id === cfg.skinTone)
          state.skin_shade = old && old.recommenderTone === state.skin_tone ? old.id : null
          state.skin_tone_detected = null
          if (!['Light', 'Medium', 'Tan', 'Deep'].includes(String(state.skin_tone))) state.skin_tone = old?.recommenderTone ?? 'Medium'
          delete cfg.skinTone
          state.avatar_config = { ...DEFAULT_AVATAR_CONFIG, ...cfg, bodyType: cfg.bodyType === 'average' ? null : (cfg.bodyType ?? null) }
          const looks = (state.saved_avatar_looks ?? {}) as Record<string, Record<string, unknown>>
          for (const k of Object.keys(looks)) {
            delete looks[k].skinTone
            looks[k] = { ...DEFAULT_AVATAR_CONFIG, ...looks[k] }
          }
        }
        if (version < 2) {
          delete state.avatar_builder
          delete state.avatars
          state.avatar_config = initAvatarForModel(profileModel(String(state.gender ?? DEFAULT_GENDER)), null)
          state.saved_avatar_looks = {}
          state.selected_avatar_key = null
          state.active_avatar_tab = 'appearance'
        }
        if (version < 4) {
          // v4 records which model the settings belong to (modelKey). Existing customisations are kept:
          // they are adopted for the model currently shown instead of being reset.
          const gender = String(state.gender ?? DEFAULT_GENDER)
          const adopt = (cfg: AvatarConfig): AvatarConfig => ({ ...cfg, modelKey: resolvePresentation(cfg, gender).presentation })
          state.avatar_config = adopt({ ...DEFAULT_AVATAR_CONFIG, ...((state.avatar_config ?? {}) as Partial<AvatarConfig>) })
          const looks = (state.saved_avatar_looks ?? {}) as Record<string, AvatarConfig>
          for (const k of Object.keys(looks)) looks[k] = adopt({ ...DEFAULT_AVATAR_CONFIG, ...looks[k] })
        }
        if (version < 5) {
          // v5 replaced the female starter outfit (blush graphic tee + skinny jeans); swap it only if untouched.
          const cfg = state.avatar_config as AvatarConfig | undefined
          if (cfg?.modelKey === 'female' && cfg.top === 'top_graphic_tee' && cfg.topColor === '#e2b4ae' && cfg.bottom === 'bottom_jeans_light' && !cfg.full) {
            state.avatar_config = { ...cfg, ...MODEL_DEFAULT_OUTFIT.female }
          }
        }
        if (version < 6) {
          // v6 dropped the revealing / logo items from the catalogue: swap them for the model's starter piece.
          const removed = ['top_graphic_tee', 'top_camisole', 'top_tank', 'top_sport_crop', 'bottom_denim_shorts']
          const fix = (cfg: AvatarConfig | undefined): AvatarConfig | undefined => {
            if (!cfg) return cfg
            const d = MODEL_DEFAULT_OUTFIT[cfg.modelKey ?? 'female']
            const out = { ...cfg }
            if (out.top && removed.includes(out.top)) Object.assign(out, { top: d.top, topColor: d.topColor })
            if (out.bottom && removed.includes(out.bottom)) Object.assign(out, { bottom: d.bottom, bottomColor: d.bottomColor })
            return out
          }
          state.avatar_config = fix(state.avatar_config as AvatarConfig | undefined)
          const looks = (state.saved_avatar_looks ?? {}) as Record<string, AvatarConfig>
          for (const k of Object.keys(looks)) looks[k] = fix(looks[k])!
        }
        return state as unknown as StyleState
      },
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
)

/** The user_profile dict the Streamlit recommendations page built from session state. */
export function selectUserProfile(s: StyleState): UserProfile {
  return {
    gender: s.gender,
    height: s.height,
    weight: s.weight,
    skin_tone: s.skin_tone,
    style: s.style,
    occasion: s.occasion,
    budget: s.budget,
    favorite_colours: s.favorite_colours,
    avoid_colours: s.avoid_colours,
  }
}
