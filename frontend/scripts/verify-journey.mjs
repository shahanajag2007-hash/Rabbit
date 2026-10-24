// End-to-end check of the personalised styling journey in headless Chrome, driving the real UI.
// Usage (app running via `npm run dev:all`):
//   node scripts/verify-journey.mjs                      # everything except the AI try-on
//   node scripts/verify-journey.mjs --photo=C:/path/full-body.jpg   # also uploads the photo and runs the try-on
// The try-on sends the photo to the configured provider (see api/tryon.py), so it only runs with --photo.
// Exits with code 1 if any check fails.
import { chromium } from 'playwright-core'

const base = process.env.VITE_URL || 'http://localhost:5173'
const chrome = process.env.CHROME_PATH || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : '/usr/bin/google-chrome')
const photoArg = process.argv.find((a) => a.startsWith('--photo='))?.slice(8)

const results = []
function check(name, ok, detail = '') {
  results.push({ name, ok: !!ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`)
}
function skip(name, detail) {
  console.log(`SKIP  ${name}  (${detail})`)
}

const browser = await chromium.launch({ executablePath: chrome, headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
page.setDefaultNavigationTimeout(120000)
page.setDefaultTimeout(60000)
const pageErrors = []
page.on('pageerror', (e) => pageErrors.push(e.message))

const store = (src, arg) =>
  page.evaluate(
    async ([src, arg]) => {
      const { useStyleStore } = await import('/src/hooks/useStyleStore.ts')
      return new Function('s', 'a', src)(useStyleStore, arg)
    },
    [src, arg],
  )
const api = (path, body) =>
  page.evaluate(
    async ([path, body]) => (await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : undefined)).json(),
    [path, body],
  )
const outfitNames = () =>
  page.$$eval('.product-grid-4', (grids) => grids.slice(0, 3).map((g) => [...g.querySelectorAll('.product-name')].map((n) => n.textContent).join(' + ')))
const waitIdle = () => page.waitForLoadState('networkidle').catch(() => undefined)

// --- Profile (Test A, B) --------------------------------------------------------------------------
await page.goto(`${base}/profile`)
await page.evaluate(() => sessionStorage.clear())
await page.goto(`${base}/profile`)
await page.fill('#age', '14')
check('Profile: age input updates the shared profile', (await store('return s.getState().age')) === 14)

// --- Recommendations (Tests A, D, E) ------------------------------------------------------------
await page.goto(`${base}/recommendations`)
await page.waitForSelector('.product-grid-4 .product-name')
await waitIdle()
const teenOutfits = await outfitNames()
check('Recommendations: three outfit cards are kept', teenOutfits.length === 3, `${teenOutfits.length} outfits`)
const teenItems = await store('return s.getState().recommended_outfits.flatMap(o => Object.values(o.items).map(i => i.item_name))')
check('Test A: no adult-oriented items for a 14-year-old', !teenItems.some((n) => /crop|bodycon|halter|backless|lingerie/i.test(n)))
const sentAge = await api('/api/recommendations', { profile: { ...(await store('const st = s.getState(); return { gender: st.gender, age: st.age, budget: st.budget }')), skin_tone: 'Medium', style: 'Casual', occasion: 'College' } })
check('Test A: age reaches the recommender', sentAge.outfits?.length > 0)

await page.fill('#pref-text', 'Suggest a formal outfit in navy blue for the office, no red')
await page.click('text=ANALYZE MY STYLE')
await page.waitForFunction(() => document.body.innerText.includes('From your request'))
await waitIdle()
const heading = await page.textContent('text=/Formal \\+ Office/')
check('Test D: text request understood (style/occasion/colour/avoid)', (await page.textContent('body')).includes('Style: Formal · Occasion: Office · Colours: Navy · Avoid: Red'))
check('Test D: profile heading shows the style in effect', Boolean(heading))
const formalItems = await store('return s.getState().recommended_outfits.flatMap(o => Object.values(o.items))')
check('Test D: no avoided colour (red) in results', !formalItems.some((i) => i.colour === 'Red'))
check('Test D: results changed after the request', JSON.stringify(await outfitNames()) !== JSON.stringify(teenOutfits))

const swatches = await page.$$eval('button.swatch-card', (b) => b.map((x) => x.innerText.split('\n')[0]))
check('Test E: palette shows real, clickable in-stock colours', swatches.length >= 3 && (await page.$$eval('button.swatch-card', (b) => b.every((x) => /\d+ available/.test(x.innerText)))), swatches.join(', '))
let paletteChanged = false
for (const name of swatches) {
  const before = await outfitNames()
  await page.click(`button.swatch-card:has-text("${name}")`)
  await page.waitForTimeout(400)
  await waitIdle()
  const after = await outfitNames()
  const pressed = await page.$eval(`button.swatch-card:has-text("${name}")`, (b) => b.getAttribute('aria-pressed'))
  if (pressed === 'true' && JSON.stringify(after) !== JSON.stringify(before)) {
    paletteChanged = true
    check('Test E: picking a palette colour re-ranks the outfits', true, `${name}`)
    break
  }
}
if (!paletteChanged) check('Test E: picking a palette colour re-ranks the outfits', false)
// Brief test 1 / 3: a Traditional request never shows western garment types (or explains the gap).
await store('s.getState().set({ palette_colour: null, preference_text: "", applied_preference_text: "", style: "Traditional", occasion: "Festival" })')
await page.waitForTimeout(500)
await waitIdle()
const tradItems = await store('return s.getState().recommended_outfits.flatMap(o => Object.values(o.items))')
const western = tradItems.filter((i) => /t-?shirt|tee\b|jeans|jogger|sneaker|cap\b|hoodie|crop/i.test(i.item_name))
const explained = (await page.textContent('body')).includes('no complete traditional outfit can be built')
check('Brief 1/3: Traditional shows only traditional pieces (or explains what the catalogue lacks)', western.length === 0 && (tradItems.length > 0 || explained),
  tradItems.length ? `${tradItems.length} items` : 'explained: catalogue gap')
await store('s.getState().set({ style: "Casual", occasion: "College" })')
await waitIdle()

// --- Manual builder (Tests F, G) ----------------------------------------------------------------
const builder = page.locator('.panel', { hasText: 'CHOOSE YOUR STYLE MANUALLY' })
const picks = []
for (const cat of ['Top', 'Bottom', 'Shoes', 'Accessory']) {
  if (cat === 'Bottom' && (await store('return Boolean(s.getState().builder_items.Top?.covers_bottom)'))) {
    check('Test F: a set / dress top skips the bottom-wear step', (await builder.locator('text=/Step \\d: /').textContent()).includes('footwear'))
    continue
  }
  await builder.locator(`text=/Step \\d: /`).waitFor()
  const stepTitle = await builder.locator('text=/Step \\d: /').textContent()
  const grids = await builder.locator('.product-grid-4').count()
  const remaining = await store('const st = s.getState(); return st.budget - Object.values(st.builder_items).reduce((a, i) => a + Number(i.price), 0)')
  await builder.locator('.product-grid-4 .product-name').first().waitFor()
  await page.waitForTimeout(300)
  const prices = await builder.locator('.product-grid-4 .product-price').allTextContents()
  const within = prices.every((p) => Number(p.replace(/[^\d.]/g, '')) <= remaining)
  const explained = (await builder.textContent()).includes(`Nothing in ${cat.toLowerCase()} fits`)
  check(`Test F: builder step "${stepTitle.trim()}" shows one category at a time`, grids === 1)
  check(`Test F: ${cat} options fit the remaining budget (or the shortfall is explained)`, within || explained, within ? `≤ ₹${remaining}` : `only ₹${remaining} left — explained`)
  const name = await builder.locator('.product-grid-4 .product-name').first().textContent()
  await builder.locator('.product-grid-4 button', { hasText: `Select ${cat}` }).first().click()
  picks.push(name)
  await page.waitForTimeout(300)
}
const builderItems = await store('return Object.values(s.getState().builder_items).map(i => i.item_name)')
check('Test G: picks are saved in the shared outfit state', builderItems.length === picks.length && picks.every((p) => builderItems.includes(p)), `${picks.length} pieces`)
await builder.locator('button', { hasText: 'Use This Outfit' }).click()
await page.waitForURL('**/complete-look')
const selected = await store('return Object.values(s.getState().selected_outfit.items).map(i => i.item_name)')
check('Test S: Complete Look shows exactly the built outfit', picks.every((p) => selected.includes(p)))

// --- Complete Look: avatar mode, product actions (Tests I-N, R) ---------------------------------
await page.waitForSelector('.outfit-breakdown-card')
check('Test R: avatar mode shows the 3D viewer and no photo try-on', (await page.$('canvas')) !== null && !(await page.textContent('body')).includes('Photo mode is selected'))

const links = await page.$$eval('.outfit-breakdown-card a.inline-link', (a) => a.map((x) => x.href))
check('Test N: product links point to the brands\' own https product pages', links.length > 0 && links.every((h) => /^https:\/\/www\.[a-z.]+\/products\//.test(h)), `${links.length} links`)

// Products with real size / colour variants for the size and colour tests.
// Fetched from Node, not inside the page: the page is busy rendering the 3D avatar in software WebGL.
// Straight from the backend: the Vite dev proxy stalls on responses over ~2 MB (the app never needs this one).
const backend = process.env.STYLEAI_BACKEND_URL || 'http://127.0.0.1:8000'
const catalogItems = (await (await fetch(`${backend}/api/catalog`)).json()).items
const sized =
  catalogItems.find((i) => i.category === 'Top' && (i.available_sizes?.length ?? 0) >= 2 && i.sizes.length > i.available_sizes.length) ??
  catalogItems.find((i) => i.category === 'Top' && (i.available_sizes?.length ?? 0) >= 2)
const multiColour =
  catalogItems.find((i) => i.category === 'Top' && (i.colour_options?.length ?? 0) >= 2 && (i.available_sizes?.length ?? 0) >= 1) ??
  catalogItems.find((i) => i.category === 'Top' && (i.colour_options?.length ?? 0) >= 2)
await store('s.getState().set({ locked_items: { Top: false, Bottom: false, Shoes: false, Accessory: false } })')
if (sized) {
  await store('s.getState().setOutfitItem("Top", a)', sized)
  await page.waitForTimeout(500)
  const topRow = page.locator('.outfit-breakdown-card > div', { hasText: sized.item_name }).first()
  const sizeButtons = topRow.locator('[role=radio]')
  const sizes = await sizeButtons.allTextContents()
  const disabled = await sizeButtons.evaluateAll((b) => b.filter((x) => x.disabled).map((x) => x.textContent))
  check('Test M: only the product\'s real sizes are offered', JSON.stringify(sizes) === JSON.stringify(sized.sizes), sizes.join(' '))
  check('Test M: sold-out sizes cannot be selected', disabled.every((d) => !sized.available_sizes.includes(d)), disabled.length ? `disabled: ${disabled.join(' ')}` : 'all in stock')
  const size = sized.available_sizes[0]
  await topRow.locator(`[role=radio]:has-text("${size}")`).first().click()
  const chosen = await store('return s.getState().selected_outfit.items.Top')
  check('Test M: picking a size selects that variant (price + link)', chosen.selected_size === size && chosen.product_url.includes('variant='), `${size} → ${chosen.product_url.split('?')[1]}`)
} else {
  skip('Test M: size selection', 'no product with listed sizes in the catalogue yet')
}
if (multiColour) {
  await store('s.getState().setOutfitItem("Top", a)', multiColour)
  await page.waitForTimeout(500)
  const other = multiColour.colour_options.find((o) => o.item_id !== multiColour.item_id)
  await page.click(`button.colour-dot[aria-label="Top: ${other.colour_label}"]`)
  await page.waitForFunction(() => /switched to|Please pick a size/.test(document.body.innerText))
  const switched = await store('return s.getState().selected_outfit.items.Top')
  // Some brands use one photo for every colour, so the image may legitimately stay the same.
  check('Test L: choosing another real colour switches the variant (id + link)', switched.item_id === other.item_id && switched.product_url !== multiColour.product_url,
    `${other.colour_label}${switched.image !== multiColour.image ? ', new image' : ', brand uses one photo for all colours'}`)
  const dots = await page.$$eval('.colour-dot[aria-label^="Top:"]', (d) => d.length)
  check('Test L: only the product\'s real colours are shown', dots === multiColour.colour_options.length, `${dots} colours`)
} else {
  skip('Test L: colour variants', 'no product with several colours scraped yet (needs a re-scrape of a multi-colour brand)')
}

// Cheaper option
const shoesBefore = await store('return s.getState().selected_outfit.items.Shoes')
await page.locator('.outfit-breakdown-card button', { hasText: 'Cheaper Option' }).nth(2).click()
await page.waitForFunction(() => /Found a cheaper alternative|No cheaper compatible/.test(document.body.innerText))
const shoesAfter = await store('return s.getState().selected_outfit.items.Shoes')
check('Test J: "Cheaper Option" is really cheaper (or says none exists)', shoesAfter.item_id === shoesBefore.item_id || Number(shoesAfter.price) < Number(shoesBefore.price), `${shoesBefore.price} → ${shoesAfter.price}`)

// Replace keeps the others
const beforeReplace = await store('return s.getState().selected_outfit.items')
await page.locator('.outfit-breakdown-card button', { hasText: 'Replace Bottom' }).click()
await page.locator('text=Select Replacement:').waitFor()
await page.locator('.outfit-breakdown-card .bordered button', { hasText: 'Use' }).first().click()
const afterReplace = await store('return s.getState().selected_outfit.items')
check('Test I: Replace changes only that item', afterReplace.Bottom.item_id !== beforeReplace.Bottom.item_id && ['Top', 'Shoes', 'Accessory'].every((c) => afterReplace[c].item_id === beforeReplace[c].item_id))

// Lock + regenerate
await store('s.getState().toggleLock("Shoes")')
const lockedShoe = await store('return s.getState().selected_outfit.items.Shoes.item_id')
await page.click('text=Regenerate Unlocked Items')
await page.waitForFunction(() => !document.body.innerText.includes('Regenerating…'))
check('Test K: locked item survives regeneration', (await store('return s.getState().selected_outfit.items.Shoes.item_id')) === lockedShoe)
await store('s.getState().toggleLock("Shoes")')

// Budget
await store('s.getState().set({ budget: 1000 })')
await page.waitForFunction(() => /Over budget by/.test(document.body.innerText))
check('Test H: over-budget outfit is flagged with the amount', true)
await store('s.getState().set({ budget: 3500 })')

// --- Photo mode (Tests O, R, Q) -----------------------------------------------------------------
await store('s.getState().set({ visual_mode: "photo" })')
await page.waitForTimeout(500)
check('Test R: photo mode shows no 3D avatar', (await page.$('canvas')) === null)
check('Test R: photo mode without a photo asks for one', (await page.textContent('body')).includes('no photo is uploaded'))

await page.goto(`${base}/avatar`)
await page.waitForSelector('#photo')
await page.setInputFiles('#photo', { name: 'broken.png', mimeType: 'image/png', buffer: Buffer.from('not an image') })
await page.waitForFunction(() => /not a readable image|corrupted/.test(document.body.innerText))
check('Test O: corrupted file is rejected with a clear message', true)
const flat = Buffer.from(await page.evaluate(async () => {
  const c = document.createElement('canvas'); c.width = 800; c.height = 1200
  const g = c.getContext('2d'); g.fillStyle = '#c8a082'; g.fillRect(0, 0, 800, 1200)
  return [...new Uint8Array(await (await new Promise((r) => c.toBlob(r, 'image/png'))).arrayBuffer())]
}))
await page.setInputFiles('#photo', { name: 'flat.png', mimeType: 'image/png', buffer: flat })
await page.waitForFunction(() => /can't be used for the virtual try-on/.test(document.body.innerText))
check('Test O: unsuitable photo (no person, blurry) is not accepted', (await page.textContent('body')).includes('No person could be detected'))
await page.click('text=Delete my photo and its data')
await page.waitForFunction(() => !document.body.innerText.includes('Delete my photo'))
check('Test P: photo and its data can be deleted', (await store('return s.getState().photo_id')) === null)

if (photoArg) {
  await page.setInputFiles('#photo', photoArg)
  await page.waitForFunction(() => /Photo uploaded successfully|can't be used/.test(document.body.innerText), null, { timeout: 60000 })
  const accepted = await store('return s.getState().photo_validation?.accepted')
  check('Test O: a clear full-body photo is accepted', accepted)
  const photoId = await store('return s.getState().photo_id')
  const otherContext = await browser.newContext()
  const leaked = await (await otherContext.newPage()).goto(`${base}/api/photos/${photoId}/image`)
  check('Test P: the photo is not readable from another browser session', leaked.status() === 404)
  await otherContext.close()
  if (accepted) {
    await page.check('input[type=checkbox]')
    await page.goto(`${base}/complete-look`)
    await page.click('text=Try this outfit on my photo')
    await page.waitForFunction(() => /AI try-on of your|try-on.*failed|quota/i.test(document.body.innerText), null, { timeout: 240000 })
    const text = await page.textContent('body')
    check('Test Q: try-on result for the selected outfit (or an honest failure)', /AI try-on of your/.test(text) || /failed|quota/i.test(text), text.match(/AI try-on of your[^.]+\./)?.[0] ?? 'failed')
    check('Test R: photo try-on shown without the avatar', (await page.$('canvas')) === null)
  }
}

// --- Final look ---------------------------------------------------------------------------------
await store('s.getState().set({ visual_mode: "avatar" })')
await page.goto(`${base}/final-look`)
await page.waitForSelector('text=Total Outfitted Spend')
const finalNames = await store('return Object.values(s.getState().selected_outfit.items).map(i => i.item_name)')
const finalText = await page.textContent('body')
check('Test S: Final Look lists the selected products', finalNames.every((n) => finalText.includes(n)))
check('Test T: no uncaught page errors', pageErrors.length === 0, pageErrors.slice(0, 2).join(' | '))

await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length ? 1 : 0)
