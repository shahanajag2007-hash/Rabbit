// Renders every Avatar Studio option thumbnail with the real three.js avatar.
// Usage (Vite dev server running on :5173):  node scripts/render-avatar-thumbnails.mjs [female|male ...] [--only=hair] [--keys=a,b]
// Requires Google Chrome (or set CHROME_PATH). Output: public/models/avatar/thumbs/<presentation>_<key>.png
import { chromium } from 'playwright-core'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const outDir = path.join(root, 'public/models/avatar/thumbs')
mkdirSync(outDir, { recursive: true })
const base = process.env.VITE_URL || 'http://localhost:5173'
const chrome = process.env.CHROME_PATH || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : '/usr/bin/google-chrome')
const args = process.argv.slice(2)
const only = args.find((a) => a.startsWith('--only='))?.slice(7)
const keys = args.find((a) => a.startsWith('--keys='))?.slice(7).split(',')
const presentations = args.filter((a) => !a.startsWith('--')).length ? args.filter((a) => !a.startsWith('--')) : ['female', 'male', 'neutral']

const MORPHS = ['natural', 'face_oval', 'face_round', 'face_square', 'face_heart', 'face_long', 'nose_narrow', 'nose_wide', 'nose_upturned', 'lips_full', 'lips_thin', 'lips_wide', 'eyes_large', 'eyes_almond', 'eyes_round']
const MORPH_FIELD = (id) => (id.startsWith('face_') ? 'facePreset' : id.startsWith('nose_') ? 'nose' : id.startsWith('lips_') ? 'lips' : 'eyeShape')
// Hairstyles come from src/components/avatar/hairStyles.ts (exposed by the thumbnail page).
let HAIR = []
const hairKey = (id) => `hair_${id.replace(/^hair_/, '')}`
const HAIR_COLORS = ['black', 'dark_brown', 'brown', 'light_brown', 'blonde', 'platinum', 'auburn', 'dark_auburn', 'red', 'burgundy', 'grey', 'silver', 'honey', 'rose_pink', 'pastel_pink', 'lavender', 'purple', 'blue']
const HAIR_HIGHLIGHTS = ['caramel', 'honey', 'platinum', 'copper', 'pink', 'purple', 'blue']
const BROWS = Array.from({ length: 12 }, (_, i) => `brows_eyebrow${String(i + 1).padStart(3, '0')}`)
// Garments and facial hair come from src/components/avatar/avatarCatalog.ts (exposed by the thumbnail page).
let GARMENTS = []
let FACIAL = []
const ACCESSORY_FOCUS = { earrings: 'head', necklace: 'neck', bracelet: 'wrist_r', glasses: 'face', sunglasses: 'face', watch: 'wrist', handbag: 'hand', tote: 'hand', belt: 'waist' }

function jobs(p) {
  const list = []
  // Each model has its own body presets (written by the Blender build into meta.json).
  const meta = JSON.parse(readFileSync(path.join(root, `public/models/avatar/${p}/meta.json`), 'utf8'))
  for (const b of ['average', ...meta.configs.body]) list.push([`body_${b}`, { presentation: p, config: { bodyType: b }, focus: 'full' }])
  list.push([`pose_front`, { presentation: p, focus: 'full' }])
  list.push([`pose_three_quarter`, { presentation: p, config: { pose: 'three_quarter' }, focus: 'full' }])
  for (const m of MORPHS) list.push([`morph_${m}`, { presentation: p, config: m === 'natural' ? {} : { [MORPH_FIELD(m)]: m }, focus: 'face' }])
  for (const b of BROWS) list.push([b, { presentation: p, config: { eyebrows: b }, focus: 'brows' }])
  for (const h of HAIR) list.push([hairKey(h.id), { presentation: p, config: { hairstyle: h.id }, focus: 'hair', view: h.view }])
  for (const c of HAIR_COLORS) list.push([`haircolor_${c}`, { presentation: p, config: { hairColor: c }, focus: 'hair' }])
  // Highlights are shown on long open hair (dark brown base), where the streaks are visible.
  for (const c of HAIR_HIGHLIGHTS) list.push([`hairhl_${c}`, { presentation: p, config: { hairHighlight: c, hairColor: 'dark_brown', hairstyle: 'hair_long01' }, focus: 'hair' }])
  // Only garments actually built for this model (meta.json) get a thumbnail.
  for (const g of GARMENTS.filter((id) => meta.garments[id])) list.push([g, { presentation: p, isolate: g, focus: 'auto', view: g.startsWith('shoes_') ? 'three_quarter' : 'front' }])
  for (const f of FACIAL.filter((x) => (meta.facialHair ?? []).includes(x.mesh))) list.push([f.mesh, { presentation: p, config: { facialHair: f.id, hairstyle: 'hair_short02' }, focus: 'face', view: 'three_quarter' }])
  // Earrings are shown with tied-back hair so the ears are visible.
  for (const [a, focus] of Object.entries(ACCESSORY_FOCUS)) list.push([`acc_${a}`, { presentation: p, accessories: [a], focus, config: a === 'earrings' ? { hairstyle: 'hair_ponytail01' } : {} }])
  // --only=<prefix> renders just the matching keys (e.g. --only=hair for hairstyles and hair colours).
  // --keys=<k1,k2> renders exactly those keys.
  if (keys) return list.filter(([key]) => keys.includes(key))
  return only ? list.filter(([key]) => key.startsWith(only)) : list
}

const browser = await chromium.launch({ executablePath: chrome, headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
const page = await browser.newPage({ viewport: { width: 256, height: 256 } })
page.on('pageerror', (e) => console.error('pageerror', e.message))
await page.goto(`${base}/tools/thumbnails.html`)
await page.waitForFunction(() => typeof window.__thumb === 'function' && Array.isArray(window.__hairStyles))
HAIR = await page.evaluate(() => window.__hairStyles)
GARMENTS = await page.evaluate(() => window.__garments)
FACIAL = await page.evaluate(() => window.__facialHair)
let n = 0
for (const p of presentations) {
  for (const [key, spec] of jobs(p)) {
    const dataUrl = await page.evaluate((s) => window.__thumb(s), spec)
    writeFileSync(path.join(outDir, `${p}_${key}.png`), Buffer.from(dataUrl.split(',')[1], 'base64'))
    n++
    if (n % 10 === 0) console.log(`${n} thumbnails…`)
  }
}
console.log(`Rendered ${n} thumbnails into ${outDir}`)
await browser.close()
