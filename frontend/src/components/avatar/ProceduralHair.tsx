import { useGLTF } from '@react-three/drei'
import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import { applyHairHighlight, applyHairMod } from './hairShader'
import { blendAnchor, partUrl, type AvatarMeta } from './avatarAssets'
import type { Presentation } from './avatarCatalog'
import type { BunPlace, HairLevel, HairMod, HairPart, TailPlace } from './hairStyles'

/**
 * Procedural hair parts (braids, ponytails, buns, gajra) modelled in three.js and attached to the
 * head anchors that the Blender build measured on each model and morph configuration. Paths below
 * the head follow the body surface of the current body (morphs applied), so a braid lies on the back,
 * over the shoulder or down the chest of whichever body is shown.
 */

type V3 = THREE.Vector3
const vec = (a: unknown) => new THREE.Vector3(...(((a as number[]) ?? [0, 0, 0]) as [number, number, number]))

// ---------------------------------------------------------------------------------------------
// Head frame (object space of the model, before the height scale)
// ---------------------------------------------------------------------------------------------
export interface HeadFrame {
  head: V3
  top: V3
  earL: V3
  earR: V3
  neck: V3
  eyeY: number
  eyeZ: number
  /** head centre -> crown */
  R: number
  /** half-width of the hair shell at ear height */
  rx: number
}

export function headFrame(meta: AvatarMeta, w: Record<string, number>): HeadFrame {
  const a = (k: string) => vec(blendAnchor(meta, k, w))
  const head = a('head')
  const top = a('head_top')
  const earL = a('ear_l')
  const earR = a('ear_r')
  const eye = a('eye_l')
  const R = top.y - head.y
  return { head, top, earL, earR, neck: a('neck'), eyeY: eye.y, eyeZ: eye.z, R, rx: Math.abs(earL.x) + 0.012 }
}

export function levelY(f: HeadFrame, level: HairLevel): number {
  switch (level) {
    case 'brow':
      return f.eyeY + 0.03
    case 'ear':
      return f.earL.y - 0.012
    case 'jaw':
      return f.eyeY - 0.118
    case 'shoulder':
      return f.neck.y - 0.055
    case 'collarbone':
      return f.neck.y - 0.09
    case 'chest':
      return f.neck.y - 0.16
  }
}

/** Uniforms for the hair-mesh shader modifications (see RealisticAvatar's hair material). */
export interface HairShaderMod {
  keep: 0 | 1 | 2 // none | scalp | fringe
  trimY: number | null
  fade: [number, number] | null
  wave: [number, number] | null
  volume: number
  spike: [number, number] | null
  lift: number
  crop: number
  part: number
  mirror: boolean
  frame: { earY: number; topY: number; headY: number; headZ: number; eyeY: number; eyeZ: number; neckY: number; R: number; rx: number }
}

export function shaderMod(mod: HairMod | undefined, f: HeadFrame): HairShaderMod | null {
  if (!mod) return null
  const span = f.top.y - f.earL.y
  return {
    keep: mod.keep === 'scalp' ? 1 : mod.keep === 'fringe' ? 2 : 0,
    trimY: mod.trim ? levelY(f, mod.trim) : null,
    fade: mod.fade ? [f.earL.y + mod.fade.from * span, f.earL.y + Math.max(mod.fade.to, mod.fade.from + 0.003) * span] : null,
    wave: mod.wave ? [mod.wave.amp, mod.wave.freq] : null,
    volume: mod.volume ?? 0,
    spike: mod.spike ? [mod.spike.amount, mod.spike.centre ?? 0] : null,
    lift: mod.lift ?? 0,
    crop: mod.crop ?? 0,
    part: mod.part ?? 0,
    mirror: !!mod.mirror,
    frame: { earY: f.earL.y, topY: f.top.y, headY: f.head.y, headZ: f.head.z, eyeY: f.eyeY, eyeZ: f.eyeZ, neckY: f.neck.y, R: f.R, rx: f.rx },
  }
}

// ---------------------------------------------------------------------------------------------
// Body profile: back / front surface of the current (morphed) body, binned on a 1 cm grid
// ---------------------------------------------------------------------------------------------
const CELL = 0.01
const X0 = -0.34
const NX = 69
const NY = 200

class BodyProfile {
  private minZ = new Float32Array(NX * NY).fill(Infinity)
  private maxZ = new Float32Array(NX * NY).fill(-Infinity)
  private topY = new Float32Array(NX).fill(-Infinity)

