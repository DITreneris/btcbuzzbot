import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.price_fetcher import PriceFetcher

@pytest.mark.asyncio
async def test_get_btc_price():
    # Mock the API response
    mock_response = {
        "bitcoin": {
            "usd": 50000.0,
            "usd_24h_change": 2.5
        }
    }
    
    with patch('src.price_fetcher.aiohttp.ClientSession.get') as mock_get:
        # Create a mock for the response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_resp.__aenter__.return_value = mock_resp
        mock_get.return_value = mock_resp
        
        async with PriceFetcher() as fetcher:
            price = await fetcher.get_btc_price()
            assert isinstance(price["usd"], float)
            assert price["usd"] == 50000.0
            assert price["usd_24h_change"] == 2.5

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
    # Mock the API response
    mock_response = {
        "bitcoin": {
            "usd": 50000.0,
            "usd_24h_change": 2.5
        }
    }
    
    with patch('src.price_fetcher.aiohttp.ClientSession.get') as mock_get:
        # Create a mock for the response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response
        mock_resp.__aenter__.return_value = mock_resp
        mock_get.return_value = mock_resp
        
        async with PriceFetcher() as fetcher:
            price = await fetcher.get_btc_price_with_retry()
            assert isinstance(price["usd"], float)
            assert price["usd"] == 50000.0
            assert price["usd_24h_change"] == 2.5

@pytest.mark.asyncio
async def test_get_btc_price_retry_on_error():
    """Test that the retry mechanism works when initial requests fail"""
    
    # Mock get_btc_price to fail once then succeed
    with patch.object(PriceFetcher, 'get_btc_price') as mock_get_price:
        # Set up side effects: first call raises exception, second returns valid data
        mock_get_price.side_effect = [
            Exception("API error"),  # First call raises exception
            {"usd": 50000.0, "usd_24h_change": 2.5}  # Second call returns valid data
        ]
        
        # Patch sleep to avoid actual waiting in the test
        with patch('asyncio.sleep', return_value=None):
            async with PriceFetcher() as fetcher:
                price = await fetcher.get_btc_price_with_retry(max_retries=3)
                assert isinstance(price["usd"], float)
                assert price["usd"] == 50000.0
                assert price["usd_24h_change"] == 2.5
                
                # Verify get_btc_price was called twice (1 fail + 1 success)
                assert mock_get_price.call_count == 2 