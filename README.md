# STYLEAI — AI-Powered Personalized Outfit Recommendation and Virtual Styling System

A React + Three.js dashboard on top of the existing Python recommendation engine.

```
frontend/   React 19 + Vite + TypeScript + React Three Fiber (the new UI)
api/        FastAPI layer exposing the existing Python modules over HTTP
recommender.py, skin_tone.py, avatar_engine.py, demo_data.py, shopping/   existing backend (unchanged logic)
live_catalog/   real-time product catalogue scraped from brand storefronts (see below)
data/fashion_dataset.csv   original 50-item catalogue (offline fallback, tests, Streamlit app)
app.py, pages/, ui_theme.py   original Streamlit app (kept for comparison/rollback)
tests/      API tests (pytest)
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

- Python 3.10+ (tested with 3.12)
- Node.js 20+ (tested with 24) and npm

## Setup

```bash
# backend (from the repository root)
python -m pip install -r requirements.txt

# frontend
cd frontend
npm install
```

## Run (development)

Two terminals:

```bash
# 1) backend — from the repository root
python -m uvicorn api.main:app --reload --port 8000

# 2) frontend — from frontend/
npm run dev
```

Or both at once from `frontend/`: `npm run dev:all`.

Open http://localhost:5173. The Vite dev server proxies `/api/*` to the backend on port 8000.
API docs: http://localhost:8000/docs.

### Production build

```bash
cd frontend
npm run build          # type-checks and writes frontend/dist
npm run preview        # serves dist on http://localhost:4173 (still proxies /api to the backend)
```

When the frontend is hosted on a different origin from the API, set `VITE_API_BASE_URL` at build
time and add that origin to `STYLEAI_CORS_ORIGINS` on the backend.

### Legacy Streamlit app (unchanged, for comparison)

```bash
streamlit run app.py
```

## Live product catalogue (brand stores)

Recommended products are real, in-stock products scraped from Indian brand storefronts:
Snitch, Powerlook, Rare Rabbit / Rareism, Libas, Offduty, Bonkers Corner, Urban Monkey, Campus and
Red Tape (`live_catalog/brands.py`). All of them run on Shopify, whose public storefront feed
`/products.json` is read with `requests` (no paid scraping service, no API key, no headless browser);
product descriptions are parsed with BeautifulSoup.

- **Polite scraping:** robots.txt is checked for every site; requests go one at a time (4 s per site,
  3 s between any two requests); HTTP 429 backs off (honouring `Retry-After`) and retries.
- **Mapping:** each product becomes one row per in-stock colour in the recommender's schema
  (`category`, `item_name`, `colour`, `shade`, `style`, `occasion`, `price`, `image`), plus `brand`,
  `product_url`, `mrp`, `gender`, `fabric`, `fabric_tag`. Category, style, occasion, gender and fabric are
  inferred from the title, product type, tags and description (`live_catalog/normalize.py`). Colours
  are normalised to the palette names (e.g. "Navy Blue" -> Navy, "Wine" -> Burgundy). Dresses, sets,
  sarees, innerwear, crop tops and non-clothing items are skipped (no single outfit slot / professional look).
- **Freshness:** the snapshot `data/live_catalog.json` is refreshed in a background thread on startup
  per brand: a brand is re-scraped when its data is older than `STYLEAI_CATALOG_TTL_HOURS`, and each
  brand's products are saved as soon as it finishes. Requests never wait for scraping. A brand whose
  refresh fails keeps its previous products, is retried after `STYLEAI_CATALOG_RETRY_MINUTES`, and its
  error is shown in `/api/catalog/status`.
- **Gender:** Female profiles get women's + unisex products, Male profiles men's + unisex,
  Non-binary everything.
- **Fallback:** only before the very first successful scrape (e.g. offline first run) the bundled CSV
  is used; `/api/health` reports `catalog_source: "static-fallback"` until live data exists.
- **Cheaper alternatives:** the "Brand stores" shopping provider suggests cheaper, similar products
  from the live catalogue, with links to the brand's product page.

Refresh manually: `curl -X POST http://localhost:8000/api/catalog/refresh`, then check
`curl http://localhost:8000/api/catalog/status`.

## Environment variables

Backend (read by `api/` and `shopping/`; set in your shell or process manager, never in the frontend):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `STYLEAI_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins |
| `STYLEAI_CATALOG_SOURCE` | `live` | `static` uses `data/fashion_dataset.csv` instead of the scraped catalogue |
| `STYLEAI_CATALOG_TTL_HOURS` | `6` | Re-scrape the brand stores when the snapshot is older than this |
| `STYLEAI_CATALOG_RETRY_MINUTES` | `30` | Retry a brand whose scrape failed (usually rate limiting) after this long |
| `STYLEAI_CATALOG_BRANDS` | all | Comma-separated brand keys from `live_catalog/brands.py` to scrape |
| `STYLEAI_CATALOG_PER_BRAND_CATEGORY` | `80` | Newest products kept per brand and category |
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
| POST | `/api/catalog/refresh` | start a background re-scrape of the brand stores |
| GET | `/api/meta` | `demo_data` palettes, suggestion chips, fabric notes; `skin_tone.PALETTES`; score weights |
| GET | `/api/catalog` | all catalogue items (live products) |
| POST | `/api/recommendations` | `recommender.recommend_outfits(profile, locked_items, limit)` |
| POST | `/api/outfits/score` | `recommender.score_single_outfit` |
| POST | `/api/outfits/replacements` | `recommender.get_replacement_candidates` (top 3) |
| POST | `/api/outfits/cheaper` | `recommender.get_cheaper_alternative` |
| POST | `/api/outfits/regenerate` | `recommend_outfits` with locked items, `limit=1` |
| POST | `/api/shopping/alternatives` | `shopping.ShoppingService.find_cheaper_alternatives` |
| POST | `/api/skin-tone/analyze` | `skin_tone.estimate_skin_tone` (JPG/PNG upload, ≤10 MB) |
| POST | `/api/avatar/svg` | `avatar_engine.render_fashion_avatar_svg` (2D fallback when WebGL is unavailable) |
| GET | `/api/images/{file}` | product images from `images/`, `static/`, `data/` (same lookup as the Streamlit page) |

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
python -m pytest tests -q        # API tests (run on the static CSV) + offline live-catalogue tests
python test_recommender.py       # original recommender smoke script
cd frontend && npm run build     # type-check + production build
cd frontend && node scripts/render-avatar-thumbnails.mjs   # re-render studio thumbnails (dev server running)
cd frontend && node scripts/verify-avatar.mjs              # end-to-end avatar checks in headless Chrome (dev server running)
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
- **Colour changes are display-only.** The dataset has one colour per item, so "Preview colours on the
  avatar" recolours the 3D garment only; the recommended item, price and score are unchanged.
- **Product images:** live products show the brand's own product photo. The static fallback CSV
  references image files that are not in the repo, so its cards show generated placeholders.
- **Live catalogue:** categories, styles and occasions of scraped products are keyword inferences, not
  brand-supplied labels. Brands that are not on Shopify or block bots (Myntra, Ajio, ZARA, H&M,
  Bewakoof, FabIndia) are not scraped. Shopify rate-limits per IP, so a full refresh takes a few
  minutes and a brand can temporarily fail (its previous products are kept). Prices and stock are as
  of the last refresh. The legacy Streamlit app still uses the static CSV.
- **Shopping alternatives:** besides the live brand-store provider, only the Amazon provider has a live implementation; Flipkart, Meesho and
  Shopsy only return `[MOCK]` data when `USE_MOCK_SHOPPING_DATA=True`. With no provider configured, the
  page reports that no external alternatives were found.
- **Budget:** when no outfit fits the budget, `recommend_outfits` intentionally returns the cheapest
  of its top candidates instead (existing behaviour). The cheapest possible outfit in the dataset is ₹2,596.
- **Skin-tone detection** uses the upper-centre region of the photo as a rough face proxy
  (as documented in `skin_tone.py`); it is an estimate, applied only when the user confirms it.
- **"Analyze my style"** builds its style profile text from the selected style/occasion; the free-text
  preference is not parsed by the recommender (unchanged behaviour).
- Fit, fabric and brand preferences are stored but not used by the recommender (unchanged behaviour);
  colours to avoid **are** used.
- State lives in the browser session (`sessionStorage`); closing the tab resets it.