  constructor(geometry: THREE.BufferGeometry, dict: Record<string, number> | undefined, weights: Record<string, number>, neckY: number) {
    const pos = geometry.getAttribute('position')
    const morphs = geometry.morphAttributes.position ?? []
    const active = Object.entries(weights)
      .map(([k, w]) => ({ attr: dict && dict[k] !== undefined ? morphs[dict[k]] : undefined, w }))
      .filter((m) => m.attr && m.w)
    const p = new THREE.Vector3()
    for (let i = 0; i < pos.count; i++) {
      p.fromBufferAttribute(pos, i)
      for (const m of active) {
        p.x += m.attr!.getX(i) * m.w
        p.y += m.attr!.getY(i) * m.w
        p.z += m.attr!.getZ(i) * m.w
      }
      const ix = Math.round((p.x - X0) / CELL)
      const iy = Math.round(p.y / CELL)
      if (ix < 0 || ix >= NX || iy < 0 || iy >= NY) continue
      const k = iy * NX + ix
      if (p.z < this.minZ[k]) this.minZ[k] = p.z
      if (p.z > this.maxZ[k]) this.maxZ[k] = p.z
      if (p.y < neckY - 0.01 && p.y > this.topY[ix]) this.topY[ix] = p.y
    }
  }

  private look(arr: Float32Array, y: number, x: number, pick: (a: number, b: number) => number, empty: number): number {
    const ix = Math.round((x - X0) / CELL)
    const iy = Math.round(y / CELL)
    // Always search at least +-2 cm: where the mesh is sparse, the exact cell can hold only a vertex on
    // the opposite side of the body (e.g. the face, behind the head's centre line), which would put
    // hair inside the head.
    for (let r = 2; r <= 5; r++) {
      let best = empty
      for (let dy = -r; dy <= r; dy++)
        for (let dx = -r; dx <= r; dx++) {
          const xx = ix + dx
          const yy = iy + dy
          if (xx < 0 || xx >= NX || yy < 0 || yy >= NY) continue
          best = pick(best, arr[yy * NX + xx])
        }
      if (Number.isFinite(best)) return best
    }
    return 0
  }

  /** Most-backward surface z near (x, y): max over a small window of the back of the body. */
  back(y: number, x: number): number {
    return this.look(this.minZ, y, x, Math.min, Infinity)
  }

  front(y: number, x: number): number {
    return this.look(this.maxZ, y, x, Math.max, -Infinity)
  }

  shoulderTop(x: number): number {
    const ix = Math.round((x - X0) / CELL)
    return this.topY[Math.max(0, Math.min(NX - 1, ix))]
  }
}

/** The profile is measured on the skin; hair below the neck lies on top of the worn garment. */
const CLOTHING = 0.024

// ---------------------------------------------------------------------------------------------
// Scalp ellipsoid (outer surface of the hair shell) and paths
// ---------------------------------------------------------------------------------------------
function scalp(f: HeadFrame) {
  const c = new THREE.Vector3(0, f.head.y, f.head.z - 0.008)
  const ry = f.R + 0.006
  const rz = f.R * 0.98
  return {
    c,
    rx: f.rx,
    ry,
    rz,
    /** Point on the hair surface: yaw around the head (0 = back, +pi/2 = left side), pitch (0 = ear line, pi/2 = crown). */
    at(yaw: number, pitch: number, out = 0): V3 {
      const cp = Math.cos(pitch)
      return new THREE.Vector3(Math.sin(yaw) * cp * (f.rx + out), c.y + Math.sin(pitch) * (ry + out), c.z - Math.cos(yaw) * cp * (rz + out))
    },
    /** z of the back of the hair shell at height y (for paths that must stay behind the head). */
    backZ(y: number): number {
      const t = Math.min(1, Math.abs(y - c.y) / ry)
      return c.z - rz * Math.sqrt(Math.max(0, 1 - t * t))
    },
  }
}

type Scalp = ReturnType<typeof scalp>

/**
 * Hanging path down the back from `start`. Gravity drape: the hair falls straight down and only moves
 * backwards where the head or the back pushes it out, never forwards (that made an S-shaped kink).
 */
function hangBack(start: V3, length: number, x1: number, sc: Scalp, body: BodyProfile, thick: number, f: HeadFrame, overScalp = true): V3[] {
  const pts: V3[] = [start.clone()]
  const steps = Math.max(4, Math.round(length / 0.04))
  let z = start.z
  for (let i = 1; i <= steps; i++) {
    const t = i / steps
    const y = start.y - length * t
    const x = start.x + (x1 - start.x) * Math.min(1, t * 2.2)
    let surface: number
    // The scalp shell is ponytail01's gathered back; hair over open long hair follows the skull itself.
    if (y > f.neck.y + 0.02) surface = (overScalp ? Math.min(sc.backZ(y), body.back(y, x)) : body.back(y, x)) - thick
    else surface = body.back(y, x) - thick - CLOTHING // lies on the garment, not the skin
    z = Math.min(surface, z)
    pts.push(new THREE.Vector3(x, y, z))
  }
  return pts
}

