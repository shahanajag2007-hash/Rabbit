import { useGLTF } from '@react-three/drei'
import { useEffect, useState } from 'react'
import * as THREE from 'three'
import { AVATAR_ASSET_ROOT, type AvatarConfig, type BodyTypeId, type Presentation } from './avatarCatalog'

export type Vec3 = [number, number, number]
export type Anchors = Record<string, Vec3 | number | number[]>

/** Per-gender metadata written by the Blender build (see public/models/avatar/README.md). */
export interface AvatarMeta {
  gender: Presentation
  assetSource: string
  configs: { body: string[]; face: string[]; age?: string[]; height?: string[] }
  anchors: Record<string, Anchors>
  maskBits: Record<string, number>
  garments: Record<string, { source: string; slot: string }>
  hair: string[]
  eyebrows: string[]
  /** Facial hair meshes built for this model (absent in older builds). */
  facialHair?: string[]
  /** Tintable (luminance-only) base-colour texture per garment, from the build's postprocess. */
  baseColor?: Record<string, string>
  textures: Record<string, string[]>
}

const metaCache = new Map<Presentation, Promise<AvatarMeta>>()

export function loadAvatarMeta(p: Presentation): Promise<AvatarMeta> {
  if (!metaCache.has(p)) {
    const promise = fetch(`${AVATAR_ASSET_ROOT}/${p}/meta.json`).then(async (r) => {
      if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) {
        throw new Error(`Avatar assets for "${p}" are missing (expected ${AVATAR_ASSET_ROOT}/${p}/meta.json).`)
      }
      return (await r.json()) as AvatarMeta
    })
    promise.catch(() => metaCache.delete(p))
    metaCache.set(p, promise)
  }
  return metaCache.get(p)!
}

export function useAvatarMeta(p: Presentation): { meta: AvatarMeta | null; error: string | null } {
  const [state, setState] = useState<{ p: Presentation; meta: AvatarMeta | null; error: string | null }>({ p, meta: null, error: null })
  useEffect(() => {
    let alive = true
    loadAvatarMeta(p)
      .then((meta) => alive && setState({ p, meta, error: null }))
      .catch((e: Error) => alive && setState({ p, meta: null, error: e.message }))
    return () => {
      alive = false
    }
  }, [p])
  return state.p === p ? { meta: state.meta, error: state.error } : { meta: null, error: null }
}

export function partUrl(p: Presentation, id: string) {
  return `${AVATAR_ASSET_ROOT}/${p}/${id}.gltf`
}

// ---------------------------------------------------------------------------
// Texture cache (skin / eye / neutral garment textures swapped at runtime)
// ---------------------------------------------------------------------------
const textureLoader = new THREE.TextureLoader()
const textureCache = new Map<string, THREE.Texture>()

export function avatarTexture(file: string, opts: { colorSpace?: THREE.ColorSpace } = {}): THREE.Texture {
  const url = `${AVATAR_ASSET_ROOT}/tex/${file}`
  let tex = textureCache.get(url)
  if (!tex) {
    tex = textureLoader.load(url, undefined, undefined, () => console.warn(`[STYLEAI] texture failed to load: ${url}`))
    tex.flipY = false // glTF UV convention
    // Colour textures are sRGB; data maps (e.g. age detail ratios) pass NoColorSpace.
    tex.colorSpace = opts.colorSpace ?? THREE.SRGBColorSpace
    tex.anisotropy = 4
    textureCache.set(url, tex)
  }
  return tex
}

/** Linear blend of per-configuration anchor points by the active morph weights. */
export function blendAnchor(meta: AvatarMeta, key: string, weights: Record<string, number>): number[] | number | undefined {
  const base = meta.anchors.basis?.[key]
  if (base === undefined) return undefined
  if (typeof base === 'number') {
    let v = base
    for (const [cfg, w] of Object.entries(weights)) {
      const a = meta.anchors[cfg]?.[key]
      if (typeof a === 'number' && w) v += (a - base) * w
    }
    return v
  }
  const out = [...(base as number[])]
  for (const [cfg, w] of Object.entries(weights)) {
    const a = meta.anchors[cfg]?.[key] as number[] | undefined
    if (!a || !w) continue
    for (let i = 0; i < out.length; i++) out[i] += (a[i] - (base as number[])[i]) * w
  }
  return out
}

/**
 * Morph-target weights for the body, face customisation and (optional) age. `body` is either a
 * preset id (weight 1) or fractional body weights (the profile estimate blends presets).
 */
export function morphWeights(config: AvatarConfig, body: BodyTypeId | Record<string, number>, extra: Record<string, number> = {}): Record<string, number> {
  const w: Record<string, number> = { ...extra }
  if (typeof body === 'string') {
    if (body !== 'average') w[body] = 1
  } else {
    for (const [k, v] of Object.entries(body)) if (v) w[k] = (w[k] ?? 0) + v
  }
  for (const key of [config.facePreset, config.nose, config.lips, config.eyeShape]) {
    if (key && key !== 'natural') w[key] = 1
  }
  return w
}

/** Start fetching the parts every avatar needs as soon as the presentation is known. */
export function preloadAvatar(p: Presentation, ids: string[]) {
  for (const id of ['body', 'eyes', 'eyelashes', 'teeth', ...ids]) useGLTF.preload(partUrl(p, id))
}
