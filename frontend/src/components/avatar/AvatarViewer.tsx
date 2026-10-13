import { ContactShadows, Environment, Lightformer, OrbitControls, useProgress } from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { toLegacyBuilder, type AvatarView } from '../../hooks/useAvatar'
import { useStyleStore } from '../../hooks/useStyleStore'
import { api } from '../../services/api'
import type { AvatarBuilder, Outfit } from '../../types'
import { AssetErrorBoundary } from './AssetErrorBoundary'
import { preloadAvatar, useAvatarMeta } from './avatarAssets'
import { hairMeshes, hairStyle } from './hairStyles'
import { RealisticAvatar } from './RealisticAvatar'

interface Props {
  view: AvatarView
  /** Raw outfit items, only used by the 2D fallback when WebGL is unavailable. */
  outfitItems?: Outfit['items']
  height?: number
}

const VIEWS = { Front: 0, Side: Math.PI / 2, Back: Math.PI } as const
type ViewName = keyof typeof VIEWS

function hasWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    return false
  }
}

/**
 * Full-body framing uses a fixed reference height (not the avatar's own height), so a 150 cm avatar
 * is visibly shorter than a 180 cm one instead of being zoomed to fill the same frame. The reference
 * only grows for avatars taller than it, so the head is never cropped.
 */
const FRAME_REF_M = 1.9

/** Smoothly moves the camera to the requested preset (full-body framing) and zoom level. */
function CameraRig({ view, nonce, zoom, figureHeight, controls }: { view: ViewName; nonce: number; zoom: number; figureHeight: number; controls: React.RefObject<OrbitControlsImpl | null> }) {
  const camera = useThree((s) => s.camera)
  const goal = useRef<{ pos: THREE.Vector3; target: THREE.Vector3 } | null>(null)
  const frameHeight = Math.max(FRAME_REF_M, figureHeight + 0.06)
  useEffect(() => {
    const angle = VIEWS[view]
    const distance = (2.25 * frameHeight + 0.5) / zoom
    // Zooming in moves the focus up towards the face; zoomed out frames the full body (feet on the floor).
    const t = Math.min(1, Math.max(0, (zoom - 1) / 1.8))
    const targetY = frameHeight * 0.5 * (1 - t) + figureHeight * 0.92 * t
    goal.current = {
      pos: new THREE.Vector3(Math.sin(angle) * distance, targetY + 0.05, Math.cos(angle) * distance),
      target: new THREE.Vector3(0, targetY, 0),
    }
  }, [view, nonce, zoom, figureHeight, frameHeight])
  useFrame((_, dt) => {
    const g = goal.current
    const c = controls.current
    if (!g || !c) return
    const k = 1 - Math.pow(0.0015, dt)
    camera.position.lerp(g.pos, k)
    c.target.lerp(g.target, k)
    c.update()
    if (camera.position.distanceTo(g.pos) < 0.002 && c.target.distanceTo(g.target) < 0.002) goal.current = null
  })
  return null
}

/** Height scale beside the avatar: 10 cm ticks (bold every 50 cm) and a marker at the profile height. */
function HeightScale({ heightM }: { heightM: number }) {
  const ticks = useMemo(() => Array.from({ length: 21 }, (_, i) => i / 10), [])
  return (
    <group position={[-0.62, 0, -0.1]}>
      <mesh position={[0, 1.0, 0]}>
        <boxGeometry args={[0.004, 2.0, 0.004]} />
        <meshBasicMaterial color="#b9b0c8" />
      </mesh>
      {ticks.map((y) => (
        <mesh key={y} position={[0.012, y, 0]}>
          <boxGeometry args={[y * 10 % 5 === 0 ? 0.03 : 0.016, 0.003, 0.003]} />
          <meshBasicMaterial color="#b9b0c8" />
        </mesh>
      ))}
      <mesh position={[0.25, heightM, 0]}>
        <boxGeometry args={[0.5, 0.004, 0.004]} />
        <meshBasicMaterial color="#7b5cc4" transparent opacity={0.55} />
      </mesh>
    </group>
  )
}