/**
 * Hanging path for a pigtail tied behind the ear: falls down the side-back of the head (following the
 * hair shell at its own x, not the centre line) and then down the upper back, drifting towards x1.
 */
function hangSide(start: V3, length: number, x1: number, sc: Scalp, body: BodyProfile, thick: number, f: HeadFrame): V3[] {
  const pts: V3[] = [start.clone()]
  const steps = Math.max(4, Math.round(length / 0.03))
  let z = start.z
  for (let i = 1; i <= steps; i++) {
    const t = i / steps
    const y = start.y - length * t
    const x = start.x + (x1 - start.x) * Math.min(1, t * 1.6)
    let surface: number
    if (y > f.neck.y + 0.02) {
      const ex = Math.min(0.98, Math.abs(x) / sc.rx)
      const ey = Math.min(0.98, Math.abs(y - sc.c.y) / sc.ry)
      const shell = sc.c.z - sc.rz * Math.sqrt(Math.max(0.02, 1 - ex * ex - ey * ey))
      surface = Math.min(shell, body.back(y, x)) - thick
    } else surface = body.back(y, x) - thick - CLOTHING
    z = Math.min(surface, z)
    pts.push(new THREE.Vector3(x, y, z))
  }
  return pts
}

/** Path from behind the ear, over the shoulder, down the front of the body. */
function overShoulder(side: 1 | -1, length: number, sc: Scalp, body: BodyProfile, thick: number, f: HeadFrame, fromBack = false): V3[] {
  const ear = side === 1 ? f.earL : f.earR
  const xs = side * 0.105
  const shoulderY = body.shoulderTop(xs)
  const pts: V3[] = []
  if (fromBack) pts.push(sc.at(side * 0.35, 0.05, 0.004))
  pts.push(new THREE.Vector3(side * (Math.abs(ear.x) - 0.006), ear.y - 0.03, ear.z - 0.05))
  pts.push(new THREE.Vector3(side * (Math.abs(ear.x) + 0.012), f.neck.y - 0.01, f.neck.z - 0.012))
  const topY = shoulderY + thick + CLOTHING
  pts.push(new THREE.Vector3(xs, topY, body.front(shoulderY - 0.03, xs) - 0.035))
  const remaining = Math.max(0.05, length - (ear.y - topY))
  // Dense samples so the path follows the convex upper chest instead of cutting a chord through it.
  const steps = Math.max(3, Math.round(remaining / 0.02))
  for (let i = 1; i <= steps; i++) {
    const y = topY - remaining * (i / steps)
    const x = side * (0.103 - 0.012 * (i / steps))
    pts.push(new THREE.Vector3(x, y, body.front(y, x) + thick + CLOTHING))
  }
  return pts
}

// ---------------------------------------------------------------------------------------------
// Geometry builders
// ---------------------------------------------------------------------------------------------
const LOBE = new THREE.SphereGeometry(1, 14, 10)

interface Frame {
  p: V3
  t: V3
  n: V3
  s: V3
}

/** Points along a curve with tangent, outward normal (away from `inside`) and side vectors. */
function frames(curve: THREE.Curve<V3>, count: number, outward: (p: V3) => V3): Frame[] {
  const out: Frame[] = []
  for (let i = 0; i <= count; i++) {
    const u = i / count
    const p = curve.getPointAt(u)
    const t = curve.getTangentAt(u).normalize()
    const n = outward(p).projectOnPlane(t).normalize()
    const s = new THREE.Vector3().crossVectors(t, n).normalize()
    out.push({ p, t, n, s })
  }
  return out
}

function lobe(fr: Frame, offset: number, tilt: number, sx: number, sy: number, sz: number, push = 0): THREE.BufferGeometry {
  const axis = fr.t.clone().applyAxisAngle(fr.n, tilt)
  const side = new THREE.Vector3().crossVectors(axis, fr.n).normalize()
  const m = new THREE.Matrix4().makeBasis(side, axis, fr.n)
  m.scale(new THREE.Vector3(sx, sy, sz))
  m.setPosition(fr.p.clone().addScaledVector(fr.s, offset).addScaledVector(fr.n, push))
  return LOBE.clone().applyMatrix4(m)
}

