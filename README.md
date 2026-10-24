# STYLEAI — AI-Powered Personalized Outfit Recommendation and Virtual Styling System

A React + Three.js dashboard on top of the existing Python recommendation engine.

```
frontend/   React 19 + Vite + TypeScript + React Three Fiber (the new UI)
api/        FastAPI layer exposing the existing Python modules over HTTP
recommender.py, preferences.py   recommendation engine + free-text request parser
skin_tone.py, avatar_engine.py, demo_data.py, shopping/   original backend modules
live_catalog/   product catalogue: brand-store scraper, garment types / style rules, imports, CLI
data/live_catalog_seed.json   committed product catalogue (refreshed daily by GitHub Actions)
data/fashion_dataset.csv   original 50-item catalogue (tests, Streamlit app)
models/     MediaPipe pose model for photo validation (Apache-2.0)
tools/tryon-worker/   optional open-source try-on worker (CatVTON; non-commercial licence)
app.py, pages/, ui_theme.py   original Streamlit app (kept for comparison/rollback)
tests/      backend tests (pytest)
```

## The six-page dashboard

| # | Page | Route | Contains |
| - | ---- | ----- | -------- |
| 1 | Profile | `/profile` | Name, age, gender, height, weight, budget slider + budget card |
| 2 | Appearance | `/appearance` | 4 substeps: skin tone, favourite colours, style, occasion · optional *Fine-Tune Style Signals* (fit, fabrics, colours to avoid, brands) |
| 3 | Avatar | `/avatar` | Photo upload (with skin-tone analysis) **or** avatar studio with live 3D preview · saved looks / identities |
| 4 | Recommendations | `/recommendations` | **Protected Recommended Outfit page** — preference analysis, colour palette, 3 recommended outfits |
| 5 | Complete Look | `/complete-look` | 3D outfit preview, item breakdown (remove / replace / cheaper / lock), budget & alternatives, regenerate, why-this-outfit, fabric details |
| 6 | Final Look | `/final-look` | Final 3D look, summary, restart / modify |

## Requirements

- Python 3.10–3.12 (tested with 3.12) and pip
- Node.js 20+ (tested with 24) and npm
- Git. Nothing machine-specific: all paths are relative to the repository.
- Optional, only for photo try-on on your own hardware: see [tools/tryon-worker](tools/tryon-worker/README.md).

## Quick start (after cloning)

```bash
# 1. backend dependencies (from the repository root; a virtual environment is recommended)
python -m venv .venv
.venv\Scripts\activate            # macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt

# 2. frontend dependencies
cd frontend
npm install

# 3. (optional) local settings — every value has a working default
cd ..
copy .env.example .env            # macOS / Linux: cp .env.example .env

# 4. run backend + frontend together (from frontend/)
cd frontend
npm run dev:all
```

Open http://localhost:5173 (API docs: http://localhost:8000/docs). Products come from the committed
catalogue (`data/live_catalog_seed.json`), so no scraping, API keys or AI model are needed to use and test
profiles, recommendations, the outfit builder, Complete Look, the avatar and photo validation. Photo
try-on shows a clear "not configured" message until a try-on provider is set up (see below).

Two terminals instead of `dev:all`: `python -m uvicorn api.main:app --port 8000` (repository root) and
`npm run dev` (in `frontend/`).

### Tests

```bash
python -m pytest tests -q                    # backend: recommender, style rules, catalogue, photos, try-on caching (offline)
cd frontend && npm run build                 # type-check + production build
cd frontend && npm run lint                  # oxlint
cd frontend && node scripts/verify-journey.mjs   # end-to-end in headless Chrome (app running)
```

### Production build

```bash
cd frontend
npm run build          # type-checks and writes frontend/dist
npm run preview        # serves dist on http://localhost:4173 (still proxies /api to the backend)
```

When the frontend is hosted on a different origin from the API, set `VITE_API_BASE_URL` at build
time and add that origin to `STYLEAI_CORS_ORIGINS` on the backend. Authenticated photo/try-on
requests use credentialed CORS; for deployments on different sites, configure HTTPS and set
`STYLEAI_COOKIE_SAMESITE=none` and `STYLEAI_COOKIE_SECURE=true`.

