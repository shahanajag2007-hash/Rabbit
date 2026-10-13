import { RoundedBox } from '@react-three/drei'
import { useMemo } from 'react'
import * as THREE from 'three'
import { blendAnchor, type AvatarMeta } from './avatarAssets'
import type { AccessoryId } from './avatarCatalog'

/**
 * Accessories modelled in three.js and attached to anchor points measured on the real
 * MakeHuman body for every body-type / face configuration (see build_avatar.py).
 * The CC0 asset pack has no jewellery, eyewear, watches or bags, so these are simple
 * hand-modelled meshes rather than scanned products.
 */

const GOLD = new THREE.MeshStandardMaterial({ color: '#d8b04c', metalness: 1, roughness: 0.22 })
const STEEL = new THREE.MeshStandardMaterial({ color: '#c9ccd1', metalness: 1, roughness: 0.2 })
const FRAME = new THREE.MeshStandardMaterial({ color: '#1d1a1a', metalness: 0.2, roughness: 0.35 })
const LENS_DARK = new THREE.MeshPhysicalMaterial({ color: '#0d0f12', roughness: 0.05, metalness: 0.3, clearcoat: 1, transparent: true, opacity: 0.92 })
const LENS_CLEAR = new THREE.MeshPhysicalMaterial({ color: '#dfeaf0', roughness: 0.02, clearcoat: 1, transparent: true, opacity: 0.16 })
const LEATHER_TAN = new THREE.MeshPhysicalMaterial({ color: '#8a5a35', roughness: 0.45, clearcoat: 0.3 })
const LEATHER_DARK = new THREE.MeshPhysicalMaterial({ color: '#2a2220', roughness: 0.4, clearcoat: 0.35 })
const CANVAS = new THREE.MeshPhysicalMaterial({ color: '#e7dcc6', roughness: 0.95, sheen: 0.4, sheenColor: new THREE.Color('#ffffff') })
const WATCH_FACE = new THREE.MeshStandardMaterial({ color: '#f5f3ee', roughness: 0.3 })

const v = (a: number[] | number | undefined) => new THREE.Vector3(...((a as number[]) ?? [0, 0, 0]))
const UP = new THREE.Vector3(0, 1, 0)

function Eyewear({ meta, w, dark }: { meta: AvatarMeta; w: Record<string, number>; dark: boolean }) {
  const eyeL = v(blendAnchor(meta, 'eye_l', w))
  const eyeR = v(blendAnchor(meta, 'eye_r', w))
  const earL = v(blendAnchor(meta, 'ear_l', w))
  const earR = v(blendAnchor(meta, 'ear_r', w))
  const front = -(blendAnchor(meta, 'eyes_front', w) as number) + 0.013
  const y = (eyeL.y + eyeR.y) / 2 + 0.002
  const half = Math.abs(eyeL.x - eyeR.x) / 2
  const lensR = half * 0.62
  const temples = useMemo(
    () =>
      [1, -1].map((side) => {
        const start = new THREE.Vector3(side * (half + lensR * 1.05), y + 0.004, front - 0.004)
        const end = (side === 1 ? (eyeL.x > 0 ? earL : earR) : eyeL.x > 0 ? earR : earL).clone().add(new THREE.Vector3(0, 0.022, -0.004))
        const mid = start.clone().add(end).multiplyScalar(0.5)
        const len = start.distanceTo(end)
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), end.clone().sub(start).normalize())
        return { mid, len, q }
      }),
    [half, lensR, y, front, eyeL, earL, earR],
  )
  return (
    <group>
      {[1, -1].map((side) => (
        <group key={side} position={[side * half, y, front]}>
          <mesh material={FRAME} scale={[1.15, 0.86, 1]}>
            <torusGeometry args={[lensR, dark ? 0.0024 : 0.0017, 10, 40]} />
          </mesh>
          <mesh material={dark ? LENS_DARK : LENS_CLEAR} scale={[1.15, 0.86, 1]}>
            <circleGeometry args={[lensR, 40]} />
          </mesh>
        </group>
      ))}
      <mesh material={FRAME} position={[0, y + 0.004, front + 0.001]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.0016, 0.0016, Math.max(0.004, 2 * half - 2 * lensR * 1.1), 8]} />
      </mesh>
      {temples.map((t, i) => (
        <mesh key={i} material={FRAME} position={t.mid} quaternion={t.q}>
          <boxGeometry args={[0.0022, 0.004, t.len]} />
        </mesh>
      ))}
    </group>
  )
}

function Earrings({ meta, w }: { meta: AvatarMeta; w: Record<string, number> }) {
  return (
    <group>
      {(['ear_l', 'ear_r'] as const).map((k) => {
        const p = v(blendAnchor(meta, k, w))
        const out = Math.sign(p.x) * 0.002
        return (
          <group key={k} position={[p.x + out, p.y - 0.006, p.z]}>
            <mesh material={GOLD}>
              <sphereGeometry args={[0.0028, 12, 10]} />
            </mesh>
            <mesh material={GOLD} position={[0, -0.009, 0]} rotation={[0, Math.PI / 2, 0]}>
              <torusGeometry args={[0.007, 0.0012, 8, 28]} />
            </mesh>
          </group>
        )
      })}
    </group>
  )
}