/** Three-strand (or fishtail) plait along a curve: overlapping tilted lobes alternating sides. */
function braidGeometry(curve: THREE.Curve<V3>, width: number, outward: (p: V3) => V3, opts: { fishtail?: boolean; taperStart?: number; closed?: boolean }): THREE.BufferGeometry {
  const len = curve.getLength()
  const step = width * (opts.fishtail ? 0.3 : 0.52)
  const count = Math.max(2, Math.floor(len / step))
  const fr = frames(curve, count, outward)
  const parts: THREE.BufferGeometry[] = []
  for (let i = 0; i < fr.length - (opts.closed ? 1 : 0); i++) {
    const u = i / count
    // taper towards the end (and optionally from a narrow start, for French braids)
    let k = opts.closed ? 1 : 1 - 0.45 * Math.pow(u, 1.6)
    if (opts.taperStart) k *= opts.taperStart + (1 - opts.taperStart) * Math.min(1, u / 0.35)
    const w = width * k
    const side = i % 2 === 0 ? 1 : -1
    if (opts.fishtail) {
      parts.push(lobe(fr[i], side * w * 0.2, side * 0.38, w * 0.3, step * 1.55, w * 0.27))
    } else {
      parts.push(lobe(fr[i], side * w * 0.2, side * 0.62, w * 0.36, step * 1.25, w * 0.31))
      // centre strand peeking between the crossings gives the plait its depth
      parts.push(lobe(fr[i], 0, 0, w * 0.22, step * 0.7, w * 0.2, -w * 0.06))
    }
  }
  return mergeGeometries(parts)!
}

/** Ponytail / loose hair: a tube with a tapering, clumpy radius. u = around, v = along (strand texture runs along v). */
function tubeGeometry(curve: THREE.Curve<V3>, radius: (t: number, angle: number) => number, seg = 64, radial = 18): THREE.BufferGeometry {
  const fr = curve.computeFrenetFrames(seg, false)
  const positions: number[] = []
  const normals: number[] = []
  const uvs: number[] = []
  const index: number[] = []
  const p = new THREE.Vector3()
  const nrm = new THREE.Vector3()
  for (let i = 0; i <= seg; i++) {
    const t = i / seg
    curve.getPointAt(t, p)
    const N = fr.normals[i]
    const B = fr.binormals[i]
    for (let j = 0; j <= radial; j++) {
      const a = (j / radial) * Math.PI * 2
      const r = radius(t, a)
      nrm.set(0, 0, 0).addScaledVector(N, Math.cos(a)).addScaledVector(B, Math.sin(a)).normalize()
      positions.push(p.x + nrm.x * r, p.y + nrm.y * r, p.z + nrm.z * r)
      normals.push(nrm.x, nrm.y, nrm.z)
      uvs.push((j / radial) * 2, t * 3)
    }
  }
  for (let i = 0; i < seg; i++)
    for (let j = 0; j < radial; j++) {
      const a = i * (radial + 1) + j
      const b = a + radial + 1
      // Counter-clockwise seen from outside (face normal = outward radial direction).
      index.push(a, a + 1, b, b, a + 1, b + 1)
    }
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  g.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3))
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2))
  g.setIndex(index)
  return g
}

const clumps = (a: number, t: number, amount: number) => 1 + amount * (0.55 * Math.sin(a * 5 + t * 7) + 0.45 * Math.sin(a * 9 - t * 13))

function tailGeometry(curve: THREE.Curve<V3>, width: number, curl: number, sleek: boolean): THREE.BufferGeometry {
  const profile = (t: number) => (t < 0.06 ? 0.5 + 0.5 * (t / 0.06) : 1 - 0.8 * Math.pow((t - 0.06) / 0.94, 1.4))
  if (!curl) return tubeGeometry(curve, (t, a) => width * profile(t) * clumps(a, t, sleek ? 0.04 : 0.12))
  // Curly: several ringlets spiralling around the centre line.
  const parts: THREE.BufferGeometry[] = []
  const fr = curve.computeFrenetFrames(80, false)
  for (let k = 0; k < 7; k++) {
    const phase = (k / 7) * Math.PI * 2
    const pts: V3[] = []
    for (let i = 0; i <= 80; i++) {
      const t = i / 80
      const c = curve.getPointAt(t)
      const spread = width * profile(t) * (0.55 + 0.25 * Math.sin(phase * 3))
      const a = phase + t * 26 * curl
      pts.push(c.addScaledVector(fr.normals[i], Math.cos(a) * spread).addScaledVector(fr.binormals[i], Math.sin(a) * spread))
    }
    const ringlet = new THREE.CatmullRomCurve3(pts)
    parts.push(tubeGeometry(ringlet, (t) => width * 0.33 * (1 - 0.6 * t), 90, 10))
  }
  parts.push(tubeGeometry(curve, (t, a) => width * 0.55 * profile(t) * clumps(a, t, 0.2)))
  return mergeGeometries(parts)!
}

