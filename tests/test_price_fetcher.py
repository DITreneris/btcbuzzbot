import pytest
import asyncio
from src.price_fetcher import PriceFetcher

@pytest.mark.asyncio
async def test_get_btc_price():
    async with PriceFetcher() as fetcher:
        price = await fetcher.get_btc_price()
        assert isinstance(price["usd"], float)
        assert price["usd"] > 0

@pytest.mark.asyncio
async def test_price_change_calculation():
    fetcher = PriceFetcher()
    # Test positive change
    assert fetcher.calculate_price_change(100, 80) == 25.0
    # Test negative change
    assert fetcher.calculate_price_change(80, 100) == -20.0
    # Test zero previous price
    assert fetcher.calculate_price_change(100, 0) == 0.0

@pytest.mark.asyncio
async def test_get_btc_price_with_retry():
    async with PriceFetcher() as fetcher:
        price = await fetcher.get_btc_price_with_retry()
        assert isinstance(price["usd"], float)
        assert price["usd"] > 0 