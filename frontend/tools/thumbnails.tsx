/**
 * Dev tool: renders Avatar Studio option thumbnails with the *same* three.js avatar used by the app,
 * so every thumbnail shows the real asset/result. Driven by scripts/render-avatar-thumbnails.mjs.
 */
import { Environment, Lightformer, useProgress } from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Suspense, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import * as THREE from 'three'
import { blendAnchor, loadAvatarMeta, morphWeights, type AvatarMeta } from '../src/components/avatar/avatarAssets'
import { ageWeights, DEFAULT_AVATAR_CONFIG, DEFAULT_BROWS, DEFAULT_HAIR, FACIAL_HAIR, GARMENTS, type AvatarConfig, type Presentation } from '../src/components/avatar/avatarCatalog'
import { HAIRSTYLES } from '../src/components/avatar/hairStyles'
import { RealisticAvatar, type ResolvedAvatar } from '../src/components/avatar/RealisticAvatar'

export interface ThumbSpec {
  presentation: Presentation
  config?: Partial<AvatarConfig>
  worn?: ResolvedAvatar['worn']
  accessories?: ResolvedAvatar['accessories']
  isolate?: string
  focus: 'full' | 'face' | 'head' | 'hair' | 'brows' | 'wrist' | 'wrist_r' | 'neck' | 'waist' | 'hand' | 'auto'
  view?: 'front' | 'three_quarter' | 'side' | 'back' | 'back_three_quarter'
  /** Optional profile age (age morphs + skin detail); default: young-adult base model. */
  age?: number
}

declare global {
  interface Window {
    __thumb?: (spec: ThumbSpec) => Promise<string>
    /** Hairstyle ids and preferred thumbnail view, read by the render script. */
    __hairStyles?: { id: string; view: string }[]
    /** Available garment ids and facial hair meshes, read by the render script. */
    __garments?: string[]
    __facialHair?: { id: string; mesh: string }[]
  }
}

const HEIGHT_CM = 170
const SIZE = Number(new URLSearchParams(location.search).get('size') ?? 256)

function Framer({ spec, meta, group, onDone }: { spec: ThumbSpec; meta: AvatarMeta; group: React.RefObject<THREE.Group | null>; onDone: (url: string) => void }) {
  const { camera, gl, scene } = useThree()
  const frames = useRef(0)
  const done = useRef(false)
  const { active } = useProgress()
  useFrame(() => {
    if (done.current || active) return
    let meshes = 0
    group.current?.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) meshes++
    })
    if (!meshes) return
    frames.current += 1
    if (frames.current === 4) {
      const cfg = { ...DEFAULT_AVATAR_CONFIG, ...(spec.config ?? {}) }
      const w = morphWeights(cfg, cfg.bodyType ?? 'average')
      const scale = HEIGHT_CM / 100 / (blendAnchor(meta, 'head_top', w) as number[])[1]
      const a = (k: string) => new THREE.Vector3(...((blendAnchor(meta, k, w) as number[]) ?? [0, 0, 0])).multiplyScalar(scale)
      let center = new THREE.Vector3()
      let size = 1
      if (spec.focus === 'full' || spec.focus === 'auto') {
        const box = new THREE.Box3().setFromObject(group.current!, true)
        // Lengthened dresses move their hem down through the aLayer offset, which Box3 does not see.
        let drop = 0
        group.current!.traverse((o) => {
          const lay = (o as THREE.Mesh).isMesh ? ((o as THREE.Mesh).geometry.getAttribute('aLayer') as THREE.BufferAttribute | undefined) : undefined
          if (lay) for (let i = 0; i < lay.count; i++) drop = Math.min(drop, lay.getY(i) * o.getWorldScale(new THREE.Vector3()).y)
        })
        box.min.y += drop
        center = box.getCenter(new THREE.Vector3())
        const s = box.getSize(new THREE.Vector3())
        size = Math.max(s.x, s.y, spec.view === 'three_quarter' ? s.z : 0) * 1.12
      } else if (spec.focus === 'face') {
        center = a('eye_l').add(a('eye_r')).multiplyScalar(0.5).add(new THREE.Vector3(0, -0.035, 0))
        size = 0.27
      } else if (spec.focus === 'brows') {
        center = a('eye_l').add(a('eye_r')).multiplyScalar(0.5).add(new THREE.Vector3(0, 0.012, 0))
        size = 0.13
      } else if (spec.focus === 'head' || spec.focus === 'hair') {
        center = a('head').add(new THREE.Vector3(0, spec.focus === 'hair' ? -0.02 : 0.06, 0))
        size = spec.focus === 'hair' ? 0.62 : 0.36
      } else if (spec.focus === 'neck') {
        center = a('neck').add(new THREE.Vector3(0, 0.02, 0))
        size = 0.32
      } else if (spec.focus === 'wrist' || spec.focus === 'wrist_r') {
        center = a(spec.focus === 'wrist' ? 'wrist_l' : 'wrist_r')
        size = 0.2
      } else if (spec.focus === 'waist') {
        center = a('waist').add(new THREE.Vector3(0, -0.05, 0))
        size = 0.55
      } else if (spec.focus === 'hand') {
        center = a('hand_r').add(new THREE.Vector3(0.05, -0.2, 0))
        size = 0.6
      }
      const cam = camera as THREE.OrthographicCamera
      const dir =
        spec.view === 'three_quarter' ? new THREE.Vector3(-0.75, 0.12, 0.65).normalize()
        : spec.view === 'side' ? new THREE.Vector3(1, 0, 0)
        : spec.view === 'back' ? new THREE.Vector3(0, 0.08, -1).normalize()
        : spec.view === 'back_three_quarter' ? new THREE.Vector3(-0.7, 0.12, -0.7).normalize()
        : new THREE.Vector3(0, 0, 1)
      cam.position.copy(center).addScaledVector(dir, 5)
      cam.lookAt(center)
      cam.zoom = SIZE / size
      cam.updateProjectionMatrix()
    }
    if (frames.current === 8) {
      gl.render(scene, camera)
      done.current = true
      onDone(gl.domElement.toDataURL('image/png'))
    }
  })
  return null
}

