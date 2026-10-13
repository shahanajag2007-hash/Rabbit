import { useGLTF } from '@react-three/drei'
import { Suspense, useEffect, useLayoutEffect, useMemo, useState } from 'react'
import * as THREE from 'three'
import { AccessoryMeshes } from './Accessories'
import { avatarTexture, blendAnchor, partUrl, type AvatarMeta } from './avatarAssets'
import {
  EYE_COLORS,
  HAIR_COLORS,
  HAIR_HIGHLIGHTS,
  SKIN_TEXTURES,
  SKIN_TONES,
  garment,
  heightMorph,
  type AccessoryId,
  type AvatarConfig,
  type BodyTypeId,
  type Presentation,
} from './avatarCatalog'
import { applyHairHighlight, applyHairMod, hairModCuts } from './hairShader'
import { DEFAULT_HAIRSTYLE, hairStyle } from './hairStyles'
import { headFrame, ProceduralHair, shaderMod, type HairShaderMod } from './ProceduralHair'
import { layerFitOffsets } from './layerFit'
import { morphedPositions, scalpCoverage } from './scalpCoverage'
import { ageDetailWeights, scalpColor, skinUniforms } from './skinShader'

/** A garment worn in a slot, with an optional colour (applied to a neutral version of its texture). */
export interface WornGarment {
  id: string
  color: string | null
}

export interface ResolvedAvatar {
  presentation: Presentation
  config: AvatarConfig
  hairstyle: string
  eyebrows: string
  /** Facial hair mesh id (facial_*), or null. */
  facialHair: string | null
  /** Skin shade derived from the profile (skin_tone + skin_shade). */
  skinTone: string
  /** Body preset actually applied (chosen, or suggested from height/weight, mapped to this model). */
  bodyType: BodyTypeId
  /** All morph-target weights (body type, face, age). */
  morphs: Record<string, number>
  worn: { top?: WornGarment; outerwear?: WornGarment; bottom?: WornGarment; full?: WornGarment; footwear?: WornGarment; hat?: WornGarment }
  accessories: AccessoryId[]
  heightCm: number
  /** Age shown on the skin (wrinkle detail); 0 = none. Body/face age shape comes from `morphs`. */
  ageYears: number
}

type PartKind = 'body' | 'eyes' | 'lashes' | 'brows' | 'hair' | 'teeth' | 'garment'

interface PartProps {
  url: string
  kind: PartKind
  weights: Record<string, number>
  /** body only */
  hiddenBits?: number[]
  skin?: { map: string; tint: [number, number, number] }
  eyeMap?: string
  hairColor?: string
  /** Highlight streak colour (hair meshes only; null = none). */
  hairHighlight?: string | null
  garmentColor?: string | null
  garmentNeutralMap?: string | null
  /** hair only: shader modification turning the mesh into another style (trim, fade, waves, ...) */
  hairMod?: HairShaderMod | null
  /** body only: age-detail map and weights, scalp root colour */
  skinDetail?: { ageMap: string; ageWeights: [number, number]; scalp: string }
  /** reports the live mesh (body: scalp shading; bottom garment: layer fit) */
  onMesh?: (mesh: THREE.Mesh | null) => void
  /** Garment drawn in plain `garmentColor`, without its texture print (layer under a dress). */
  plain?: boolean
}

function applyMorphs(mesh: THREE.Mesh, weights: Record<string, number>) {
  const dict = mesh.morphTargetDictionary
  const infl = mesh.morphTargetInfluences
  if (!dict || !infl) return
  infl.fill(0)
  for (const [name, w] of Object.entries(weights)) {
    const i = dict[name]
    if (i !== undefined) infl[i] = w
  }
}

