import * as THREE from 'three'
import { morphedPositions } from './scalpCoverage'

/**
 * Garment layering. Every garment is fitted to the body on its own, so where an untucked top (sweater,
 * tunic, jacket) overlaps a bottom, whichever lies further from the skin pokes through the other.
 *
 * For each body vertex we measure how far the outer garment sits from the skin along the body normal.
 * Every vertex of the inner garment (the bottom) that lies under the outer garment is then pulled in
 * along that normal to just inside the outer garment (and never into the skin). The result is a per-
 * vertex offset applied after the morph targets (garment shader in RealisticAvatar), recomputed when
 * the garments or the body morphs change, so it follows height, weight, age and body type.
 */

const CELL = 0.01
const cellKey = (ix: number, iy: number, iz: number) => ((ix + 512) * 1024 + (iy + 512)) * 1024 + (iz + 512)
const keyOf = (x: number, y: number, z: number) => cellKey(Math.floor(x / CELL), Math.floor(y / CELL), Math.floor(z / CELL))

export interface MeshInput {
  geometry: THREE.BufferGeometry
  dict: Record<string, number> | undefined
}

/** Points sampled every ~5 mm over a mesh's (morphed) triangles, with the surface normal, in a spatial hash. */
function sampleSurface(mesh: MeshInput, weights: Record<string, number>) {
  const pos = morphedPositions(mesh.geometry, mesh.dict, weights)
  const idx = mesh.geometry.index
  const triCount = idx ? idx.count / 3 : pos.length / 9
  const grid = new Map<number, number[]>()
  const pts: number[] = []
  const nrm: number[] = []
  const normal = mesh.geometry.getAttribute('normal') as THREE.BufferAttribute | undefined
  const fn = new THREE.Vector3()
  const tmp = new THREE.Vector3()
  let minY = Infinity
  let maxY = -Infinity
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const p = new THREE.Vector3()
  const vtx = (i: number, out: THREE.Vector3) => out.set(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2])
  for (let t = 0; t < triCount; t++) {
    const i0 = idx ? idx.getX(t * 3) : t * 3
    const i1 = idx ? idx.getX(t * 3 + 1) : t * 3 + 1
    const i2 = idx ? idx.getX(t * 3 + 2) : t * 3 + 2
    vtx(i0, a)
    vtx(i1, b)
    vtx(i2, c)
    // Outward normal of the garment surface (vertex normals as authored, averaged over the triangle).
    fn.set(0, 0, 0)
    if (normal) for (const i of [i0, i1, i2]) fn.add(tmp.fromBufferAttribute(normal, i))
    fn.normalize()
    const edge = Math.max(a.distanceTo(b), b.distanceTo(c), c.distanceTo(a))
    const steps = Math.min(20, Math.max(1, Math.ceil(edge / 0.005)))
    for (let i = 0; i <= steps; i++)
      for (let j = 0; j <= steps - i; j++) {
        p.set(0, 0, 0).addScaledVector(a, 1 - (i + j) / steps).addScaledVector(b, i / steps).addScaledVector(c, j / steps)
        const k = keyOf(p.x, p.y, p.z)
        let cell = grid.get(k)
        if (!cell) grid.set(k, (cell = []))
        cell.push(pts.length)
        pts.push(p.x, p.y, p.z)
        nrm.push(fn.x, fn.y, fn.z)
        if (p.y < minY) minY = p.y
        if (p.y > maxY) maxY = p.y
      }
  }
  return { grid, pts, nrm, minY, maxY }
}

/**
 * Per-vertex offsets (x, y, z) for `inner` so it stays inside `outers` where they overlap.
 * @param body     original body geometry (normals) and its morphed positions
 */