function spiral(center: V3, n: V3, r0: number, r1: number, turns: number, dome: number, steps = 90): THREE.CatmullRomCurve3 {
  const u = new THREE.Vector3().crossVectors(n, Math.abs(n.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0)).normalize()
  const v = new THREE.Vector3().crossVectors(n, u).normalize()
  const pts: V3[] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const a = t * turns * Math.PI * 2
    const r = r0 + (r1 - r0) * t
    pts.push(center.clone().addScaledVector(u, Math.cos(a) * r).addScaledVector(v, Math.sin(a) * r).addScaledVector(n, dome * Math.sin(t * Math.PI * 0.5)))
  }
  return new THREE.CatmullRomCurve3(pts)
}

function circle(center: V3, n: V3, r: number, steps = 48): V3[] {
  const u = new THREE.Vector3().crossVectors(n, Math.abs(n.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0)).normalize()
  const v = new THREE.Vector3().crossVectors(n, u).normalize()
  return Array.from({ length: steps }, (_, i) => {
    const a = (i / steps) * Math.PI * 2
    return center.clone().addScaledVector(u, Math.cos(a) * r).addScaledVector(v, Math.sin(a) * r)
  })
}

function bunGeometry(center: V3, n: V3, size: number, style: 'coil' | 'braided' | 'smooth' | 'messy'): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = []
  // core volume
  const core = new THREE.SphereGeometry(size * 0.78, 24, 16)
  const m = new THREE.Matrix4().lookAt(new THREE.Vector3(), n, new THREE.Vector3(0, 1, 0))
  m.scale(new THREE.Vector3(1, 1, 0.72))
  m.setPosition(center.clone().addScaledVector(n, size * 0.12))
  parts.push(core.applyMatrix4(m))
  const outward = (p: V3) => p.clone().sub(center).addScaledVector(n, size * 0.6)
  if (style === 'coil') {
    parts.push(tubeGeometry(spiral(center, n, size * 0.82, size * 0.12, 2.3, size * 0.55), (t, a) => size * (0.34 - 0.16 * t) * clumps(a, t, 0.08), 120, 14))
  } else if (style === 'braided') {
    parts.push(braidGeometry(spiral(center, n, size * 0.8, size * 0.15, 2.1, size * 0.5, 120), size * 0.5, outward, { closed: true }))
  } else if (style === 'smooth') {
    parts.push(tubeGeometry(spiral(center, n, size * 0.7, size * 0.25, 1.2, size * 0.5), (t, a) => size * 0.3 * clumps(a, t, 0.05), 80, 14))
  } else {
    parts.push(tubeGeometry(spiral(center, n, size * 0.82, size * 0.2, 1.8, size * 0.5), (t, a) => size * (0.33 - 0.1 * t) * clumps(a, t, 0.25), 100, 14))
    // loose loops and wisps
    const rnd = (i: number) => Math.abs(Math.sin(i * 91.7 + 3.1)) // deterministic
    for (let i = 0; i < 6; i++) {
      const dir = new THREE.Vector3(rnd(i) - 0.5, rnd(i + 7) - 0.3, rnd(i + 13) - 0.5).normalize()
      const a = center.clone().addScaledVector(dir, size * 0.45).addScaledVector(n, size * 0.2)
      const b = center.clone().addScaledVector(dir, size * (1.1 + 0.4 * rnd(i + 3))).addScaledVector(n, size * (0.35 + 0.3 * rnd(i + 5)))
      const c = center.clone().addScaledVector(dir.clone().applyAxisAngle(n, 0.9), size * 0.6).addScaledVector(n, size * 0.5)
      parts.push(tubeGeometry(new THREE.CatmullRomCurve3([a, b, c]), (t) => size * 0.09 * (1 - 0.5 * t), 24, 8))
    }
  }
  return mergeGeometries(parts)!
}