/** Rebuild the body index so skin hidden under worn garments is not drawn (prevents poke-through). */
function maskBody(geometry: THREE.BufferGeometry, original: THREE.BufferAttribute, bits: number[]) {
  // Up to three 24-bit mask attributes (_HIDEA/_HIDEB/_HIDEC), one bit per garment piece.
  const attrs = ['_hidea', '_hideb', '_hidec'].map((n) => geometry.getAttribute(n) as THREE.BufferAttribute | undefined)
  if (!attrs[0] || !bits.length) {
    geometry.setIndex(original)
    return
  }
  const masks = [0, 0, 0]
  for (const bit of bits) masks[Math.floor(bit / 24)] |= 1 << (bit % 24)
  const hidden = (v: number) => attrs.some((a, i) => !!a && masks[i] !== 0 && (Math.round(a.getX(v)) & masks[i]) !== 0)
  const src = original.array
  const out: number[] = []
  for (let i = 0; i < src.length; i += 3) {
    const v0 = src[i], v1 = src[i + 1], v2 = src[i + 2]
    if (hidden(v0) && hidden(v1) && hidden(v2)) continue
    out.push(v0, v1, v2)
  }
  geometry.setIndex(out)
}

/**
 * Alpha-tested parts (hair, brows, lashes, eye shells) output their texture alpha. On a transparent
 * canvas that value would *replace* the framebuffer alpha of the opaque head behind them, so the page
 * background showed through every strand edge (pale streaks that made hair look like a wig). Colour is
 * written as usual; alpha only accumulates (src + dst), so it never drops below what is already drawn.
 */
function keepFramebufferAlpha(mat: THREE.Material) {
  mat.blending = THREE.CustomBlending
  mat.blendEquation = THREE.AddEquation
  mat.blendSrc = THREE.OneFactor
  mat.blendDst = THREE.ZeroFactor
  mat.blendEquationAlpha = THREE.AddEquation
  mat.blendSrcAlpha = THREE.OneFactor
  mat.blendDstAlpha = THREE.OneFactor
}

/** Garment shader: adds the per-vertex layering offset (layerFit.ts) after the morph targets. */
function installGarmentLayer(mat: THREE.Material) {
  if (mat.userData.layerInstalled) return
  mat.userData.layerInstalled = true
  mat.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec3 aLayer;')
      .replace('#include <morphtarget_vertex>', '#include <morphtarget_vertex>\ntransformed += aLayer;')
  }
  mat.customProgramCacheKey = () => 'styleai-garment-v1'
}