### Legacy Streamlit app (unchanged, for comparison)

```bash
streamlit run app.py
```

## How it fits together

```
Profile + Appearance + text request + palette pick  (frontend/src/hooks/useStyleStore.ts — one shared store)
        │  POST /api/recommendations, /api/builder/options, /api/palette   (frontend/src/services/api.ts)
        ▼
api/main.py ── recommender.py ── preferences.py (text request)      ── live_catalog/garments.py (garment types,
        │       hard filters → item scores → outfit combinations          style rules)
        │       → budget → diversity-aware top 3 → reasons / notes
        ▼
live_catalog/ (product catalogue: committed seed + optional refresh + data/imports/)
        │
Complete Look / Final Look ── avatar (frontend/src/components/avatar) or photo try-on
                               api/photos.py (private upload + validation) → api/tryon.py (providers + cache)
```

- **Recommendation engine** (`recommender.py`, rule-based, no ML): the chosen style is a requirement.
  Traditional only allows ethnic garment types (kurtas, kurta sets, sarees, palazzos, salwars, juttis,
  jhumkas…), Formal only formal ones, and western styles exclude ethnic-only pieces. Explicit text
  requests ("only black", "no heels", "do not recommend crop tops") are filters too; favourite colours,
  palette picks, fit, fabrics and brands rank. When the catalogue cannot satisfy a requirement the page
  says so instead of relaxing it. The three outfits are picked with a diversity penalty for reusing the
  same products. Full outfits (kurta sets, sarees, dresses, suits) fill the Top slot and need no bottom.
- **Catalogue** (`live_catalog/`): normalised products with category, garment type, style, occasion, colour,
  sizes, variants, price, image, product URL, brand and source.
- **Try-on** (`api/tryon.py`): provider-independent; see below.

## Product catalogue

Products are real, in-stock items from Indian brand storefronts on Shopify (`live_catalog/brands.py`):
western/casual (Snitch, Powerlook, Rare Rabbit, Offduty, Bonkers Corner, Urban Monkey, Campus, Red Tape) and
ethnic/traditional wear (Libas, Janasya, Bunaai, Suta, Okhai, Vastramay, Kisah, Sojanya, Fizzy Goblet,
Needledust, Giva). Each store's robots.txt allows its public `/products.json` feed, which is read with
`requests` + BeautifulSoup (no paid service, no headless browser).

- **Shared, committed catalogue:** `data/live_catalog_seed.json` is what everyone runs on. The scheduled
  GitHub workflow `.github/workflows/refresh-catalog.yml` re-scrapes daily from GitHub's servers and commits
  it; teammates get it with `git pull`. Run it by hand from the repository's **Actions** tab.
- **Why not scrape from our laptops by default:** Shopify rate-limits per IP across all its stores. When a
  home or college network scrapes too much, Shopify blocks that IP for a while — and then the *browsers* on
  that network cannot open the product links either. Local background refresh is therefore off
  (`STYLEAI_CATALOG_AUTO_REFRESH=false`); after a 429 every store fetch pauses for 20 minutes.
- **Manual refresh / checks** (from the repository root):
  `python -m live_catalog status`, `python -m live_catalog refresh [--brand KEY] [--write-seed]`,
  `python -m live_catalog check-links` (opens a few product links per brand; 429/blocked = inconclusive).
- **Marketplaces (Amazon, Flipkart, Myntra, AJIO, Tata CLiQ, Nykaa Fashion)** are not scraped: their terms
  prohibit it or they block automated access. Their products can be added from authorized affiliate /
  partner exports through **`data/imports/`** (JSON or CSV; schema and validation in
  `live_catalog/imports.py`). `link_type: "search"` marks retailer search links, shown as "Search on …".
- **Links:** scraped products link to the store's canonical `/products/<handle>` page (and the chosen
  variant), seen in the store's own feed at refresh time. Only https links on the brands' own domains are
  shown. Prices and stock are as of the last refresh (shown on Complete Look).
- **Gender:** Female → women's + unisex, Male → men's + unisex, Non-binary → everything.

