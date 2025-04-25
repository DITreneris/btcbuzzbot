"""
Module for fetching news-related tweets from Twitter.
"""

import logging
import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# Ensure src is in the path if running directly
if 'src' not in sys.path and os.path.exists('src'):
     sys.path.insert(0, os.path.abspath('.'))

# Project Imports with error handling
try:
    from src.database import Database
    DATABASE_CLASS_AVAILABLE = True
except ImportError as e:
    DATABASE_CLASS_AVAILABLE = False
    print(f"Error importing Database from src.database: {e}. NewsFetcher may fail.")
    Database = None # Placeholder

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError as e:
    TWEEPY_AVAILABLE = False
    print("Error importing tweepy. Twitter functionality will be disabled.")
    tweepy = None # Placeholder

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_NEWS_FETCH_MAX_RESULTS = 10

class NewsFetcher:
    def __init__(self, db_instance: Optional[Database] = None):
        self.db = db_instance
        self.bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')
        self.twitter_client = None
        self.initialized = False

        if not self.db or not TWEEPY_AVAILABLE:
            logger.error("NewsFetcher initialization failed due to missing dependencies (Database or tweepy).")
            return

        if not self.bearer_token:
            logger.error("NewsFetcher initialization failed: TWITTER_BEARER_TOKEN not set in environment.")
            return

        try:
            self.twitter_client = self._setup_twitter_client(self.bearer_token)
            if self.twitter_client:
                 logger.info("NewsFetcher initialized successfully.")
                 self.initialized = True
            else:
                 logger.error("NewsFetcher initialization failed: Could not setup Twitter client.")

        except Exception as e:
            logger.error(f"Error during NewsFetcher initialization: {e}", exc_info=True)

    def _setup_twitter_client(self, bearer_token: str) -> Optional[tweepy.Client]:
        """Authenticates with Twitter API v2 using tweepy."""
        try:
            # Using Bearer Token (App-only auth) is sufficient for searching tweets
            # Set wait_on_rate_limit=False to handle it manually
            client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=False)
            # Verify credentials (optional, but good practice) - REMOVED as it requires user context
            # client.get_me() # Throws exception if token is invalid
            logger.info("Twitter client authenticated successfully using Bearer Token.")
            return client
        except Exception as e:
            logger.error(f"Failed to authenticate Twitter client: {e}", exc_info=True)
            return None

    async def fetch_tweets(self, query: Optional[str] = None, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetches recent tweets based on a query using Twitter API v2 search."""
        if not self.initialized or not self.twitter_client:
            logger.error("NewsFetcher not initialized or Twitter client unavailable.")
            return []

        # Determine max_results: use argument if provided, else env var, else default
        if max_results is None:
            fetch_limit = int(os.environ.get('NEWS_FETCH_MAX_RESULTS', DEFAULT_NEWS_FETCH_MAX_RESULTS))
        else:
            fetch_limit = max_results
            
        # Removed $BTC as it causes 400 error on standard v2 endpoint
        default_query = "#Bitcoin -is:retweet"
        # Get search query directly from env var or use default
        search_query = os.environ.get('TWITTER_SEARCH_QUERY', default_query)
        # Ensure max_results is within Twitter API limits (currently 5-100)
        # We use the configured fetch_limit here.
        safe_max_results = max(5, min(fetch_limit, 100)) # Ensure it's at least 5 and at most 100

        logger.info(f"Fetching up to {safe_max_results} tweets (limit: {fetch_limit}) for query: '{search_query}'")

        processed_tweets = []
        try:
            # Use recent search endpoint
            response = self.twitter_client.search_recent_tweets(
                query=search_query,
                max_results=safe_max_results,
                tweet_fields=["created_at", "public_metrics", "entities"], # Request needed fields
                expansions=["author_id"], # Request author info
                user_fields=["username"] # Get username from author_id
            )

            if response.data:
                users = {user.id: user for user in response.includes.get('users', [])} # Map users by ID
                fetched_at = datetime.now(timezone.utc).isoformat()

                for tweet in response.data:
                    author_info = users.get(tweet.author_id)
                    author_username = author_info.username if author_info else "Unknown"
                    tweet_url = f"https://twitter.com/{author_username}/status/{tweet.id}"
                    
                    # Extract published time, ensuring it's timezone-aware (UTC)
                    published_at = tweet.created_at
                    if published_at and not published_at.tzinfo:
                         published_at = published_at.replace(tzinfo=timezone.utc)
                    published_at_iso = published_at.isoformat() if published_at else fetched_at

                    processed_tweets.append({
                        "original_tweet_id": str(tweet.id),
                        "author": author_username,
                        "tweet_text": tweet.text,
                        "tweet_url": tweet_url,
                        "published_at": published_at_iso,
                        "fetched_at": fetched_at
                        # Optional fields like is_news, score, etc., will be added later by analyzer
                    })
                logger.info(f"Successfully fetched {len(processed_tweets)} tweets.")
            else:
                logger.info("No tweets found matching the query.")

        except tweepy.errors.RateLimitError as e:
             # Catch rate limit specifically
             logger.warning(f"Twitter rate limit hit during fetch: {e}. Skipping this fetch cycle and returning no tweets.")
             return [] # Return empty list immediately without blocking
        except tweepy.errors.TweepyException as e:
            logger.error(f"Twitter API error during fetch: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error during tweet fetching: {e}", exc_info=True)

        return processed_tweets

    async def store_fetched_tweets(self, tweets: List[Dict[str, Any]]):
        """Stores fetched tweets in the database, avoiding duplicates."""
        if not self.initialized or not self.db:
             logger.error("NewsFetcher not initialized or Database unavailable.")
             return
             
        if not tweets:
            return

        stored_count = 0
        skipped_count = 0
        for tweet_data in tweets:
            try:
                inserted_id = await self.db.store_news_tweet(tweet_data)
                if inserted_id is not None:
                    stored_count += 1
                    logger.debug(f"Stored news tweet {tweet_data['original_tweet_id']} with DB ID {inserted_id}")
                else:
                    skipped_count += 1
                    logger.debug(f"Skipped duplicate news tweet {tweet_data['original_tweet_id']}")
            except Exception as e:
                logger.error(f"Error storing tweet {tweet_data.get('original_tweet_id', 'N/A')} in DB: {e}", exc_info=True)
                # Optionally skip failed inserts or retry?

        logger.info(f"Finished storing tweets. Stored: {stored_count}, Skipped (duplicates/errors): {skipped_count + (len(tweets) - stored_count - skipped_count)}")

    async def run_cycle(self):
        """Runs a single cycle of fetching and storing news tweets using this instance."""
        if not self.initialized:
            logger.error("Cannot run fetch cycle: NewsFetcher not initialized.")
            return

        try:
            logger.info("Starting news fetch cycle...")
            fetched_tweets = await self.fetch_tweets()
            if fetched_tweets:
                await self.store_fetched_tweets(fetched_tweets)
            logger.info("News fetch cycle finished.")
        except Exception as e:
            logger.error(f"Error during news fetch cycle execution: {e}", exc_info=True)

    async def fetch_and_store_tweets(self, query="(#Bitcoin OR #BTC) -is:retweet lang:en", max_results=100):
        """Fetches recent tweets matching the query and stores them."""
        logger.info(f"Starting fetch_and_store_tweets. Query: '{query}', Max results: {max_results}")
        last_fetched_id = await self.db.get_last_fetched_tweet_id()
        logger.info(f"Last fetched tweet ID: {last_fetched_id}")

        fetched_count = 0
        stored_count = 0
        try:
            # Use pagination to get more tweets if needed, respecting limits
            # Note: search_recent_tweets automatically handles some pagination aspects
            # We use the 'since_id' parameter to avoid fetching duplicates
            response = self.twitter_client.search_recent_tweets(
                query,
                tweet_fields=["created_at", "public_metrics", "author_id"],
                user_fields=["username"], # Add user_fields to get username
                expansions=["author_id"], # Expand author_id to include user details
                max_results=min(max_results, 100), # Ensure max_results <= 100 per request
                since_id=last_fetched_id
            )

            # Check for errors in response (Tweepy v2 specific)
            if response.errors:
                 logger.error(f"Twitter API errors during fetch: {response.errors}")
                 # Handle specific errors if needed (e.g., rate limits)
                 return # Stop processing if there are errors

            tweets = response.data
            users = {user.id: user for user in response.includes.get('users', [])} if response.includes else {}

            if not tweets:
                logger.info("No new tweets found since the last fetch.")
                return

            logger.info(f"Successfully fetched {len(tweets)} tweets from Twitter API.")
            fetched_count = len(tweets)

            for tweet in tweets:
                author_info = users.get(tweet.author_id)
                author_username = author_info.username if author_info else "Unknown"
                # Ensure created_at is timezone-aware (UTC)
                created_at_aware = tweet.created_at
                if created_at_aware.tzinfo is None:
                    created_at_aware = created_at_aware.replace(tzinfo=timezone.utc)

                success = await self.db.store_news_tweet(
                    tweet_id=tweet.id,
                    text=tweet.text,
                    author_id=tweet.author_id,
                    author_username=author_username,
                    published_at=created_at_aware, # Store aware datetime
                    fetched_at=datetime.now(timezone.utc) # Store aware datetime
                )
                if success:
                    stored_count += 1

            logger.info(f"Finished storing tweets. Stored {stored_count}/{fetched_count} new tweets.")

        except tweepy.errors.TweepyException as e:
             logger.error(f"Twitter API error during fetch: {e}", exc_info=True)
             # Specific handling for rate limits
             if isinstance(e, tweepy.errors.TooManyRequests):
                 logger.warning("Twitter API rate limit hit. Skipping this fetch cycle.")
             # Re-raise or handle other Tweepy errors as needed
        except Exception as e:
            logger.error(f"Unexpected error during fetch_and_store_tweets: {e}", exc_info=True)

    async def get_recent_news_tweets(self, limit=10):
        """Retrieves the most recently stored news tweets."""
        # Implementation of get_recent_news_tweets method
        pass

if __name__ == '__main__':
    # Basic test execution if run directly
    logging.basicConfig(level=logging.INFO)
    # Load .env for direct execution
    from dotenv import load_dotenv
    load_dotenv()
    
    logger.info("Running manual news fetch cycle...")
    asyncio.run(run_fetch_cycle())
    logger.info("Manual news fetch cycle finished.") 