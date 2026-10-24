"""The API tests compare against the bundled CSV, so they run with the static catalogue.
Live-catalogue behaviour is tested offline in test_live_catalog.py."""
import os

os.environ.setdefault("STYLEAI_CATALOG_SOURCE", "static")
os.environ.setdefault("STYLEAI_SKIP_DOTENV", "1")  # never pick up a developer's .env in tests
