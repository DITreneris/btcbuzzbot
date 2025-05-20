import pytest
import os
import sys
import asyncio
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, call

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.main import post_btc_update, post_direct_tweet

class TestMain:
    """Test suite for the main module"""
    
    @pytest.fixture
    def mock_price_data(self):
        """Mock price data for tests"""
        return {
            "usd": 50000.0,
            "usd_24h_change": 1.5
        }
    
    @pytest.fixture
    def mock_latest_price_data(self):
        """Mock latest price data from database"""
        return {
            "price": 49000.0,
            "timestamp": datetime.now().isoformat()
        }
    
    @pytest.fixture
    def mock_content(self):
        """Mock content for tests"""
        return {
            "id": 1,
            "text": "HODL to the moon! 🚀",
            "type": "quote",
            "category": "motivational"
        }
    
    @pytest.fixture
    def mock_config(self):
        """Mock Config object"""
        config = MagicMock()
        config.sqlite_db_path = "test.db"
        config.coingecko_retry_limit = 3
        config.twitter_api_key = "test_key"
        config.twitter_api_secret = "test_secret"
        config.twitter_access_token = "test_token"
        config.twitter_access_token_secret = "test_token_secret"
        config.enable_discord_posting = True
        config.discord_webhook_url = "https://discord.webhook/test"
        return config
    
    # ------ Test post_btc_update function ------
    @pytest.mark.asyncio
    async def test_post_btc_update_basic(self, mock_config, mock_price_data, mock_latest_price_data, mock_content):
        """Test basic successful tweet posting via post_btc_update"""
        
        # Mock all dependencies
        with patch('src.main.Database') as mock_db_class, \
             patch('src.main.NewsRepository') as mock_news_repo_class, \
             patch('src.main.ContentManager') as mock_content_manager_class, \
             patch('src.main.PriceFetcher') as mock_price_fetcher_class, \
             patch('src.main.TwitterClient') as mock_twitter_class, \
             patch('src.main.send_discord_message') as mock_discord, \
             patch('src.main.Config', return_value=mock_config):
            
            # Configure mocks
            mock_db = AsyncMock()
            mock_db.get_latest_price.return_value = mock_latest_price_data
            mock_db.store_price.return_value = True
            mock_db.has_posted_recently.return_value = False
            mock_db.log_post.return_value = True
            mock_db_class.return_value = mock_db
            
            mock_news_repo = AsyncMock()
            mock_news_repo.get_recent_analyzed_news.return_value = []
            mock_news_repo_class.return_value = mock_news_repo
            
            mock_content_manager = AsyncMock()
            mock_content_manager.get_random_content.return_value = mock_content
            mock_content_manager_class.return_value = mock_content_manager
            
            mock_price_fetcher = AsyncMock()
            mock_price_fetcher.__aenter__.return_value = mock_price_fetcher
            mock_price_fetcher.__aexit__.return_value = None
            mock_price_fetcher.get_btc_price_with_retry.return_value = mock_price_data
            mock_price_fetcher.calculate_price_change.return_value = 2.04  # Calculated price change
            mock_price_fetcher_class.return_value = mock_price_fetcher
            
            mock_twitter = AsyncMock()
            expected_tweet_id = "123456789"
            mock_twitter.post_tweet.return_value = expected_tweet_id
            mock_twitter_class.return_value = mock_twitter
            
            # Call the function with a scheduled time
            result = await post_btc_update(config=mock_config, scheduled_time_str="08:00")
            
            # Assertions
            assert result == expected_tweet_id
            
            # Verify price fetching
            assert mock_price_fetcher.get_btc_price_with_retry.called
            
            # Verify database operations
            mock_db.get_latest_price.assert_called_once()
            mock_db.store_price.assert_called_once_with(mock_price_data["usd"])
            mock_db.has_posted_recently.assert_called_once()
            mock_db.log_post.assert_called_once()
            
            # Verify content fetching - should use random content since no news
            mock_content_manager.get_random_content.assert_called_once()
            
            # Verify tweet posting - content should include price and quote
            call_args = mock_twitter.post_tweet.call_args[0]
            tweet_text = call_args[0]
            assert "$50,000.00" in tweet_text  # Formatted price
            assert mock_content["text"] in tweet_text  # Quote text
            assert "📈" in tweet_text  # Up emoji for positive change
            
            # Verify Discord posting
            assert mock_discord.called
            discord_args = mock_discord.call_args[0]
            assert mock_config.discord_webhook_url == discord_args[0]
            assert "$50,000.00" in discord_args[1]  # Same content sent to Discord
    
    @pytest.mark.asyncio
    async def test_post_btc_update_with_news(self, mock_config, mock_price_data, mock_latest_price_data):
        """Test posting a tweet with significant news summary"""
        
        # Create mock news data with high significance
        mock_news = [{
            'original_tweet_id': '123456789',
            'llm_raw_analysis': json.dumps({
                'significance_score': 8,  # High significance
                'sentiment_score': 7,
                'summary': 'Bitcoin adoption surges as major retailer announces integration.',
                'keywords': ['bitcoin', 'adoption', 'retail']
            })
        }]
        
        # Mock all dependencies
        with patch('src.main.Database') as mock_db_class, \
             patch('src.main.NewsRepository') as mock_news_repo_class, \
             patch('src.main.ContentManager') as mock_content_manager_class, \
             patch('src.main.PriceFetcher') as mock_price_fetcher_class, \
             patch('src.main.TwitterClient') as mock_twitter_class, \
             patch('src.main.send_discord_message') as mock_discord, \
             patch('src.main.Config', return_value=mock_config):
            
            # Configure mocks
            mock_db = AsyncMock()
            mock_db.get_latest_price.return_value = mock_latest_price_data
            mock_db.store_price.return_value = True
            mock_db.has_posted_recently.return_value = False
            mock_db.log_post.return_value = True
            mock_db_class.return_value = mock_db
            
            mock_news_repo = AsyncMock()
            mock_news_repo.get_recent_analyzed_news.return_value = mock_news
            mock_news_repo_class.return_value = mock_news_repo
            
            # Content manager should not be used due to significant news
            mock_content_manager = AsyncMock()
            mock_content_manager_class.return_value = mock_content_manager
            
            mock_price_fetcher = AsyncMock()
            mock_price_fetcher.__aenter__.return_value = mock_price_fetcher
            mock_price_fetcher.__aexit__.return_value = None
            mock_price_fetcher.get_btc_price_with_retry.return_value = mock_price_data
            mock_price_fetcher.calculate_price_change.return_value = 2.04
            mock_price_fetcher_class.return_value = mock_price_fetcher
            
            mock_twitter = AsyncMock()
            expected_tweet_id = "123456789"
            mock_twitter.post_tweet.return_value = expected_tweet_id
            mock_twitter_class.return_value = mock_twitter
            
            # Call the function
            result = await post_btc_update(config=mock_config, scheduled_time_str="12:00")
            
            # Assertions
            assert result == expected_tweet_id
            
            # Verify content handling - should use news, not random content
            mock_content_manager.get_random_content.assert_not_called()
            
            # Verify news repository was queried
            mock_news_repo.get_recent_analyzed_news.assert_called_once()
            
            # Verify tweet posting - content should include news summary
            call_args = mock_twitter.post_tweet.call_args[0]
            tweet_text = call_args[0]
            assert "$50,000.00" in tweet_text  # Formatted price
            assert "Bitcoin adoption surges" in tweet_text  # News summary
            assert "#Bitcoin #News" in tweet_text  # News hashtags
    
    @pytest.mark.asyncio
    async def test_post_btc_update_negative_price_change(self, mock_config, mock_price_data, mock_latest_price_data, mock_content):
        """Test tweet posting with negative price change"""
        
        # Adjust price data for negative change
        mock_price_data["usd"] = 48000.0  # Lower than latest price
        
        # Mock all dependencies
        with patch('src.main.Database') as mock_db_class, \
             patch('src.main.NewsRepository') as mock_news_repo_class, \
             patch('src.main.ContentManager') as mock_content_manager_class, \
             patch('src.main.PriceFetcher') as mock_price_fetcher_class, \
             patch('src.main.TwitterClient') as mock_twitter_class, \
             patch('src.main.send_discord_message') as mock_discord, \
             patch('src.main.Config', return_value=mock_config):
            
            # Configure mocks
            mock_db = AsyncMock()
            mock_db.get_latest_price.return_value = mock_latest_price_data
            mock_db.store_price.return_value = True
            mock_db.has_posted_recently.return_value = False
            mock_db.log_post.return_value = True
            mock_db_class.return_value = mock_db
            
            mock_news_repo = AsyncMock()
            mock_news_repo.get_recent_analyzed_news.return_value = []
            mock_news_repo_class.return_value = mock_news_repo
            
            mock_content_manager = AsyncMock()
            mock_content_manager.get_random_content.return_value = mock_content
            mock_content_manager_class.return_value = mock_content_manager
            
            mock_price_fetcher = AsyncMock()
            mock_price_fetcher.__aenter__.return_value = mock_price_fetcher
            mock_price_fetcher.__aexit__.return_value = None
            mock_price_fetcher.get_btc_price_with_retry.return_value = mock_price_data
            mock_price_fetcher.calculate_price_change.return_value = -2.04  # Negative price change
            mock_price_fetcher_class.return_value = mock_price_fetcher
            
            mock_twitter = AsyncMock()
            expected_tweet_id = "123456789"
            mock_twitter.post_tweet.return_value = expected_tweet_id
            mock_twitter_class.return_value = mock_twitter
            
            # Call the function
            result = await post_btc_update(config=mock_config, scheduled_time_str="16:00")
            
            # Assertions
            assert result == expected_tweet_id
            
            # Verify tweet posting - check for down emoji
            call_args = mock_twitter.post_tweet.call_args[0]
            tweet_text = call_args[0]
            assert "$48,000.00" in tweet_text  # Formatted price
            assert "-2.04%" in tweet_text  # Negative percentage
            assert "📉" in tweet_text  # Down emoji for negative change
    
    @pytest.mark.asyncio
    async def test_post_btc_update_recent_post_skip(self, mock_config, mock_price_data):
        """Test skipping post when recent post exists"""
        
        # Mock all dependencies
        with patch('src.main.Database') as mock_db_class, \
             patch('src.main.NewsRepository') as mock_news_repo_class, \
             patch('src.main.ContentManager') as mock_content_manager_class, \
             patch('src.main.PriceFetcher') as mock_price_fetcher_class, \
             patch('src.main.TwitterClient') as mock_twitter_class, \
             patch('src.main.Config', return_value=mock_config):
            
            # Configure mocks - set has_posted_recently to True
            mock_db = AsyncMock()
            mock_db.has_posted_recently.return_value = True  # Recent post exists
            mock_db_class.return_value = mock_db
            
            # These should be created but not used much
            mock_news_repo_class.return_value = AsyncMock()
            mock_content_manager_class.return_value = AsyncMock()
            mock_price_fetcher_class.return_value = AsyncMock()
            mock_twitter_class.return_value = AsyncMock()
            
            # Call the function
            result = await post_btc_update(config=mock_config, scheduled_time_str="20:00")
            
            # Should return None since posting was skipped
            assert result is None
            
            # Verify database check
            mock_db.has_posted_recently.assert_called_once()
            
            # Twitter client post_tweet should not be called
            twitter_instance = mock_twitter_class.return_value
            twitter_instance.post_tweet.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_post_direct_tweet(self, mock_price_data):
        """Test direct tweet posting (fallback functionality)"""
        
        # Mock all dependencies
        with patch('src.main.Config') as mock_config_class, \
             patch('src.main.TwitterClient') as mock_twitter_class, \
             patch('src.main.PriceFetcher') as mock_price_fetcher_class:
            
            # Configure mocks
            mock_config = MagicMock()
            mock_config.twitter_api_key = "test_key"
            mock_config.twitter_api_secret = "test_secret"
            mock_config.twitter_access_token = "test_token"
            mock_config.twitter_access_token_secret = "test_token_secret"
            mock_config.coingecko_retry_limit = 3
            mock_config_class.return_value = mock_config
            
            mock_twitter = AsyncMock()
            expected_tweet_id = "123456789"
            mock_twitter.post_tweet.return_value = expected_tweet_id
            mock_twitter_class.return_value = mock_twitter
            
            mock_price_fetcher = AsyncMock()
            mock_price_fetcher.__aenter__.return_value = mock_price_fetcher
            mock_price_fetcher.__aexit__.return_value = None
            mock_price_fetcher.get_btc_price_with_retry.return_value = mock_price_data
            mock_price_fetcher_class.return_value = mock_price_fetcher
            
            # Call the function
            result = await post_direct_tweet()
            
            # Assertions
            assert result == expected_tweet_id
            
            # Verify price fetching
            assert mock_price_fetcher.get_btc_price_with_retry.called
            
            # Verify tweet posting - content should include price
            call_args = mock_twitter.post_tweet.call_args[0]
            tweet_text = call_args[0]
            assert "$50,000.00" in tweet_text  # Formatted price
            assert "HODL to the moon" in tweet_text  # Hardcoded fallback quote 