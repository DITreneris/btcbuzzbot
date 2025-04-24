"""
TwitterHandler module for BTCBuzzBot.
Handles the posting of tweets using the TwitterClient.
"""

import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('btcbuzzbot.tweet_handler')

# --- Configuration Defaults ---
DEFAULT_PRICE_FETCH_MAX_RETRIES = 3
DEFAULT_TWEET_HASHTAGS = "#Bitcoin #Crypto"
DEFAULT_MAX_TWEET_LENGTH = 280
# --- End Configuration Defaults ---

# Flag to track if TwitterClient is available
TWITTER_CLIENT_AVAILABLE = False
TWEEPY_AVAILABLE = False

# Try different import approaches
try:
    # First try absolute imports for project modules
    from src.twitter_client import TwitterClient
    from src.database import Database
    from src.price_fetcher import PriceFetcher
    TWITTER_CLIENT_AVAILABLE = True
    logger.info("TwitterClient module imported successfully")
except ImportError:
    try:
        # Then try relative imports
        from twitter_client import TwitterClient
        from database import Database
        from price_fetcher import PriceFetcher
        TWITTER_CLIENT_AVAILABLE = True
        logger.info("TwitterClient module imported via relative import")
    except ImportError:
        # Log but don't crash, implement fallback
        logger.error("Could not import TwitterClient module, will use direct tweepy implementation")
        # Check if tweepy is at least available
        try:
            import tweepy
            from dotenv import load_dotenv
            TWEEPY_AVAILABLE = True
            logger.info("Tweepy available for direct implementation")
        except ImportError:
            logger.error("Tweepy not available - tweet functionality will be disabled")

