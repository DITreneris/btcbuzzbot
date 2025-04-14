"""
Direct tweet posting script for BTCBuzzBot.
This script triggers an immediate tweet using the same function as the 'Tweet Now' button.
"""

import os
import sys
import json
import logging
import datetime
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('btcbuzzbot.tweet_now')

# Add the current directory to the path for imports
sys.path.insert(0, os.path.abspath('.'))

# Try to import our tweet_handler_direct module
try:
    import tweet_handler_direct
    logger.info("Tweet handler imported successfully")
except ImportError as e:
    logger.error(f"Failed to import tweet_handler_direct: {e}")
    sys.exit(1)

def get_db_connection():
    """Connect to the SQLite database"""
    db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
    
    # Check if the database file exists
    if not Path(db_path).exists():
        logger.error(f"Database file not found: {db_path}")
        return None
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_bitcoin_price():
    """Fetch the current Bitcoin price from the database"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Database connection failed"}
        
    try:
        # Get the latest price from the database
        latest_price = conn.execute(
            'SELECT * FROM prices ORDER BY timestamp DESC LIMIT 1'
        ).fetchone()
        
        # Get the previous price for calculating change
        day_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat()
        previous_price = conn.execute(
            'SELECT * FROM prices WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1',
            (day_ago,)
        ).fetchone()
        
        conn.close()
        
        if not latest_price:
            return {"success": False, "error": "No price data found"}
            
        current_price = latest_price['price']
        
        # Calculate price change percentage
        if previous_price:
            prev_price = previous_price['price']
            price_change = ((current_price - prev_price) / prev_price) * 100
        else:
            price_change = 0
            
        return {
            "success": True,
            "price": current_price,
            "price_change": price_change
        }
        
    except Exception as e:
        logger.error(f"Error fetching Bitcoin price: {e}")
        if conn:
            conn.close()
        return {"success": False, "error": str(e)}

def get_random_content():
    """Get random content (quote or joke) from the database"""
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        # Choose randomly between quotes and jokes
        collection = "quotes" if datetime.datetime.now().second % 2 == 0 else "jokes"
        
        # Get random content
        content = conn.execute(
            f'SELECT * FROM {collection} ORDER BY RANDOM() LIMIT 1'
        ).fetchone()
        
        conn.close()
        
        if not content:
            logger.warning(f"No content found in {collection} table")
            return None
            
        return {
            "text": content['text'],
            "type": "quote" if collection == "quotes" else "joke"
        }
        
    except Exception as e:
        logger.error(f"Error getting random content: {e}")
        if conn:
            conn.close()
        return None

def log_post(tweet_id, tweet, price, price_change, content_type):
    """Log a successful post to the database"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        conn.execute(
            'INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (tweet_id, tweet, datetime.datetime.utcnow().isoformat(), price, price_change, content_type, 0, 0)
        )
        conn.commit()
        
        # Update bot status
        conn.execute(
            'INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)',
            (datetime.datetime.utcnow().isoformat(), 'Running', f'Manual tweet posted: {tweet_id}')
        )
        conn.commit()
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error logging post: {e}")
        if conn:
            conn.close()
        return False

def tweet_now():
    """Post a tweet now"""
    logger.info("Starting manual tweet process...")
    
    # Fetch Bitcoin price
    price_data = fetch_bitcoin_price()
    if not price_data["success"]:
        logger.error(f"Failed to fetch Bitcoin price: {price_data.get('error', 'Unknown error')}")
        return False
        
    # Get random content
    content = get_random_content()
    if not content:
        logger.error("Failed to get random content")
        return False
        
    # Post the tweet
    logger.info(f"Posting tweet with content: {content['text']}")
    result = tweet_handler_direct.post_tweet(
        content=content["text"],
        content_type=content["type"],
        price=price_data["price"]
    )
    
    if result["success"]:
        logger.info(f"Tweet posted successfully! Tweet ID: {result['tweet_id']}")
        
        # Log the post
        if log_post(
            result['tweet_id'], 
            result['tweet'], 
            price_data["price"], 
            price_data["price_change"], 
            content["type"]
        ):
            logger.info("Post logged successfully")
        else:
            logger.warning("Failed to log post to database")
            
        return True
    else:
        logger.error(f"Failed to post tweet: {result.get('error', 'Unknown error')}")
        return False

if __name__ == "__main__":
    print("BTCBuzzBot - Tweet Now Utility")
    print("-" * 40)
    
    success = tweet_now()
    
    if success:
        print("✅ Tweet posted successfully!")
    else:
        print("❌ Tweet posting failed!")
        sys.exit(1) 