## Photo try-on providers

Set `STYLEAI_TRYON_PROVIDER` in `.env` to a fallback chain; the first one that can run is used:

| Provider | What it is | Cost / limits | Renders |
| --- | --- | --- | --- |
| `worker` | Open-source CatVTON on your own hardware ([tools/tryon-worker](tools/tryon-worker/README.md)), local or on a teammate's GPU machine via `STYLEAI_TRYON_WORKER_URL` | No per-image fee or quota; needs ~7 GB disk, a GPU for good speed; **non-commercial licence** | top, bottom, sets/dresses |
| `huggingface` | IDM-VTON Space on Hugging Face (`STYLEAI_TRYON_SPACE`, or any compatible Gradio URL) | Free shared GPU with a small daily quota (a few images); a free `HF_TOKEN` raises it; non-commercial licence | top only |
| `fashn` | FASHN API | Paid per image (`FASHN_API_KEY`) | top, bottom, one-pieces |
| `none` | Disabled | — | — |

Try-ons only run when the user clicks **Try this outfit on my photo** (after consenting). Results are
cached by a hash of the photo content + garments + provider/model + parameters in `var/tryon-cache/`
(private, git-ignored, deleted with the photo): the same photo and outfit never run the model twice, even
after re-uploading, and identical requests in flight share one job. Jobs time out
(`STYLEAI_TRYON_TIMEOUT`), can be cancelled, and failures are shown as failures — never as a fake image.

## Troubleshooting

- **Product links show "429 Too Many Requests" or don't load:** your network's IP is rate-limited by
  Shopify (usually from scraping). Wait an hour or so; keep `STYLEAI_CATALOG_AUTO_REFRESH=false`.
- **"Cannot reach the STYLEAI backend" / 502:** the backend is not running or port 8000 is taken by an
  old process. Stop it (`netstat -ano | findstr :8000` then end that PID) and start `npm run dev:all` again.
- **Backend changes not picked up:** with this uvicorn version on Windows, `--reload` can hang after a Python
  file changes; restart `npm run dev:all`.
- **Photo checks say "unavailable":** `mediapipe` did not install; re-run `pip install -r requirements.txt`.
- **Try-on "not configured":** start the worker (`tools/tryon-worker`) or set `HF_TOKEN` for the hosted
  Space; the provider status is at http://localhost:8000/api/tryon/provider.
- **`pip check` reports huggingface-hub conflicts:** keep `gradio_client<2` (it pins huggingface-hub < 1.0,
  which transformers needs).
- **TLS / certificate errors when fetching** (antivirus or corporate proxy): `truststore` (in
  requirements) makes Python use the OS certificate store.

## Environment variables