export function layerFitOffsets(
  body: MeshInput,
  bodyPos: Float32Array,
  outers: MeshInput[],
  inner: MeshInput,
  weights: Record<string, number>,
): Float32Array {
  const innerPos = morphedPositions(inner.geometry, inner.dict, weights)
  const offsets = new Float32Array(innerPos.length)
  if (!outers.length) return offsets
  const outer = outers.map((o) => sampleSurface(o, weights))
  const yLo = Math.min(...outer.map((o) => o.minY)) - 0.03
  const yHi = Math.max(...outer.map((o) => o.maxY))

  // 1. Body vertices in the overlap band: distance of the outer garment along the body normal.
  const normal = body.geometry.getAttribute('normal') as THREE.BufferAttribute
  const nb = bodyPos.length / 3
  const outerDist = new Float32Array(nb).fill(-1)
  const cover = new Float32Array(nb)
  const bodyGrid = new Map<number, number[]>()
  const n = new THREE.Vector3()
  const bp = new THREE.Vector3()
  const d = new THREE.Vector3()
  for (let i = 0; i < nb; i++) {
    const y = bodyPos[i * 3 + 1]
    if (y < yLo || y > yHi) continue
    bp.set(bodyPos[i * 3], y, bodyPos[i * 3 + 2])
    n.fromBufferAttribute(normal, i).normalize()
    let best = Infinity
    let w = 0
    // March along the normal up to 8 cm, looking for outer-garment samples close to the ray.
    for (let t = 0; t <= 0.08; t += 0.01) {
      const cx = Math.floor((bp.x + n.x * t) / CELL)
      const cy = Math.floor((bp.y + n.y * t) / CELL)
      const cz = Math.floor((bp.z + n.z * t) / CELL)
      for (const o of outer)
        for (let dx = -1; dx <= 1; dx++)
          for (let dy = -1; dy <= 1; dy++)
            for (let dz = -1; dz <= 1; dz++) {
              const cell = o.grid.get(cellKey(cx + dx, cy + dy, cz + dz))
              if (!cell) continue
              for (const s of cell) {
                d.set(o.pts[s] - bp.x, o.pts[s + 1] - bp.y, o.pts[s + 2] - bp.z)
                const along = d.dot(n)
                if (along < -0.004) continue
                // Only count the garment if we meet it from the inside (its normal faces along the ray).
                // A hand hanging beside the hip meets the outside of a tunic and must not count.
                if (o.nrm[s] * n.x + o.nrm[s + 1] * n.y + o.nrm[s + 2] * n.z < 0.2) continue
                const lateral = Math.sqrt(Math.max(0, d.lengthSq() - along * along))
                const lw = 1 - THREE.MathUtils.smoothstep(lateral, 0.01, 0.02)
                if (lw <= 0) continue
                if (along < best) best = along
                if (lw > w) w = lw
              }
            }
      if (best < Infinity && t > best + 0.02) break
    }
    if (best === Infinity) continue
    outerDist[i] = Math.max(0, best)
    cover[i] = w
    const k = keyOf(bp.x, bp.y, bp.z)
    let cell = bodyGrid.get(k)
    if (!cell) bodyGrid.set(k, (cell = []))
    cell.push(i)
  }

  // 2. Inner-garment vertices: nearest covered body vertex -> pull in along its normal.
  const ni = innerPos.length / 3
  const v = new THREE.Vector3()
  for (let i = 0; i < ni; i++) {
    v.set(innerPos[i * 3], innerPos[i * 3 + 1], innerPos[i * 3 + 2])
    if (v.y < yLo || v.y > yHi) continue
    const cx = Math.floor(v.x / CELL)
    const cy = Math.floor(v.y / CELL)
    const cz = Math.floor(v.z / CELL)
    let nearest = -1
    let nd = Infinity
    for (let dx = -4; dx <= 4; dx++)
      for (let dy = -2; dy <= 2; dy++)
        for (let dz = -4; dz <= 4; dz++) {
          const cell = bodyGrid.get(cellKey(cx + dx, cy + dy, cz + dz))
          if (!cell) continue
          for (const b of cell) {
            const dist = (bodyPos[b * 3] - v.x) ** 2 + (bodyPos[b * 3 + 1] - v.y) ** 2 + (bodyPos[b * 3 + 2] - v.z) ** 2
            if (dist < nd) {
              nd = dist
              nearest = b
            }
          }
        }
    if (nearest < 0) continue
    n.fromBufferAttribute(normal, nearest).normalize()
    bp.set(bodyPos[nearest * 3], bodyPos[nearest * 3 + 1], bodyPos[nearest * 3 + 2])
    const current = d.copy(v).sub(bp).dot(n)
    // 8 mm inside the outer garment (clears its folds), at least 1.5 mm above the skin (which is masked).
    const target = Math.max(0.0015, outerDist[nearest] - 0.008)
    if (current <= target) continue
    const pull = (target - current) * cover[nearest]
    offsets[i * 3] = n.x * pull
    offsets[i * 3 + 1] = n.y * pull
    offsets[i * 3 + 2] = n.z * pull
  }

  // 3. Smooth the offsets over the inner mesh so the hem of the overlap blends in without a step.
  const index = inner.geometry.index
  for (let pass = 0; pass < 4 && index; pass++) {
    const sum = new Float32Array(offsets.length)
    const cnt = new Float32Array(ni)
    for (let t = 0; t < index.count; t += 3) {
      const tri = [index.getX(t), index.getX(t + 1), index.getX(t + 2)]
      for (const a of tri)
        for (const b of tri) {
          sum[a * 3] += offsets[b * 3]
          sum[a * 3 + 1] += offsets[b * 3 + 1]
          sum[a * 3 + 2] += offsets[b * 3 + 2]
          cnt[a] += 1
        }
    }
    for (let i = 0; i < ni; i++) {
      if (!cnt[i]) continue
      // Keep at least the vertex's own pull (smoothing must not let it pop back out).
      for (let k = 0; k < 3; k++) {
        const avg = sum[i * 3 + k] / cnt[i]
        offsets[i * 3 + k] = Math.abs(avg) > Math.abs(offsets[i * 3 + k]) ? avg : offsets[i * 3 + k]
      }
    }
  }
  return offsets
}
