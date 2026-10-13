from typing import Dict, List, Optional
import time

class SearchQuery:
    def __init__(self, item: Dict):
        self.category = item.get("category", "")
        self.item_name = item.get("item_name", "")
        self.colour = item.get("colour", "")
        self.style = item.get("style", "")
        self.occasion = item.get("occasion", "")
        self.target_price = float(item.get("price", 0))
        
    def to_keywords(self) -> str:
        # e.g. "White Casual Top"
        parts = []
        if self.colour:
            parts.append(self.colour)
        # Avoid putting too many styles into query
        primary_style = self.style.split("|")[0] if self.style else ""
        if primary_style:
            parts.append(primary_style)
        if self.item_name:
            parts.append(self.item_name)
        else:
            parts.append(self.category)
        return " ".join(parts).strip()


class ShoppingAlternative:
    def __init__(self, platform: str, product_name: str, price: float, original_price: float, url: str = "", image: str = ""):
        self.platform = platform
        self.product_name = product_name
        self.price = float(price)
        self.original_price = float(original_price)
        self.savings = max(0.0, self.original_price - self.price)
        self.url = url
        self.image = image
        self.timestamp = time.time()
        
        # Determine match type based on heuristics
        # If it's a mock or perfect match
        self.match_type = "Similar alternative" 
        
    def to_dict(self) -> Dict:
        return {
            "platform": self.platform,
            "product_name": self.product_name,
            "price": self.price,
            "original_price": self.original_price,
            "savings": self.savings,
            "url": self.url,
            "image": self.image,
            "match_type": self.match_type,
            "timestamp": self.timestamp
        }


class BaseShoppingProvider:
    @property
    def name(self) -> str:
        raise NotImplementedError
        
    def is_configured(self) -> bool:
        """Returns True if valid API credentials exist."""
        return False
        
    def search_alternative(self, query: SearchQuery, max_price: float) -> Optional[ShoppingAlternative]:
        """Search for a cheaper alternative up to max_price."""
        raise NotImplementedError
