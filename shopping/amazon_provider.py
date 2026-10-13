import os
import json
import time
import logging
import requests
from typing import Optional, Dict
from .product_matcher import BaseShoppingProvider, SearchQuery, ShoppingAlternative
import random

class AmazonProvider(BaseShoppingProvider):
    def __init__(self):
        self._access_token = None
        self._token_expiry = 0

        # Load configuration safely: environment variables first (FastAPI backend),
        # then Streamlit secrets (legacy Streamlit frontend).
        self.config = {}
        env_config = {
            "credential_id": os.environ.get("AMAZON_CREDENTIAL_ID"),
            "credential_secret": os.environ.get("AMAZON_CREDENTIAL_SECRET"),
            "marketplace": os.environ.get("AMAZON_MARKETPLACE"),
            "partner_tag": os.environ.get("AMAZON_PARTNER_TAG"),
        }
        if env_config["credential_id"] and env_config["credential_secret"]:
            self.config = {key: value for key, value in env_config.items() if value}
        else:
            try:
                import streamlit as st

                if "amazon" in st.secrets:
                    self.config = st.secrets["amazon"]
            except Exception:
                pass
            
    @property
    def name(self) -> str:
        return "Amazon"
        
    def is_configured(self) -> bool:
        return bool(self.config.get("credential_id") and self.config.get("credential_secret"))
        
    def _get_access_token(self) -> Optional[str]:
        """Obtain OAuth 2.0 client-credentials token."""
        if not self.is_configured():
            return None
            
        current_time = time.time()
        if self._access_token and current_time < self._token_expiry:
            return self._access_token
            
        client_id = self.config.get("credential_id")
        client_secret = self.config.get("credential_secret")
        
        try:
            response = requests.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "amazon::creatorsapi"
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                # Cache token until 5 minutes before expiration
                self._token_expiry = current_time + expires_in - 300
                return self._access_token
            else:
                logging.error(f"Amazon Creators API auth failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Amazon API token request error: {str(e)}")
            return None
            
    def _search_live(self, query: SearchQuery) -> Optional[Dict]:
        """Execute SearchItems against Creators API."""
        token = self._get_access_token()
        if not token:
            return None
            
        marketplace = self.config.get("marketplace", "www.amazon.in")
        partner_tag = self.config.get("partner_tag", "")
        
        url = f"https://api.{marketplace}/creators-api/v1/searchitems"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "Keywords": query.to_keywords(),
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "ItemCount": 3,
            "Resources": [
                "Images.Primary.Medium",
                "ItemInfo.Title",
                "ItemInfo.Features",
                "Offers.Listings.Price"
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            
            if response.status_code == 429:
                logging.warning("Amazon API rate limit exceeded.")
                return None
            elif response.status_code in [401, 403]:
                logging.error(f"Amazon API auth/access denied: {response.status_code}")
                return None
            elif response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Amazon API unexpected error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Amazon SearchItems request error: {str(e)}")
            return None
            
    def search_alternative(self, query: SearchQuery, max_price: float) -> Optional[ShoppingAlternative]:
        if not self.is_configured():
            if os.environ.get("USE_MOCK_SHOPPING_DATA", "False").lower() == "true":
                # Mock behavior
                if max_price > 0:
                    mock_price = max_price * random.uniform(0.7, 0.95)
                    return ShoppingAlternative(
                        platform=self.name,
                        product_name=f"[MOCK] {query.to_keywords()} (Amazon Edition)",
                        price=mock_price,
                        original_price=query.target_price,
                        url=f"https://www.amazon.in/s?k={query.to_keywords().replace(' ', '+')}",
                        image=""
                    )
            return None
            
        # LIVE API LOGIC
        data = self._search_live(query)
        if not data:
            return None
            
        # Safely map response fields
        try:
            items = data.get("SearchResult", {}).get("Items", [])
            for item in items:
                title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue")
                url = item.get("DetailPageURL")
                image = item.get("Images", {}).get("Primary", {}).get("Medium", {}).get("URL", "")
                
                # Check price
                listings = item.get("Offers", {}).get("Listings", [])
                if not listings:
                    continue
                    
                price_info = listings[0].get("Price", {})
                amount = price_info.get("Amount")
                
                if amount and amount <= max_price:
                    return ShoppingAlternative(
                        platform=self.name,
                        product_name=title or f"Amazon Product ({item.get('ASIN', 'Unknown')})",
                        price=amount,
                        original_price=query.target_price,
                        url=url or f"https://www.amazon.in/dp/{item.get('ASIN')}",
                        image=image
                    )
                    
        except Exception as e:
            logging.error(f"Amazon response mapping error: {str(e)}")
            
        return None
