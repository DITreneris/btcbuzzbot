import asyncio
import os
from datetime import datetime
import traceback
import logging
import json
import sys

from src.price_fetcher import PriceFetcher
from src.database import Database
from src.db.news_repo import NewsRepository
from src.db.content_repo import ContentRepository
from src.twitter_client import TwitterClient
from src.content_manager import ContentManager
from src.config import Config
from src.discord_poster import send_discord_message
from src.telegram_poster import send_telegram_message

logger = logging.getLogger(__name__)

def _format_news_tweet(current_price: float, price_change: float, news_item: dict) -> str:
    """Formats a tweet string based on news significance and sentiment."""
    summary = news_item.get('summary', "No summary available.")
    significance = news_item.get('significance_label', "Medium").lower()
    sentiment = news_item.get('sentiment_label', "Neutral").lower()

    emoji = ""
    template = ""

    # Base price string
    price_str = f"BTC: ${current_price:,.2f} | {price_change:+.2f}%"

    if significance == "high":
        if sentiment == "positive":
            emoji = "🚀"
            template = f"{price_str} {emoji}\n🔥 BIG NEWS for #Bitcoin! {summary} #CryptoNews"
        elif sentiment == "negative":
            emoji = "⚠️"
            template = f"{price_str} {emoji}\n🚨 Critical #Bitcoin Update! {summary} #CryptoAlert"
        else: # Neutral or other
            emoji = "📰"
            template = f"{price_str} {emoji}\n📢 Key #Bitcoin Development: {summary} #BTCNews"
    elif significance == "medium":
        if sentiment == "positive":
            emoji = "📈"
            template = f"{price_str} {emoji}\n👍 Positive #Bitcoin Signal: {summary} #Crypto"
        elif sentiment == "negative":
            emoji = "📉" # Could also be a more neutral warning for medium sig
            template = f"{price_str} {emoji}\n❗ Notable #Bitcoin Update (Caution): {summary} #BTC"
        else: # Neutral or other
            emoji = "📊"
            template = f"{price_str} {emoji}\n🔍 #Bitcoin Update: {summary} #CryptoReport"
    else: # Low significance or undefined
        if sentiment == "positive":
            emoji = "💡"
        elif sentiment == "negative":
            emoji = "🧐"
        else:
            emoji = "➡️"
        # Simpler template for low significance
        template = f"{price_str} {emoji}\n{summary} #Bitcoin"

    # Log the chosen template parts for debugging
    template_lines = template.split('\n')
    log_template_preview = template_lines[1][:50] if len(template_lines) > 1 else template_lines[0][:50]
    logger.debug(f"Formatted news tweet - Significance: {significance}, Sentiment: {sentiment}, Emoji: {emoji}, Template used: {log_template_preview}...")
    return template

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
        db = Database(config.sqlite_db_path) 
        news_repo = NewsRepository(config.sqlite_db_path)
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
            latest_price_data = await db.get_latest_price()
            previous_price = latest_price_data["price"] if latest_price_data else current_price
            logger.info(f"Previous BTC price: ${previous_price:,.2f}")
            
            # Calculate price change
            price_change = price_fetcher.calculate_price_change(current_price, previous_price)
            logger.info(f"Price change: {price_change:+.2f}%")
            
            # Store new price in database
            logger.info("Storing new price in database...")
            await db.store_price(current_price)
            
            # --- Determine Tweet Content based on Schedule ---
            tweet = ""
            content_type = "price_only" # Default, will be updated
            use_fallback_content = True # Assume fallback unless suitable news found

            # For ALL scheduled times, try to use news summary first
            logger.info(f"Scheduled time is {scheduled_time_str or 'other'}. Checking for suitable news...")
            selected_news_content = None # Will store dict of the selected news item
            NEWS_HOURS_LIMIT = config.news_hours_limit # Get from config

            # Define Significance Score Thresholds (Consider making these configurable)
            HIGH_SIG_SCORE_THRESHOLD = 0.8 # e.g., for "High"
            MEDIUM_SIG_SCORE_THRESHOLD = 0.4 # e.g., for "Medium"
            # LOW_SIG_SCORE_THRESHOLD = 0.1 # Not explicitly used if we iterate top-down
            
            try:
                recent_analyzed_news = await news_repo.get_recent_analyzed_news(hours_limit=NEWS_HOURS_LIMIT)
                logger.info(f"Found {len(recent_analyzed_news)} recently analyzed news items for potential use.")

                for news_item in recent_analyzed_news:
                    # news_item is now a dict with structured fields from get_recent_analyzed_news
                    sig_score = news_item.get('significance_score')
                    sentiment_label = news_item.get('sentiment_label')
                    summary = news_item.get('summary')
                    news_text = news_item.get('text') # Full text for context if needed
                    sentiment_source = news_item.get('sentiment_source')
                    original_tweet_id = news_item.get('original_tweet_id')

                    if not summary: # Essential for the tweet
                        logger.debug(f"Skipping news {original_tweet_id}: missing summary.")
                        continue
                    
                    logger.debug(f"Evaluating news {original_tweet_id}: Sig Score: {sig_score}, Sentiment: {sentiment_label}, Source: {sentiment_source}")

                    # Decision logic based on significance and sentiment
                    use_this_news = False
                    if sig_score is not None:
                        if sig_score >= HIGH_SIG_SCORE_THRESHOLD:
                            use_this_news = True
                            logger.info(f"Selected news {original_tweet_id} due to HIGH significance ({sig_score}).")
                        elif sig_score >= MEDIUM_SIG_SCORE_THRESHOLD:
                            if sentiment_label in ["Positive", "Neutral"]:
                                use_this_news = True
                                logger.info(f"Selected news {original_tweet_id} due to MEDIUM significance ({sig_score}) and Positive/Neutral sentiment.")
                            else:
                                logger.debug(f"Skipping news {original_tweet_id}: MEDIUM significance but sentiment ({sentiment_label}) not Positive/Neutral.")
                        # else: (Low significance)
                            # logger.debug(f"Skipping news {original_tweet_id}: LOW significance ({sig_score}).")
                    
                    # Optional: Add stricter rules if sentiment_source is a fallback
                    if use_this_news and sentiment_source and "vader_fallback" in sentiment_source:
                        # Example: only use if HIGH significance for VADER fallbacks
                        if sig_score < HIGH_SIG_SCORE_THRESHOLD:
                            logger.info(f"De-selecting news {original_tweet_id}: VADER fallback sentiment and not HIGH significance.")
                            use_this_news = False

                    if use_this_news:
                        selected_news_content = news_item # Store the whole dict
                        break # Found suitable news, stop iterating
                
                if not selected_news_content:
                    logger.info("No suitable news item found after evaluating recent analyses.")

            except Exception as e_news_select:
                 logger.error(f"Error during news selection logic: {e_news_select}", exc_info=True)
                 # Ensure selected_news_content remains None or is reset if error occurs mid-selection
                 selected_news_content = None 

            # --- Generate tweet based on whether suitable news was found ---
            if selected_news_content and selected_news_content.get('summary'):
                # Use the new helper function to format the tweet
                tweet = _format_news_tweet(current_price, price_change, selected_news_content)
                content_type = 'news_summary' # Keep track of content type
                use_fallback_content = False
                logger.info(f"Using formatted news tweet (Original ID: {selected_news_content.get('original_tweet_id')}).")
            
            if use_fallback_content:
                logger.info("No suitable news found or fallback explicitly required. Falling back to random content.")
                content = await content_manager.get_random_content()
                if content:
                    # For fallback content, emoji is based purely on price change
                    emoji = "📈" if price_change >= 0 else "📉"
                    tweet = f"BTC: ${current_price:,.2f} | {price_change:+.2f}% {emoji}\n{content['text']}\n#Bitcoin #Crypto"
                    content_type = content["type"]
                else:
                    logger.warning("Failed to get random content. Falling back to price-only tweet.")
                    emoji = "📈" if price_change >= 0 else "📉"
                    tweet = f"BTC: ${current_price:,.2f} | {price_change:+.2f}% {emoji}\n#Bitcoin #Price"
                    content_type = "price_fallback"

            # --- END Content Determination ---
            logger.debug(f"Generated tweet content: {tweet}")

            # --- START Duplicate Check ---
            logger.info("Checking for recent posts...")
            if await db.has_posted_recently(minutes=5):
                logger.warning("Skipping post: A tweet was already posted successfully in the last 5 minutes.")
                return None # Indicate skipped post
            # --- END Duplicate Check ---
            
            # Post to Twitter
            logger.info("Posting to Twitter...")
            tweet_id = await twitter.post_tweet(tweet)
            
            if tweet_id:
                logger.info(f"Successfully posted tweet with ID: {tweet_id}")
                
                # Post to Discord if enabled
                if config.enable_discord_posting:
                    logger.info("Discord posting enabled. Sending message...")
                    discord_success = await send_discord_message(
                        config.discord_webhook_url,
                        tweet
                    )
                    if discord_success:
                        logger.info("Successfully posted message to Discord.")
                    else:
                        logger.warning("Failed to post message to Discord.")
                
                # Post to Telegram if enabled
                if config.enable_telegram_posting:
                    logger.info("Telegram posting enabled. Sending message...")
                    telegram_success = await send_telegram_message(
                        config.telegram_bot_token,
                        config.telegram_chat_id,
                        tweet
                    )
                    if telegram_success:
                        logger.info("Successfully posted message to Telegram.")
                    else:
                        logger.warning("Failed to post message to Telegram.")
                
                return tweet_id
            else:
                logger.warning("Failed to post tweet - no tweet ID returned")
                return None
                
        except Exception as e:
            logger.error(f"Error in post_btc_update: {e}", exc_info=True)
            traceback.print_exc()
            return None
            
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