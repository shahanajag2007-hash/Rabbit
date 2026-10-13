import os
import logging
from typing import Dict, List, Optional
from .product_matcher import SearchQuery, ShoppingAlternative, BaseShoppingProvider

# Import specific providers
from .amazon_provider import AmazonProvider
from .flipkart_provider import FlipkartProvider
from .meesho_provider import MeeshoProvider
from .shopsy_provider import ShopsyProvider

# Toggle for development testing
# USE_MOCK_SHOPPING_DATA is evaluated dynamically now

class ShoppingService:
    def __init__(self):
        self.providers: List[BaseShoppingProvider] = [
            AmazonProvider(),
            FlipkartProvider(),
            MeeshoProvider(),
            ShopsyProvider(),
        ]
        
    def find_cheaper_alternatives(self, original_outfit: Dict, budget: float, locked_categories: List[str]) -> Dict[str, Dict]:
        """
        Attempts to find a cheaper alternative for the given outfit without touching locked items.
        Returns a dictionary of category -> alternative dict.
        """
        total_price = sum(float(item["price"]) for item in original_outfit.get("items", {}).values())
        if total_price <= budget:
            return {} # Within budget, no need to optimize
            
        excess = total_price - budget
        
        # Sort unlocked items by price descending to try replacing the most expensive items first
        unlocked_items = []
        for cat, item in original_outfit.get("items", {}).items():
            if cat not in locked_categories:
                unlocked_items.append((cat, item))
                
        unlocked_items.sort(key=lambda x: float(x[1].get("price", 0)), reverse=True)
        
        alternatives = {}
        savings_achieved = 0.0
        
        for cat, item in unlocked_items:
            if savings_achieved >= excess:
                break # We've saved enough!
                
            query = SearchQuery(item)
            current_price = float(item.get("price", 0))
            
            # We want to save as much as we can, up to the remaining excess
            target_max_price = current_price - 1 # Must be at least slightly cheaper
            
            best_alt = None
            best_savings = 0.0
            
            for provider in self.providers:
                if not provider.is_configured() and os.environ.get("USE_MOCK_SHOPPING_DATA", "False").lower() != "true":
                    continue
                    
                try:
                    alt = provider.search_alternative(query, max_price=target_max_price)
                    if alt and alt.savings > best_savings:
                        best_alt = alt
                        best_savings = alt.savings
                except Exception as e:
                    logging.warning(f"Provider {provider.name} failed during search: {e}")
                    
            if best_alt:
                alternatives[cat] = best_alt.to_dict()
                savings_achieved += best_savings
                
        return alternatives
