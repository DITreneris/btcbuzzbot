import asyncio
import os
from datetime import datetime
import traceback
import logging
import json

from src.price_fetcher import PriceFetcher
from src.database import Database
from src.db.news_repo import NewsRepository
from src.db.content_repo import ContentRepository
from src.twitter_client import TwitterClient
from src.content_manager import ContentManager
from src.config import Config
from src.discord_poster import send_discord_message

logger = logging.getLogger(__name__)

async def post_direct_tweet():
    """Post a direct tweet without database dependencies"""
    logger.info("Starting direct tweet posting (fallback)...")
    
    # Initialize configuration
    config = Config()
    
    # Initialize Twitter client
    twitter = TwitterClient(
        config.twitter_api_key,
        config.twitter_api_secret,
        config.twitter_access_token,
        config.twitter_access_token_secret
    )
    
    try:
        # Fetch current BTC price
        async with PriceFetcher() as pf:
            price_data = await pf.get_btc_price_with_retry(config.coingecko_retry_limit)
            current_price = price_data["usd"]
            logger.info(f"Direct tweet fallback: Current BTC price: ${current_price:,.2f}")
        
        # Use a hardcoded quote since we don't have DB access
        content = {
            "text": "HODL to the moon! 🚀",
            "type": "quote",
            "category": "motivational"
        }
        
        # Format tweet
        emoji = "📈"  # Always use up emoji for first tweet
        tweet = f"BTC: ${current_price:,.2f} {emoji}\n{content['text']}\n#Bitcoin #Crypto"
        
        # Post tweet
        logger.info(f"Direct tweet fallback: Posting tweet: {tweet}")
        tweet_id = await twitter.post_tweet(tweet)
        
        if tweet_id:
            logger.info(f"Direct tweet fallback: Successfully posted tweet with ID: {tweet_id}")
            return tweet_id
        else:
            logger.warning("Direct tweet fallback: Failed to post tweet - no tweet ID returned")
            return None
    
    except Exception as e:
        logger.error(f"Direct tweet fallback: Error posting update: {e}", exc_info=True)
        traceback.print_exc()
        return None

