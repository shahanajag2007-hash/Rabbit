// End-to-end check of the Avatar Studio against the *rendered* three.js avatar.
// Usage (Vite dev server running on :5173):  node scripts/verify-avatar.mjs
// Requires Google Chrome (or set CHROME_PATH). Exits with code 1 if any check fails.
//
// It drives the app's own zustand store (same module instance the page uses) and then measures the
// live scene exposed in development by AvatarViewer (DevSceneHook): world-space body height, morph
// influences, skin material and shader uniforms, which hair / garment meshes are actually drawn, and
// whether the camera frames the whole figure.
import { chromium } from 'playwright-core'

const base = process.env.VITE_URL || 'http://localhost:5173'
const chrome = process.env.CHROME_PATH || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : '/usr/bin/google-chrome')
const QUICK = process.argv.includes('--quick') // skip the every-hairstyle / every-garment sweeps

const results = []
function check(name, ok, detail = '') {
  results.push({ name, ok: !!ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`)
}

const browser = await chromium.launch({ executablePath: chrome, headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
const page = await browser.newPage({ viewport: { width: 900, height: 700 } })
// Leaving the avatar page takes ~30 s under software WebGL (SwiftShader context teardown), not on a real GPU.
page.setDefaultNavigationTimeout(120000)
const pageErrors = []
const assetErrors = []
page.on('pageerror', (e) => pageErrors.push(e.message))
page.on('console', (m) => {
  const t = m.text()
  if (m.type() === 'error' && /404|failed to load|Could not load/i.test(t) && !/\/api\//.test(t)) assetErrors.push(t.slice(0, 160))
  if (/texture failed to load/.test(t)) assetErrors.push(t.slice(0, 160))
})
page.on('response', (r) => {
  if (r.status() >= 400 && r.url().includes('/models/')) assetErrors.push(`${r.status()} ${r.url()}`)
})

/** Run a store action in the page. */
const store = (fn, arg) =>
  page.evaluate(
    async ([src, a]) => {
      const { useStyleStore } = await import('/src/hooks/useStyleStore.ts')
      return new Function('s', 'a', src)(useStyleStore, a)
    },
    [fn, arg],
  )
const cfg = () => store(`return s.getState().avatar_config`)

/** Measure the rendered avatar once loading has finished and the result is stable (3 equal samples). */
async function probe() {
  let last = null
  let lastObj = null
  let same = 0
  const diffs = new Set()
  for (let i = 0; i < 300; i++) {
    const p = await page.evaluate(async () => {
      if (document.querySelector('.viewer-loading')) return null // assets still loading
      const THREE = await import('/node_modules/.vite/deps/three.js').catch(() => null)
      const scenes = [...(window.__styleaiScenes ?? [])]
      const scene = scenes[scenes.length - 1]
      if (!scene || !THREE) return null
      const meshes = []
      scene.traverse((o) => o.isMesh && o.visible && meshes.push(o))
      const bodies = meshes.filter((m) => m.name === 'body')
      const body = bodies[0]
      if (!body) return null
      scene.updateMatrixWorld(true)
      const box = new THREE.Box3().setFromObject(body, true)
      const influences = {}
      for (const [k, i] of Object.entries(body.morphTargetDictionary ?? {})) if (body.morphTargetInfluences[i] > 0.001) influences[k] = +body.morphTargetInfluences[i].toFixed(3)
      const skinMap = body.material.map?.source?.data?.src ?? body.material.map?.image?.src ?? ''
      const named = meshes.map((m) => m.name).filter(Boolean)
      const hairMeshes = meshes.filter((m) => m.name.startsWith('hair_'))
      const facial = meshes.filter((m) => m.name.startsWith('facial_'))
      const procedural = meshes.filter((m) => m.material?.map?.isCanvasTexture)
      const skinU = body.material.userData.skinUniforms
      const scalp = body.geometry.getAttribute('aScalp')
      let covered = 0
      if (scalp) for (const v of scalp.array) if (v > 0.5) covered++
      // Whole figure (all avatar meshes) projected through the live camera.
      const cam = scene.userData.camera
      // precise = morphed vertex positions (the plain bounding box spans every morph target's extent)
      const all = new THREE.Box3()
      for (const m of meshes) if (/^(body|hair_|top_|bottom_|full_|dress_|outer_|shoes_|hat_)/.test(m.name)) all.union(new THREE.Box3().setFromObject(m, true))
      const shoes = meshes.filter((m) => m.name.startsWith('shoes_'))
      const shoeFloor = shoes.length ? Math.min(...shoes.map((m) => new THREE.Box3().setFromObject(m, true).min.y)) : null
      // Unmorphed top of the body mesh identifies the base model.
      const pos = body.geometry.getAttribute('position')
      let baseTop = -Infinity
      for (let i = 0; i < pos.count; i++) baseTop = Math.max(baseTop, pos.getY(i))
      let inFrame = null
      if (cam) {
        cam.updateMatrixWorld(true)
        const ys = [all.min, all.max].map((v) => v.clone().project(cam).y)
        inFrame = { bottom: +ys[0].toFixed(3), top: +ys[1].toFixed(3) }
      }
      return {
        bodies: bodies.length,
        localTop: +baseTop.toFixed(3),
        shoeFloor: shoeFloor === null ? null : +shoeFloor.toFixed(4),
        height: +(box.max.y - box.min.y).toFixed(4),
        floor: +box.min.y.toFixed(4),
        depth: +(box.max.z - box.min.z).toFixed(4),
        width: +(box.max.x - box.min.x).toFixed(4),
        influences,
        skinMap: skinMap.split('/').pop(),
        skinColor: '#' + body.material.color.getHexString(),
        ageWeights: skinU ? [+skinU.uAgeWeights.value.x.toFixed(3), +skinU.uAgeWeights.value.y.toFixed(3)] : null,
        ageMap: skinU?.uAgeMap.value?.source?.data?.src?.split('/').pop() ?? null,
        scalpCovered: covered,
        hair: hairMeshes.map((m) => m.name),
        hairColor: hairMeshes[0] ? '#' + hairMeshes[0].material.color.getHexString() : null,
        hairBlendKeepsAlpha: hairMeshes.every((m) => m.material.blending === THREE.CustomBlending && m.material.blendDstAlpha === THREE.OneFactor),
        facial: facial.map((m) => m.name),
        proceduralHair: procedural.length,
        garments: named.filter((n) => /^(top|bottom|shoes|outer|hat|dress|full)_/.test(n)).sort(),
        inFrame,
        state: JSON.parse(document.querySelector('.model-canvas')?.getAttribute('data-avatar-state') ?? 'null'),
      }
    })
    const key = JSON.stringify(p)
    if (p && lastObj) for (const k of Object.keys(p)) if (JSON.stringify(p[k]) !== JSON.stringify(lastObj[k])) diffs.add(k)
    lastObj = p ?? lastObj
    same = p && key === last ? same + 1 : 0
    if (same >= 2) return p
    last = key
    await page.waitForTimeout(400)
  }
  throw new Error(`avatar did not settle (changing: ${[...diffs].join(', ') || 'still loading'})`)
}

const MODEL_TOP = { female: 1.632, male: 1.774, neutral: 1.703 } // local body-mesh top (MakeHuman models, basis)
const modelOf = (p) => Object.entries(MODEL_TOP).sort((a, b) => Math.abs(a[1] - p.localTop) - Math.abs(b[1] - p.localTop))[0][0]
const sameJSON = (a, b) => JSON.stringify(a) === JSON.stringify(b)

// ------------------------------------------------------------------------------------------------
await page.goto(`${base}/profile`)
await page.evaluate(() => sessionStorage.clear())
await page.goto(`${base}/profile`)
await store(`s.getState().set({ gender: 'Female', height: 160, weight: 52, age: 22, skin_tone: 'Medium', budget: 4000 })`)
await page.goto(`${base}/avatar`)
let p = await probe()
check('Female profile loads the female model', modelOf(p) === 'female' && p.state.presentation === 'female', `localTop ${p.localTop}`)
check('Exactly one avatar body in the scene', p.bodies === 1, `${p.bodies}`)
check('Rendered female avatar wears the female starter outfit (tunic, harem pants, flats)', sameJSON(p.garments, ['bottom_harem', 'shoes_flats', 'top_tunic']), p.garments.join(','))

// 1. Height -> MakeHuman height morph + calibrated stature, feet on the floor, figure in frame
const heights = {}
for (const h of [150, 165, 180, 195, 165]) {
  await store(`s.getState().set({ height: a })`, h)
  heights[h] = await probe()
}
for (const h of [150, 165, 180, 195]) check(`Height ${h} cm renders a ${(h / 100).toFixed(2)} m figure (sole to crown)`, Math.abs(heights[h].height - h / 100) < 0.012, `${heights[h].height} m`)
check('150 cm uses the MakeHuman short-height morph', (heights[150].influences.height_short ?? 0) > 0.05, JSON.stringify(heights[150].influences))
check('195 cm uses the MakeHuman tall-height morph', (heights[195].influences.height_tall ?? 0) > 0.2, JSON.stringify(heights[195].influences))
check('Taller profile gives a visibly taller avatar (150 vs 180 cm)', heights[180].height - heights[150].height > 0.28)
check('Shoes stay on the floor at every height', [150, 165, 180, 195].every((h) => Math.abs(heights[h].shoeFloor) < 0.006), [150, 195].map((h) => heights[h].shoeFloor).join(', '))
check('Repeated height changes do not accumulate error (165 cm twice)', Math.abs(heights[165].height - 1.65) < 0.012)
check('Whole figure stays in frame at 195 cm (head and feet visible)', heights[195].inFrame && heights[195].inFrame.top < 1 && heights[195].inFrame.bottom > -1, JSON.stringify(heights[195].inFrame))
check('Whole figure stays in frame at 150 cm', heights[150].inFrame && heights[150].inFrame.top < 1 && heights[150].inFrame.bottom > -1, JSON.stringify(heights[150].inFrame))

// 2. Weight -> body build (fractional morphs from height AND weight), independent of height
await store(`s.getState().set({ height: 168, weight: 50 })`)
const light = await probe()
await store(`s.getState().set({ weight: 64 })`)
const mid = await probe()
await store(`s.getState().set({ weight: 90 })`)
const heavy = await probe()
check('Low weight-for-height blends towards the slim preset', (light.influences.slim ?? 0) > 0.3 && !light.influences.full, JSON.stringify(light.influences))
check('High weight-for-height blends towards the full preset', (heavy.influences.full ?? 0) > 0.5, JSON.stringify(heavy.influences))
check('Weight changes the rendered body volume', heavy.depth > light.depth + 0.012 && heavy.width > light.width && mid.depth > light.depth, `depth ${light.depth} < ${mid.depth} < ${heavy.depth}, width ${light.width} -> ${heavy.width}`)
check('Weight does not change stature', Math.abs(heavy.height - light.height) < 0.012, `${light.height} vs ${heavy.height}`)
await store(`s.getState().set({ height: 168, weight: 60 })`)

// 3. Age -> continuous age morphs + skin detail
const ages = {}
for (const a of [15, 22, 25, 40, 55, 72, 88]) {
  await store(`s.getState().set({ age: a })`, a)
  ages[a] = await probe()
}
check('Age 15: teen morph (age_14/age_18), no skin ageing', (ages[15].influences.age_14 ?? 0) > 0 && ages[15].ageWeights?.every((w) => w === 0), JSON.stringify(ages[15].influences))
check('Age 22: young-adult blend, no older morphs or skin ageing', (ages[22].influences.age_18 ?? 0) > 0 && !ages[22].influences.age_45 && ages[22].ageWeights?.every((w) => w === 0), JSON.stringify(ages[22].influences))
check('Age 25: base adult model (no age morph)', !Object.keys(ages[25].influences).some((k) => k.startsWith('age_')), JSON.stringify(ages[25].influences))
check('Age 40: partial age_45 morph + subtle middle-age skin detail', (ages[40].influences.age_45 ?? 0) > 0.6 && ages[40].ageWeights[0] > 0.3, `${JSON.stringify(ages[40].influences)} skin ${ages[40].ageWeights}`)
check('Age 72: age_65/age_85 morphs + old-age skin detail', (ages[72].influences.age_65 ?? 0) > 0.5 && ages[72].ageWeights[1] > 0.5, `${JSON.stringify(ages[72].influences)} skin ${ages[72].ageWeights}`)
check('Age 88: oldest configuration', (ages[88].influences.age_85 ?? 0) === 1)
check('Skin age detail uses the age map for this model', /age_detail_female\.png/.test(ages[72].ageMap ?? ''), ages[72].ageMap)
check('Age changes keep the profile height', [15, 25, 72, 88].every((a) => Math.abs(ages[a].height - 1.68) < 0.012), [15, 25, 72, 88].map((a) => ages[a].height).join(', '))
await store(`s.getState().set({ age: 22 })`)

// 4. Skin tone (profile <-> avatar) and its persistence through other changes
await store(`s.getState().setSkinTone('Deep')`)
p = await probe()
check('Profile skin tone Deep is rendered with the dark skin texture', p.skinMap.includes('darkskinned'), `${p.skinMap} ${p.skinColor}`)
await store(`s.getState().setSkinShade('olive')`)
const olive = await probe()
const tone = await store(`return s.getState().skin_tone`)
check('Choosing a studio shade (Olive) updates the profile skin tone to Tan', tone === 'Tan', tone)
await store(`s.getState().updateAvatar({ hairColor: 'auburn' })`)
const auburn = await probe()
await store(`s.getState().set({ height: 181, weight: 75, age: 47 })`)
await store(`s.getState().updateAvatar({ hairstyle: 'in_double_braids', top: 'top_sweater', bottom: 'bottom_long_skirt' })`)
p = await probe()
check('Skin tone unchanged after height/weight/age/hair/clothing changes', p.skinMap === olive.skinMap && p.skinColor === olive.skinColor, `${p.skinMap} ${p.skinColor}`)
check('Hair colour unchanged after height/weight/age/hair/clothing changes', p.hairColor === auburn.hairColor, `${auburn.hairColor} -> ${p.hairColor}`)
check('Clothing change does not reset proportions', Math.abs(p.height - 1.81) < 0.012 && (p.influences.age_45 ?? 0) > 0.8, `${p.height} m ${JSON.stringify(p.influences)}`)
await store(`s.getState().set({ height: 168, weight: 60, age: 22 })`)

// 5. Hair integration
await store(`s.getState().updateAvatar({ hairstyle: 'hair_bob02' })`)
p = await probe()
check('Hair materials never lower the canvas alpha (no see-through strands)', p.hairBlendKeepsAlpha)
check('Scalp under the hairstyle is root-shaded', p.scalpCovered > 300, `${p.scalpCovered} body vertices`)
// Highlights: streak strength and the head frame they are placed by, read from the live hair materials
// (procedural parts included, via a space-buns style).
const streaks = () =>
  page.evaluate(() => {
    const out = []
    const scene = [...(window.__styleaiScenes ?? [])].pop()
    scene?.traverse((o) => o.isMesh && o.visible && o.material?.userData?.hairUniforms && out.push([o.material.userData.hairUniforms.uHairStreak.value.w, o.material.userData.hairUniforms.uHairFace.value.x]))
    return out
  })
await store(`s.getState().updateAvatar({ hairstyle: 'hair_long01', hairHighlight: 'pink' })`)
await probe()
let st = await streaks()
check('Highlights: every hair material gets the streaks and the head frame (plain mesh)', st.length > 0 && st.every(([w, eyeY]) => w > 0 && eyeY > 1), JSON.stringify(st))
await store(`s.getState().updateAvatar({ hairstyle: 'in_half_up_space_buns' })`)
await probe()
st = await streaks()
check('Highlights: also on procedural parts (space buns)', st.length >= 2 && st.every(([w]) => w > 0), JSON.stringify(st))
await store(`s.getState().updateAvatar({ hairHighlight: null })`)
await probe()
st = await streaks()
check('Highlights: None removes them', st.length > 0 && st.every(([w]) => w === 0), JSON.stringify(st))
await store(`s.getState().updateAvatar({ hairstyle: 'hair_bob02' })`)
await store(`s.getState().updateAvatar({ hairstyle: 'mx_low_fade' })`)
const fade = await probe()
check('Switching hairstyle replaces the previous meshes (no leftovers)', sameJSON([...fade.hair].sort(), ['hair_short01', 'hair_short04']), fade.hair.join(','))
check('Scalp shading follows the new hairstyle', fade.scalpCovered !== p.scalpCovered, `${p.scalpCovered} -> ${fade.scalpCovered}`)

// 6. Customise on the female model, then switch to male
await store(`s.getState().updateAvatar({ hairstyle: 'in_double_braids', bodyType: 'curvy', top: 'top_sport_crop', hairColor: 'auburn', eyeColor: 'green', accessories: ['watch'] })`)
await store(`s.getState().set({ recommended_outfits: [{ score: 9, items: {} }], selected_outfit: { items: { Top: { item_id: 1, category: 'Top', item_name: 'Linen Polo', colour: 'Navy', style: 'Casual', occasion: 'College', price: 999 } } } })`)
const profileSnap = `const g = s.getState(); return { name: g.user_name, height: g.height, weight: g.weight, age: g.age, budget: g.budget, skin: g.skin_tone, shade: g.skin_shade, style: g.style, recs: g.recommended_outfits, sel: g.selected_outfit }`
const before = await store(profileSnap)
p = await probe()
check('Body type Curvy is a real morph on the rendered body', p.influences.curvy === 1, JSON.stringify(p.influences))
check('Double braids: scalp mesh + procedural braids are drawn', p.hair.includes('hair_ponytail01') && p.proceduralHair >= 1)

await store(`s.getState().set({ gender: 'Male' })`)
p = await probe()
const cfgM = await cfg()
check('Profile gender Male switches to the male model automatically', modelOf(p) === 'male' && p.state.presentation === 'male', `localTop ${p.localTop}`)
check('Male defaults: default hairstyle, suggested body, starter outfit', cfgM.hairstyle === null && cfgM.bodyType === null && cfgM.top === 'top_white_tee' && cfgM.bottom === 'bottom_suit_trousers', `${cfgM.top}/${cfgM.bottom}`)
check('Rendered male avatar wears the male starter outfit', sameJSON(p.garments, ['bottom_suit_trousers', 'shoes_white_sneakers', 'top_white_tee']), p.garments.join(','))
check('Female-only customisations reset (no braids, no curvy morph)', p.proceduralHair === 0 && !p.influences.curvy)
check('Unrelated choices kept (eye colour, hair colour, accessories)', cfgM.eyeColor === 'green' && cfgM.hairColor === 'auburn' && cfgM.accessories.includes('watch'))
check('Profile, skin tone, recommendations and selected outfit untouched by the switch', sameJSON(before, await store(profileSnap)))

// 7. Facial hair (male)
await store(`s.getState().updateAvatar({ facialHair: 'full_beard' })`)
p = await probe()
check('Facial hair: full beard mesh is drawn on the male model', p.facial.includes('facial_beard_full'), p.facial.join(','))
await store(`s.getState().updateAvatar({ facialHair: 'mustache' })`)
p = await probe()
check('Facial hair: switching to a moustache replaces the beard', sameJSON(p.facial, ['facial_moustache']), p.facial.join(','))
await store(`s.getState().updateAvatar({ facialHair: 'none' })`)

// 8. Clothing: every available garment renders on every model, replacing the previous item
const catalog = await page.evaluate(async () => (await import('/src/components/avatar/avatarCatalog.ts')).GARMENTS.map((g) => ({ id: g.id, slot: g.slot, available: g.available !== false, underlayer: g.underlayer ?? null })))
const field = { top: 'top', bottom: 'bottom', full: 'full', outerwear: 'outerwear', footwear: 'footwear', hat: 'hat' }
const models = QUICK ? ['female'] : ['female', 'male', 'neutral']
const garmentFailures = []
for (const model of models) {
  await store(`s.getState().updateAvatar({ presentation: a })`, model)
  for (const g of catalog.filter((x) => x.available)) {
    await store(`s.getState().updateAvatar({ [a[0]]: a[1], ...(a[0] === 'full' ? {} : { full: null }) })`, [field[g.slot], g.id])
    const q = await probe()
    const others = q.garments.filter((n) => n !== g.id)
    const sameSlot = catalog.filter((x) => x.slot === g.slot && x.id !== g.id).map((x) => x.id)
    let ok = q.garments.includes(g.id) && !others.some((n) => sameSlot.includes(n))
    // A sleeveless dress draws its declared long-sleeve layer underneath; nothing else from other slots.
    if (g.slot === 'full') ok = ok && !q.garments.some((n) => /^(top|bottom|outer)_/.test(n) && n !== g.underlayer) && (!g.underlayer || q.garments.includes(g.underlayer))
    if (!ok) garmentFailures.push(`${model}/${g.id}: drew ${q.garments.join(',')}`)
  }
  await store(`s.getState().updateAvatar({ full: null, outerwear: null })`)
}
check(`All ${catalog.filter((x) => x.available).length} available garments render and replace their slot on ${models.join('/')}`, garmentFailures.length === 0, garmentFailures.slice(0, 4).join('; '))
check('Revealing / logo items are not offered (camisole, tank, crop top, shorts, graphic tee)', !catalog.some((x) => /camisole|top_tank|sport_crop|denim_shorts|graphic_tee/.test(x.id)), catalog.map((x) => x.id).filter((id) => /camisole|tank|crop|shorts|graphic/.test(id)).join(','))
// Dresses: sleeves layer + lengthened skirt; wide skirt worn over a tucked-in top.
// Switching model re-initialises the outfit, so the dress is put on after the switch.
await store(`s.getState().updateAvatar({ presentation: 'female' })`)
await store(`s.getState().updateAvatar({ full: 'dress_shift' })`)
p = await probe()
check('Shift dress is worn with long sleeves (fitted layer underneath)', p.garments.includes('dress_shift') && p.garments.includes('top_longsleeve_tee'), p.garments.join(','))
const stretched = await page.evaluate(() => {
  const scene = [...(window.__styleaiScenes ?? [])].pop()
  let maxDown = 0
  scene?.traverse((o) => {
    const lay = o.isMesh && o.visible ? o.geometry?.attributes?.aLayer : null
    if (!lay) return
    for (let i = 0; i < lay.count; i++) maxDown = Math.min(maxDown, lay.getY(i))
  })
  return maxDown
})
check('Shift dress is lengthened below the hips (>= 20 cm at the hem)', stretched < -0.2, `${stretched.toFixed(3)} m`)
await store(`s.getState().updateAvatar({ full: null, top: 'top_tunic', bottom: 'bottom_long_skirt' })`)
p = await probe()
const tucked = await page.evaluate(() => {
  const scene = [...(window.__styleaiScenes ?? [])].pop()
  let moved = 0
  scene?.traverse((o) => {
    const lay = o.isMesh && o.visible ? o.geometry?.attributes?.aLayer : null
    if (!lay) return
    let n = 0
    for (let i = 0; i < lay.count; i++) if (Math.hypot(lay.getX(i), lay.getY(i), lay.getZ(i)) > 1e-4) n++
    moved = Math.max(moved, n)
  })
  return moved
})
check('Tunic is tucked inside the wide long skirt (layer offsets on the top)', tucked > 50 && p.garments.includes('top_tunic') && p.garments.includes('bottom_long_skirt'), `${tucked} vertices moved`)
await store(`s.getState().updateAvatar({ top: 'top_tunic', bottom: 'bottom_harem' })`)
const unavailable = catalog.filter((x) => !x.available).map((x) => x.id)
check('Garments without a mesh are listed as unavailable (not faked)', unavailable.every((id) => /hoodie|coat|saree|sherwani|sandals/.test(id)), unavailable.join(','))

// 9. Every hairstyle renders on every model
if (!QUICK) {
  const styles = await page.evaluate(async () => (await import('/src/components/avatar/hairStyles.ts')).HAIRSTYLES.map((h) => ({ id: h.id, layers: h.layers.map((l) => l.mesh), parts: (h.parts ?? []).length })))
  const failures = []
  for (const model of ['female', 'male', 'neutral']) {
    await store(`s.getState().updateAvatar({ presentation: a })`, model)
    for (const st of styles) {
      await store(`s.getState().updateAvatar({ hairstyle: a })`, st.id)
      const q = await probe()
      const ok = q.state.hairstyle === st.id && sameJSON([...q.hair].sort(), [...st.layers].sort()) && (st.parts ? q.proceduralHair >= 1 : q.proceduralHair === 0)
      if (!ok) failures.push(`${model}/${st.id}: drew ${q.hair} + ${q.proceduralHair}`)
    }
  }
  check(`All ${styles.length} hairstyles draw their meshes/parts on all 3 models`, failures.length === 0, failures.slice(0, 5).join('; '))
}

// 10. Avatar clothing never touches the recommendation; persistence; Final Look; pages
await store(`s.getState().updateAvatar({ presentation: null })`)
const rec = await store(`const g = s.getState(); return { recs: g.recommended_outfits, sel: g.selected_outfit }`)
check('Avatar clothing changes leave recommendations and the selected outfit unchanged', sameJSON(rec.recs, before.recs) && sameJSON(rec.sel, before.sel))
const cfgBefore = await cfg()
await page.goto(`${base}/recommendations`)
await page.goto(`${base}/avatar`)
check('Avatar settings persist across navigation and reload', sameJSON(cfgBefore, await cfg()))
await page.goto(`${base}/final-look`)
p = await probe()
check('Final Look renders the recommended polo on the avatar', p.garments.includes('top_polo') && p.state.worn.top?.color, JSON.stringify(p.state.worn.top))
const nav = await page.evaluate(async () => (await import('/src/routes.ts')).PAGES.map((x) => x.label))
check('Six dashboard pages, the sixth is Final Look', nav.length === 6 && nav[5].includes('Final Look'), nav.join(' | '))
for (const path of ['/profile', '/appearance', '/avatar', '/recommendations', '/complete-look', '/final-look']) {
  await page.goto(`${base}${path}`)
  const h1 = await page.locator('h1').first().textContent({ timeout: 15000 }).catch(() => null)
  check(`Page ${path} renders`, !!h1, h1 ?? 'no heading')
}

check('No avatar asset failed to load (404 / texture errors)', assetErrors.length === 0, [...new Set(assetErrors)].slice(0, 4).join(' | '))
check('No uncaught page errors', pageErrors.length === 0, pageErrors.slice(0, 3).join(' | '))
await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length ? 1 : 0)
