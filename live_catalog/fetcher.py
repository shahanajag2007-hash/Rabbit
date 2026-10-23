"""Polite HTTP fetching for brand storefronts.

- robots.txt is honoured (cached per domain);
- requests are spaced out: ``MIN_INTERVAL`` seconds per domain and ``GLOBAL_INTERVAL`` seconds
  between any two requests (Shopify rate-limits per client IP across all of its stores);
- HTTP 429 / connection resets back off (``Retry-After`` when given) and retry a few times.
"""
from __future__ import annotations

import logging
import threading
import time
import urllib.robotparser
from typing import Dict, List, Optional

import requests

try:  # Use the OS certificate store (fixes TLS errors behind antivirus/corporate proxies).
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover - optional dependency
    pass

logger = logging.getLogger("styleai.live_catalog")

USER_AGENT = "Mozilla/5.0 (compatible; StyleAIBot/1.0; outfit recommender catalogue refresh)"
MIN_INTERVAL = 4.0
GLOBAL_INTERVAL = 3.0
MAX_RETRIES = 2  # a throttled brand is retried by the next refresh instead
MAX_BACKOFF = 90.0
TIMEOUT = 30


class FetchError(Exception):
    pass


class PoliteFetcher:
    def __init__(self, min_interval: float = MIN_INTERVAL, max_retries: int = MAX_RETRIES,
                 global_interval: float = GLOBAL_INTERVAL):
        self.min_interval = min_interval
        self.global_interval = global_interval
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self._robots: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}
        self._last_request: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _wait_turn(self, domain: str) -> None:
        with self._lock:
            now = time.monotonic()
            slot = max(
                now,
                self._last_request.get(domain, float("-inf")) + self.min_interval,
                self._last_request.get("*", float("-inf")) + self.global_interval,
            )
            self._last_request[domain] = self._last_request["*"] = slot
        if slot > now:
            time.sleep(slot - now)

    def allowed(self, domain: str, path: str) -> bool:
        if domain not in self._robots:
            parser: Optional[urllib.robotparser.RobotFileParser] = urllib.robotparser.RobotFileParser()
            try:
                self._wait_turn(domain)
                response = self.session.get(f"https://{domain}/robots.txt", timeout=TIMEOUT)
                if response.status_code >= 400:
                    parser = None  # no robots.txt: everything allowed
                else:
                    parser.parse(response.text.splitlines())
            except requests.RequestException as exc:
                raise FetchError(f"robots.txt unavailable: {exc}") from exc
            self._robots[domain] = parser
        parser = self._robots[domain]
        return parser is None or parser.can_fetch(USER_AGENT, f"https://{domain}{path}")

    def get_json(self, domain: str, path: str) -> Dict:
        if not self.allowed(domain, path):
            raise FetchError(f"robots.txt disallows {path}")
        url = f"https://{domain}{path}"
        last_error = ""
        for attempt in range(self.max_retries + 1):
            self._wait_turn(domain)
            try:
                response = self.session.get(url, timeout=TIMEOUT)
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}"
                backoff = min(MAX_BACKOFF, 10.0 * (attempt + 1))
            else:
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise FetchError("response is not JSON") from exc
                if response.status_code not in (429, 502, 503, 504):
                    raise FetchError(f"HTTP {response.status_code}")
                last_error = f"HTTP {response.status_code}"
                retry_after = response.headers.get("Retry-After", "")
                backoff = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else 15.0 * (attempt + 1)
                backoff = min(MAX_BACKOFF, backoff)
            if attempt < self.max_retries:
                logger.info("%s: %s, retrying in %.0fs", url, last_error, backoff)
                time.sleep(backoff)
        raise FetchError(f"{last_error} after {self.max_retries + 1} attempts")


def fetch_shopify_products(fetcher: PoliteFetcher, domain: str, max_pages: int) -> List[Dict]:
    """All products from a Shopify storefront feed, newest first (250 per page)."""
    products: List[Dict] = []
    for page in range(1, max_pages + 1):
        try:
            batch = fetcher.get_json(domain, f"/products.json?limit=250&page={page}").get("products", [])
        except FetchError:
            if products:  # keep what we already have from earlier pages
                logger.warning("%s: page %d failed, keeping %d products", domain, page, len(products))
                break
            raise
        products.extend(batch)
        if len(batch) < 250:
            break
    return products