// ---------------------------------------------------------------------------------------------
// Materials
// ---------------------------------------------------------------------------------------------
let strandTex: THREE.CanvasTexture | null = null
/** Fine lengthwise strands (luminance only; tinted by the hair colour like the mesh textures). */
function strandTexture(): THREE.CanvasTexture {
  if (strandTex) return strandTex
  const W = 256
  const H = 64
  const c = document.createElement('canvas')
  c.width = W
  c.height = H
  const g = c.getContext('2d')!
  g.fillStyle = 'rgb(150,150,150)'
  g.fillRect(0, 0, W, H)
  let seed = 7
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
  for (let i = 0; i < 900; i++) {
    const x = rnd() * W
    const l = 70 + rnd() * 150
    g.strokeStyle = `rgba(${l},${l},${l},${0.25 + rnd() * 0.5})`
    g.lineWidth = 0.6 + rnd() * 1.6
    g.beginPath()
    g.moveTo(x, 0)
    g.lineTo(x + (rnd() - 0.5) * 6, H)
    g.stroke()
  }
  strandTex = new THREE.CanvasTexture(c)
  strandTex.wrapS = strandTex.wrapT = THREE.RepeatWrapping
  strandTex.colorSpace = THREE.SRGBColorSpace
  strandTex.anisotropy = 4
  return strandTex
}

function hairMaterial(color: string, highlight: string | null, f: HeadFrame): THREE.MeshPhysicalMaterial {
  const tex = strandTexture()
  const mat = new THREE.MeshPhysicalMaterial({ map: tex, bumpMap: tex, bumpScale: 0.6, roughness: 0.55, metalness: 0 })
  // Same tinting as the hair meshes (RealisticAvatar): texture x hair colour, sheen in the hair's own colour.
  mat.color.set(color).multiplyScalar(1.25)
  mat.sheen = 0.5
  mat.sheenRoughness = 0.4
  mat.sheenColor.set(color).lerp(new THREE.Color('#ffffff'), 0.25)
  // Same highlight streaks as the hair meshes (the shader needs the head frame, no other changes).
  applyHairMod(mat, shaderMod({}, f))
  applyHairHighlight(mat, highlight)
  return mat
}

const TIE = new THREE.MeshStandardMaterial({ color: '#1b1716', roughness: 0.5 })
const JASMINE = new THREE.MeshPhysicalMaterial({ color: '#fbf8ee', roughness: 0.55, sheen: 0.6, sheenColor: new THREE.Color('#ffffff') })
const BUD_GREEN = new THREE.MeshStandardMaterial({ color: '#7d9c4a', roughness: 0.7 })

// ---------------------------------------------------------------------------------------------
// Assembly
// ---------------------------------------------------------------------------------------------
interface Built {
  hair: THREE.BufferGeometry[]
  ties: { at: V3; dir: V3; r: number }[]
  flowers: V3[]
}

/** Thickness of the open long hair (hair_long01) over the back of the skull. */
const LONG_HAIR = 0.012

function tiePoint(place: TailPlace | BunPlace, sc: Scalp, body: BodyProfile, side: 1 | -1 = 1): { at: V3; dir: V3 } {
  switch (place) {
    case 'high':
      return { at: sc.at(0, 0.78, 0.004), dir: new THREE.Vector3(0, 0.3, -1).normalize() }
    case 'mid':
      return { at: sc.at(0, 0.32, 0.003), dir: new THREE.Vector3(0, 0, -1) }
    case 'low':
      return { at: sc.at(0, -0.32, 0), dir: new THREE.Vector3(0, -0.35, -1).normalize() }
    case 'half_up': {
      // Tied on top of the open long hair, which lies close to the skull (not on the scalp shell).
      const y = sc.at(0, 0.5).y
      return { at: new THREE.Vector3(0, y, body.back(y, 0) - LONG_HAIR), dir: new THREE.Vector3(0, -0.6, -1).normalize() }
    }
    case 'side':
    case 'pair':
      return { at: sc.at(side * 1.25, -0.22, 0.002), dir: new THREE.Vector3(side * 0.7, -0.2, -0.7).normalize() }
    case 'pair_high': {
      const at = sc.at(side * 1.2, 0.5, 0.003)
      return { at, dir: at.clone().sub(sc.c).normalize() }
    }
    case 'pair_top': {
      const at = sc.at(side * 1.35, 0.98, 0.004)
      return { at, dir: at.clone().sub(sc.c).normalize() }
    }
  }
}

