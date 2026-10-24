"""Catalogue maintenance from the command line (run from the repository root).

    python -m live_catalog status                     # products per brand, last refresh, errors
    python -m live_catalog refresh [--brand KEY ...]  # scrape now (politely; stops on rate limiting)
    python -m live_catalog refresh --write-seed       # ... and copy the result to data/live_catalog_seed.json
    python -m live_catalog check-links [--sample 3]   # open a few product links per brand and report

The scheduled GitHub workflow (.github/workflows/refresh-catalog.yml) runs `refresh --write-seed` and
commits the seed, so teammates get fresh products with `git pull` without scraping from their own network.
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from collections import defaultdict

import requests

from api.settings import load_env

load_env()

from .catalog import DEFAULT_SEED, DEFAULT_SNAPSHOT, LiveCatalog  # noqa: E402
from .fetcher import paused_for  # noqa: E402

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"


def _status(catalog: LiveCatalog) -> None:
    status = catalog.status()
    print(f"source={status['source']} items={status['items']} refreshed_at={status['refreshed_at']} "
          f"auto_refresh={status['auto_refresh']} paused_min={status['rate_limit_pause_minutes']}")
    for key, brand in status["brands"].items():
        print(f"  {brand['name']:<16} {brand['items']:>4} items  fetched={brand['fetched_at']}  error={brand['error']}")
    for name, report in status["imports"].items():
        print(f"  import {name}: {report}")


def _check_links(catalog: LiveCatalog, sample: int) -> int:
    """Open a few product URLs per source. 200 = page served; 404 = broken; 429 / blocked = inconclusive."""
    frame = catalog.frame()
    by_source = defaultdict(list)
    for row in frame.to_dict(orient="records"):
        if row.get("product_url"):
            by_source[row.get("brand")].append(row)
    report, broken = {}, 0
    for brand, rows in by_source.items():
        results = []
        for row in rows[:sample]:
            try:
                response = requests.get(row["product_url"], headers={"User-Agent": BROWSER_UA}, timeout=20, allow_redirects=True, stream=True)
                status = response.status_code
                response.close()
            except requests.RequestException as exc:
                status = type(exc).__name__
            verdict = "ok" if status == 200 else "broken" if status in (404, 410) else "inconclusive"
            broken += verdict == "broken"
            results.append({"url": row["product_url"], "status": status, "verdict": verdict, "link_type": row.get("link_type")})
            print(f"  {verdict:<12} {status!s:<16} {brand}: {row['product_url']}")
            if status == 429:
                print("  rate-limited: stopping the link check (results so far are kept)")
                report[brand] = results
                return broken
            time.sleep(6)
        report[brand] = results
    with open("data/link_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(f"{broken} broken links; report in data/link_report.json")
    return broken


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m live_catalog")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    refresh = sub.add_parser("refresh")
    refresh.add_argument("--brand", action="append", help="brand key from live_catalog/brands.py (repeatable)")
    refresh.add_argument("--write-seed", action="store_true", help="copy the result to data/live_catalog_seed.json")
    refresh.add_argument("--wait-on-limit", action="store_true", help="wait out rate-limit pauses and continue (for CI)")
    refresh.add_argument("--max-wait-minutes", type=float, default=150, help="give up waiting after this long")
    links = sub.add_parser("check-links")
    links.add_argument("--sample", type=int, default=3)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    catalog = LiveCatalog()
    if args.command == "status":
        _status(catalog)
        return 0
    if args.command == "refresh":
        brands = [b for b in catalog.brands if not args.brand or b.key in args.brand]
        deadline = time.time() + args.max_wait_minutes * 60
        while brands:
            catalog.refresh(brands)
            # Brands stopped by the shared rate-limit pause (not by a real error) are retried after it.
            brands = [b for b in brands if "rate-limited" in str(catalog.status()["brands"].get(b.key, {}).get("error") or "")]
            if not brands or not args.wait_on_limit or time.time() + paused_for() > deadline:
                break
            wait = paused_for() + 5
            print(f"Rate-limited: waiting {wait / 60:.0f} min, then continuing with {len(brands)} brand(s) ...", flush=True)
            time.sleep(wait)
        _status(catalog)
        if args.write_seed and DEFAULT_SNAPSHOT.exists():
            shutil.copy(DEFAULT_SNAPSHOT, DEFAULT_SEED)
            print(f"seed updated: {DEFAULT_SEED}")
        return 0
    return 1 if _check_links(catalog, args.sample) else 0


if __name__ == "__main__":
    sys.exit(main())
