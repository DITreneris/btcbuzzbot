"""
TwitterHandler module for BTCBuzzBot.
Handles the posting of tweets using the TwitterClient.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from src.twitter_client import TwitterClient
from src.database import Database
from src.config import Config
from src.price_fetcher import PriceFetcher

# Setup logger
logger = logging.getLogger('btcbuzzbot.tweet_handler')

class TweetHandler:
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.sqlite_db_path)
        self.twitter_client = TwitterClient(
            self.config.twitter_api_key,
            self.config.twitter_api_secret,
            self.config.twitter_access_token,
            self.config.twitter_access_token_secret
        )
        self.price_fetcher = PriceFetcher()
        self.initialized = True
        logger.info("TweetHandler initialized")
        
    async def post_tweet(self, content: str, content_type: str, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Post a tweet with the given content and price.
        
        Args:
            content: The content to post
            content_type: The type of content (quote, joke, etc.)
            price: Current BTC price (optional, will be fetched if not provided)
            
        Returns:
            Dictionary with result information
        """
        if not self.initialized:
            logger.error("TweetHandler not initialized")
            return {
                'success': False,
                'error': 'TweetHandler not initialized'
            }
            
        try:
            # Get the current price if not provided
            current_price = price
            previous_price = None
            price_change = 0.0
            
            if current_price is None:
                logger.info("Fetching current BTC price")
                price_data = await self.price_fetcher.get_btc_price_with_retry(self.config.coingecko_retry_limit)
                current_price = price_data["usd"]
                
                # Get the previous price for comparison
                latest_price_data = await self.db.get_latest_price()
                previous_price = latest_price_data["price"] if latest_price_data else current_price
                
                # Calculate price change
                price_change = self.price_fetcher.calculate_price_change(current_price, previous_price)
                
                # Store the new price in the database
                await self.db.store_price(current_price)
            
            # Format the tweet
            emoji = "📈" if price_change >= 0 else "📉"
            tweet = f"BTC: ${current_price:,.2f}"
            
            # Add price change if we have it
            if previous_price is not None:
                tweet += f" | {price_change:+.2f}% {emoji}"
                
            # Add content and hashtags
            tweet += f"\n{content}\n#Bitcoin #Crypto"
            
            logger.info(f"Posting tweet: {tweet}")
            
            # Post the tweet
            tweet_id = await self.twitter_client.post_tweet(tweet)
            
            if tweet_id:
                # Log the tweet in the database
                post_id = await self.db.log_post(
                    tweet_id=tweet_id,
                    tweet=tweet,
                    price=current_price,
                    price_change=price_change,
                    content_type=content_type
                )
                
                logger.info(f"Successfully posted tweet with ID: {tweet_id}, logged as post ID: {post_id}")
                
                return {
                    'success': True,
                    'tweet_id': tweet_id,
                    'post_id': post_id,
                    'tweet': tweet
                }
            else:
                logger.error("Failed to post tweet - no tweet ID returned")
                return {
                    'success': False,
                    'error': 'Failed to post tweet - no tweet ID returned'
                }
                
        except Exception as e:
            logger.error(f"Error posting tweet: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def close(self):
        """Close all resources"""
        if hasattr(self, 'db'):
            await self.db.close()

# Singleton instance
_tweet_handler_instance = None

# Function to get singleton instance
def get_tweet_handler() -> TweetHandler:
    """Get the singleton instance of TweetHandler"""
    global _tweet_handler_instance
    if _tweet_handler_instance is None:
        _tweet_handler_instance = TweetHandler()
    return _tweet_handler_instance

# Function to initialize tweet handler once
async def initialize():
    """Initialize the tweet handler singleton"""
    handler = get_tweet_handler()
    return handler

# Synchronous wrapper for post_tweet for compatibility with non-async code
def post_tweet(content: str, content_type: str, price: Optional[float] = None) -> Dict[str, Any]:
    """
    Post a tweet (synchronous wrapper).
    
    Args:
        content: The content to post
        content_type: The type of content (quote, joke, etc.)
        price: Current BTC price (optional, will be fetched if not provided)
        
    Returns:
        Dictionary with result information
    """
    handler = get_tweet_handler()
    
    # Create a new event loop for async operation if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If there's no event loop in this thread, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        # Run the async post_tweet function
        result = loop.run_until_complete(handler.post_tweet(content, content_type, price))
        return result
    except Exception as e:
        logger.error(f"Error in post_tweet wrapper: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

# Test function for direct runs
async def test_tweet_handler():
    """Test the tweet handler"""
    handler = get_tweet_handler()
    
    # Test posting a tweet
    content = "Testing the tweet handler! HODL to the moon! 🚀"
    result = await handler.post_tweet(content, "test")
    
    if result['success']:
        print(f"✅ Tweet posted successfully! Tweet ID: {result['tweet_id']}")
    else:
        print(f"❌ Tweet posting failed! Error: {result.get('error', 'Unknown error')}")
    
    # Clean up
    await handler.close()

# For testing
if __name__ == "__main__":
    # Run the test function
    asyncio.run(test_tweet_handler()) 