function buildParts(parts: HairPart[], f: HeadFrame, body: BodyProfile): Built {
  const sc = scalp(f)
  const out: Built = { hair: [], ties: [], flowers: [] }
  const awayFromAxis = (p: V3) => new THREE.Vector3(p.x, 0, p.z - f.head.z * 0.5).normalize()
  const awayFromHead = (p: V3) => p.clone().sub(sc.c)
  for (const part of parts) {
    if (part.kind === 'braid') {
      const width = part.width ?? (part.style === 'fishtail' ? 0.036 : 0.04)
      // Clearance from the surface it lies on (lobes are ~0.31 x width deep, plus alternating offsets).
      const thick = width * 0.55
      const length = part.length ?? 0.5
      const outward = (p: V3) => (p.y > f.neck.y ? awayFromHead(p) : awayFromAxis(p))
      const add = (pts: V3[], o: { taperStart?: number; closed?: boolean } = {}) => {
        const curve = new THREE.CatmullRomCurve3(pts, !!o.closed, 'centripetal')
        out.hair.push(braidGeometry(curve, width, outward, { fishtail: part.style === 'fishtail', ...o }))
        if (!o.closed) {
          const end = curve.getPointAt(1)
          const dir = curve.getTangentAt(1)
          out.ties.push({ at: end, dir, r: width * 0.22 })
          // loose end below the tie
          const tuft = new THREE.CatmullRomCurve3([end, end.clone().addScaledVector(dir, 0.05)])
          out.hair.push(tubeGeometry(tuft, (t, a) => width * 0.26 * (1 - 0.85 * t) * clumps(a, t, 0.2), 10, 12))
        }
        if (part.gajra) {
          for (let i = 0; i < 22; i++) {
            const u = 0.02 + i * 0.016
            const p = curve.getPointAt(u)
            const t = curve.getTangentAt(u)
            const n = outward(p).projectOnPlane(t).normalize()
            const s = new THREE.Vector3().crossVectors(t, n).normalize()
            out.flowers.push(p.clone().addScaledVector(s, width * 0.5).addScaledVector(n, width * 0.28))
            out.flowers.push(p.clone().addScaledVector(s, width * 0.62).addScaledVector(n, width * 0.05).addScaledVector(t, 0.006))
          }
        }
      }
      if (part.path === 'back') add(hangBack(sc.at(0, -0.3, 0.002), length, 0, sc, body, thick, f))
      if (part.path === 'back_pair')
        for (const side of [1, -1] as const) add(hangBack(sc.at(side * 0.55, -0.32, 0.002), length, side * 0.065, sc, body, thick, f))
      if (part.path === 'front_pair') for (const side of [1, -1] as const) add(overShoulder(side, length, sc, body, thick, f, true))
      if (part.path === 'side') add(overShoulder(1, length, sc, body, thick, f, true))
      if (part.path === 'french') {
        const head: V3[] = [0.98, 0.78, 0.55, 0.3, 0.05].map((pitch) => sc.at(0, pitch, 0.004))
        const below = hangBack(sc.at(0, -0.28, 0.003), length, 0, sc, body, thick, f).slice(1)
        add([...head, ...below], { taperStart: 0.55 })
      }
      if (part.path === 'crown') {
        const pts: V3[] = []
        const frontY = f.eyeY + 0.07
        const backY = f.earL.y + 0.02
        for (let i = 0; i < 28; i++) {
          const yaw = (i / 28) * Math.PI * 2
          const y = (frontY + backY) / 2 - ((frontY - backY) / 2) * Math.cos(yaw)
          const pitch = Math.asin(Math.max(-1, Math.min(1, (y - sc.c.y) / sc.ry)))
          pts.push(sc.at(yaw, pitch, 0.007))
        }
        add(pts, { closed: true })
      }
    } else if (part.kind === 'tail') {
      // `width` is the tube radius at the tie: ~2.5 cm gives a natural 5 cm ponytail.
      const width = part.width ?? 0.025
      const sides: (1 | -1)[] = part.place === 'pair' || part.place === 'pair_high' ? [1, -1] : [1]
      for (const side of sides) {
        const { at, dir } = tiePoint(part.place, sc, body, side)
        // The tube starts inside the scalp so its open end is hidden under the hair.
        const buried = at.clone().addScaledVector(dir, -0.02)
        let pts: V3[]
        if (part.place === 'side' || part.place === 'pair') {
          pts = [buried, at, ...overShoulder(side, part.length, sc, body, width * 0.6, f).slice(1)]
        } else if (part.place === 'pair_high') {
          // Stands out from the tie, then falls behind the ear and down the upper back.
          const lift = at.clone().addScaledVector(dir, 0.014)
          const start = new THREE.Vector3(lift.x, lift.y - 0.03, lift.z - 0.006)
          pts = [buried, at, lift, ...hangSide(start, part.length - 0.05, side * 0.085, sc, body, width * 0.8, f)]
        } else {
          const halfUp = part.place === 'half_up'
          const lift = at.clone().addScaledVector(dir, halfUp ? 0.01 : 0.02)
          // Falls straight from the tie: start no further back than the lift point, so the tail never
          // swings out and back into the head (which made a hook).
          const y0 = lift.y - 0.025
          // A half-up tail lies on the open long hair (~1.4 cm over the scalp) instead of the head.
          const clearance = halfUp ? width + LONG_HAIR : width * 0.75
          const surfaceZ = halfUp ? body.back(y0, 0) : sc.backZ(y0)
          const hang = hangBack(new THREE.Vector3(0, y0, Math.min(lift.z - 0.004, surfaceZ - clearance)), part.length - 0.04, 0, sc, body, clearance, f, !halfUp)
          pts = [buried, at, lift, ...hang]
        }
        out.hair.push(tailGeometry(new THREE.CatmullRomCurve3(pts, false, 'centripetal'), width, part.curl ?? 0, !!part.sleek))
        out.ties.push({ at, dir, r: width * 0.48 })
      }
    } else if (part.kind === 'bun') {
      const sides: (1 | -1)[] = part.place === 'pair_top' ? [1, -1] : [1]
      for (const side of sides) {
        const { at, dir } = tiePoint(part.place, sc, body, side)
        // A half-up bun sits on top of the open hair, so it needs to stand out further.
        const center = at.clone().addScaledVector(dir, part.size * (part.place === 'half_up' ? 0.85 : 0.35))
        out.hair.push(bunGeometry(center, dir, part.size, part.style))
        if (part.gajra) {
          const ring = circle(center.clone().addScaledVector(dir, part.size * 0.05), dir, part.size * 1.0, 30)
          const ring2 = circle(center.clone().addScaledVector(dir, part.size * 0.3), dir, part.size * 0.88, 26)
          out.flowers.push(...ring, ...ring2)
        }
      }
    }
  }
  return out
}