function AvatarPart({ url, kind, weights, hiddenBits, skin, eyeMap, hairColor, hairHighlight = null, garmentColor, garmentNeutralMap, hairMod, skinDetail, onMesh, plain = false }: PartProps) {
  const gltf = useGLTF(url)

  // Own copy of the mesh + material so per-avatar changes never leak into the glTF cache.
  const { object, mesh, originalIndex } = useMemo(() => {
    const object = gltf.scene.clone(true)
    let found: THREE.Mesh | null = null
    object.traverse((o) => {
      const m = o as THREE.Mesh
      if (!m.isMesh) return
      found = found ?? m
      const src = m.material as THREE.MeshStandardMaterial
      const mat = new THREE.MeshPhysicalMaterial({
        map: src.map,
        normalMap: src.normalMap ?? null,
        roughness: 0.8,
        metalness: 0,
      })
      mat.userData.originalMap = src.map
      m.material = mat
      m.castShadow = kind !== 'lashes' && kind !== 'brows' && kind !== 'teeth'
      m.receiveShadow = true
      m.frustumCulled = false // morphs can move vertices outside the bind-pose bounds
      if (kind === 'garment') {
        // Own geometry copy with a layering offset (filled in by LayerFit; zeros = as fitted).
        m.geometry = m.geometry.clone()
        m.geometry.setAttribute('aLayer', new THREE.BufferAttribute(new Float32Array(m.geometry.getAttribute('position').count * 3), 3))
      }
      if (kind === 'body') {
        m.geometry = m.geometry.clone()
        // Scalp coverage (filled in by ScalpShading); zeros = bare skin until the hair is measured.
        m.geometry.setAttribute('aScalp', new THREE.BufferAttribute(new Float32Array(m.geometry.getAttribute('position').count), 1))
      }
    })
    const mesh = found as THREE.Mesh | null
    const originalIndex = mesh && kind === 'body' && mesh.geometry.index ? mesh.geometry.index.clone() : null
    return { object, mesh, originalIndex }
  }, [gltf.scene, kind])

  useEffect(
    () => () => {
      object.traverse((o) => {
        const m = o as THREE.Mesh
        if (m.isMesh) {
          ;(m.material as THREE.Material).dispose()
          if (kind === 'body' || kind === 'garment') m.geometry.dispose()
        }
      })
    },
    [object, kind],
  )

  useLayoutEffect(() => {
    if (!mesh) return
    applyMorphs(mesh, weights)
  }, [mesh, weights])

  useEffect(() => {
    if (!onMesh) return
    onMesh(mesh)
    return () => onMesh(null)
  }, [mesh, kind, onMesh])

  useLayoutEffect(() => {
    if (!mesh || kind !== 'body' || !originalIndex) return
    maskBody(mesh.geometry, originalIndex, hiddenBits ?? [])
  }, [mesh, kind, originalIndex, hiddenBits])

  useLayoutEffect(() => {
    if (!mesh) return
    const mat = mesh.material as THREE.MeshPhysicalMaterial
    switch (kind) {
      case 'body':
        if (skin) {
          mat.map = avatarTexture(skin.map)
          mat.color.setRGB(...skin.tint)
        }
        mat.roughness = 0.58
        mat.sheen = 0.25
        mat.sheenRoughness = 0.7
        mat.sheenColor.set('#ffd8c8')
        mat.side = THREE.FrontSide
        if (skinDetail) {
          const u = skinUniforms(mat)
          u.uAgeMap.value = avatarTexture(skinDetail.ageMap, { colorSpace: THREE.NoColorSpace })
          u.uAgeWeights.value.set(...skinDetail.ageWeights)
          u.uScalpColor.value.copy(scalpColor(skinDetail.scalp))
        }
        break
      case 'eyes':
        if (eyeMap) mat.map = avatarTexture(eyeMap)
        // The cornea shell is transparent in the iris texture's alpha channel.
        mat.alphaTest = 0.5
        mat.roughness = 0.08
        mat.clearcoat = 1
        mat.clearcoatRoughness = 0.05
        break
      case 'teeth':
        mat.roughness = 0.35
        break
      case 'lashes':
        mat.alphaTest = 0.4
        mat.side = THREE.DoubleSide
        mat.color.set('#1a1412')
        break
      case 'brows':
        mat.alphaTest = 0.3
        mat.side = THREE.DoubleSide
        mat.color.set(hairColor ?? '#3b271c').multiplyScalar(0.85)
        mat.roughness = 0.9
        break
      case 'hair':
        mat.alphaTest = 0.32
        mat.alphaToCoverage = true
        mat.side = THREE.DoubleSide
        mat.color.set(hairColor ?? '#3b271c')
        mat.roughness = 0.55
        // Soft anisotropic-looking highlight in the hair's own colour (white sheen made it look grey).
        mat.sheen = 0.5
        mat.sheenRoughness = 0.4
        mat.sheenColor.set(hairColor ?? '#3b271c').lerp(new THREE.Color('#ffffff'), 0.25)
        applyHairMod(mat, hairMod ?? null)
        applyHairHighlight(mat, hairHighlight)
        // Removed sections must not cast shadows (the default depth material does not know the cuts).
        mesh.castShadow = !hairModCuts(hairMod ?? null)
        break
      case 'garment':
        installGarmentLayer(mat)
        mat.side = THREE.DoubleSide
        mat.roughness = 0.88
        mat.sheen = 0.35
        mat.sheenRoughness = 0.6
        mat.sheenColor.set('#ffffff')
        if (plain && garmentColor) {
          mat.map = null
          mat.color.set(garmentColor)
        } else if (garmentColor && garmentNeutralMap) {
          mat.map = avatarTexture(garmentNeutralMap)
          mat.color.set(garmentColor)
        } else {
          mat.map = mat.userData.originalMap ?? mat.map
          mat.color.set('#ffffff')
        }
        break
    }
    if (kind === 'hair' || kind === 'brows' || kind === 'lashes' || kind === 'eyes') keepFramebufferAlpha(mat)
    mat.transparent = false
    mat.depthWrite = true
    mat.needsUpdate = true
  }, [mesh, kind, skin, eyeMap, hairColor, hairHighlight, garmentColor, garmentNeutralMap, hairMod, skinDetail, plain])

  return <primitive object={object} />
}