/** Development only: exposes the live scene so scripts/verify-avatar.mjs can measure the rendered avatar. */
function DevSceneHook() {
  const scene = useThree((s) => s.scene)
  const camera = useThree((s) => s.camera)
  useEffect(() => {
    if (!import.meta.env.DEV) return
    const w = window as unknown as { __styleaiScenes?: Set<THREE.Scene> }
    scene.userData.camera = camera
    ;(w.__styleaiScenes ??= new Set()).add(scene)
    return () => void w.__styleaiScenes?.delete(scene)
  }, [scene, camera])
  return null
}

function Studio() {
  return (
    <>
      <hemisphereLight args={['#fff8f2', '#dcd3e6', 0.45]} />
      <directionalLight
        position={[1.6, 3.6, 2.8]}
        intensity={2.1}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-bias={-0.0003}
        shadow-normalBias={0.02}
        shadow-camera-left={-1.2}
        shadow-camera-right={1.2}
        shadow-camera-top={2.2}
        shadow-camera-bottom={-0.3}
      />
      <directionalLight position={[-2.6, 2.2, 1.6]} intensity={0.6} color="#ffe9df" />
      <directionalLight position={[0, 2.5, -3]} intensity={0.9} color="#eae3ff" />
      {/* Offline studio environment: soft reflections without downloading an HDR. */}
      <Environment resolution={256} frames={1}>
        <Lightformer intensity={1.6} position={[0, 3, 2.5]} scale={[5, 2, 1]} />
        <Lightformer intensity={1.0} position={[-3, 1.6, 1]} rotation-y={Math.PI / 2} scale={[3, 2.5, 1]} color="#fff0e8" />
        <Lightformer intensity={0.8} position={[3, 1.6, -1]} rotation-y={-Math.PI / 2} scale={[3, 2.5, 1]} color="#efe9ff" />
      </Environment>
      <mesh rotation-x={-Math.PI / 2} position={[0, -0.002, 0]} receiveShadow>
        <circleGeometry args={[1.3, 64]} />
        <meshStandardMaterial color="#efeaf3" roughness={0.95} />
      </mesh>
      <ContactShadows position={[0, 0.001, 0]} opacity={0.55} scale={2.4} blur={2.2} far={1.4} resolution={512} color="#2d174d" />
    </>
  )
}

