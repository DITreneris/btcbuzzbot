import asyncio
import os
from datetime import datetime
import traceback

from src.price_fetcher import PriceFetcher
from src.database import Database
from src.twitter_client import TwitterClient
from src.content_manager import ContentManager
from src.config import Config

async def post_direct_tweet():
    """Post a direct tweet without database dependencies"""
    print("Starting direct tweet posting...")
    
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
            print(f"Current BTC price: ${current_price:,.2f}")
        
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
        print(f"Posting tweet: {tweet}")
        tweet_id = await twitter.post_tweet(tweet)
        
        if tweet_id:
            print(f"Successfully posted tweet with ID: {tweet_id}")
            return tweet_id
        else:
            print("Failed to post tweet - no tweet ID returned")
            return None
    
    except Exception as e:
        print(f"Error posting update: {e}")
        traceback.print_exc()
        return None

async def post_btc_update(config=None):
    """Fetch BTC price and post update to Twitter"""
    # Initialize configuration
    if config is None:
        config = Config()
    
    try:
        print(f"Initializing SQLite database at {config.sqlite_db_path}...")
        # Initialize database
        db = Database(config.sqlite_db_path)
        price_fetcher = PriceFetcher()
        twitter = TwitterClient(
            config.twitter_api_key,
            config.twitter_api_secret,
            config.twitter_access_token,
            config.twitter_access_token_secret
        )
        content_manager = ContentManager(db)
        
        try:
            # Fetch current BTC price
            print("Fetching BTC price...")
            async with price_fetcher as pf:
                price_data = await pf.get_btc_price_with_retry(config.coingecko_retry_limit)
                current_price = price_data["usd"]
                print(f"Current BTC price: ${current_price:,.2f}")
            
            # Get latest price from database for comparison
            print("Fetching latest price from database...")
            latest_price_data = await db.get_latest_price()
            previous_price = latest_price_data["price"] if latest_price_data else current_price
            print(f"Previous BTC price: ${previous_price:,.2f}")
            
            # Calculate price change
            price_change = price_fetcher.calculate_price_change(current_price, previous_price)
            print(f"Price change: {price_change:+.2f}%")
            
            # Store new price in database
            print("Storing new price in database...")
            await db.store_price(current_price)
            
            # Get random content
            print("Getting random content...")
            content = await content_manager.get_random_content()
            
            # Format tweet
            emoji = "📈" if price_change >= 0 else "📉"
            tweet = f"BTC: ${current_price:,.2f} | {price_change:+.2f}% {emoji}\n{content['text']}\n#Bitcoin #Crypto"
            
            # --- START Duplicate Check ---
            print("Checking for recent posts...")
            if await db.has_posted_recently(minutes=5):
                print("Skipping post: A tweet was already posted successfully in the last 5 minutes.")
                return None # Indicate skipped post
            # --- END Duplicate Check ---
            
            # Post tweet
            print(f"Posting tweet: {tweet}")
            tweet_id = await twitter.post_tweet(tweet)
            
            if tweet_id:
                # Log successful post
                print("Logging successful post to database...")
                await db.log_post(
                    tweet_id=tweet_id, 
                    tweet=tweet, 
                    price=current_price, 
                    price_change=price_change, 
                    content_type=content["type"]
                )
                
                print(f"Successfully posted tweet: {tweet_id}")
                return tweet_id
            else:
                print("Failed to post tweet - no tweet ID returned")
                return None
        
        except Exception as e:
            print(f"Error in database operations: {e}")
            raise
        finally:
            # Close connections
            print("Closing database connection...")
            await db.close()
    
    except Exception as e:
        print(f"Database error: {e}")
        print("Falling back to direct tweet posting...")
        
        # Fall back to direct tweet posting without database
        return await post_direct_tweet()

async def setup_database():
    """Set up the database with initial content"""
    try:
        config = Config()
        # Removed confusing log message, Database class handles its own logging.
        # print(f"Setting up SQLite database at {config.sqlite_db_path}...") 
        db = Database(config.sqlite_db_path)
        cm = ContentManager(db)
        
        try:
            # Add initial content if needed
            await cm.add_initial_content()
        finally:
            await db.close()
    except Exception as e:
        print(f"Database setup failed: {e}")
        print("Continuing without database setup...")

async def main():
    """Main function"""
    try:
        # Try to setup database with initial content if needed
        await setup_database()
    except Exception as e:
        print(f"Database setup failed: {e}")
    
    # Post BTC update
    await post_btc_update()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 