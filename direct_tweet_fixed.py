"""
Enhanced direct tweet script for BTCBuzzBot with proper database logging.
This script ensures that tweets are properly logged to the database to appear in the web interface.
"""

import os
import sys
import time
import traceback
import sqlite3
from datetime import datetime, timedelta
import json
import random
import tweepy

# Make sure Python can find modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not available, relying on system environment variables")

def log_to_database(tweet_id, tweet_text, price, price_change):
    """Log tweet to database with improved error handling"""
    try:
        db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
        print(f"Logging tweet to database at {db_path}")
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check and fix posts table schema
        cursor.execute("PRAGMA table_info(posts)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"Found columns: {column_names}")
        
        # Add 'content' column if missing
        if 'content' not in column_names:
            print("Adding 'content' column to posts table")
            cursor.execute("ALTER TABLE posts ADD COLUMN content TEXT NOT NULL DEFAULT ''")
            conn.commit()
        
        # Get the posts table schema for debugging
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'")
        schema = cursor.fetchone()
        if schema:
            print(f"Posts table schema: {schema[0]}")
        else:
            print("Warning: Could not retrieve posts table schema")
        
        # Determine which schema we're using based on available columns
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract content from the tweet with proper error handling
        content_lines = tweet_text.split('\n') if tweet_text else [""]
        price_line = content_lines[0] if content_lines else ""  # e.g. "BTC: $84,500.00 | -0.67% 📉"
        content = content_lines[1] if len(content_lines) > 1 else ""  # The quote part
        
        content_type = "regular"  # Default content type
        
        # Check for specific content markers
        if content and any(marker in content.lower() for marker in ["hodl", "moon", "diamond", "hands", "crypto"]):
            content_type = "quote"
        elif content and any(marker in content.lower() for marker in ["joke", "laugh", "funny", "humor"]):
            content_type = "joke"
        
        if 'tweet' in column_names:
            print("Using original schema with tweet field")
            try:
                cursor.execute('''
                    INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (tweet_id, tweet_text, current_timestamp, price, price_change, content_type, 0, 0, content))
                conn.commit()
                print("✅ Successfully inserted post with original schema")
            except sqlite3.Error as e:
                print(f"⚠️ Error inserting post with original schema: {e}")
                # Try alternative schema
                try:
                    # Check if we have all required columns before inserting
                    required_columns = ["tweet_id", "timestamp", "price", "price_change", "content_type"]
                    if all(col in column_names for col in required_columns):
                        cursor.execute('''
                            INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (tweet_id, tweet_text, current_timestamp, price, price_change, content_type))
                        conn.commit()
                        print("✅ Successfully inserted post with minimal schema")
                    else:
                        missing_cols = [col for col in required_columns if col not in column_names]
                        print(f"❌ Missing required columns in posts table: {', '.join(missing_cols)}")
                        raise ValueError(f"Cannot insert: missing columns {missing_cols}")
                except sqlite3.Error as e2:
                    print(f"❌ Error with minimal schema: {e2}")
                    raise
        elif 'content' in column_names:
            print("Using newer schema with content field")
            try:
                # Check if we have all required columns before inserting
                required_columns = ["tweet_id", "timestamp", "price", "price_change", "content_type", "content"]
                if all(col in column_names for col in required_columns):
                    cursor.execute('''
                        INSERT INTO posts (tweet_id, timestamp, price, price_change, content_type, likes, retweets, content)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (tweet_id, current_timestamp, price, price_change, content_type, 0, 0, tweet_text))
                    conn.commit()
                    print("✅ Successfully inserted post with content schema")
                else:
                    missing_cols = [col for col in required_columns if col not in column_names]
                    print(f"⚠️ Missing some columns in posts table: {', '.join(missing_cols)}")
                    
                    # Try with just the available columns
                    available_cols = [col for col in required_columns if col in column_names]
                    placeholders = ", ".join(["?"] * len(available_cols))
                    columns_str = ", ".join(available_cols)
                    
                    values = []
                    for col in available_cols:
                        if col == "tweet_id": values.append(tweet_id)
                        elif col == "timestamp": values.append(current_timestamp)
                        elif col == "price": values.append(price)
                        elif col == "price_change": values.append(price_change)
                        elif col == "content_type": values.append(content_type)
                        elif col == "content": values.append(tweet_text)
                    
                    cursor.execute(f"INSERT INTO posts ({columns_str}) VALUES ({placeholders})", values)
                    conn.commit()
                    print(f"✅ Inserted post with available columns: {columns_str}")
            except sqlite3.Error as e:
                print(f"❌ Error inserting post with content schema: {e}")
                raise
                
        # Log price data to prices table
        try:
            # Check if the currency column exists in the prices table
            cursor.execute("PRAGMA table_info(prices)")
            price_columns = cursor.fetchall()
            price_column_names = [col[1] for col in price_columns]
            
            # Check if source column exists
            source_exists = 'source' in price_column_names
            currency_exists = 'currency' in price_column_names
            
            # Default values
            source_value = "CoinGecko"
            currency_value = "USD"
            
            if source_exists and currency_exists:
                cursor.execute('''
                    INSERT INTO prices (price, timestamp, source, currency)
                    VALUES (?, ?, ?, ?)
                ''', (price, current_timestamp, source_value, currency_value))
            elif source_exists:
                cursor.execute('''
                    INSERT INTO prices (price, timestamp, source)
                    VALUES (?, ?, ?)
                ''', (price, current_timestamp, source_value))
            elif currency_exists:
                cursor.execute('''
                    INSERT INTO prices (price, timestamp, currency)
                    VALUES (?, ?, ?)
                ''', (price, current_timestamp, currency_value))
            else:
                cursor.execute('''
                    INSERT INTO prices (price, timestamp)
                    VALUES (?, ?)
                ''', (price, current_timestamp))
            
            conn.commit()
            print("✅ Successfully logged price data")
        except sqlite3.Error as e:
            print(f"⚠️ Could not log price data: {e}")
        
        # Update bot status
        try:
            # Calculate next scheduled run - 4 hours from now
            next_scheduled = (datetime.now() + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if bot_status table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_status'")
            if not cursor.fetchone():
                # Create bot_status table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE bot_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        next_scheduled_run TEXT,
                        message TEXT
                    )
                ''')
                conn.commit()
            
            # Check the schema of the bot_status table
            cursor.execute("PRAGMA table_info(bot_status)")
            bot_status_columns = [col[1] for col in cursor.fetchall()]
            
            # Check if there's an existing status record
            cursor.execute("SELECT COUNT(*) FROM bot_status")
            if cursor.fetchone()[0] > 0:
                # Check which columns exist and create appropriate update statement
                if all(col in bot_status_columns for col in ["status", "timestamp", "next_scheduled_run", "message"]):
                    cursor.execute('''
                        INSERT INTO bot_status (timestamp, status, next_scheduled_run, message)
                        VALUES (?, ?, ?, ?)
                    ''', (current_timestamp, 'Running', next_scheduled, f"Posted tweet with ID: {tweet_id}"))
                else:
                    # Create a simpler query with available columns
                    available_cols = []
                    values = []
                    
                    if "timestamp" in bot_status_columns:
                        available_cols.append("timestamp")
                        values.append(current_timestamp)
                    
                    if "status" in bot_status_columns:
                        available_cols.append("status")
                        values.append("Running")
                    
                    if "next_scheduled_run" in bot_status_columns:
                        available_cols.append("next_scheduled_run")
                        values.append(next_scheduled)
                    
                    if "message" in bot_status_columns:
                        available_cols.append("message")
                        values.append(f"Posted tweet with ID: {tweet_id}")
                    
                    if available_cols:
                        columns_str = ", ".join(available_cols)
                        placeholders = ", ".join(["?"] * len(available_cols))
                        cursor.execute(f"INSERT INTO bot_status ({columns_str}) VALUES ({placeholders})", values)
            else:
                # Insert new status record
                cursor.execute('''
                    INSERT INTO bot_status (timestamp, status, next_scheduled_run, message)
                    VALUES (?, ?, ?, ?)
                ''', (current_timestamp, 'Running', next_scheduled, f"Posted tweet with ID: {tweet_id}"))
            
            conn.commit()
            print("✅ Successfully updated bot status")
        except sqlite3.Error as e:
            print(f"⚠️ Could not update bot status: {e}")
        
        conn.close()
        print(f"✅ Successfully logged tweet {tweet_id} to database")
        return True
        
    except Exception as e:
        print(f"❌ Error logging to database: {e}")
        # Emergency fix - create a backup file if we can't log to database
        try:
            # Try to create an emergency_posts table if it doesn't exist
            try:
                emergency_conn = sqlite3.connect(db_path)
                emergency_cursor = emergency_conn.cursor()
                emergency_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS emergency_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tweet_id TEXT NOT NULL,
                        tweet TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        error TEXT
                    )
                ''')
                emergency_cursor.execute('''
                    INSERT INTO emergency_posts (tweet_id, tweet, timestamp, error)
                    VALUES (?, ?, ?, ?)
                ''', (tweet_id, tweet_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), str(e)))
                emergency_conn.commit()
                emergency_conn.close()
                print("✅ Saved to emergency_posts table")
            except Exception as e2:
                print(f"❌ Emergency table failed: {e2}")
                
            # Also try writing to a text file
            with open('emergency_tweets.txt', 'a') as f:
                f.write(f"TWEET ID: {tweet_id}\n")
                f.write(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"CONTENT: {tweet_text}\n")
                f.write(f"ERROR: {e}\n")
                f.write("-" * 50 + "\n")
            print("✅ Saved to emergency_tweets.txt")
        except Exception as e3:
            print(f"❌ All emergency backups failed: {e3}")
        
        return False

def post_tweet():
    """
    Post a tweet about the current BTC price and a motivational quote.
    Selected based on price movement trend.
    Returns: boolean indicating success or failure
    """
    try:
        # Get auth from .env file
        load_dotenv()
        
        # Log env var availability for debugging
        twitter_creds = {
            'TWITTER_API_KEY': os.environ.get('TWITTER_API_KEY'),
            'TWITTER_API_SECRET': os.environ.get('TWITTER_API_SECRET'),
            'TWITTER_ACCESS_TOKEN': os.environ.get('TWITTER_ACCESS_TOKEN'),
            'TWITTER_ACCESS_SECRET': os.environ.get('TWITTER_ACCESS_SECRET'),
        }
        
        # Check if all Twitter credentials are available
        missing_creds = [k for k, v in twitter_creds.items() if not v]
        if missing_creds:
            print(f"ERROR: Missing Twitter credentials: {', '.join(missing_creds)}")
            return False
            
        # Connect to the database and get the current BTC price
        conn = sqlite3.connect("btcbuzzbot.db")
        conn.row_factory = sqlite3.Row
        
        # Get the most recent BTC price
        last_row = conn.execute("""
            SELECT * FROM price_data
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()
        btc_price = round(last_row["price"], 2)
        
        # Get the previous BTC price for comparison
        previous_row = conn.execute("""
            SELECT * FROM price_data
            WHERE id < ?
            ORDER BY id DESC
            LIMIT 1
        """, (last_row["id"],)).fetchone()
        
        if previous_row:
            previous_price = round(previous_row["price"], 2)
            price_change = ((btc_price - previous_price) / previous_price) * 100
            price_change = round(price_change, 2)
        else:
            # If no previous price, assume 0% change
            price_change = 0.0
        
        # Load message templates from JSON file
        template_key = "BTC_UP" if price_change >= 0 else "BTC_DOWN"
        emoji = "📈" if price_change >= 0 else "📉"
        
        try:
            # Try to load templates
            if os.path.exists('tweet_templates.json'):
                with open('tweet_templates.json', 'r') as f:
                    templates = json.load(f)
                
                if template_key in templates and templates[template_key]:
                    quote = random.choice(templates[template_key])
                else:
                    # Fallback quotes
                    if price_change >= 0:
                        quote = "Stay bullish, Bitcoin is on the rise! #HODL"
                    else:
                        quote = "Buy the dip! These prices won't last forever. #BTFD"
            else:
                # Fallback quotes if file not found
                if price_change >= 0:
                    quote = "Bitcoin going up! This is the way. #BTC"
                else:
                    quote = "Temporary dip, long-term gains. Keep stacking sats! #Bitcoin"
        except Exception as e:
            print(f"Error loading templates: {e}")
            # Fallback quotes if error
            if price_change >= 0:
                quote = "Number go up! Bitcoin doing what it does best. #BTC"
            else:
                quote = "Weak hands sell, strong hands accumulate. Diamond hands win! #BTC"
        
        # Format the tweet
        tweet = f"BTC: ${btc_price:,.2f}"
        
        # Add price change
        tweet += f" | {price_change:+.2f}% {emoji}"
        
        # Add quote
        tweet += f"\n{quote}"
        
        # If quote doesn't already include hashtags, add some
        if "#" not in quote:
            if "bitcoin" not in quote.lower() and "btc" not in quote.lower():
                tweet += " #Bitcoin"
            if "btc" not in quote.lower() and "bitcoin" not in quote.lower():
                tweet += " #BTC"
        
        print(f"Generated tweet: {tweet}")
        
        # Post the tweet using the Twitter API
        try:
            print("Authenticating with Twitter API...")
            auth = tweepy.OAuth1UserHandler(
                os.environ.get("TWITTER_API_KEY"),
                os.environ.get("TWITTER_API_SECRET"),
                os.environ.get("TWITTER_ACCESS_TOKEN"),
                os.environ.get("TWITTER_ACCESS_SECRET")
            )
            
            api = tweepy.API(auth)
            print("Posting tweet...")
            
            try:
                response = api.update_status(tweet)
                tweet_id = response.id_str
                print(f"Tweet posted successfully with ID: {tweet_id}")
                
                # Store the tweet in the database
                current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute(
                    'INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (tweet_id, tweet, current_timestamp, btc_price, price_change, "quote", 0, 0, quote)
                )
                conn.commit()
                
                # Update bot status
                conn.execute(
                    'INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)',
                    (current_timestamp, 'Running', f'Tweet posted with ID: {tweet_id}')
                )
                conn.commit()
                
                return True
            except tweepy.errors.TweepyException as e:
                print(f"Tweepy Error: {type(e).__name__}: {e}")
                # Get more details from the exception
                if hasattr(e, 'response'):
                    if hasattr(e.response, 'text'):
                        print(f"Response text: {e.response.text}")
                    if hasattr(e.response, 'status_code'):
                        print(f"Status code: {e.response.status_code}")
                # Check for rate limiting
                if hasattr(e, 'api_codes') and 88 in e.api_codes:
                    print("Rate limit exceeded")
                # Check for duplicate tweet
                if hasattr(e, 'api_codes') and 187 in e.api_codes:
                    print("Duplicate tweet detected")
                
                # Log the error to the database
                current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute(
                    'INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)',
                    (current_timestamp, 'Error', f'Tweet failed: {str(e)}')
                )
                conn.commit()
                
                return False
                
        except Exception as general_tweet_error:
            print(f"Unexpected error when posting tweet: {type(general_tweet_error).__name__}: {general_tweet_error}")
            
            # Log the error to the database
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                'INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)',
                (current_timestamp, 'Error', f'Tweet failed: {str(general_tweet_error)}')
            )
            conn.commit()
            
            return False
            
    except Exception as e:
        print(f"Error in post_tweet: {type(e).__name__}: {e}")
        
        try:
            # Try to log to database if connection exists
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect("btcbuzzbot.db")
            conn.execute(
                'INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)',
                (current_timestamp, 'Error', f'Error in post_tweet: {str(e)}')
            )
            conn.commit()
            conn.close()
        except:
            # If even logging fails, just print to console
            print("Could not log error to database")
            
        return False
    finally:
        # Close the database connection if it exists
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    success = post_tweet()
    
    if success:
        print("\n✅ Tweet posted successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tweet posting failed!")
        sys.exit(1) 