function SvgFallback({ builder, outfitItems }: { builder: AvatarBuilder; outfitItems?: Outfit['items'] }) {
  const [svg, setSvg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    api
      .avatarSvg(builder, outfitItems)
      .then((r) => alive && setSvg(r.svg))
      .catch((e: Error) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [builder, outfitItems])
  if (error) return <div className="viewer-fallback muted">{error}</div>
  // SVG markup is generated server-side by avatar_engine.py from validated option values.
  return <div className="viewer-fallback" dangerouslySetInnerHTML={{ __html: svg ?? '' }} />
}

function LoadingOverlay() {
  const { active, progress } = useProgress()
  if (!active) return null
  return (
    <div className="viewer-loading" role="status">
      <span className="spinner" /> Loading avatar… {Math.round(progress)}%
    </div>
  )
}

export function AvatarViewer({ view: avatarView, outfitItems, height = 540 }: Props) {
  const { resolved } = avatarView
  const { meta, error: metaError } = useAvatarMeta(resolved.presentation)
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null)
  const [viewName, setViewName] = useState<ViewName>('Front')
  const [nonce, setNonce] = useState(0)
  const [zoom, setZoom] = useState(1)
  const [autoRotate, setAutoRotate] = useState(false)
  const controls = useRef<OrbitControlsImpl | null>(null)
  const webgl = useMemo(() => hasWebGL(), [])
  const weight = useStyleStore((s) => s.weight)
  const occasion = useStyleStore((s) => s.occasion)
  const figureHeight = resolved.heightCm / 100
  const assetKey = `${resolved.presentation}`
  const failed = failure && failure.key === assetKey ? failure.message : null

  useEffect(() => {
    const style = hairStyle(resolved.hairstyle)
    preloadAvatar(resolved.presentation, [...(style ? hairMeshes(style) : []), resolved.eyebrows])
  }, [resolved.presentation, resolved.hairstyle, resolved.eyebrows])

  if (!webgl) {
    return (
      <div className="model-card">
        <div className="model-canvas" style={{ height }}>
          <SvgFallback builder={toLegacyBuilder(resolved, weight, occasion)} outfitItems={outfitItems} />
          <div className="viewer-note">WebGL is not available in this browser, so the simplified 2D avatar is shown instead.</div>
        </div>
      </div>
    )
  }

  const problem = metaError ?? failed
  const go = (v: ViewName) => {
    setAutoRotate(false)
    setViewName(v)
    setNonce((n) => n + 1)
  }

  return (
    <div className="model-card">
      <div
        className="model-canvas"
        style={{ height }}
        data-avatar-state={JSON.stringify({
          presentation: resolved.presentation,
          heightCm: resolved.heightCm,
          hairstyle: resolved.hairstyle,
          eyebrows: resolved.eyebrows,
          skinTone: resolved.skinTone,
          bodyType: resolved.bodyType,
          morphs: resolved.morphs,
          face: [resolved.config.facePreset, resolved.config.nose, resolved.config.lips, resolved.config.eyeShape],
          hairColor: resolved.config.hairColor,
          worn: resolved.worn,
          accessories: resolved.accessories,
        })}
      >
        <Canvas
          shadows={{ type: THREE.PCFShadowMap }}
          dpr={[1, 2]}
          gl={{ antialias: true, preserveDrawingBuffer: true }}
          camera={{ fov: 30, near: 0.03, far: 50, position: [0, 1, 4.3] }}
          aria-label="Interactive 3D avatar preview"
        >
          <color attach="background" args={['#f7f4fa']} />
          <Studio />
          {import.meta.env.DEV && <DevSceneHook />}
          {meta && !problem && <HeightScale heightM={figureHeight} />}
          <CameraRig view={viewName} nonce={nonce} zoom={zoom} figureHeight={figureHeight} controls={controls} />
          {meta && !problem && (
            <AssetErrorBoundary key={assetKey} fallback={null} onError={(e) => setFailure({ key: assetKey, message: e.message.slice(0, 120) })}>
              <Suspense fallback={null}>
                <RealisticAvatar resolved={resolved} meta={meta} />
              </Suspense>
            </AssetErrorBoundary>
          )}
          <OrbitControls
            ref={controls}
            makeDefault
            enablePan={false}
            enableDamping
            minDistance={0.5}
            maxDistance={6.5}
            minPolarAngle={0.2}
            maxPolarAngle={Math.PI / 2 + 0.08}
            autoRotate={autoRotate}
            autoRotateSpeed={1.4}
          />
        </Canvas>
        <LoadingOverlay />
        {problem && (
          <div className="viewer-error" role="alert">
            <strong>The 3D avatar could not be loaded.</strong>
            <span>{problem}</span>
            <span className="muted">Run the asset build described in frontend/public/models/avatar/README.md.</span>
          </div>
        )}
        <div className="viewer-toolbar" role="toolbar" aria-label="Avatar view">
          {(Object.keys(VIEWS) as ViewName[]).map((v) => (
            <button key={v} type="button" aria-pressed={viewName === v && !autoRotate} onClick={() => go(v)}>
              {v}
            </button>
          ))}
          <button type="button" aria-pressed={autoRotate} onClick={() => setAutoRotate((a) => !a)}>
            {autoRotate ? 'Stop' : '360°'}
          </button>
        </div>
        <div className="viewer-zoom" role="group" aria-label="Zoom">
          <button type="button" aria-label="Zoom in" onClick={() => { setZoom((z) => Math.min(3.2, z * 1.35)); setNonce((n) => n + 1) }}>+</button>
          <button type="button" aria-label="Zoom out" onClick={() => { setZoom((z) => Math.max(0.8, z / 1.35)); setNonce((n) => n + 1) }}>−</button>
          <button type="button" aria-label="Reset view" title="Reset view" onClick={() => { setZoom(1); go('Front') }}>⟲</button>
        </div>
        {meta && !problem && (
          <div className="height-tag" aria-label="Avatar height">
            Height {Math.round(figureHeight * 100)} cm · scale in 10 cm steps
          </div>
        )}
        <div className="viewer-note">
          {meta ? `Realistic avatar · ${meta.assetSource}` : 'Loading avatar…'} · Drag to rotate, scroll or pinch to zoom.
        </div>
      </div>
      {avatarView.notes.length > 0 && (
        <ul className="viewer-notes">
          {avatarView.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
