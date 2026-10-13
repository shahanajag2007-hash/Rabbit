import * as THREE from 'three'
import type { HairShaderMod } from './ProceduralHair'

/**
 * Scalp coverage: how much of each body vertex lies *under* the current hairstyle.
 *
 * Hair cards are thin strips with gaps between them. Without this, the pale scalp skin shows through
 * those gaps as bright streaks and the hairline ends in a hard edge against bare skin, which is what
 * makes hair look like a wig. The body shader (skinShader.ts) uses this value to shade covered scalp
 * in a darker root tone of the hair colour, with a soft transition at the hairline.
 *
 * Computed from the real hair triangles after the morph targets and the same style transforms as the
 * hair shader (hairShader.ts: mirror, side part, crop, scalp/fringe keep, trim, fade), so it matches
 * what is actually drawn for every body, face and age configuration.
 */

type V3 = THREE.Vector3

/** Morphed object-space positions of a mesh for the given morph weights. */
export function morphedPositions(geometry: THREE.BufferGeometry, dict: Record<string, number> | undefined, weights: Record<string, number>): Float32Array {
  const pos = geometry.getAttribute('position') as THREE.BufferAttribute
  const out = new Float32Array(pos.array.length)
  out.set(pos.array as ArrayLike<number>)
  const morphs = geometry.morphAttributes.position ?? []
  const relative = geometry.morphTargetsRelative
  for (const [name, w] of Object.entries(weights)) {
    const i = dict?.[name]
    if (i === undefined || !w) continue
    const m = morphs[i].array as ArrayLike<number>
    if (relative) for (let k = 0; k < out.length; k++) out[k] += m[k] * w
    else for (let k = 0; k < out.length; k++) out[k] += (m[k] - (pos.array as ArrayLike<number>)[k]) * w
  }
  return out
}

/** CPU mirror of the hair shader: transformed position + how much of it survives the cuts (0..1). */
function hairVertex(p: V3, mod: HairShaderMod | null): number {
  if (!mod) return 1
  const f = mod.frame
  if (mod.mirror) p.x = -p.x
  if (mod.part) {
    const sx = f.rx + 0.02
    const sy = f.R + 0.02
    const qx = p.x / sx
    const qy = (p.y - f.headY) / sy
    const t = THREE.MathUtils.smoothstep(p.y, f.earY - 0.02, f.eyeY + 0.05)
    const a = -mod.part * t
    p.x = (qx * Math.cos(a) - qy * Math.sin(a)) * sx
    p.y = f.headY + (qx * Math.sin(a) + qy * Math.cos(a)) * sy
  }
  if (mod.crop) {
    const c = new THREE.Vector3(0, f.headY, f.headZ - 0.008)
    const radii = new THREE.Vector3(f.rx - 0.006, f.R, f.R * 0.97)
    const d = p.clone().sub(c).divide(radii)
    const r = d.length()
    if (r >= 1) {
      const target = c.clone().add(d.divideScalar(r).multiply(radii)).add(p.clone().sub(c).normalize().multiplyScalar(0.003))
      p.lerp(target, mod.crop)
    }
  }
  let keep = 1
  if (mod.keep === 1) {
    const dx = p.x / (f.rx + 0.022)
    const dy = (p.y - f.headY) / (f.R + 0.03)
    const dz = (p.z - (f.headZ - 0.008)) / (f.R + 0.004)
    if (dx * dx + dy * dy + dz * dz > 1 || p.y < f.earY - 0.03) return 0
    keep = Math.min(1, (p.y - (f.earY - 0.03)) / 0.02)
  } else if (mod.keep === 2) {
    if (p.z < f.headZ + 0.035 || p.y < f.eyeY + 0.03) return 0
  }
  if (mod.trimY !== null && p.y < mod.trimY) return 0
  if (mod.fade) {
    if (p.y < mod.fade[0]) return 0
    keep *= Math.min(1, (p.y - mod.fade[0]) / Math.max(1e-4, mod.fade[1] - mod.fade[0]))
  }
  return keep
}

export interface HairLayerInput {
  geometry: THREE.BufferGeometry
  dict: Record<string, number> | undefined
  mod: HairShaderMod | null
}

const CELL = 0.01
// Numeric cell key (the avatar fits well inside +-5 m on every axis).
const cellKey = (ix: number, iy: number, iz: number) => ((ix + 512) * 1024 + (iy + 512)) * 1024 + (iz + 512)
const key = (x: number, y: number, z: number) => cellKey(Math.floor(x / CELL), Math.floor(y / CELL), Math.floor(z / CELL))