async def post_btc_update(config=None, scheduled_time_str=None):
    """Fetch BTC price and post update to Twitter based on schedule."""
    # Initialize configuration
    if config is None:
        config = Config()

    db = None # Initialize db variable
    try:
        logger.info(f"Running post_btc_update for scheduled time: {scheduled_time_str or 'Unspecified'}")
        logger.info(f"Initializing database/repositories for post_btc_update...")
        
        # Initialize database and repositories
        # Database object is still needed for price/post logging
        db = Database(config.sqlite_db_path) 
        news_repo = NewsRepository(config.sqlite_db_path)
        # ContentManager now uses ContentRepository internally
        content_manager = ContentManager(config.sqlite_db_path)
        
        price_fetcher = PriceFetcher()
        twitter = TwitterClient(
            config.twitter_api_key,
            config.twitter_api_secret,
            config.twitter_access_token,
            config.twitter_access_token_secret
        )
        
        try:
            # Fetch current BTC price
            logger.info("Fetching BTC price...")
            async with price_fetcher as pf:
                price_data = await pf.get_btc_price_with_retry(config.coingecko_retry_limit)
                current_price = price_data["usd"]
                logger.info(f"Current BTC price: ${current_price:,.2f}")
            
            # Get latest price from database for comparison
            logger.info("Fetching latest price from database...")
            # Use the main db object for price methods
            latest_price_data = await db.get_latest_price()
            previous_price = latest_price_data["price"] if latest_price_data else current_price
            logger.info(f"Previous BTC price: ${previous_price:,.2f}")
            
            # Calculate price change
            price_change = price_fetcher.calculate_price_change(current_price, previous_price)
            logger.info(f"Price change: {price_change:+.2f}%")
            
            # Store new price in database
            logger.info("Storing new price in database...")
            # Use the main db object for price methods
            await db.store_price(current_price)
            
            # --- Determine Tweet Content based on Schedule ---
            tweet = ""
            content_type = "price_only" # Default, will be updated
            use_fallback_content = True # Assume fallback unless significant news found

            # For ALL scheduled times, try to use news summary first
            logger.info(f"Scheduled time is {scheduled_time_str or 'other'}. Checking for significant news...")
            significant_news_summary = None
            SIGNIFICANCE_THRESHOLD = 5 # Define the threshold
            NEWS_HOURS_LIMIT = 12 # How far back to look for news
            
            try:
                # Use NewsRepository here
                recent_analyzed_news = await news_repo.get_recent_analyzed_news(hours_limit=NEWS_HOURS_LIMIT)
                for news_item in recent_analyzed_news:
                    raw_analysis = news_item.get('llm_raw_analysis')
                    if raw_analysis:
                         try:
                            # Parse the JSON analysis
                            analysis_data = json.loads(raw_analysis)
                            significance = analysis_data.get('significance_score')
                            summary = analysis_data.get('summary')
                            
                            # Check significance threshold
                            if significance is not None and summary:
                                try:
                                     if int(significance) >= SIGNIFICANCE_THRESHOLD:
                                         significant_news_summary = summary
                                         logger.info(f"Found significant news (Score: {significance}) from tweet {news_item['original_tweet_id']}. Using its summary.")
                                         break # Use the first significant summary found (most recent)
                                except (ValueError, TypeError):
                                     logger.warning(f"Could not parse significance score '{significance}' as int for tweet {news_item['original_tweet_id']}")
                         except json.JSONDecodeError:
                             logger.warning(f"Could not decode JSON analysis for tweet {news_item['original_tweet_id']}")
                         except Exception as e_parse:
                              logger.error(f"Error parsing analysis for {news_item['original_tweet_id']}: {e_parse}")
            except Exception as e_db:
                 logger.error(f"Error fetching recent analyzed news from repo: {e_db}", exc_info=True)

            # --- Generate tweet based on whether significant news was found ---
            if significant_news_summary:
                emoji = "📈" if price_change >= 0 else "📉"
                # Format tweet with news summary
                tweet = f"BTC: ${current_price:,.2f} | {price_change:+.2f}% {emoji}\n{significant_news_summary}\n#Bitcoin #News"
                content_type = 'news_summary'
                use_fallback_content = False # News found, don't use fallback
            
            # Fallback to random content if no significant news found OR if use_fallback_content is still True
            if use_fallback_content:
                logger.info("No significant news found or fallback required. Falling back to random content.")
                # ContentManager is already initialized above
                content = await content_manager.get_random_content()
                if content:
                    emoji = "📈" if price_change >= 0 else "📉"
                    # Format tweet with random content
                    tweet = f"BTC: ${current_price:,.2f} | {price_change:+.2f}% {emoji}\n{content['text']}\n#Bitcoin #Crypto"
                    content_type = content["type"]
                else:
                    # Fallback if random content also fails
                    logger.warning("Failed to get random content. Falling back to price-only tweet.")
                    emoji = "📈" if price_change >= 0 else "📉"
                    tweet = f"BTC: ${current_price:,.2f} | {price_change:+.2f}% {emoji}\n#Bitcoin #Price"
                    content_type = "price_fallback"

            # --- END Content Determination ---
            logger.debug(f"Generated tweet content: {tweet}")

            # --- START Duplicate Check ---
            logger.info("Checking for recent posts...")
            # Use the main db object for post logging/checking methods
            if await db.has_posted_recently(minutes=5):
                logger.warning("Skipping post: A tweet was already posted successfully in the last 5 minutes.")
                return None # Indicate skipped post
            # --- END Duplicate Check ---
            
            # Post tweet
            logger.info(f"Posting tweet: {tweet[:50]}...")
            tweet_id = await twitter.post_tweet(tweet)
            
            if tweet_id:
                # Log successful post
                logger.info("Logging successful post to database...")
                # Use the main db object for post logging methods
                await db.log_post(
                    tweet_id=tweet_id,
                    tweet=tweet,
                    price=current_price,
                    price_change=price_change,
                    content_type=content_type
                )
                
                # --- Add Discord Posting Logic ---
                if config.enable_discord_posting:
                    discord_webhook_url = config.discord_webhook_url
                    if discord_webhook_url:
                        logger.info("Discord posting enabled. Sending message...")
                        # Send the same text as the tweet
                        # Ensure we pass the tweet_text, not the tweet object
                        discord_success = await send_discord_message(discord_webhook_url, tweet_text)
                        if discord_success:
                             logger.info("Successfully posted message to Discord.")
                    else:
                        logger.warning("Discord posting enabled, but DISCORD_WEBHOOK_URL is not set.")
                # --- End Discord Posting Logic ---
                
                logger.info(f"Successfully posted tweet: {tweet_id}")
                return tweet_id
            else:
                logger.warning("Failed to post tweet - no tweet ID returned")
                return None
        
        except Exception as e:
            logger.error(f"Error during main tweet posting logic: {e}", exc_info=True)
            raise # Re-raise to be caught by outer handler
        # Removed finally block for db.close() here - handle below

    except Exception as e:
        logger.error(f"Database connection or other critical error in post_btc_update: {e}", exc_info=True)
        logger.info("Falling back to direct tweet posting...")
        
        # Fall back to direct tweet posting without database
        # Ensure db is closed even if we fallback
        if db and hasattr(db, 'close'):
            try:
                await db.close() # Assuming db.close() might be async now?
            except Exception as close_err:
                logger.error(f"Error closing DB connection during outer exception handling: {close_err}")
        return await post_direct_tweet()
    
    finally:
        # Ensure database connection is closed
        if db and hasattr(db, 'close'):
            try:
                logger.info("Closing database connection for post_btc_update...")
                await db.close() # Assuming db.close() might be async now?
            except Exception as close_err:
                 logger.error(f"Error closing DB connection in finally block: {close_err}")


async def setup_database():
    """Set up the database with initial content"""
    # This function primarily uses ContentManager now
    try:
        config = Config()
        logger.info("Running database setup...")
        # ContentManager uses ContentRepository internally
        cm = ContentManager(config.sqlite_db_path)
        await cm.add_initial_content()
    except Exception as e:
        logger.error(f"Database setup failed: {e}", exc_info=True)
        logger.warning("Continuing without database setup...")


async def main():
    """Main function"""
    try:
        # Try to setup database with initial content if needed
        await setup_database()
    except Exception as e:
        logger.error(f"Database setup failed: {e}", exc_info=True)
    
    # Post BTC update (Example call, usually run by scheduler)
    await post_btc_update()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 