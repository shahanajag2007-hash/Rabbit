# STYLEAI — handoff: current status and to-do (2026-10-24)

Read this first, then `README.md`. Everything below was tested unless marked **untested**.

## Ground rules (from the project owner)

- **Do not redesign or remove existing UI or features.** Make additive, targeted changes. Keep the six pages,
  the four Appearance fields, the three recommendation cards, the avatar and its hairstyles.
- **Never fake results:** no invented products, prices, links, sizes, colours or try-on images. If data is
  missing, show an honest note.
- **Do not scrape from your laptop in loops.** Shopify rate-limits per IP across *all* its stores; a blocked
  IP also stops that network's browser from opening product links. Use the GitHub workflow or one
  `python -m live_catalog refresh` at a time. Do not scrape Amazon / Flipkart / Myntra / AJIO / Tata CLiQ /
  Nykaa (terms / bot protection) — use `data/imports/` with authorized feeds.
- Secrets only in `.env` (git-ignored). `.env.example` lists every setting with placeholders.

## Run it

```bash
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cd frontend && npm install && npm run dev:all        # http://localhost:5173 , API docs http://localhost:8000/docs
```

No keys, model or scraping are needed: products come from the committed `data/live_catalog_seed.json`.
Tests: `python -m pytest tests -q` (62 pass), `cd frontend && npm run build && npm run lint`,
`cd frontend && node scripts/verify-journey.mjs` (end-to-end, app running; 39/39 passed).
After editing backend Python on Windows, restart `npm run dev:all` (uvicorn `--reload` can hang).

## Where things are

| Area | Files |
| --- | --- |
| Recommendation engine (rule-based) | `recommender.py` (filters → scores → combinations → diversity → reasons/notes), `preferences.py` (free-text parser) |
| Garment types + style rules | `live_catalog/garments.py` (Traditional / Formal allowed types, western exclusions) |
| Product catalogue | `live_catalog/` — `normalize.py` (Shopify → schema), `catalog.py` (snapshot, seed, imports), `brands.py`, `fetcher.py` (polite fetch + 429 circuit breaker), `imports.py`, `__main__.py` (CLI) |
| API | `api/main.py`, `api/photos.py` (private upload + MediaPipe validation), `api/tryon.py` (provider chain + cache), `api/settings.py` (.env) |
| Frontend | `frontend/src/hooks/useStyleStore.ts` (single shared state), `pages/RecommendationsPage.tsx`, `components/outfit/*` (ManualOutfitBuilder, PhotoTryOn, OutfitBreakdown…), `components/avatar/garmentMapping.ts` |
| Try-on worker (optional) | `tools/tryon-worker/` — CatVTON (CC BY-NC-SA, non-commercial), `server.py`, `masking.py`, `setup_worker.py`, `fetch_wheels.py` |
| Daily catalogue refresh | `.github/workflows/refresh-catalog.yml` |

## Done and tested

- Style is a hard constraint (Traditional never shows crop tops / jeans / sneakers; Formal never shows casual
  prints / sneakers); text exclusions ("no heels", "do not recommend crop tops") and "only <colour>" are filters.
- Kurta sets, sarees, lehengas, dresses, suits are full outfits (Top slot, no Bottom); avatar maps them.
- Missing stock → no outfit + a note naming the missing piece (style never silently relaxed).
- Diversity-aware top 3 (penalty for reusing products), colour families (Burgundy ≈ Maroon), truthful reasons.
- Try-on: provider chain `worker,huggingface` (+ `fashn`), content-hash cache, in-flight de-duplication,
  timeout, cancel, cache deleted with the photo. Tests use a fake provider (`tests/test_tryon.py`).
- Product links verified: 8/9 sampled brand links returned the real product page (1 delisted → fixed by refresh).
- Portability: `.env.example`, `.gitignore` for secrets/caches/uploads, README quick start + troubleshooting.

## To-do (in priority order)

1. **Push-triggered: run the GitHub workflow once.** Repository → Actions → "Refresh product catalogue" →
   Run workflow. It must have `contents: write` (already in the YAML). **Untested** until it runs on GitHub.
   It should add the 10 new ethnic brands to `data/live_catalog_seed.json` (they have 0 items now because
   Shopify kept rate-limiting the owner's IP).
2. **Check Traditional / Formal coverage after that refresh** with
   `python -m live_catalog status` and the Recommendations page (women's Traditional + Festival; men's
   Traditional; women's Formal). Today men's traditional bottoms and women's formal shoes are missing, so
   those combinations show a "catalogue has no …" note. If still missing, add brands in
   `live_catalog/brands.py` (check robots.txt allows `/products.json` first) or import a feed.
3. **Finish and test the self-hosted try-on worker** (`tools/tryon-worker`, **untested**). On the owner's laptop
   (Intel Arc iGPU, no NVIDIA) the PyTorch-XPU install and the 1.7 GB fp16 UNet download were interrupted.
   Easiest on a machine with an NVIDIA GPU: `cd tools/tryon-worker && python setup_worker.py --device cuda`,
   then `.venv\Scripts\python server.py`, check `http://127.0.0.1:8100/health` → `"ready": true`, set
   `STYLEAI_TRYON_PROVIDER=worker,huggingface` in `.env`, and try an outfit on the Complete Look page in photo
   mode. Report the seconds per image. Things to verify: the MediaPipe mask quality (`masking.py`), that
   sets/dresses use category `overall`, and that the result keeps the face/background. Slow network:
   `python setup_worker.py --resumable`.
4. **Hosted fallback:** create a free Hugging Face account token and put it in `.env` as `HF_TOKEN` to raise
   the IDM-VTON quota (tops only).
5. **Optional:** brand preferences in Appearance list ZARA/H&M etc., which are not in the catalogue — consider
   adding the scraped brand names to the options (keep the existing ones).
6. **Known noise:** MediaPipe prints a `TypeError` at interpreter exit after tests (harmless library bug).
   The Vite dev proxy stalls on responses over ~2 MB (only `/api/catalog`; the app does not use it).

## Copilot prompt to continue

> You are continuing the STYLEAI project (React + Vite + TypeScript frontend in `frontend/`, FastAPI backend in
> `api/`, rule-based recommender in `recommender.py`, product catalogue in `live_catalog/`). Read `HANDOFF.md`
> and `README.md` first. Rules: do not redesign or remove existing UI/features; make small additive changes;
> never invent products, links, prices, sizes or try-on images; never scrape in loops from a laptop
> (Shopify blocks the IP) and never scrape Amazon/Flipkart/Myntra/AJIO/Tata CLiQ/Nykaa; keep secrets in `.env`.
> Run `python -m pytest tests -q` and `cd frontend && npm run build` after every change.
> Next task: work through the "To-do" list in `HANDOFF.md` in order, starting with item <N>. Before editing,
> explain which files you will change and why; after editing, run the tests and report results honestly,
> including anything you could not test.