/**
 * Measures how much of the scalp the current hairstyle covers (scalpCoverage.ts) and writes it into the
 * body's `aScalp` attribute in place. Runs in its own Suspense boundary, so loading a new hair mesh
 * never hides the avatar; until it finishes, the previous coverage stays.
 */
function ScalpShading({ body, p, layers, mods, weights, neckY }: { body: THREE.Mesh; p: Presentation; layers: string[]; mods: (HairShaderMod | null)[]; weights: Record<string, number>; neckY: number }) {
  const bodyGltf = useGLTF(partUrl(p, 'body'))
  const hairGltfs = useGLTF(layers.map((id) => partUrl(p, id))) as unknown as { scene: THREE.Object3D }[]
  const firstMesh = (o: THREE.Object3D) => {
    let found: THREE.Mesh | null = null
    o.traverse((c) => {
      if (!found && (c as THREE.Mesh).isMesh) found = c as THREE.Mesh
    })
    return found as THREE.Mesh | null
  }
  const hairKey = hairGltfs.map((g) => g.scene.uuid).join('|')
  useEffect(() => {
    const src = firstMesh(bodyGltf.scene)
    const attr = body.geometry.getAttribute('aScalp') as THREE.BufferAttribute | undefined
    // During a model switch the live body can still be the previous model's: wait for the new one.
    if (!src || !attr || attr.count !== src.geometry.getAttribute('position').count) return
    const hair = hairGltfs.map((g, i) => {
      const m = firstMesh(g.scene)
      return m ? { geometry: m.geometry, dict: m.morphTargetDictionary, mod: mods[i] } : null
    })
    const bodyPos = morphedPositions(src.geometry, src.morphTargetDictionary, weights)
    const cover = scalpCoverage(src.geometry, bodyPos, hair.filter((h): h is NonNullable<typeof h> => !!h), weights, neckY - 0.02)
    ;(attr.array as Float32Array).set(cover)
    attr.needsUpdate = true
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hairKey identifies the loaded hair meshes
  }, [body, bodyGltf, hairKey, mods, weights, neckY])
  return null
}

/**
 * Keeps the bottom inside an untucked top / jacket where they overlap (layerFit.ts) by writing the
 * bottom mesh's `aLayer` offsets in place. Own Suspense boundary: never hides the avatar while loading.
 */
function LayerFit({ inner, p, meta, innerId, outerIds, weights }: { inner: THREE.Mesh; p: Presentation; meta: AvatarMeta; innerId: string; outerIds: string[]; weights: Record<string, number> }) {
  const bodyGltf = useGLTF(partUrl(p, 'body'))
  const gltfs = useGLTF([innerId, ...outerIds].map((id) => partUrl(p, id))) as unknown as { scene: THREE.Object3D }[]
  const firstMesh = (o: THREE.Object3D) => {
    let found: THREE.Mesh | null = null
    o.traverse((c) => {
      if (!found && (c as THREE.Mesh).isMesh) found = c as THREE.Mesh
    })
    return found as THREE.Mesh | null
  }
  const key = gltfs.map((g) => g.scene.uuid).join('|')
  useEffect(() => {
    const attr = inner.geometry.getAttribute('aLayer') as THREE.BufferAttribute | undefined
    const body = firstMesh(bodyGltf.scene)
    const meshes = gltfs.map((g) => firstMesh(g.scene))
    if (!attr || !body || meshes.some((m) => !m)) return
    const [innerSrc, ...outers] = meshes as THREE.Mesh[]
    // Right after a garment change the live mesh can still be the previous garment: wait for the new one.
    if (attr.count !== innerSrc.geometry.getAttribute('position').count) return
    const bodyPos = morphedPositions(body.geometry, body.morphTargetDictionary, weights)
    const offsets = layerFitOffsets(
      { geometry: body.geometry, dict: body.morphTargetDictionary },
      bodyPos,
      outers.map((m) => ({ geometry: m.geometry, dict: m.morphTargetDictionary })),
      { geometry: innerSrc.geometry, dict: innerSrc.morphTargetDictionary },
      weights,
    )
    ;(attr.array as Float32Array).set(offsets)
    attr.needsUpdate = true
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key identifies the loaded meshes
  }, [inner, bodyGltf, key, weights, meta])
  return null
}

