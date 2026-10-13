import { useMemo } from 'react'
import { morphWeights } from '../components/avatar/avatarAssets'
import {
  ageHandling,
  AVATAR_MODELS,
  FACIAL_HAIR,
  resolveBody,
  resolvePresentation,
  shadeForProfile,
  type AvatarConfig,
} from '../components/avatar/avatarCatalog'
import { recommendedOnAvatar } from '../components/avatar/garmentMapping'
import { hairStyle } from '../components/avatar/hairStyles'
import type { ResolvedAvatar } from '../components/avatar/RealisticAvatar'
import type { AvatarBuilder, Category } from '../types'
import { useStyleStore } from './useStyleStore'

export interface AvatarView {
  resolved: ResolvedAvatar
  /** True when the profile gender has no matching body model and the user should pick one. */
  needsPresentationChoice: boolean
  /** Notes about how recommended items are approximated on the avatar. */
  notes: string[]
  /** Body preset was suggested from height & weight (the user has not chosen one). */
  bodySuggested: boolean
  /** Shown when the chosen body preset is not built for this model. */
  bodyNote: string | null
  /** Age morph weights applied from the profile age (empty for 25 and under), with an honest status. */
  age: { years: number; weights: Record<string, number>; status: string }
  /** Profile build estimate from height & weight (-1 lightest preset .. 1 heaviest), when no preset is chosen. */
  build: { value: number; label: string }
}

/** The avatar's own top + outerwear + bottom (also used under a recommended item when a dress is worn). */
function separates(config: AvatarConfig): ResolvedAvatar['worn'] {
  const worn: ResolvedAvatar['worn'] = {}
  if (config.top) worn.top = { id: config.top, color: config.topColor }
  if (config.outerwear) worn.outerwear = { id: config.outerwear, color: config.outerwearColor }
  if (config.bottom) worn.bottom = { id: config.bottom, color: config.bottomColor }
  return worn
}

function configWorn(config: AvatarConfig): ResolvedAvatar['worn'] {
  // A one-piece outfit (dress / suit / kimono) is worn instead of the separates.
  const worn: ResolvedAvatar['worn'] = config.full ? { full: { id: config.full, color: config.fullColor } } : separates(config)
  if (config.footwear) worn.footwear = { id: config.footwear, color: config.footwearColor }
  if (config.hat) worn.hat = { id: config.hat, color: null }
  return worn
}

/**
 * Resolve what the 3D avatar shows.
 *  - 'studio': the avatar's own configuration (appearance + its temporary/selected clothes).
 *  - 'outfit': same appearance, wearing the backend's selected/recommended outfit. Categories the
 *    outfit does not contain fall back to the avatar's own clothes so it is never shown unclothed.
 */