Backend (read by `api/`, `live_catalog/` and `shopping/`). Put them in `.env` (copy `.env.example`; git-ignored)
or set them in your shell — real environment variables win. Never in the frontend:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `STYLEAI_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins |
| `STYLEAI_CATALOG_SOURCE` | `live` | `static` uses `data/fashion_dataset.csv` instead of the scraped catalogue |
| `STYLEAI_CATALOG_AUTO_REFRESH` | `false` | Scrape the brand stores from this machine in the background (see *Product catalogue*) |
| `STYLEAI_CATALOG_TTL_HOURS` | `12` | With auto refresh: re-scrape a brand when its data is older than this |
| `STYLEAI_CATALOG_RETRY_MINUTES` | `45` | With auto refresh: retry a brand whose scrape failed after this long |
| `STYLEAI_RATE_LIMIT_PAUSE_MINUTES` | `20` | Pause all store fetches after a 429 |
| `STYLEAI_CATALOG_BRANDS` | all | Comma-separated brand keys from `live_catalog/brands.py` to scrape |
| `STYLEAI_CATALOG_PER_BRAND_CATEGORY` | `80` | Newest products kept per brand and category |
| `STYLEAI_TRYON_PROVIDER` | `worker,huggingface` | Try-on provider chain, e.g. `worker,huggingface` (see *Photo try-on providers*) |
| `STYLEAI_TRYON_WORKER_URL` | `http://127.0.0.1:8100` | Where the open-source try-on worker runs |
| `STYLEAI_TRYON_TIMEOUT` | `420` | Seconds before a try-on is stopped |
| `HF_TOKEN` | — | Optional Hugging Face token: larger free GPU quota for the `huggingface` try-on |
| `STYLEAI_TRYON_SPACE` | `yisol/IDM-VTON` | Hugging Face Space used by the `huggingface` try-on |
| `FASHN_API_KEY` | — | Required for `STYLEAI_TRYON_PROVIDER=fashn` |
| `FASHN_API_URL` | `https://api.fashn.ai/v1` | FASHN-compatible API base URL (backend only) |
| `STYLEAI_COOKIE_SAMESITE` | `lax` | Private photo-session cookie policy; use `none` for a cross-site frontend/API deployment |
| `STYLEAI_COOKIE_SECURE` | `false` | Set `true` with HTTPS when using `STYLEAI_COOKIE_SAMESITE=none` |
| `USE_MOCK_SHOPPING_DATA` | `False` | `True` makes the shopping providers return clearly marked `[MOCK]` alternatives (the old Streamlit Customize page forced this on) |
| `AMAZON_CREDENTIAL_ID`, `AMAZON_CREDENTIAL_SECRET`, `AMAZON_PARTNER_TAG`, `AMAZON_MARKETPLACE` | — | Amazon Creators API (falls back to `.streamlit/secrets.toml` `[amazon]` if unset) |
| `FLIPKART_AFFILIATE_ID`, `MEESHO_API_KEY`, `SHOPSY_API_KEY` | — | Mark those providers as configured (their live search is not implemented yet — see Limitations) |

Frontend (`frontend/.env.local`, see `frontend/.env.example`): `VITE_API_BASE_URL` (empty in dev),
`STYLEAI_BACKEND_URL` (dev/preview proxy target). Only `VITE_*` values reach the browser; no secrets are used there.

## API

| Method | Path | Wraps |
| ------ | ---- | ----- |
| GET | `/api/health` | dataset load check (+ `catalog_source`: `live` / `static-fallback` / `static`) |
| GET | `/api/catalog/status` | live catalogue: last refresh, items per brand/category, scrape errors |
| POST | `/api/catalog/refresh?brand=` | start a background re-scrape of the brand stores (all, or one brand key) |
| GET | `/api/meta` | `demo_data` palettes, suggestion chips, fabric notes; `skin_tone.PALETTES`; score weights |
| GET | `/api/catalog` | all catalogue items (live products) |
| POST | `/api/recommendations` | `recommender.recommend_with_notes(profile, locked_items, limit)` → outfits (with reasons), notes, what the text request was understood as |
| POST | `/api/preferences/parse` | `preferences.parse_preferences` (rule-based reading of the free-text request) |
| POST | `/api/palette` | `recommender.colour_palette` — profile colours that real products are available in |
| POST | `/api/builder/options` | `recommender.builder_options` — one step of "Choose Your Style Manually" |
| GET | `/api/products/{item_id}` | a product with its real variants (sizes, prices, links) and colours |
| GET | `/api/size-hint` | `recommender.size_hint` — rough letter size from height/weight (labelled approximate) |
| POST | `/api/outfits/score` | `recommender.score_single_outfit` |
| POST | `/api/outfits/replacements` | `recommender.get_replacement_candidates` (top 3) |
| POST | `/api/outfits/cheaper` | `recommender.get_cheaper_alternative` (strictly cheaper; uses the profile and the rest of the outfit when sent) |
| POST | `/api/outfits/regenerate` | `recommend_with_notes` with locked items, `limit=1`, excluding the current outfit |
| POST | `/api/shopping/alternatives` | `shopping.ShoppingService.find_cheaper_alternatives` |
| POST | `/api/skin-tone/analyze` | `skin_tone.estimate_skin_tone` (JPG/PNG upload, ≤10 MB) |
| POST | `/api/avatar/svg` | `avatar_engine.render_fashion_avatar_svg` (2D fallback when WebGL is unavailable) |
| GET | `/api/images/{file}` | product images from `images/`, `static/`, `data/` (same lookup as the Streamlit page) |
| POST | `/api/photos` | upload + validate a full-body photo (private to the browser session) |
| GET / DELETE | `/api/photos/{id}`, `/api/photos/{id}/image` | validation result / the photo (session only) / delete photo + derived data + try-ons |
| GET | `/api/tryon/provider` | configured virtual try-on provider and what it can render |
| POST | `/api/tryon` | start a try-on of the selected outfit on the photo (requires `consent: true`) |
| GET | `/api/tryon/{photo}/{job}`, `.../image` | try-on status / result image (session only) |