/**
 * Lengthens a dress: everything below the hips is stretched downwards by `k` (writes the dress mesh's
 * `aLayer` offsets, recomputed for the current morphs, so it follows height, weight and body type).
 */
function Lengthen({ mesh, p, meta, id, k, weights }: { mesh: THREE.Mesh; p: Presentation; meta: AvatarMeta; id: string; k: number; weights: Record<string, number> }) {
  const gltf = useGLTF(partUrl(p, id))
  useEffect(() => {
    let src: THREE.Mesh | null = null
    gltf.scene.traverse((o) => {
      if (!src && (o as THREE.Mesh).isMesh) src = o as THREE.Mesh
    })
    const source = src as THREE.Mesh | null
    const attr = mesh.geometry.getAttribute('aLayer') as THREE.BufferAttribute | undefined
    // Right after a garment change the live mesh can still be the previous garment: wait for the new one.
    if (!source || !attr || attr.count !== source.geometry.getAttribute('position').count) return
    const pos = morphedPositions(source.geometry, source.morphTargetDictionary, weights)
    const waist = (blendAnchor(meta, 'waist', weights) as number[] | undefined)?.[1] ?? 1
    const hipY = waist - 0.16
    const arr = attr.array as Float32Array
    arr.fill(0)
    for (let i = 0; i < attr.count; i++) {
      const y = pos[i * 3 + 1]
      if (y < hipY) arr[i * 3 + 1] = -(hipY - y) * (k - 1)
    }
    attr.needsUpdate = true
  }, [mesh, gltf, meta, k, weights])
  return null
}

/**
 * Reports the lowest point of the worn footwear for the current morphs. Each baked configuration is
 * grounded on its own, so blends of several can lift the soles a few millimetres; the avatar is moved
 * down by exactly that much. Own Suspense boundary, so a footwear change never hides the avatar.
 */
function Grounding({ url, weights, onGround }: { url: string; weights: Record<string, number>; onGround: (y: number) => void }) {
  const gltf = useGLTF(url)
  useEffect(() => {
    let mesh: THREE.Mesh | null = null
    gltf.scene.traverse((o) => {
      if (!mesh && (o as THREE.Mesh).isMesh) mesh = o as THREE.Mesh
    })
    const m = mesh as THREE.Mesh | null
    if (!m) return
    const pos = morphedPositions(m.geometry, m.morphTargetDictionary, weights)
    let min = Infinity
    for (let i = 1; i < pos.length; i += 3) if (pos[i] < min) min = pos[i]
    onGround(min)
  }, [gltf, weights, onGround])
  return null
}

function neutralMapFor(meta: AvatarMeta, id: string): string | null {
  // Newer builds record each garment's real base-colour texture; older ones are matched by name.
  if (meta.baseColor?.[id]) return meta.baseColor[id]
  const diffuse = meta.textures[id]?.find((t) => t.includes('diffuse'))
  return diffuse ? diffuse.replace(/\.(png|jpg)$/, '_neutral.jpg') : null
}

