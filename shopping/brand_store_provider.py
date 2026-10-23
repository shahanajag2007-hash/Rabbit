"""Cheaper alternatives from the live brand-store catalogue (scraped, see live_catalog/)."""
from __future__ import annotations

import re
from typing import Callable, Optional

import pandas as pd

from .product_matcher import BaseShoppingProvider, SearchQuery, ShoppingAlternative

_STOP = {"men", "mens", "women", "womens", "the", "and", "with", "for", "fit", "regular", "slim", "relaxed"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", str(text).lower()) if len(w) > 2 and w not in _STOP}


class BrandStoreProvider(BaseShoppingProvider):
    def __init__(self, frame_getter: Callable[[], Optional[pd.DataFrame]]):
        self._frame_getter = frame_getter

    @property
    def name(self) -> str:
        return "Brand stores"

    def _frame(self) -> Optional[pd.DataFrame]:
        try:
            frame = self._frame_getter()
        except Exception:
            return None
        return frame if frame is not None and "product_url" in frame.columns else None

    def is_configured(self) -> bool:
        frame = self._frame()
        return frame is not None and not frame.empty

    def search_alternative(self, query: SearchQuery, max_price: float) -> Optional[ShoppingAlternative]:
        frame = self._frame()
        if frame is None or max_price <= 0:
            return None
        rows = frame[(frame["category"] == query.category) & (frame["price"] <= max_price)]
        if query.gender in ("Men", "Women") and "gender" in rows.columns:
            rows = rows[rows["gender"].isin([query.gender, "Unisex"])]
        if rows.empty:
            return None
        wanted = _words(query.item_name)
        styles = {s.strip().lower() for s in str(query.style).split("|") if s.strip()}
        colour = str(query.colour).lower()

        def score(row: pd.Series) -> float:
            value = 3.0 * len(wanted & _words(row["item_name"]))
            value += 3.0 if str(row["colour"]).lower() == colour else 0.0
            value += 1.0 * len(styles & {s.strip().lower() for s in str(row["style"]).split("|")})
            return value

        scored = rows.assign(_score=rows.apply(score, axis=1))
        # Must share the garment type (a title word) or the colour to count as an alternative.
        scored = scored[scored["_score"] >= 3.0]
        if scored.empty:
            return None
        best = scored.sort_values(["_score", "price"], ascending=[False, True]).iloc[0]
        alternative = ShoppingAlternative(
            platform=str(best.get("brand") or self.name),
            product_name=str(best["item_name"]),
            price=float(best["price"]),
            original_price=query.target_price,
            url=str(best.get("product_url") or ""),
            image=str(best.get("image") or ""),
        )
        same_colour = str(best["colour"]).lower() == colour
        alternative.match_type = "Same colour, similar style" if same_colour else "Similar style"
        return alternative
