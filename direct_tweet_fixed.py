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
    """Post a tweet directly using the Twitter API and log to database"""
    print(f"---- Direct Tweet Fixed Script - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ----")
    
    # Flag to track if we're in simulation mode
    simulation_mode = False
    
    # Try importing tweepy - required for this script
    try:
        # First try normal import
        try:
            import tweepy
            print("✅ Tweepy imported successfully!")
        except ImportError:
            # If that fails, set simulation mode
            print("⚠️ Tweepy not found, running in SIMULATION MODE (will log to DB but not post tweets)")
            simulation_mode = True
            
    except Exception as e:
        print(f"⚠️ Failed to import tweepy: {e}")
        print("Running in SIMULATION MODE (will log to DB but not post tweets)")
        simulation_mode = True
    
    # Initialize price variables
    btc_price = 84500.00  # Default price if can't fetch
    price_change = 0.0
    requests_available = False
    
    # Try importing requests for price fetch
    try:
        import requests
        requests_available = True
        print("✅ Requests imported successfully!")
    except ImportError as e:
        print(f"❌ Failed to import requests: {e}")
        print("Will use sample price since requests module is unavailable")
        
    # Twitter API credentials - from environment variables
    try:
        API_KEY = os.environ.get('TWITTER_API_KEY', '')
        API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
        ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
        ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
        
        # Print first and last few chars of credentials for debugging
        if not simulation_mode:
            # Safely print part of the credentials
            def safe_truncate(text, show_chars=3):
                if not text:
                    return "MISSING"
                if len(text) <= show_chars * 2:
                    return "TOO SHORT"
                return f"{text[:show_chars]}...{text[-show_chars:]}"
            
            print(f"API Key: {safe_truncate(API_KEY)}")
            print(f"API Secret: {safe_truncate(API_SECRET)}")
            print(f"Access Token: {safe_truncate(ACCESS_TOKEN)}")
            print(f"Access Token Secret: {safe_truncate(ACCESS_TOKEN_SECRET)}")
        
        # Check if credentials are set (only if not in simulation mode)
        if not simulation_mode and not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
            missing = []
            if not API_KEY: missing.append("TWITTER_API_KEY")
            if not API_SECRET: missing.append("TWITTER_API_SECRET")
            if not ACCESS_TOKEN: missing.append("TWITTER_ACCESS_TOKEN")
            if not ACCESS_TOKEN_SECRET: missing.append("TWITTER_ACCESS_TOKEN_SECRET")
            
            print(f"⚠️ Missing Twitter API credentials: {', '.join(missing)}")
            print("Running in SIMULATION MODE (will log to DB but not post tweets)")
            simulation_mode = True
    except Exception as e:
        print(f"⚠️ Error getting Twitter credentials: {e}")
        print("Running in SIMULATION MODE (will log to DB but not post tweets)")
        simulation_mode = True
    
    # Fetch Bitcoin price if requests is available
    if requests_available:
        try:
            print("Fetching Bitcoin price from CoinGecko...")
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", 
                                  timeout=10)
            # Check for successful response
            if response.status_code == 200:
                data = response.json()
                if "bitcoin" in data and "usd" in data["bitcoin"]:
                    btc_price = data["bitcoin"]["usd"]
                    print(f"✅ Current BTC price: ${btc_price:,.2f}")
                else:
                    print("⚠️ Unexpected response format from CoinGecko, using default price")
            else:
                print(f"⚠️ CoinGecko API returned status code {response.status_code}, using default price")
            
            # Try to get previous price from database to calculate change
            try:
                db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT price FROM prices ORDER BY timestamp DESC LIMIT 1')
                prev_price_record = cursor.fetchone()
                conn.close()
                
                if prev_price_record:
                    prev_price = prev_price_record[0]
                    price_change = ((btc_price - prev_price) / prev_price) * 100
                    print(f"Previous price: ${prev_price:,.2f}, Change: {price_change:+.2f}%")
                else:
                    print("No previous price record found")
            except Exception as e:
                print(f"Error fetching previous price: {e}")
        except Exception as e:
            print(f"❌ Error fetching Bitcoin price: {e}")
            # Use sample price
            print(f"Using sample price: ${btc_price:,.2f}")
    else:
        # If requests module is not available, use sample price and try to get change from DB
        print(f"Using sample price: ${btc_price:,.2f}")
        try:
            db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT price FROM prices ORDER BY timestamp DESC LIMIT 1')
            prev_price_record = cursor.fetchone()
            conn.close()
            
            if prev_price_record:
                prev_price = prev_price_record[0]
                price_change = ((btc_price - prev_price) / prev_price) * 100
                print(f"Previous price: ${prev_price:,.2f}, Change: {price_change:+.2f}%")
            else:
                print("No previous price record found, using default 0% change")
        except Exception as e:
            print(f"Error fetching previous price: {e}")
    
    # Create tweet content
    try:
        # Try to load message templates from tweet_templates.json
        try:
            import json
            templates_file = 'tweet_templates.json'
            
            if os.path.exists(templates_file):
                with open(templates_file, 'r') as f:
                    templates = json.load(f)
                
                # Choose template based on price movement
                if price_change >= 0:
                    template_key = "BTC_UP"
                    emoji = "📈"
                else:
                    template_key = "BTC_DOWN"
                    emoji = "📉"
                
                if template_key in templates and templates[template_key]:
                    quote = random.choice(templates[template_key])
                    print(f"Using template from {template_key}")
                else:
                    # Fallback to default quotes
                    print("Template not found in JSON, using fallback quotes")
                    fallback_quotes = [
                        "HODL to the moon! 🚀",
                        "Buy the dip, enjoy the trip. 📈",
                        "In crypto we trust. 💎",
                        "Not your keys, not your coins. 🔑",
                        "Blockchain is not just a technology, it's a revolution. ⚡",
                        "Bitcoin fixes this. 🧠",
                        "Diamond hands win in the long run. 💎🙌",
                        "Fear is temporary, regret is forever. 🤔",
                        "The best time to buy Bitcoin was yesterday. The second best time is today. ⏰",
                        "Time in the market beats timing the market. ⌛"
                    ]
                    quote = random.choice(fallback_quotes)
            else:
                # File doesn't exist, use default quotes
                print(f"Template file {templates_file} not found, using default quotes")
                default_quotes = [
                    "HODL to the moon! 🚀",
                    "Buy the dip, enjoy the trip. 📈",
                    "In crypto we trust. 💎",
                    "Not your keys, not your coins. 🔑",
                    "Blockchain is not just a technology, it's a revolution. ⚡",
                    "Bitcoin fixes this. 🧠",
                    "Diamond hands win in the long run. 💎🙌",
                    "Fear is temporary, regret is forever. 🤔",
                    "The best time to buy Bitcoin was yesterday. The second best time is today. ⏰",
                    "Time in the market beats timing the market. ⌛"
                ]
                quote = random.choice(default_quotes)
                emoji = "📈" if price_change >= 0 else "📉"
        except Exception as template_error:
            # If any error occurs with templates, fall back to default quotes
            print(f"Error loading templates: {template_error}, using default quotes")
            fallback_quotes = [
                "HODL to the moon! 🚀",
                "Buy the dip, enjoy the trip. 📈",
                "In crypto we trust. 💎",
                "Not your keys, not your coins. 🔑",
                "Blockchain is not just a technology, it's a revolution. ⚡",
                "Bitcoin fixes this. 🧠",
                "Diamond hands win in the long run. 💎🙌",
                "Fear is temporary, regret is forever. 🤔",
                "The best time to buy Bitcoin was yesterday. The second best time is today. ⏰",
                "Time in the market beats timing the market. ⌛"
            ]
            quote = random.choice(fallback_quotes)
            emoji = "📈" if price_change >= 0 else "📉"
        
        # Format the tweet
        tweet = f"BTC: ${btc_price:,.2f}"
        
        # Add price change if available
        if price_change != 0.0:
            tweet += f" | {price_change:+.2f}% {emoji}"
            
        # Add quote
        tweet += f"\n{quote}"
        
        # If the quote doesn't already contain hashtags, add standard ones
        if "#Bitcoin" not in quote and "#BTC" not in quote:
            tweet += "\n#Bitcoin #Crypto"
        
        # Validate tweet length (Twitter limit is 280 characters)
        if len(tweet) > 280:
            # Truncate the quote if needed
            max_quote_length = 280 - (len(tweet) - len(quote))
            quote_truncated = quote[:max_quote_length-3] + "..."
            tweet = f"BTC: ${btc_price:,.2f}"
            if price_change != 0.0:
                tweet += f" | {price_change:+.2f}% {emoji}"
            tweet += f"\n{quote_truncated}"
            
            # Add hashtags only if there's room and they're not in the quote
            if len(tweet) < 268 and "#Bitcoin" not in quote and "#BTC" not in quote:
                tweet += "\n#Bitcoin #Crypto"
        
        print(f"Tweet content: {tweet}")
    except Exception as e:
        print(f"❌ Error creating tweet content: {e}")
        return False
    
    # If we're in simulation mode, just log to database without posting
    if simulation_mode:
        print("SIMULATION MODE: Skipping actual tweet posting")
        # Generate a simulated tweet ID using timestamp
        simulated_tweet_id = f"sim_{int(time.time())}"
        print(f"Simulated Tweet ID: {simulated_tweet_id}")
        
        # Log to database
        print("Logging simulated tweet to database...")
        log_success = log_to_database(
            tweet_id=simulated_tweet_id,
            tweet_text=tweet,
            price=btc_price,
            price_change=price_change
        )
        
        if log_success:
            print("✅ Simulated tweet successfully logged to database")
            return True
        else:
            print("❌ Failed to log simulated tweet to database")
            return False
    
    # Post the tweet if not in simulation mode
    try:
        print("Creating Twitter API client...")
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        
        print("Posting tweet...")
        response = client.create_tweet(text=tweet)
        
        if response and hasattr(response, 'data') and 'id' in response.data:
            tweet_id = response.data['id']
            print(f"✅ Tweet successfully posted with ID: {tweet_id}")
            print(f"Tweet URL: https://twitter.com/i/web/status/{tweet_id}")
            
            # Log to database
            print("Logging tweet to database...")
            log_success = log_to_database(
                tweet_id=tweet_id,
                tweet_text=tweet,
                price=btc_price,
                price_change=price_change
            )
            
            if log_success:
                print("✅ Tweet successfully logged to database")
            else:
                print("⚠️ Tweet posted but failed to log to database")
                
            return True
        else:
            print(f"❌ Failed to post tweet - unexpected response format: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Error posting tweet: {e}")
        traceback.print_exc()
        
        # Try to log as a simulated tweet if actual posting fails
        print("Attempting to log as a simulated tweet instead...")
        simulated_tweet_id = f"fail_{int(time.time())}"
        log_success = log_to_database(
            tweet_id=simulated_tweet_id,
            tweet_text=tweet,
            price=btc_price,
            price_change=price_change
        )
        
        if log_success:
            print("✅ Failed tweet logged to database as a record")
            return True
        
        return False

if __name__ == "__main__":
    success = post_tweet()
    
    if success:
        print("\n✅ Tweet posted successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tweet posting failed!")
        sys.exit(1) 