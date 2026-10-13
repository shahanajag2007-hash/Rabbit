import os
from typing import Optional
from .product_matcher import BaseShoppingProvider, SearchQuery, ShoppingAlternative
import random

class MeeshoProvider(BaseShoppingProvider):
    @property
    def name(self) -> str:
        return "Meesho"
        
    def is_configured(self) -> bool:
        return bool(os.environ.get("MEESHO_API_KEY"))
        
    def search_alternative(self, query: SearchQuery, max_price: float) -> Optional[ShoppingAlternative]:
        if not self.is_configured() and os.environ.get("USE_MOCK_SHOPPING_DATA", "False").lower() == "true":
            if max_price > 0:
                mock_price = max_price * random.uniform(0.5, 0.85)
                return ShoppingAlternative(
                    platform=self.name,
                    product_name=f"[MOCK] {query.to_keywords()} (Meesho Value)",
                    price=mock_price,
                    original_price=query.target_price,
                    url=f"https://www.meesho.com/search?q={query.to_keywords().replace(' ', '%20')}",
                    image=""
                )
        return None