## Personalised recommendations

One rule-based engine (`recommender.py`, no machine learning) serves every page. It uses:

- **Profile:** budget (hard limit for the whole outfit), gender (product filter), **age** (under-18s never
  get adult-oriented items; a gentle age/style affinity that never overrides the user's own choices),
  height and weight (only for a rough, clearly labelled size guide — never fit claims).
- **The four Appearance steps:** skin-tone palette, favourite colours (exact shades first, related shades
  such as Burgundy for Maroon next), style and occasion. **The style is a requirement**: Traditional and
  Formal allow only their garment types (`live_catalog/garments.py`), western styles exclude ethnic-only
  pieces; occasion and colours rank within that.
- **Fine-tune signals:** preferred fit (matched against the product's stated fit), fabrics, brands, and
  "styles & tones to avoid" (Overly Bright / Pastels rank lower, Neon names are excluded, Clashing Tones
  penalises clashing pairs, Dense Layering penalises layered tops).
- **The free-text request** (`preferences.py`, rule-based): style, occasion, colours ("navy", "neutral
  colours"), negations ("no black"), per-garment fit ("oversized tops with straight-fit jeans"), fabrics,
  and budgets ("under 2,500", "₹3k", "affordable"). A style in the request replaces the profile style for
  that search. Exclusions ("no heels", "do not recommend crop tops") and "only …" colours are filters, not
  preferences. The page shows exactly what was understood.
- **The palette:** colours from the skin tone, favourites and style that real products exist in (with
  counts); clicking one prioritises it.

Pipeline: hard filters (style rules, exclusions, avoided / required colours, age) → item scores (colour 30,
style 20, occasion 20) → best + cheaper candidates → every combination within budget (full outfits such as
kurta sets, sarees or dresses take no bottom; an outfit may have no accessory) scored with compatibility (15)
and budget (15) → diversity-aware top 3 (each pick is penalised for reusing products already shown) →
truthful reasons per outfit, and notes when something can't be met. If the catalogue has nothing for a
required piece (e.g. no traditional footwear) no outfit is shown and the note says what is missing —
the style is never silently relaxed.

**Choose Your Style Manually** (below the three outfits) builds an outfit step by step — top, bottom,
shoes, optional accessory — each step ranking products that go with the earlier picks and fit the budget
left; changing an earlier pick keeps later ones unless the budget no longer allows them.

**Complete Look:** real sizes (sold-out sizes disabled; the chosen size sets the variant's price and link),
the product's real in-stock colours under "Preview colours" (switching changes the item, image, price and
link), product links, Replace / Cheaper Option (always strictly cheaper) / Lock (kept through Regenerate),
and budget totals with the time prices were last checked.

## Photo mode and virtual try-on

- **Upload** (Avatar page → Upload your photo): JPG/PNG/WebP up to 10 MB. The server decodes and
  re-encodes it (EXIF/GPS removed), stores it under `var/uploads/` (not served publicly, not in git) for
  that browser session only (random HttpOnly cookie), and it can be deleted with its derived data.
- **Validation** (local, `api/photos.py`): resolution, sharpness, lighting, and with the MediaPipe Pose model
  (`models/pose_landmarker_lite.task`, Apache-2.0) exactly one person, head-to-feet visible and large
  enough in frame. Unsuitable photos are rejected with the reason. Derived data: pose keypoints, a
  shoulder/hip ratio and a face-region skin-tone estimate (no face embeddings, no identification).
- **Try-on** (`api/tryon.py`): with explicit consent, the photo and the selected products' images are sent
  to the configured provider (see *Photo try-on providers*). Results are cached by photo content and outfit,
  private, and deleted with the photo.
- Complete Look and Final Look show **either** the photo try-on (photo mode) **or** the 3D avatar
  (avatar mode), never both.

## 3D avatar and Avatar Studio

The avatar is a **realistic, textured human** built from the CC0 MakeHuman system assets and CC0 asset
packs with MPFB2 in Blender: female- and male-presenting body models with face, eyes, eyebrows, eyelashes,
teeth, hair, beards, fitted clothing and shoes. Assets live in `frontend/public/models/avatar/`; licence, layout and the
rebuild pipeline (`tools/avatar-pipeline/`) are documented in
[frontend/public/models/README.md](frontend/public/models/README.md).

- **Three base models** built separately: female-presenting, male-presenting and androgynous (MakeHuman
  gender 0.5). The profile gender picks the model; Non-binary starts on the androgynous model and is asked
  to choose. Each model has its own body presets and default hair/brows; hair and clothing list the model's
  own collection first, with every other compatible style under "More styles".
- **Initialised from the profile:** height drives MakeHuman's height morph (natural proportions) and the
  stature is calibrated exactly, against a fixed height scale in the viewer; height + weight blend the
  lighter/heavier body presets (an appearance approximation the user can override); age blends MakeHuman's
  age morphs from teen (14) to 85 and, from 30, adds wrinkle detail derived from MakeHuman's aged skins
  (can be switched off); skin comes from the profile skin tone.
- **Skin tone has one source of truth: the profile** (`skin_tone` for the recommender plus `skin_shade` for
  the finer avatar shade). Picking a shade in the studio updates the profile tone; changing the tone on the
  Appearance page updates the avatar. A tone detected from a photo is stored separately (`skin_tone_detected`).
- **Default outfit per model:** a casual starter outfit (fitted tee + jeans for female-presenting, crew tee +
  chinos-style trousers for male-presenting); switching the model loads that model's defaults automatically.
- **Avatar Studio categories:** Appearance (body model, pose, eye colour), Face (face shape, eye shape, nose,
  lips, 12 eyebrow styles, 4 beards/moustache), Hairstyle (~50 styles incl. an Indian collection, 12 colours),
  Skin Tone (9 tones), Body Type (5), Clothing (T-shirts, polos, casual tops, formal shirts & blouses, sweaters,
  dresses, suits, traditional-style tunic / harem pants / long skirt / kimono, jeans, formal and casual trousers,
  shorts, skirts, outerwear; men's or women's styles listed first), Footwear (8), Accessories (jewellery,
  eyewear, watch, bags, belt, fedora; several can be worn at once). Every option card shows a thumbnail rendered from the real asset.
- Face shapes and body types are **morph targets baked in Blender**; every garment and hair mesh was
  re-fitted for each one, so clothes follow the body without stretching the face or hands.
- The configuration is stored with asset IDs (`avatar_config` in session state) and can be saved per occasion.
- **Avatar clothing is visualisation only.** It never changes the recommended outfit, product selection,
  ranking or shopping results (separate `avatar_config` vs `recommended_outfits` / `selected_outfit` state).
  A banner at the top of the Avatar Studio explains this.
- **Complete Look / Final Look** show the same avatar wearing the backend's recommended outfit: each item is
  mapped to the closest real 3D garment and tinted with the item's colour. Approximations are listed under the viewer.
- The viewer has full-body framing, Front/Side/Back/360° views, drag-rotate, zoom buttons and a reset.
- If WebGL is unavailable, the original 2D SVG avatar from `avatar_engine.py` is shown.

## Tests

```bash
python -m pytest tests -q        # API, personalisation, photo and live-catalogue tests (offline)
python test_recommender.py       # original recommender smoke script
cd frontend && npm run build     # type-check + production build
cd frontend && node scripts/render-avatar-thumbnails.mjs   # re-render studio thumbnails (dev server running)
cd frontend && node scripts/verify-avatar.mjs              # end-to-end avatar checks in headless Chrome (dev server running)
cd frontend && node scripts/verify-journey.mjs             # profile → recommendations → builder → complete look → photo checks
cd frontend && node scripts/verify-journey.mjs --photo=PATH  # same, plus a real photo upload and AI try-on (sends PATH to the provider)
```

## Limitations

- **Avatar assets are limited to CC0 MakeHuman assets.** No CC0 hoodie, long coat, saree, sherwani, sandals
  or stubble exists, so those options are shown disabled. The traditional-style items are the closest CC0
  garments (a long tunic, harem pants, a long full skirt, a kimono), labelled as such, not authentic kurtas
  or lehengas. Garments are shared between the three models (each re-fitted to the model).
- **Body presets, height proportions and age shaping are appearance approximations** (MakeHuman morphs), not
  measurements. Recommended items without a matching 3D garment (for example chinos, loafers) are shown as the
  closest available garment in the item's colour, with a note under the viewer.
- **Layering** of independently fitted garments is corrected in real time (`layerFit.ts`); small specks can
  remain for very baggy bottoms under fitted tops (e.g. harem pants under the sweater).
- **Asset size:** each model folder is ~80 MB (every mesh carries body, face, height and age morphs); only
  the parts being worn are downloaded (about 15 MB for a first view).
- **Accessories** (glasses, jewellery, watch, bags, belt) are simple modelled meshes attached to measured body
  points, not scanned products.
- **Garments are static fits**, not cloth simulation; the avatar is posed but not animated.
- **Colours and sizes come from the brands' variants.** Products scraped before the variant update (and
  brands that list each colour as a separate product) show a single colour; sizes appear once a brand has
  been re-scraped. The original CSV items have neither.
- **Product images:** live products show the brand's own product photo. The static fallback CSV
  references image files that are not in the repo, so its cards show generated placeholders.
- **Live catalogue:** categories, garment types, styles and occasions of scraped products are keyword
  inferences, not brand-supplied labels. Marketplaces (Amazon, Flipkart, Myntra, AJIO, Tata CLiQ, Nykaa)
  are not scraped; use `data/imports/` with authorized feeds. Shopify rate-limits per IP, so refreshes are
  slow and brands can temporarily fail (previous products are kept); new brands appear once a refresh
  succeeds (GitHub workflow). Prices and stock are as of the last refresh. The Streamlit app uses the CSV.
- **Shopping alternatives:** besides the live brand-store provider, only the Amazon provider has a live implementation; Flipkart, Meesho and
  Shopsy only return `[MOCK]` data when `USE_MOCK_SHOPPING_DATA=True`. With no provider configured, the
  page reports that no external alternatives were found.
- **Budget:** when no outfit fits the budget, the cheapest real combinations are shown, marked "over
  budget", with a note giving the cheapest possible total.
- **Recommendations are rule-based**, not machine learning; the text request is read with keyword rules
  (no LLM), so unusual phrasing may not be picked up — the page shows what was understood.
- **Catalogue coverage limits results:** e.g. traditional or formal outfits need ethnic / formal stock
  (bottoms, footwear) from the newly added brands; until their first successful refresh the page says
  which piece is missing instead of substituting western items.
- **Size guide** is a rough letter size from height/weight, not a brand size chart or a fit prediction.
- **Photo validation** needs the MediaPipe package; without it photos are not accepted for try-on (the
  check is reported as unavailable). Skin tone from the face area is an estimate, applied only on request.
- **Virtual try-on:** the hosted Hugging Face quota is small (a few images a day; `HF_TOKEN` raises it) and
  that model renders tops only; the self-hosted worker has no quota but needs suitable hardware and is
  slow without an NVIDIA GPU. Both are non-commercial models. They approximate fabric and fit, do not
  simulate the chosen size, and identity preservation is good but not guaranteed. No similarity score is
  shown because none is measured. Products without a brand photo (the CSV items) can't be tried on.
- **Photo privacy** is per browser session (no accounts): anyone using the same browser profile shares it.
- **Backend auto-reload:** with this uvicorn version on Windows, `--reload` can hang after a Python file
  changes (also on the original code); restart `npm run dev:all` after backend edits.
- State lives in the browser session (`sessionStorage`); closing the tab resets it.