function Ties({ ties }: { ties: Built['ties'] }) {
  return (
    <>
      {ties.map((t, i) => (
        <mesh key={i} position={t.at} quaternion={new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), t.dir.clone().normalize())} material={TIE}>
          <torusGeometry args={[t.r, t.r * 0.28, 8, 20]} />
        </mesh>
      ))}
    </>
  )
}

function Flowers({ points }: { points: V3[] }) {
  const { buds, greens } = useMemo(() => {
    const buds = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 10, 8), JASMINE, points.length)
    const greens = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 6, 5), BUD_GREEN, Math.ceil(points.length / 5))
    const m = new THREE.Matrix4()
    const q = new THREE.Quaternion()
    points.forEach((p, i) => {
      q.setFromEuler(new THREE.Euler(Math.sin(i * 12.9) * 1.4, Math.cos(i * 7.3) * 1.4, Math.sin(i * 3.7)))
      m.compose(p, q, new THREE.Vector3(0.0046, 0.0068, 0.0046))
      buds.setMatrixAt(i, m)
      if (i % 5 === 0) {
        m.compose(p.clone().add(new THREE.Vector3(0, 0.003, 0)), q, new THREE.Vector3(0.0022, 0.0022, 0.0022))
        greens.setMatrixAt(i / 5, m)
      }
    })
    buds.castShadow = true
    return { buds, greens }
  }, [points])
  useEffect(
    () => () => {
      buds.geometry.dispose()
      greens.geometry.dispose()
      buds.dispose()
      greens.dispose()
    },
    [buds, greens],
  )
  return (
    <>
      <primitive object={buds} />
      <primitive object={greens} />
    </>
  )
}

export function ProceduralHair({ presentation, meta, weights, parts, color, highlight = null }: { presentation: Presentation; meta: AvatarMeta; weights: Record<string, number>; parts: HairPart[]; color: string; highlight?: string | null }) {
  const body = useGLTF(partUrl(presentation, 'body'))
  const frame = useMemo(() => headFrame(meta, weights), [meta, weights])
  const profile = useMemo(() => {
    let mesh: THREE.Mesh | null = null
    body.scene.traverse((o) => {
      if (!mesh && (o as THREE.Mesh).isMesh) mesh = o as THREE.Mesh
    })
    const m = mesh as THREE.Mesh | null
    return m ? new BodyProfile(m.geometry, m.morphTargetDictionary, weights, frame.neck.y) : null
  }, [body.scene, weights, frame.neck.y])
  const built = useMemo(() => (profile ? buildParts(parts, frame, profile) : null), [parts, frame, profile])
  const geometry = useMemo(() => (built && built.hair.length ? mergeGeometries(built.hair) : null), [built])
  const material = useMemo(() => hairMaterial(color, highlight, frame), [color, highlight, frame])
  useEffect(() => () => geometry?.dispose(), [geometry])
  useEffect(() => () => material.dispose(), [material])
  if (!built || !geometry) return null
  return (
    <group>
      <mesh geometry={geometry} material={material} castShadow receiveShadow frustumCulled={false} />
      <Ties ties={built.ties} />
      {built.flowers.length > 0 && <Flowers points={built.flowers} />}
    </group>
  )
}