class TweetHandler:
    def __init__(self, db_instance: Optional[Database] = None):
        self.db = db_instance
        self.twitter_client = None
        self.price_fetcher = None
        self.initialized = False

        if not self.db:
            logger.error("TweetHandler initialization failed: Database instance not provided.")
            return

        # Read API keys directly from environment
        api_key = os.environ.get('TWITTER_API_KEY')
        api_secret = os.environ.get('TWITTER_API_SECRET')
        access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

        if not all([api_key, api_secret, access_token, access_token_secret]):
            logger.error("TweetHandler initialization failed: Twitter API credentials missing in environment.")
            return

        try:
            # Initialize components
            if TWITTER_CLIENT_AVAILABLE:
                self.twitter_client = TwitterClient(api_key, api_secret, access_token, access_token_secret)
            else:
                 logger.error("TweetHandler cannot initialize TwitterClient (module import failed). Tweet posting may fail.")
                 # We could potentially add the direct tweepy fallback init here if needed

            self.price_fetcher = PriceFetcher() # Assuming PriceFetcher handles its own config/env vars
            
            # Mark as initialized ONLY if the above succeeds
            self.initialized = True
            logger.info("TweetHandler initialized")
            
        except Exception as e:
             logger.error(f"Error during TweetHandler initialization: {e}", exc_info=True)
             # Ensure initialized is False if an error occurred
             self.initialized = False 
        
    async def post_tweet(self, content: str, content_type: str, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Post a tweet with the given content and price.
        
        Args:
            content: The content to post (quote/joke text)
            content_type: The type of content (quote, joke, price)
            price: Current BTC price (only used if content_type='price', optional)
            
        Returns:
            Dictionary with result information
        """
        logger.info(f"--- Method TweetHandler.post_tweet ENTERED (content_type: {content_type}) ---")

        if not self.initialized:
            logger.error("TweetHandler not initialized")
            return {
                'success': False,
                'error': 'TweetHandler not initialized'
            }
        if not self.twitter_client:
             logger.error("TwitterClient not available within TweetHandler.")
             return {'success': False, 'error': 'TwitterClient not available'}
        if not self.price_fetcher:
             logger.error("PriceFetcher not available within TweetHandler.")
             return {'success': False, 'error': 'PriceFetcher not available'}
        if not self.db:
             logger.error("Database not available within TweetHandler.")
             return {'success': False, 'error': 'Database not available'}

        try:
            # 1. Fetch Bitcoin Price using PriceFetcher
            if not self.price_fetcher:
                return {"success": False, "error": "PriceFetcher not initialized"}

            try:
                # Use configured max_retries
                price_fetch_retries = int(os.environ.get('PRICE_FETCH_MAX_RETRIES', DEFAULT_PRICE_FETCH_MAX_RETRIES))
                price_data = await self.price_fetcher.get_btc_price_with_retry(max_retries=price_fetch_retries)
            except Exception as price_err:
                error_msg = f"Could not fetch BTC price: {str(price_err)}"
                logger.error(f"TweetHandler: {error_msg}", exc_info=True)
                return {"success": False, "error": error_msg}

            current_price = price_data.get('usd', 0.0)
            # Attempt to get 24h change from PriceFetcher result if available
            # Assuming get_btc_price_with_retry might return more than just {'usd': price}
            price_change_24h = price_data.get("usd_24h_change", 0.0)
            logger.debug(f"TweetHandler: Price data fetched: ${current_price:,.2f}, Change: {price_change_24h:.2f}%")


            # Store the new price in the database - ONLY pass price now
            await self.db.store_price(current_price) # REMOVED price_change argument
            logger.debug("TweetHandler: Price stored in DB.")

            # --- Calculate 24h Price Change ---
            price_change_24h = 0.0 # Default to 0.0
            try:
                previous_price = await self.db.get_price_from_approx_24h_ago()
                if previous_price is not None and previous_price > 0:
                    price_change_24h = ((current_price - previous_price) / previous_price) * 100
                    logger.info(f"Calculated 24h price change: {price_change_24h:.2f}% (Current: ${current_price:,.2f}, Previous: ${previous_price:,.2f})")
                else:
                    logger.warning("Could not retrieve price from ~24h ago to calculate change. Defaulting to 0.00%.")
            except Exception as calc_err:
                logger.error(f"Error calculating 24h price change: {calc_err}", exc_info=True)
            # --- End Price Change Calculation ---

            # Format the tweet using helper method
            tweet_text = self._format_tweet(current_price, price_change_24h, content, content_type)

            logger.info(f"Formatted Tweet: {tweet_text}")

            # --- Duplicate Check ---
            logger.debug("Checking for recent duplicate posts...")
            # Call has_posted_recently without argument to use configured env var
            is_duplicate = await self.db.has_posted_recently()
            if is_duplicate:
                logger.warning("Skipping tweet: A similar post was found within the configured duplicate check interval.")
                return {'success': False, 'error': 'Skipped: Recent post detected'}
            logger.debug("No recent duplicate post found.")

            # Post the tweet via TwitterClient
            logger.debug("Calling TwitterClient.post_tweet...")
            tweet_id = await self.twitter_client.post_tweet(tweet_text)
            
            if tweet_id:
                # Log the tweet in the database
                logger.debug(f"Tweet posted (ID: {tweet_id}). Logging to DB...")
                post_id = await self.db.log_post(
                    tweet_id=tweet_id,
                    tweet=tweet_text,
                    price=current_price,
                    price_change=price_change_24h,
                    content_type=content_type
                )
                
                logger.info(f"Successfully posted tweet with ID: {tweet_id}, logged as post ID: {post_id}")
                
                return {
                    'success': True,
                    'tweet_id': tweet_id,
                    'post_id': post_id,
                    'tweet': tweet_text
                }
            else:
                logger.error("Failed to post tweet - no tweet ID returned by TwitterClient")
                return {
                    'success': False,
                    'error': 'Failed to post tweet - no tweet ID returned by TwitterClient'
                }
                
        except Exception as e:
            logger.error(f"Error in TweetHandler.post_tweet: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
            
    def _format_tweet(self, price: float, price_change: float, quote_or_joke_text: Optional[str], content_type: str) -> str:
        """Helper function to format the tweet text."""
        emoji = "📈" if price_change >= 0 else "📉"
        tweet = f"BTC: ${price:,.2f} | 24h: {price_change:+.2f}% {emoji}"

        if quote_or_joke_text and content_type in ['quote', 'joke']:
            tweet += f"\n\n{quote_or_joke_text}"

        # Add standard hashtags from config
        hashtags = os.environ.get('DEFAULT_TWEET_HASHTAGS', DEFAULT_TWEET_HASHTAGS)
        if hashtags:
             tweet += f"\n\n{hashtags}"

        # Ensure tweet length is within limits
        max_length = int(os.environ.get('MAX_TWEET_LENGTH', DEFAULT_MAX_TWEET_LENGTH))
        if len(tweet) > max_length:
            logger.warning(f"Tweet exceeds {max_length} characters, attempting to truncate...")
            chars_to_remove = len(tweet) - max_length + 3 # Add 3 for ellipsis
            if quote_or_joke_text:
                truncated_content = quote_or_joke_text[:-chars_to_remove] + "..."
                # Re-format with truncated content and hashtags
                tweet = f"BTC: ${price:,.2f} | 24h: {price_change:+.2f}% {emoji}\n\n{truncated_content}"
                if hashtags: tweet += f"\n\n{hashtags}"
            else:
                 tweet = tweet[:max_length - 3] + "..."
                 
            logger.warning(f"Truncated tweet: {tweet}")
            if len(tweet) > max_length:
                 logger.error("Tweet still too long after truncation attempt! Posting may fail.")

        return tweet

    async def close(self):
        """Close all resources"""
        if hasattr(self, 'db') and self.db:
            # await self.db.close() # Assuming db instance is managed elsewhere now
            pass # DB is managed by scheduler_tasks now

async def test_tweet_handler():
    print("Testing TweetHandler...")
    # Load .env for testing if needed
    from dotenv import load_dotenv
    load_dotenv()

    # Need a DB instance for testing
    test_db = None
    try:
        test_db = Database() # Assuming Database reads env vars for connection
        await test_db.init_db() # Ensure tables exist
        handler = TweetHandler(db_instance=test_db)
        if handler.initialized:
            print("Handler initialized.")
            # Test posting a quote
            result_quote = await handler.post_tweet("This is a test quote.", "quote")
            print(f"Post Quote Result: {result_quote}")
            # Test posting a price tweet
            result_price = await handler.post_tweet("", "price") # Handler fetches price
            print(f"Post Price Result: {result_price}")
        else:
            print("Handler failed to initialize.")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        if test_db:
            await test_db.close()

if __name__ == '__main__':
    # Run the async test function
    asyncio.run(test_tweet_handler()) 