export function useAvatarView(mode: 'studio' | 'outfit'): AvatarView {
  const config = useStyleStore((s) => s.avatar_config)
  const gender = useStyleStore((s) => s.gender)
  const height = useStyleStore((s) => s.height)
  const weight = useStyleStore((s) => s.weight)
  const age = useStyleStore((s) => s.age)
  const profileSkin = useStyleStore((s) => s.skin_tone)
  const profileShade = useStyleStore((s) => s.skin_shade)
  const items = useStyleStore((s) => s.selected_outfit?.items)
  const overrides = useStyleStore((s) => s.garment_colour_overrides)

  return useMemo(() => {
    const { presentation, needsChoice } = resolvePresentation(config, gender)
    const worn = configWorn(config)
    let accessories = [...config.accessories]
    let notes: string[] = []

    if (mode === 'outfit' && items && Object.keys(items).length) {
      const rec = recommendedOnAvatar(items)
      notes = rec.notes
      const slotOf: Record<Category, (keyof ResolvedAvatar['worn'])[]> = {
        Top: ['top', 'outerwear'],
        Bottom: ['bottom'],
        Shoes: ['footwear'],
        Accessory: [],
      }
      // A recommended top or bottom replaces the avatar's own one-piece outfit; the avatar's separates
      // fill whichever of top / bottom the recommendation does not contain.
      if (worn.full && (items.Top || items.Bottom)) {
        delete worn.full
        Object.assign(worn, separates(config))
      }
      for (const category of Object.keys(slotOf) as Category[]) {
        if (!items[category]) continue
        for (const slot of slotOf[category]) delete worn[slot]
        for (const slot of slotOf[category]) {
          const g = rec.worn[slot as keyof typeof rec.worn]
          if (g) worn[slot] = { ...g, color: overrides[category] ?? g.color }
        }
      }
      accessories = Array.from(new Set([...accessories, ...rec.accessories]))
    }

    const heightCm = Number(height) || 168
    const body = resolveBody(presentation, config.bodyType, heightCm, Number(weight) || 60)
    const ageInfo = ageHandling(Number(age) || 0, config.useProfileAge)
    const model = AVATAR_MODELS[presentation]
    const resolved: ResolvedAvatar = {
      presentation,
      config,
      // Unknown ids (e.g. from an older saved session) fall back to the model's default style.
      hairstyle: hairStyle(config.hairstyle)?.id ?? model.defaultHair,
      eyebrows: config.eyebrows ?? model.defaultBrows,
      // Older saved looks may use retired ids; unknown values mean clean-shaven.
      facialHair: FACIAL_HAIR.find((f) => f.id === config.facialHair && f.available !== false)?.mesh ?? null,
      skinTone: shadeForProfile(profileSkin, profileShade),
      bodyType: body.id,
      // Fractional weights: a chosen preset, or the continuous height+weight estimate.
      morphs: morphWeights(config, body.weights, ageInfo.weights),
      worn,
      accessories,
      heightCm,
      ageYears: config.useProfileAge ? Number(age) || 0 : 0,
    }
    return {
      resolved,
      needsPresentationChoice: needsChoice,
      notes,
      bodySuggested: body.fromProfile,
      bodyNote: body.note,
      age: { years: Number(age) || 0, weights: ageInfo.weights, status: ageInfo.status },
      build: { value: body.estimate.build, label: body.estimate.label },
    }
  }, [config, gender, height, weight, age, profileSkin, profileShade, items, overrides, mode])
}

/** Old 2D avatar parameters (avatar_engine.py), used only when WebGL is unavailable. */
export function toLegacyBuilder(r: ResolvedAvatar, weight: number, occasion: string): AvatarBuilder {
  const hair: Record<string, string> = {
    hair_long01: 'Long Straight', hair_ponytail01: 'Ponytail', hair_braid01: 'Ponytail', hair_bob01: 'Bob', hair_bob02: 'Bob',
    hair_afro01: 'Curly', hair_short01: 'Bob', hair_short02: 'Bob', hair_short03: 'Bob', hair_short04: 'Bob',
  }
  return {
    gender: r.presentation === 'male' ? 'Male' : 'Female',
    model_preset: r.config.pose === 'three_quarter' ? 'Model B' : 'Model A',
    body_shape: { average: 'Balanced', slim: 'Slim', athletic: 'Athletic', curvy: 'Curvy', full: 'Curvy', broad: 'Athletic', heavy: 'Curvy' }[r.bodyType],
    height: r.heightCm,
    weight,
    skin_tone: { porcelain: 'Porcelain', fair: 'Light Beige', light: 'Light Beige', medium: 'Warm Almond', olive: 'Warm Almond', tan: 'Golden Tan', brown: 'Deep Cocoa', deep: 'Deep Cocoa', espresso: 'Espresso' }[r.skinTone] ?? 'Medium',
    hair_style: (() => {
      const style = hairStyle(r.hairstyle)
      if (style?.parts?.length) return 'Ponytail' // braids, ponytails and buns are all tied back
      return hair[style?.layers[0]?.mesh ?? r.hairstyle] ?? 'Long Straight'
    })(),
    hair_colour: 'Dark Brown',
    occasion,
    accessory: r.accessories.includes('watch') ? 'Minimal Watch' : r.accessories.includes('sunglasses') ? 'Sunglasses' : r.accessories.includes('glasses') ? 'Glasses' : r.accessories.includes('earrings') ? 'Earrings' : 'Minimal Watch',
  }
}
