"""Live product catalogue scraped from brand storefronts, cached on disk.

- ``LiveCatalog.frame()`` returns the current products as a DataFrame in the recommender's schema.
- A refresh runs in a background thread when the snapshot is older than the TTL; requests never
  wait for scraping. Each brand is refreshed independently: a brand that fails keeps its
  previous products.
- The snapshot (``data/live_catalog.json``, not in git) survives restarts. A fresh checkout starts
  from the committed seed (``data/live_catalog_seed.json``) and refreshes it in the background.
  Only when neither exists is the bundled CSV used, reported as ``source="static-fallback"``.
"""
from __future__ import annotations

import json
import re
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import pandas as pd

from .brands import BRANDS, Brand
from .fetcher import FetchError, PoliteFetcher, fetch_shopify_products, paused_for
from .garments import garment_type
from .imports import load_imports
from .normalize import _FABRIC_WORD, classify_category, classify_fit, classify_occasion, full_outfit_type, normalize_product

logger = logging.getLogger("styleai.live_catalog")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SNAPSHOT = ROOT / "data" / "live_catalog.json"
DEFAULT_SEED = ROOT / "data" / "live_catalog_seed.json"
# Raw storefront feeds (not in git): lets normalisation changes be re-applied without re-scraping.
DEFAULT_RAW_DIR = ROOT / "data" / "raw_catalog"
# Products from authorized feeds (affiliate exports etc.), see imports.py.
DEFAULT_IMPORT_DIR = ROOT / "data" / "imports"
# Background scraping from this machine. Off by default: Shopify rate-limits per IP, and a blocked IP
# also stops this network's browser from opening the product links. The shared catalogue is refreshed
# by the scheduled GitHub workflow (or `python -m live_catalog refresh`) and committed as the seed.
AUTO_REFRESH = os.environ.get("STYLEAI_CATALOG_AUTO_REFRESH", "false").strip().lower() in ("1", "true", "yes", "on")
REQUIRED_CATEGORIES = ("Top", "Bottom", "Shoes", "Accessory")
# A brand whose scrape failed (usually rate limiting) is retried after this many minutes.
RETRY_MINUTES = float(os.environ.get("STYLEAI_CATALOG_RETRY_MINUTES", "45"))
# Newest products per brand and category: keeps the catalogue balanced across brands and the
# recommender's per-request ranking fast.
PER_BRAND_CATEGORY_LIMIT = int(os.environ.get("STYLEAI_CATALOG_PER_BRAND_CATEGORY", "80"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _age_hours(stamp: Optional[str]) -> float:
    if not stamp:
        return float("inf")
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds() / 3600
    except ValueError:
        return float("inf")


def _limit_rows(rows: List[Dict]) -> List[Dict]:
    counts: Dict[str, int] = {}
    kept = []
    for row in rows:  # feeds are newest first
        key = row["category"]
        if counts.get(key, 0) < PER_BRAND_CATEGORY_LIMIT:
            counts[key] = counts.get(key, 0) + 1
            kept.append(row)
    return kept


def _reclassify(row: Dict) -> Optional[Dict]:
    """Re-apply the current category, occasion and fit rules to a stored row (snapshots outlive rule
    changes). Returns None for rows the current rules skip (e.g. sets)."""
    category = classify_category(str(row.get("item_name", "")), str(row.get("product_type", "")))
    if category is None:
        return None
    row["category"] = category
    full_type = full_outfit_type(str(row.get("item_name", "")), str(row.get("product_type", "")))
    row["subcategory"] = full_type or garment_type(category, str(row.get("item_name", "")), str(row.get("product_type", "")))
    row["covers_bottom"] = bool(full_type)
    text = f"{row.get('item_name', '')} {row.get('product_type', '')}"
    styles = [s for s in str(row.get("style") or "").split("|") if s]
    row["occasion"] = "|".join(classify_occasion(styles, text))
    if not row.get("fit"):
        row["fit"] = classify_fit(text)
    tag = str(row.get("fabric_tag") or "")
    if tag and (len(tag) > 40 or not _FABRIC_WORD.search(tag)):
        row["fabric"] = row["fabric_tag"] = None  # marketing copy saved by older rules
    elif tag:
        row["fabric_tag"] = re.sub(r"^(.+?)(?:[\s,]+\1)+$", r"\1", tag, flags=re.I)  # "Mesh Mesh" -> "Mesh"
    return row


def _with_colour_options(frame: pd.DataFrame) -> pd.DataFrame:
    """Each row lists the in-stock colours of its product (real variants, for colour previews)."""
    if "product_id" not in frame.columns:
        return frame
    options: Dict[str, List[Dict]] = {}
    for row in frame.itertuples(index=False):
        if isinstance(row.product_id, str):
            options.setdefault(row.product_id, []).append({
                "item_id": row.item_id,
                "colour": row.colour,
                "colour_label": getattr(row, "colour_label", None) or row.colour,
                "image": row.image,
                "price": float(row.price),
            })
    frame = frame.copy()
    frame["colour_options"] = [options.get(pid, []) if isinstance(pid, str) else [] for pid in frame["product_id"]]
    return frame


class LiveCatalog:
    def __init__(
        self,
        snapshot_path: Path = DEFAULT_SNAPSHOT,
        brands: Iterable[Brand] = BRANDS,
        ttl_hours: float = float(os.environ.get("STYLEAI_CATALOG_TTL_HOURS", "12")),
        fallback_loader: Optional[Callable[[], pd.DataFrame]] = None,
        fetcher_factory: Callable[[], PoliteFetcher] = PoliteFetcher,
        seed_path: Optional[Path] = None,
        raw_dir: Optional[Path] = None,
    ):
        selected = {key.strip() for key in os.environ.get("STYLEAI_CATALOG_BRANDS", "").split(",") if key.strip()}
        self.brands = [brand for brand in brands if not selected or brand.key in selected]
        self.snapshot_path = Path(snapshot_path)
        if seed_path is None and self.snapshot_path == DEFAULT_SNAPSHOT:
            seed_path = DEFAULT_SEED
        self.seed_path = Path(seed_path) if seed_path else None
        if raw_dir is None and self.snapshot_path == DEFAULT_SNAPSHOT:
            raw_dir = DEFAULT_RAW_DIR
        self.raw_dir = Path(raw_dir) if raw_dir else None
        self.import_dir: Optional[Path] = DEFAULT_IMPORT_DIR if self.snapshot_path == DEFAULT_SNAPSHOT else None
        self.import_report: Dict[str, Dict] = {}
        self.ttl_hours = ttl_hours
        self.fallback_loader = fallback_loader
        self._fetcher = fetcher_factory()  # one fetcher: shared spacing and cached robots.txt
        self._lock = threading.Lock()
        self._refreshing = threading.Event()
        self._snapshot: Dict = self._load_snapshot()
        self._frame: Optional[pd.DataFrame] = None
        self._frame_version = -1
        self._version = 0
        self._filtered: Dict[tuple, pd.DataFrame] = {}

    # -- snapshot ------------------------------------------------------------

    def _load_snapshot(self) -> Dict:
        for path in (self.snapshot_path, self.seed_path):
            if path is None:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data.get("brands"), dict):
                    if path == self.seed_path:
                        logger.info("No local catalogue yet; starting from the committed seed %s", path.name)
                    return data
            except FileNotFoundError:
                continue
            except (OSError, ValueError) as exc:
                logger.warning("Ignoring unreadable catalogue snapshot %s: %s", path, exc)
        return {"brands": {}, "refreshed_at": None}

    def _save_snapshot(self, snapshot: Dict) -> None:
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.snapshot_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.snapshot_path)

    def _rows(self) -> List[Dict]:
        rows = []
        for entry in self._snapshot["brands"].values():
            checked = entry.get("fetched_at")
            for row in entry.get("items", []):
                # Scraped rows: the URL is the store's canonical /products/<handle> page, seen in its feed.
                current = _reclassify({"link_type": "product", "source": entry.get("domain"), **row, "price_checked_at": checked})
                if current is not None:
                    rows.append(current)
        if self.import_dir is not None:
            imported, self.import_report = load_imports(self.import_dir)
            rows.extend(r for r in (_reclassify(row) for row in imported) if r is not None)
        return rows

    def has_live_data(self) -> bool:
        rows = self._rows()
        present = {row["category"] for row in rows}
        return bool(rows) and all(category in present for category in REQUIRED_CATEGORIES)

    # -- refresh ---------------------------------------------------------------

    def due_brands(self) -> List[Brand]:
        """Brands never scraped, older than the TTL, or failed more than RETRY_MINUTES ago."""
        due = []
        for brand in self.brands:
            entry = self._snapshot["brands"].get(brand.key, {})
            if entry.get("error") and _age_hours(entry.get("failed_at")) * 60 >= RETRY_MINUTES:
                due.append(brand)
            elif not entry.get("error") and _age_hours(entry.get("fetched_at")) >= self.ttl_hours:
                due.append(brand)
        return due

    def is_stale(self) -> bool:
        return bool(self.due_brands())

    def refresh_async(self, force: bool = False, only: Optional[Iterable[str]] = None) -> bool:
        """Start a background refresh of the due brands (all brands if forced, or just ``only`` brand
        keys) unless one is already running. Automatic (non-forced) refreshes only run when
        STYLEAI_CATALOG_AUTO_REFRESH is on."""
        if self._refreshing.is_set():
            return False
        if not force and not only and not AUTO_REFRESH:
            return False
        if only:
            keys = set(only)
            brands = [brand for brand in self.brands if brand.key in keys]
        else:
            brands = list(self.brands) if force else self.due_brands()
        if not brands:
            return False
        self._refreshing.set()
        threading.Thread(target=self._refresh_guarded, args=(brands,), name="live-catalog-refresh", daemon=True).start()
        return True

    def _refresh_guarded(self, brands: List[Brand]) -> None:
        try:
            self.refresh(brands)
        except Exception:  # pragma: no cover - never let the thread die noisily
            logger.exception("Live catalogue refresh failed")
        finally:
            self._refreshing.clear()

    def _save_raw(self, brand: Brand, products: List[Dict]) -> None:
        if self.raw_dir is None:
            return
        try:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
            (self.raw_dir / f"{brand.key}.json").write_text(json.dumps(products, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not cache raw feed for %s: %s", brand.name, exc)

    def _normalize(self, brand: Brand, products: List[Dict]) -> List[Dict]:
        rows: List[Dict] = []
        for product in products:
            try:
                rows.extend(normalize_product(product, brand.key, brand.name, brand.domain, brand.gender))
            except Exception as exc:  # one malformed product must not drop the brand
                logger.debug("%s: skipped product %s: %s", brand.name, product.get("id"), exc)
        return _limit_rows(rows)

    def rebuild_from_raw(self) -> Dict:
        """Re-normalise the cached raw feeds (no network), keeping each brand's fetch time."""
        if self.raw_dir is None:
            return self.status()
        with self._lock:
            brands = dict(self._snapshot.get("brands", {}))
        for brand in self.brands:
            path = self.raw_dir / f"{brand.key}.json"
            if not path.exists() or brand.key not in brands:
                continue
            rows = self._normalize(brand, json.loads(path.read_text(encoding="utf-8")))
            if rows:
                brands[brand.key] = {**brands[brand.key], "items": rows}
        with self._lock:
            self._snapshot = {**self._snapshot, "brands": brands}
            self._version += 1
            self._filtered.clear()
            snapshot = self._snapshot
        self._save_snapshot(snapshot)
        return self.status()

    def _scrape_brand(self, brand: Brand) -> Dict:
        started = time.monotonic()
        try:
            products = fetch_shopify_products(self._fetcher, brand.domain, brand.max_pages)
        except FetchError as exc:
            return {"ok": False, "error": str(exc)}
        self._save_raw(brand, products)
        rows = self._normalize(brand, products)
        logger.info("%s: %d products -> %d items in %.0fs", brand.name, len(products), len(rows), time.monotonic() - started)
        return {"ok": True, "items": rows, "products_seen": len(products)}

    def _commit(self, brand: Brand, result: Dict) -> None:
        """Swap one brand's result into the snapshot and save it (products appear as each brand finishes)."""
        with self._lock:
            brands = dict(self._snapshot.get("brands", {}))
            previous = brands.get(brand.key, {})
            if result["ok"] and result["items"]:
                brands[brand.key] = {
                    "name": brand.name,
                    "domain": brand.domain,
                    "fetched_at": _now(),
                    "products_seen": result["products_seen"],
                    "items": result["items"],
                    "error": None,
                }
            else:
                error = result.get("error") or "no usable products"
                brands[brand.key] = {**previous, "name": brand.name, "domain": brand.domain,
                                     "items": previous.get("items", []), "error": error, "failed_at": _now()}
                logger.warning("%s: refresh failed (%s); keeping %d previous items",
                               brand.name, error, len(previous.get("items", [])))
            snapshot = {"brands": brands, "refreshed_at": _now()}
            self._snapshot = snapshot
            self._version += 1
            self._filtered.clear()
        try:
            self._save_snapshot(snapshot)
        except OSError as exc:
            logger.warning("Could not save catalogue snapshot: %s", exc)

    def refresh(self, brands: Optional[Iterable[Brand]] = None) -> Dict:
        """Scrape the given brands (default: all), one after another through one polite fetcher."""
        for brand in list(brands) if brands is not None else self.brands:
            self._commit(brand, self._scrape_brand(brand))
        return self.status()

    # -- data ------------------------------------------------------------------

    def source(self) -> str:
        return "live" if self.has_live_data() else "static-fallback"

    def frame(self) -> pd.DataFrame:
        with self._lock:
            if self._frame is not None and self._frame_version == self._version:
                return self._frame
            if self.has_live_data():
                frame = pd.DataFrame(self._rows())
                frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
                frame = frame.dropna(subset=["price"]).drop_duplicates("item_id").reset_index(drop=True)
                frame = _with_colour_options(frame)
            elif self.fallback_loader is not None:
                frame = self.fallback_loader()
            else:
                raise RuntimeError("No live catalogue data yet and no fallback configured.")
            self._frame, self._frame_version = frame, self._version
            return frame

    def frame_for(self, gender: Optional[str]) -> pd.DataFrame:
        """Products for a profile gender (Female -> women's + unisex, Male -> men's + unisex).

        A category left empty by the filter keeps all of its products, so an outfit can always be built.
        """
        frame = self.frame()
        audience = {"female": "Women", "woman": "Women", "women": "Women",
                    "male": "Men", "man": "Men", "men": "Men"}.get(str(gender or "").strip().lower())
        if audience is None or "gender" not in frame.columns:
            return frame
        key = (self._frame_version, audience)
        with self._lock:
            cached = self._filtered.get(key)
        if cached is not None:
            return cached
        mask = frame["gender"].isin([audience, "Unisex"])
        parts = []
        for category, rows in frame.groupby("category", sort=False):
            matched = rows[mask.loc[rows.index]]
            parts.append(matched if not matched.empty else rows)
        filtered = pd.concat(parts).sort_index() if parts else frame
        with self._lock:
            self._filtered[key] = filtered
        return filtered

    def item(self, item_id: str) -> Optional[Dict]:
        """One catalogue row by id (any gender), or None."""
        frame = self.frame()
        match = frame[frame["item_id"].astype(str) == str(item_id)]
        return match.iloc[0].to_dict() if not match.empty else None

    def status(self) -> Dict:
        brands = {}
        for key, entry in self._snapshot.get("brands", {}).items():
            items = entry.get("items", [])
            counts: Dict[str, int] = {}
            for row in items:
                counts[row["category"]] = counts.get(row["category"], 0) + 1
            brands[key] = {
                "name": entry.get("name"),
                "domain": entry.get("domain"),
                "items": len(items),
                "by_category": counts,
                "fetched_at": entry.get("fetched_at"),
                "error": entry.get("error"),
            }
        return {
            "source": self.source(),
            "refreshed_at": self._snapshot.get("refreshed_at"),
            "ttl_hours": self.ttl_hours,
            "stale": self.is_stale(),
            "refreshing": self._refreshing.is_set(),
            "items": int(len(self.frame())) if (self.has_live_data() or self.fallback_loader) else 0,
            "brands": brands,
            "imports": self.import_report,
            "auto_refresh": AUTO_REFRESH,
            "rate_limit_pause_minutes": round(paused_for() / 60, 1),
        }