/**
 * Per-vertex scalp coverage (0..1) for the body.
 * @param body      body geometry (original vertex order; index used for smoothing)
 * @param bodyPos   morphed body positions
 * @param minY      only vertices above this height are considered (neck and head)
 */
export function scalpCoverage(body: THREE.BufferGeometry, bodyPos: Float32Array, layers: HairLayerInput[], weights: Record<string, number>, minY: number): Float32Array {
  const n = bodyPos.length / 3
  const cover = new Float32Array(n)
  // 1. Sample every surviving hair triangle at ~4 mm into a spatial hash (keep weight per sample).
  const grid = new Map<number, number[]>()
  const pts: number[] = []
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const p = new THREE.Vector3()
  for (const layer of layers) {
    const pos = morphedPositions(layer.geometry, layer.dict, weights)
    const idx = layer.geometry.index
    const triCount = idx ? idx.count / 3 : pos.length / 9
    const vtx = (i: number, out: V3) => out.set(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2])
    for (let t = 0; t < triCount; t++) {
      const i0 = idx ? idx.getX(t * 3) : t * 3
      const i1 = idx ? idx.getX(t * 3 + 1) : t * 3 + 1
      const i2 = idx ? idx.getX(t * 3 + 2) : t * 3 + 2
      vtx(i0, a)
      vtx(i1, b)
      vtx(i2, c)
      if (a.y < minY - 0.05 && b.y < minY - 0.05 && c.y < minY - 0.05) continue
      const edge = Math.max(a.distanceTo(b), b.distanceTo(c), c.distanceTo(a))
      const steps = Math.min(24, Math.max(1, Math.ceil(edge / 0.004)))
      for (let i = 0; i <= steps; i++)
        for (let j = 0; j <= steps - i; j++) {
          const u = i / steps
          const v = j / steps
          p.set(0, 0, 0).addScaledVector(a, 1 - u - v).addScaledVector(b, u).addScaledVector(c, v)
          const keep = hairVertex(p, layer.mod)
          if (keep <= 0.05) continue
          const k = key(p.x, p.y, p.z)
          let cell = grid.get(k)
          if (!cell) grid.set(k, (cell = []))
          cell.push(pts.length)
          pts.push(p.x, p.y, p.z, keep)
        }
    }
  }
  if (!pts.length) return cover

  // 2. A body vertex is covered when hair lies just outside it along its normal (not beside it).
  const normal = body.getAttribute('normal') as THREE.BufferAttribute
  const nrm = new THREE.Vector3()
  const bp = new THREE.Vector3()
  const d = new THREE.Vector3()
  for (let i = 0; i < n; i++) {
    const y = bodyPos[i * 3 + 1]
    if (y < minY) continue
    bp.set(bodyPos[i * 3], y, bodyPos[i * 3 + 2])
    nrm.fromBufferAttribute(normal, i).normalize()
    let best = 0
    const cx = Math.floor(bp.x / CELL)
    const cy = Math.floor(bp.y / CELL)
    const cz = Math.floor(bp.z / CELL)
    for (let dx = -3; dx <= 3; dx++)
      for (let dy = -3; dy <= 3; dy++)
        for (let dz = -3; dz <= 3; dz++) {
          const cell = grid.get(cellKey(cx + dx, cy + dy, cz + dz))
          if (!cell) continue
          for (const s of cell) {
            d.set(pts[s] - bp.x, pts[s + 1] - bp.y, pts[s + 2] - bp.z)
            const along = d.dot(nrm)
            if (along < -0.004 || along > 0.03) continue
            const lateral = Math.sqrt(Math.max(0, d.lengthSq() - along * along))
            const w = pts[s + 3] * (1 - THREE.MathUtils.smoothstep(lateral, 0.003, 0.012))
            if (w > best) best = w
          }
        }
    cover[i] = best
  }

  // 3. Two smoothing passes over the mesh edges: a soft hairline (fine roots and shadow over a few
  //    millimetres) instead of a hard cut between hair and bare skin.
  const index = body.index
  for (let pass = 0; pass < 2 && index; pass++) {
    const sum = new Float32Array(n)
    const cnt = new Float32Array(n)
    for (let t = 0; t < index.count; t += 3) {
      const v = [index.getX(t), index.getX(t + 1), index.getX(t + 2)]
      for (const x of v)
        for (const y of v) {
          sum[x] += cover[y]
          cnt[x] += 1
        }
    }
    for (let i = 0; i < n; i++) if (cnt[i]) cover[i] = 0.5 * cover[i] + 0.5 * (sum[i] / cnt[i])
  }
  return cover
}