function Necklace({ meta, w }: { meta: AvatarMeta; w: Record<string, number> }) {
  const neck = v(blendAnchor(meta, 'neck', w))
  const [rx, ry] = (blendAnchor(meta, 'neck_radii', w) as number[]) ?? [0.06, 0.06]
  return (
    <group position={[neck.x, neck.y + 0.005, neck.z + 0.008]} rotation={[0.42, 0, 0]}>
      <mesh material={GOLD} scale={[rx * 1.18, ry * 1.32, 1]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1, 0.0016 / Math.max(rx, 0.01), 8, 64]} />
      </mesh>
      <mesh material={GOLD} position={[0, -0.004, ry * 1.32 + 0.004]}>
        <sphereGeometry args={[0.0055, 16, 12]} />
      </mesh>
    </group>
  )
}

function WristPiece({ meta, w, side, kind }: { meta: AvatarMeta; w: Record<string, number>; side: 'l' | 'r'; kind: 'watch' | 'bracelet' }) {
  const wrist = v(blendAnchor(meta, `wrist_${side}`, w))
  const dir = v(blendAnchor(meta, `forearm_dir_${side}`, w)).normalize()
  const radius = ((blendAnchor(meta, `wrist_radius_${side}`, w) as number) ?? 0.03) * 1.08
  const q = new THREE.Quaternion().setFromUnitVectors(UP, dir)
  const pos = wrist.clone().addScaledVector(dir, -0.025)
  const outward = Math.sign(wrist.x) || 1
  if (kind === 'bracelet') {
    return (
      <group position={pos} quaternion={q}>
        <mesh material={GOLD} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[radius, 0.0022, 10, 48]} />
        </mesh>
        <mesh material={GOLD} position={[0, 0.006, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[radius * 1.01, 0.0016, 10, 48]} />
        </mesh>
      </group>
    )
  }
  return (
    <group position={pos} quaternion={q}>
      <mesh material={LEATHER_DARK}>
        <cylinderGeometry args={[radius, radius, 0.018, 40, 1, true]} />
      </mesh>
      <group position={[outward * radius, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
        <mesh material={STEEL}>
          <cylinderGeometry args={[0.017, 0.017, 0.007, 40]} />
        </mesh>
        <mesh material={WATCH_FACE} position={[0, outward * 0.0036, 0]}>
          <cylinderGeometry args={[0.0145, 0.0145, 0.001, 40]} />
        </mesh>
      </group>
    </group>
  )
}

function Belt({ meta, w }: { meta: AvatarMeta; w: Record<string, number> }) {
  const waist = v(blendAnchor(meta, 'waist', w))
  const [rx, ry] = (blendAnchor(meta, 'waist_radii', w) as number[]) ?? [0.14, 0.1]
  const y = waist.y - 0.035
  return (
    <group position={[waist.x, y, waist.z]}>
      <mesh material={LEATHER_DARK} scale={[rx * 1.09, 1, ry * 1.14]}>
        <cylinderGeometry args={[1, 1, 0.034, 64, 1, true]} />
      </mesh>
      <mesh material={STEEL} position={[0, 0, ry * 1.14 + 0.003]}>
        <boxGeometry args={[0.04, 0.03, 0.005]} />
      </mesh>
    </group>
  )
}

function Bag({ meta, w, tote }: { meta: AvatarMeta; w: Record<string, number>; tote: boolean }) {
  const hand = v(blendAnchor(meta, 'hand_r', w))
  const outward = Math.sign(hand.x) || 1
  const size: [number, number, number] = tote ? [0.09, 0.34, 0.32] : [0.08, 0.17, 0.25]
  const top = hand.y - 0.03
  return (
    <group position={[hand.x + outward * (size[0] / 2 + 0.01), top - (tote ? 0.08 : 0.06), hand.z]}>
      <RoundedBox args={size} radius={0.012} smoothness={4} material={tote ? CANVAS : LEATHER_TAN} position={[0, -size[1] / 2, 0]} castShadow />
      <mesh material={tote ? CANVAS : LEATHER_TAN} position={[0, 0.0, 0]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[tote ? 0.09 : 0.06, tote ? 0.006 : 0.005, 10, 32, Math.PI]} />
      </mesh>
      {!tote && (
        <mesh material={GOLD} position={[outward * (size[0] / 2 + 0.001), -0.05, 0]}>
          <boxGeometry args={[0.002, 0.02, 0.03]} />
        </mesh>
      )}
    </group>
  )
}

export function AccessoryMeshes({ meta, weights, accessories }: { meta: AvatarMeta; weights: Record<string, number>; accessories: AccessoryId[] }) {
  return (
    <group>
      {accessories.includes('glasses') && <Eyewear meta={meta} w={weights} dark={false} />}
      {accessories.includes('sunglasses') && <Eyewear meta={meta} w={weights} dark />}
      {accessories.includes('earrings') && <Earrings meta={meta} w={weights} />}
      {accessories.includes('necklace') && <Necklace meta={meta} w={weights} />}
      {accessories.includes('watch') && <WristPiece meta={meta} w={weights} side="l" kind="watch" />}
      {accessories.includes('bracelet') && <WristPiece meta={meta} w={weights} side="r" kind="bracelet" />}
      {accessories.includes('belt') && <Belt meta={meta} w={weights} />}
      {accessories.includes('handbag') && <Bag meta={meta} w={weights} tote={false} />}
      {accessories.includes('tote') && <Bag meta={meta} w={weights} tote />}
    </group>
  )
}
