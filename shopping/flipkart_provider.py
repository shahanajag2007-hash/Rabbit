import os
from typing import Optional
from .product_matcher import BaseShoppingProvider, SearchQuery, ShoppingAlternative
import random

class FlipkartProvider(BaseShoppingProvider):
    @property
    def name(self) -> str:
        return "Flipkart"
        
    def is_configured(self) -> bool:
        return bool(os.environ.get("FLIPKART_AFFILIATE_ID"))
        
    def search_alternative(self, query: SearchQuery, max_price: float) -> Optional[ShoppingAlternative]:
        if not self.is_configured() and os.environ.get("USE_MOCK_SHOPPING_DATA", "False").lower() == "true":
            if max_price > 0:
                mock_price = max_price * random.uniform(0.65, 0.90)
                return ShoppingAlternative(
                    platform=self.name,
                    product_name=f"[MOCK] {query.to_keywords()} (Flipkart Match)",
                    price=mock_price,
                    original_price=query.target_price,
                    url=f"https://www.flipkart.com/search?q={query.to_keywords().replace(' ', '+')}",
                    image=""
                )
        return None