function ThumbScene({ spec, onDone }: { spec: ThumbSpec; onDone: (url: string) => void }) {
  const [meta, setMeta] = useState<AvatarMeta | null>(null)
  const group = useRef<THREE.Group>(null)
  useEffect(() => {
    loadAvatarMeta(spec.presentation).then(setMeta)
  }, [spec.presentation])
  if (!meta) return null
  const config: AvatarConfig = { ...DEFAULT_AVATAR_CONFIG, ...(spec.config ?? {}) }
  const resolved: ResolvedAvatar = {
    presentation: spec.presentation,
    config,
    hairstyle: config.hairstyle ?? DEFAULT_HAIR[spec.presentation],
    eyebrows: config.eyebrows ?? DEFAULT_BROWS[spec.presentation],
    facialHair: FACIAL_HAIR.find((f) => f.id === config.facialHair)?.mesh ?? null,
    skinTone: 'fair',
    bodyType: config.bodyType ?? 'average',
    morphs: morphWeights(config, config.bodyType ?? 'average', spec.age ? ageWeights(spec.age) : {}),
    worn: spec.worn ?? {
      top: { id: config.top ?? 'top_white_tee', color: config.topColor },
      bottom: { id: config.bottom ?? 'bottom_jeans_light', color: config.bottomColor },
      footwear: { id: config.footwear ?? 'shoes_white_sneakers', color: config.footwearColor },
      ...(config.hat ? { hat: { id: config.hat, color: null } } : {}),
    },
    accessories: spec.accessories ?? [],
    heightCm: HEIGHT_CM,
    ageYears: spec.age ?? 0,
  }
  return (
    <>
      <group ref={group}>
        <Suspense fallback={null}>
          <RealisticAvatar resolved={resolved} meta={meta} isolate={spec.isolate} />
        </Suspense>
      </group>
      <Framer spec={spec} meta={meta} group={group} onDone={onDone} />
    </>
  )
}

function App() {
  const [job, setJob] = useState<{ spec: ThumbSpec; resolve: (s: string) => void; id: number } | null>(null)
  useEffect(() => {
    let id = 0
    window.__thumb = (spec) => new Promise((resolve) => setJob({ spec, resolve, id: ++id }))
    window.__garments = GARMENTS.filter((g) => g.available !== false).map((g) => g.id)
    window.__facialHair = FACIAL_HAIR.filter((f) => f.mesh).map((f) => ({ id: f.id, mesh: f.mesh! }))
    window.__hairStyles = HAIRSTYLES.filter((h) => h.available !== false).map((h) => ({ id: h.id, view: h.thumbView ?? 'front' }))
  }, [])
  return (
    <Canvas orthographic dpr={1} gl={{ preserveDrawingBuffer: true, alpha: true, antialias: true }} camera={{ position: [0, 1, 5], zoom: 100, near: 0.01, far: 50 }} style={{ width: SIZE, height: SIZE }}>
      <hemisphereLight args={['#fff8f2', '#dcd3e6', 0.55]} />
      <directionalLight position={[1.6, 3.6, 2.8]} intensity={2.0} />
      <directionalLight position={[-2.6, 2.2, 1.6]} intensity={0.7} color="#ffe9df" />
      <directionalLight position={[0, 2.5, -3]} intensity={0.8} color="#eae3ff" />
      <Environment resolution={128} frames={1}>
        <Lightformer intensity={1.6} position={[0, 3, 2.5]} scale={[5, 2, 1]} />
        <Lightformer intensity={1.0} position={[-3, 1.6, 1]} rotation-y={Math.PI / 2} scale={[3, 2.5, 1]} />
      </Environment>
      {job && <ThumbScene key={job.id} spec={job.spec} onDone={(url) => job.resolve(url)} />}
    </Canvas>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
