import aiohttp
from datetime import datetime
from typing import Dict, Optional
import asyncio

class PriceFetcher:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_btc_price(self) -> Dict[str, float]:
        """Fetch current BTC price in USD asynchronously"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(f"{self.base_url}/simple/price?ids=bitcoin&vs_currencies=usd") as response:
                if response.status == 200:
                    data = await response.json()
                    return data["bitcoin"]
                else:
                    print(f"Error fetching price: HTTP {response.status}")
                    return {"usd": 0.0}
        except Exception as e:
            print(f"Error fetching price: {e}")
            return {"usd": 0.0}

    def calculate_price_change(self, current_price: float, previous_price: float) -> float:
        """Calculate percentage price change"""
        if previous_price == 0:
            return 0.0
        return ((current_price - previous_price) / previous_price) * 100

    async def get_btc_price_with_retry(self, max_retries: int = 3) -> Dict[str, float]:
        """Fetch BTC price with retry mechanism"""
        for attempt in range(max_retries):
            try:
                return await self.get_btc_price()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)  # Exponential backoff 