export function RealisticAvatar({ resolved, meta, isolate }: { resolved: ResolvedAvatar; meta: AvatarMeta; isolate?: string }) {
  const { presentation: p, config, worn } = resolved
  // Profile height first shapes the body through MakeHuman's height morph (natural proportions), then
  // the remaining difference is calibrated with a uniform scale below. Morphs only exist in newer builds.
  // MakeHuman grounds the figure on its shoe soles: the bare foot sits ~2 cm above the floor inside the
  // shoes. Stature (profile height) is measured barefoot, from the sole of the foot to the crown.
  const bodyGltf = useGLTF(partUrl(p, 'body'))
  const soleY = useMemo(() => {
    let src: THREE.Mesh | null = null
    bodyGltf.scene.traverse((o) => {
      if (!src && (o as THREE.Mesh).isMesh) src = o as THREE.Mesh
    })
    const mesh = src as THREE.Mesh | null
    if (!mesh) return () => 0
    return (w: Record<string, number>) => {
      const pos = morphedPositions(mesh.geometry, mesh.morphTargetDictionary, w)
      let min = Infinity
      for (let i = 1; i < pos.length; i += 3) if (pos[i] < min) min = pos[i]
      return min
    }
  }, [bodyGltf])
  const weights = useMemo(() => {
    if (!meta.configs.height?.length) return resolved.morphs
    const top = (w: Record<string, number>) => (blendAnchor(meta, 'head_top', w) as number[] | undefined)?.[1]
    // The morph aims the crown at profile height + sole height (both in model units, before scaling).
    const target = resolved.heightCm + soleY(resolved.morphs) * 100
    return { ...resolved.morphs, ...heightMorph(top, target, resolved.morphs) }
  }, [meta, resolved.morphs, resolved.heightCm, soleY])
  const sole = useMemo(() => soleY(weights), [soleY, weights])
  // Lowest point that touches the floor: the shoe sole when footwear is worn, else the bare foot.
  const [shoeFloor, setShoeFloor] = useState<{ id: string; y: number } | null>(null)
  const footwearId = worn.footwear && meta.garments[worn.footwear.id] ? worn.footwear.id : null
  const onGround = useMemo(() => (y: number) => footwearId && setShoeFloor({ id: footwearId, y }), [footwearId])
  const ground = footwearId ? (shoeFloor?.id === footwearId ? shoeFloor.y : 0) : sole

  const skinTone = SKIN_TONES.find((t) => t.id === resolved.skinTone) ?? SKIN_TONES[3]
  const skin = useMemo(() => ({ map: SKIN_TEXTURES[p][skinTone.texture], tint: skinTone.tint }), [p, skinTone])
  const eyeMap = `${(EYE_COLORS.find((e) => e.id === config.eyeColor) ?? EYE_COLORS[0]).id}_eye.png`
  const hairColor = (HAIR_COLORS.find((h) => h.id === config.hairColor) ?? HAIR_COLORS[1]).hex
  const hairHighlight = HAIR_HIGHLIGHTS.find((h) => h.id === config.hairHighlight)?.hex ?? null

  // Outerwear includes its own shirt front, so the top is not drawn underneath it. A one-piece
  // outfit (dress / suit / kimono) replaces top, outerwear and bottom.
  const slots = (['top', 'outerwear', 'bottom', 'full', 'footwear', 'hat'] as const).filter((s) => {
    if (!worn[s]) return false
    if (s === 'top' && worn.outerwear) return false
    if (worn.full && (s === 'top' || s === 'outerwear' || s === 'bottom')) return false
    return true
  })
  // A wide skirt (lehenga-style) is worn over the top: the top is tucked inside it instead.
  const skirtOver = slots.includes('bottom') && !!garment(worn.bottom?.id)?.overTop && !!meta.garments[worn.bottom!.id]
  const upperSlot = slots.includes('outerwear') ? 'outerwear' : slots.includes('top') ? 'top' : null
  // Untucked top / jacket worn over the bottom: the bottom is fitted inside it (LayerFit).
  const layerOuter = useMemo(
    () => (skirtOver ? [] : (['top', 'outerwear'] as const).filter((s) => slots.includes(s) && meta.garments[worn[s]!.id]).map((s) => worn[s]!.id)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [meta, skirtOver, slots.map((s) => worn[s]!.id).join('|')],
  )
  // Sleeveless dresses get a fitted long-sleeve layer underneath; short ones are lengthened.
  const dress = slots.includes('full') && meta.garments[worn.full!.id] ? garment(worn.full!.id) : undefined
  const underId = dress?.underlayer && meta.garments[dress.underlayer] ? dress.underlayer : null
  const underColor = worn.full?.color ?? dress?.underlayerColor ?? '#2e2e33'
  const hiddenBits = useMemo(
    () => [...slots.map((s) => worn[s]!.id), ...(underId ? [underId] : [])].map((id) => meta.maskBits[id]).filter((b): b is number => typeof b === 'number'),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [meta, underId, slots.map((s) => worn[s]!.id).join('|')],
  )

  // Hairstyle = one or two real hair meshes (optionally modified in the shader) + procedural parts.
  const style = hairStyle(resolved.hairstyle) ?? hairStyle(DEFAULT_HAIRSTYLE[p])!
  const frame = useMemo(() => headFrame(meta, weights), [meta, weights])
  // Every layer gets the head frame (an empty mod changes nothing): highlights are placed relative to it.
  const hairMods = useMemo(() => style.layers.map((l) => shaderMod(l.mod ?? {}, frame)), [style, frame])

  // Stature uses the crown of the *morphed* head (height, body, face and age morphs all move it), and
  // whatever the height morph could not reach is calibrated with a uniform scale (no distortion).
  const [bodyMesh, setBodyMesh] = useState<THREE.Mesh | null>(null)
  const [bottomMesh, setBottomMesh] = useState<THREE.Mesh | null>(null)
  const [upperMesh, setUpperMesh] = useState<THREE.Mesh | null>(null)
  const [fullMesh, setFullMesh] = useState<THREE.Mesh | null>(null)
  const [underMesh, setUnderMesh] = useState<THREE.Mesh | null>(null)
  // Skin under the hair and under facial hair gets the root shading.
  const facial = resolved.facialHair && meta.facialHair?.includes(resolved.facialHair) ? resolved.facialHair : null
  const shadedLayers = useMemo(() => [...style.layers.map((l) => l.mesh as string), ...(facial ? [facial] : [])], [style, facial])
  const shadedMods = useMemo(() => [...hairMods, ...(facial ? [null] : [])], [hairMods, facial])
  const skinDetail = useMemo(
    () => ({ ageMap: `age_detail_${p === 'male' ? 'male' : 'female'}.png`, ageWeights: ageDetailWeights(resolved.ageYears), scalp: hairColor }),
    [p, resolved.ageYears, hairColor],
  )

  const headTop = (blendAnchor(meta, 'head_top', weights) as number[] | undefined)?.[1] ?? (meta.anchors.basis.head_top as number[])[1]
  // Calibrated barefoot stature: crown minus sole = profile height (shoes add their real sole height).
  const scale = resolved.heightCm / 100 / (headTop - sole)
  const yaw = config.pose === 'three_quarter' ? -0.5 : 0

  if (isolate) {
    // Thumbnail tool: a single garment on its own (as fitted to this body), shown as worn: a dress with
    // its long-sleeve layer and its lengthened skirt.
    const iso = garment(isolate)
    const isoUnder = iso?.underlayer && meta.garments[iso.underlayer] ? iso.underlayer : null
    return (
      <group scale={scale}>
        <AvatarPart url={partUrl(p, isolate)} kind="garment" weights={weights} garmentColor={null} garmentNeutralMap={null} onMesh={setFullMesh} />
        {isoUnder && (
          <Suspense fallback={null}>
            <AvatarPart url={partUrl(p, isoUnder)} kind="garment" weights={weights} garmentColor={iso!.underlayerColor ?? '#2e2e33'} garmentNeutralMap={null} plain onMesh={setUnderMesh} />
          </Suspense>
        )}
        {isoUnder && underMesh && (
          <Suspense fallback={null}>
            <LayerFit inner={underMesh} p={p} meta={meta} innerId={isoUnder} outerIds={[isolate]} weights={weights} />
          </Suspense>
        )}
        {iso?.lengthen && fullMesh && (
          <Suspense fallback={null}>
            <Lengthen mesh={fullMesh} p={p} meta={meta} id={isolate} k={iso.lengthen} weights={weights} />
          </Suspense>
        )}
      </group>
    )
  }

  return (
    <group rotation={[0, yaw, 0]} scale={scale} position={[0, -ground * scale, 0]}>
      <AvatarPart url={partUrl(p, 'body')} kind="body" weights={weights} hiddenBits={hiddenBits} skin={skin} skinDetail={skinDetail} onMesh={setBodyMesh} />
      {bodyMesh && (
        <Suspense fallback={null}>
          <ScalpShading body={bodyMesh} p={p} layers={shadedLayers} mods={shadedMods} weights={weights} neckY={frame.neck.y} />
        </Suspense>
      )}
      <AvatarPart url={partUrl(p, 'eyes')} kind="eyes" weights={weights} eyeMap={eyeMap} />
      <AvatarPart url={partUrl(p, 'eyelashes')} kind="lashes" weights={weights} />
      <AvatarPart url={partUrl(p, 'teeth')} kind="teeth" weights={weights} />
      <Suspense fallback={null}>
        <AvatarPart url={partUrl(p, resolved.eyebrows)} kind="brows" weights={weights} hairColor={hairColor} />
      </Suspense>
      {resolved.facialHair && meta.facialHair?.includes(resolved.facialHair) && (
        <Suspense fallback={null}>
          <AvatarPart url={partUrl(p, resolved.facialHair)} kind="hair" weights={weights} hairColor={hairColor} hairMod={null} />
        </Suspense>
      )}
      {style.layers.map((layer, i) => (
        <Suspense key={`hair${i}:${layer.mesh}`} fallback={null}>
          <AvatarPart url={partUrl(p, layer.mesh)} kind="hair" weights={weights} hairColor={hairColor} hairHighlight={hairHighlight} hairMod={hairMods[i]} />
        </Suspense>
      ))}
      {style.parts?.length ? (
        <Suspense fallback={null}>
          <ProceduralHair presentation={p} meta={meta} weights={weights} parts={style.parts} color={hairColor} highlight={hairHighlight} />
        </Suspense>
      ) : null}
      {slots.map((s) => {
        const w = worn[s]!
        if (!meta.garments[w.id]) return null
        const tintable = garment(w.id)?.tintable
        return (
          <Suspense key={s} fallback={null}>
            <AvatarPart
              url={partUrl(p, w.id)}
              kind="garment"
              weights={weights}
              garmentColor={tintable ? w.color : null}
              garmentNeutralMap={tintable ? neutralMapFor(meta, w.id) : null}
              onMesh={s === 'bottom' ? setBottomMesh : s === 'full' ? setFullMesh : s === upperSlot ? setUpperMesh : undefined}
            />
          </Suspense>
        )
      })}
      {underId && (
        <Suspense fallback={null}>
          <AvatarPart url={partUrl(p, underId)} kind="garment" weights={weights} garmentColor={underColor} garmentNeutralMap={null} plain onMesh={setUnderMesh} />
        </Suspense>
      )}
      {underId && underMesh && (
        <Suspense fallback={null}>
          <LayerFit inner={underMesh} p={p} meta={meta} innerId={underId} outerIds={[worn.full!.id]} weights={weights} />
        </Suspense>
      )}
      {dress?.lengthen && fullMesh && (
        <Suspense fallback={null}>
          <Lengthen mesh={fullMesh} p={p} meta={meta} id={worn.full!.id} k={dress.lengthen} weights={weights} />
        </Suspense>
      )}
      {skirtOver && upperSlot && upperMesh && meta.garments[worn[upperSlot]!.id] && (
        <Suspense fallback={null}>
          <LayerFit inner={upperMesh} p={p} meta={meta} innerId={worn[upperSlot]!.id} outerIds={[worn.bottom!.id]} weights={weights} />
        </Suspense>
      )}
      {footwearId && (
        <Suspense fallback={null}>
          <Grounding url={partUrl(p, footwearId)} weights={weights} onGround={onGround} />
        </Suspense>
      )}
      {bottomMesh && layerOuter.length > 0 && slots.includes('bottom') && (
        <Suspense fallback={null}>
          <LayerFit inner={bottomMesh} p={p} meta={meta} innerId={worn.bottom!.id} outerIds={layerOuter} weights={weights} />
        </Suspense>
      )}
      <AccessoryMeshes meta={meta} weights={weights} accessories={resolved.accessories} />
    </group>
  )
}
