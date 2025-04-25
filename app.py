import os
import sqlite3
import datetime
import time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import asyncio
import json
import logging
from collections import defaultdict
from datetime import timedelta, timezone

# Database imports
import psycopg2
from psycopg2.extras import RealDictCursor
import tweepy
from src.database import Database

# Import requests with proper error handling
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests module not available - external API functionality will be limited")

# Import load_dotenv from dotenv
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__, static_folder=os.environ.get('STATIC_FOLDER', 'static'), template_folder=os.environ.get('TEMPLATE_FOLDER', 'templates'))
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

# --- START DB Configuration ---
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_POSTGRES = False
if DATABASE_URL:
    # Fix Heroku's postgres:// prefix
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    IS_POSTGRES = True
    print("DATABASE_URL detected. Using PostgreSQL for Flask app.")
else:
    SQLITE_DB_PATH = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
    print(f"No DATABASE_URL found. Using SQLite ({SQLITE_DB_PATH}) for Flask app.")
# --- END DB Configuration ---

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Database helper functions
def get_db_connection():
    """Get a database connection (PostgreSQL or SQLite)"""
    if IS_POSTGRES:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            print(f"Error connecting to PostgreSQL: {e}")
            # Potentially add fallback to parsed URL components if needed, similar to src/database.py
            raise # Re-raise the exception to indicate connection failure
    else:
        # SQLite connection
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row # Keep row factory for SQLite
        return conn

def init_db():
    """Initialize database with required tables for web interface (PostgreSQL/SQLite)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Common table creation logic (using standard SQL compatible types)
            # Bot Logs Table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_logs (
                id {pg_id_type} PRIMARY KEY {pg_autoincrement},
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
            '''.format(
                pg_id_type="SERIAL" if IS_POSTGRES else "INTEGER",
                pg_autoincrement="" if IS_POSTGRES else "AUTOINCREMENT"
            ))

            # Bot Status Table (used by web interface)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_status (
                id {pg_id_type} PRIMARY KEY {pg_autoincrement},
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                next_scheduled_run TEXT,
                message TEXT
            )
            '''.format(
                pg_id_type="SERIAL" if IS_POSTGRES else "INTEGER",
                pg_autoincrement="" if IS_POSTGRES else "AUTOINCREMENT"
            ))

            # Scheduler Config Table (used by web interface)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduler_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            ''')

            # Note: The core tables like 'posts', 'prices', 'quotes', 'jokes' 
            # are primarily managed by the worker (src/database.py). 
            # We might want to consolidate table creation later, but for now, 
            # ensure web-specific tables exist.
            
            # Insert default schedule if not present
            config_query = "SELECT value FROM scheduler_config WHERE key = %s" if IS_POSTGRES else "SELECT value FROM scheduler_config WHERE key = ?"
            cursor.execute(config_query, ('schedule',))
            config = cursor.fetchone()
            if not config:
                default_schedule = '08:00,12:00,16:00,20:00'
                insert_schedule_query = "INSERT INTO scheduler_config (key, value) VALUES (%s, %s)" if IS_POSTGRES else "INSERT INTO scheduler_config (key, value) VALUES (?, ?)"
                cursor.execute(
                    insert_schedule_query,
                    ('schedule', default_schedule)
                )
            
            conn.commit() # Commit changes
            cursor.close()
            print("Web interface database tables checked/initialized.")
    except Exception as e:
        print(f"Error initializing web database: {e}")
        # Ensure connection is closed if open
        # (context manager 'with get_db_connection()' should handle this)

# Helper functions for bot data
def get_bot_status():
    """Get the current bot status"""
    try:
        with get_db_connection() as conn:
            # Use RealDictCursor for PostgreSQL to get dict-like rows
            cursor_factory = RealDictCursor if IS_POSTGRES else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            
            # Adjust query syntax for placeholders
            status_query = "SELECT * FROM bot_status ORDER BY timestamp DESC LIMIT 1"
            cursor.execute(status_query)
            status_row = cursor.fetchone()
            
            # If no status exists, return a default
            if not status_row:
                cursor.close()
                return {
                    'status': 'Unknown',
                    'timestamp': datetime.datetime.utcnow().isoformat(),
                    'next_scheduled_run': None,
                    'message': 'Bot status not available'
                }
            
            # Check if we have a scheduled status
            scheduled_query = "SELECT * FROM bot_status WHERE status = 'Scheduled' ORDER BY timestamp DESC LIMIT 1"
            cursor.execute(scheduled_query)
            scheduled_status_row = cursor.fetchone()
            cursor.close()
            
            result = dict(status_row)
            
            # Add next_scheduled_run from the scheduled status if available
            if scheduled_status_row and 'next_scheduled_run' in scheduled_status_row and scheduled_status_row['next_scheduled_run']:
                result['next_scheduled_run'] = scheduled_status_row['next_scheduled_run']
                
            return result
    except Exception as e:
        print(f"Error getting bot status: {e}")
        # Return a fallback status
        return {
            'status': 'Error',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'next_scheduled_run': None,
            'message': f'Error retrieving status: {str(e)}'
        }

def get_recent_posts(limit=10):
    """Get recent posts from the database"""
    with get_db_connection() as conn:
        cursor_factory = RealDictCursor if IS_POSTGRES else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        query = "SELECT * FROM posts ORDER BY timestamp DESC LIMIT %s" if IS_POSTGRES else "SELECT * FROM posts ORDER BY timestamp DESC LIMIT ?"
        cursor.execute(query, (limit,))
        posts = cursor.fetchall()
        cursor.close()
        return [dict(post) for post in posts]

def get_potential_news(limit=10):
    """Get potential news tweets from the database (tweets marked as news)."""
    news_items = []
    try:
        with get_db_connection() as conn:
            cursor_factory = RealDictCursor if IS_POSTGRES else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            # Fetch recent tweets regardless of is_news status, order by fetched time
            query = """
                SELECT * FROM news_tweets 
                ORDER BY fetched_at DESC 
                LIMIT %s
            """ if IS_POSTGRES else """
                SELECT * FROM news_tweets 
                ORDER BY fetched_at DESC 
                LIMIT ?
            """
            cursor.execute(query, (limit,))
            news_items = cursor.fetchall()
            cursor.close()
            app.logger.info(f"Fetched {len(news_items)} potential news tweets from DB.")
    except Exception as e:
        app.logger.error(f"Error fetching potential news tweets: {e}", exc_info=True)
        # Return empty list on error to avoid breaking the template
        return []
    return news_items

def get_posts_paginated(page=1, per_page=10, date_from=None, date_to=None, content_type=None):
    """Get paginated posts with filtering"""
    with get_db_connection() as conn:
        cursor_factory = RealDictCursor if IS_POSTGRES else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        
        query = 'SELECT * FROM posts WHERE 1=1'
        params = []
        param_placeholder = "%s" if IS_POSTGRES else "?"
        
        # Apply filters
        if date_from:
            query += f' AND timestamp >= {param_placeholder}'
            params.append(date_from)
        if date_to:
            query += f' AND timestamp <= {param_placeholder}'
            params.append(date_to)
        if content_type:
            query += f' AND content_type = {param_placeholder}'
            params.append(content_type)
            
        # Count total matching records
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
        cursor.execute(count_query, params)
        total_result = cursor.fetchone()
        total = total_result['count'] if total_result else 0
        
        # Add pagination
        if IS_POSTGRES:
            query += ' ORDER BY timestamp DESC LIMIT %s OFFSET %s'
        else:
            query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
            
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        
        # Execute query
        cursor.execute(query, params)
        posts = cursor.fetchall()
        cursor.close()
        return [dict(post) for post in posts], total

def get_price_history(days=7):
    """Get Bitcoin price history for the specified number of days"""
    with get_db_connection() as conn:
        cursor_factory = RealDictCursor if IS_POSTGRES else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        
        param_placeholder = "%s" if IS_POSTGRES else "?"
        timestamp = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
        query = f'SELECT * FROM prices WHERE timestamp >= {param_placeholder} ORDER BY timestamp ASC'
        cursor.execute(query, (timestamp,))
        prices = cursor.fetchall()
        cursor.close()
        return [dict(price) for price in prices]

def fetch_bitcoin_price():
    """Fetch current Bitcoin price from CoinGecko API"""
    max_retries = int(os.environ.get("COINGECKO_RETRY_LIMIT", 3))
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            
            # Add CoinGecko API key to headers
            headers = {}
            api_key = os.environ.get("COINGECKO_API_KEY")
            if api_key:
                headers["x-cg-api-key"] = api_key
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            # Handle rate limiting
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    return {
                        "success": False,
                        "error": "Rate limit exceeded for CoinGecko API"
                    }
            
            # Handle other error status codes
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
            
            data = response.json()
            
            if "bitcoin" in data:
                price = data["bitcoin"]["usd"]
                price_change = data["bitcoin"].get("usd_24h_change", 0)
                
                return {
                    "success": True,
                    "price": price,
                    "price_change": price_change
                }
            else:
                return {
                    "success": False,
                    "error": "Bitcoin data not found in API response"
                }
        except requests.exceptions.RequestException as e:
            # Network error handling
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                return {
                    "success": False,
                    "error": f"Network error: {str(e)}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

def get_basic_stats():
    """Get basic statistics about the bot"""
    # Initialize default values
    stats = {
        'total_posts': 0,
        'total_quotes': 0,
        'total_jokes': 0,
        'avg_likes': 0,
        'avg_retweets': 0,
        'latest_price': None,
        'price_change': 0,
        'last_updated': None
    }

    try:
        with get_db_connection() as conn:
            cursor_factory = RealDictCursor if IS_POSTGRES else None
            # Use 'cursor' consistently now, define it once
            cursor = conn.cursor(cursor_factory=cursor_factory) 
            
            param_placeholder = "%s" if IS_POSTGRES else "?"
            
            # Totals
            cursor.execute('SELECT COUNT(*) FROM posts')
            total_posts_result = cursor.fetchone()
            stats['total_posts'] = total_posts_result['count'] if total_posts_result else 0
            
            cursor.execute('SELECT COUNT(*) FROM quotes')
            total_quotes_result = cursor.fetchone()
            stats['total_quotes'] = total_quotes_result['count'] if total_quotes_result else 0
            
            cursor.execute('SELECT COUNT(*) FROM jokes')
            total_jokes_result = cursor.fetchone()
            stats['total_jokes'] = total_jokes_result['count'] if total_jokes_result else 0
            
            # Average engagement
            cursor.execute('SELECT AVG(likes) FROM posts')
            avg_likes_result = cursor.fetchone()
            avg_likes = 0
            if avg_likes_result:
                avg_likes_val = avg_likes_result[0] if not IS_POSTGRES else avg_likes_result.get('avg')
                if avg_likes_val is not None:
                    avg_likes = avg_likes_val
            stats['avg_likes'] = round(avg_likes, 1)
            
            cursor.execute('SELECT AVG(retweets) FROM posts')
            avg_retweets_result = cursor.fetchone()
            avg_retweets = 0
            if avg_retweets_result:
                avg_retweets_val = avg_retweets_result[0] if not IS_POSTGRES else avg_retweets_result.get('avg')
                if avg_retweets_val is not None:
                    avg_retweets = avg_retweets_val
            stats['avg_retweets'] = round(avg_retweets, 1)
            
            # Most recent price & change calculation
            latest_price = None
            prev_price = None
            last_updated = None
            price_change = 0

            query_latest = "SELECT price, timestamp FROM prices ORDER BY timestamp DESC LIMIT 1"
            cursor.execute(query_latest)
            latest_price_row = cursor.fetchone()

            if latest_price_row:
                latest_price = latest_price_row['price']
                last_updated = latest_price_row['timestamp']
                
                query_prev = "SELECT price FROM prices ORDER BY timestamp DESC LIMIT 1 OFFSET 1"
                cursor.execute(query_prev)
                prev_price_row = cursor.fetchone()

                if prev_price_row:
                    prev_price = prev_price_row['price']
                    # Ensure prices are not None and prev_price is not zero before dividing
                    if latest_price is not None and prev_price is not None and prev_price != 0:
                         price_change = ((latest_price - prev_price) / prev_price) * 100
            
            # Update stats dictionary with price info
            stats['latest_price'] = latest_price
            stats['price_change'] = price_change
            stats['last_updated'] = last_updated
                
            cursor.close() # Close cursor after all queries

    except Exception as e:
        print(f"Error getting basic stats: {e}")
        # Return the initialized stats (with Nones/zeros) on error

    return stats # Return the stats dict (populated or default)

def get_recent_errors(limit=5):
    """Get recent error logs"""
    with get_db_connection() as conn:
        cursor_factory = RealDictCursor if IS_POSTGRES else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        param_placeholder = "%s" if IS_POSTGRES else "?"
        query = f"SELECT * FROM bot_logs WHERE level = 'ERROR' ORDER BY timestamp DESC LIMIT {param_placeholder}"
        cursor.execute(query, (limit,))
        errors = cursor.fetchall()
        cursor.close()
        return [dict(error) for error in errors]

def get_scheduler_config():
    """Get the scheduler configuration from the database"""
    config = {
        'post_times': '08:00,12:00,16:00,20:00', # Default
        'timezone': 'UTC' # Default
    }
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT value FROM scheduler_config WHERE key = %s" if IS_POSTGRES else "SELECT value FROM scheduler_config WHERE key = ?"
            cursor.execute(query, ('schedule',))
            schedule_row = cursor.fetchone()
            if schedule_row:
                config['post_times'] = schedule_row[0]
            # Add other config reads here if necessary (e.g., timezone)
            cursor.close()
    except Exception as e:
        print(f"Error reading scheduler config from DB: {e}. Using defaults.")
        
    # Split times into a list
    config['post_times'] = [t.strip() for t in config['post_times'].split(',')]
    return config

def post_tweet():
    """
    Manually trigger a tweet post from the web interface.
    Uses synchronous logic suitable for Flask.
    Returns: (success, info) tuple where info is a dict with tweet details or error message
    """
    
    # Load necessary config (API keys)
    # Re-check env vars as they might have changed
    load_dotenv()
    api_key = os.environ.get('TWITTER_API_KEY')
    api_secret = os.environ.get('TWITTER_API_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("ERROR: Twitter credentials missing for manual post.")
        return False, {'error': 'Twitter API credentials are not configured.'}
        
    try:
        # 1. Fetch current price (using existing sync function in app.py)
        print("Fetching price for manual tweet...")
        price_data = fetch_bitcoin_price() # This function uses requests (sync)
        if not price_data["success"]:
            print(f"Manual tweet failed: Could not fetch price - {price_data['error']}")
            return False, {'error': f"Could not fetch price: {price_data['error']}"}
            
        current_price = price_data["price"]
        price_change_24h = price_data["price_change"]
        print(f"Manual tweet price: ${current_price:,.2f}")
        
        # 2. Format Tweet (Simpler version for manual post, no random content)
        emoji = "📈" if price_change_24h >= 0 else "📉"
        # Basic tweet format for manual trigger
        tweet_text = f"Manual Trigger Test\nBTC: ${current_price:,.2f} | 24h: {price_change_24h:+.2f}% {emoji}\n#Bitcoin"
        
        # 3. Duplicate Check (Synchronous)
        print("Checking for recent posts (sync)...")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                now = datetime.datetime.utcnow()
                cutoff_time = (now - datetime.timedelta(minutes=5)).isoformat()
                
                if IS_POSTGRES:
                    cursor.execute("SELECT COUNT(*) FROM posts WHERE timestamp > %s", (cutoff_time,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM posts WHERE timestamp > ?", (cutoff_time,))
                
                count_result = cursor.fetchone()
                # Fix: Handle None result and access count correctly based on DB type
                count = 0
                if count_result:
                    if IS_POSTGRES:
                        count = count_result.get('count', 0)
                    else:
                        count = count_result[0] # SQLite returns a tuple
                     
                cursor.close()
                if count > 0:
                    print("Manual tweet skipped: Recent post found.")
                    return False, {'error': 'Skipped: A tweet was posted successfully in the last 5 minutes.'}
        except Exception as db_check_err:
            print(f"Warning: DB check for recent posts failed: {db_check_err}. Proceeding anyway.")
            # Decide if you want to block or allow if check fails

        # 4. Post Tweet (Synchronous Tweepy v2)
        print(f"Posting manual tweet: {tweet_text}")
        try:
            client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            response = client.create_tweet(text=tweet_text)
            
            if not response or not response.data or not response.data.get('id'):
                 print("Manual tweet failed: No valid response from Twitter API.")
                 return False, {'error': 'Failed to post tweet - no valid response from Twitter API.'}
                 
            tweet_id = response.data['id']
            print(f"Manual tweet posted successfully! ID: {tweet_id}")

        except tweepy.errors.TweepyException as e:
            print(f"Manual tweet failed: TweepyException - {e}")
            # Attempt to parse Twitter API error details
            error_detail = str(e)
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                try: error_detail = e.response.json() # Or e.response.text
                except: pass
            return False, {'error': f'Twitter API Error: {error_detail}'}
        except Exception as post_err:
             print(f"Manual tweet failed: Unexpected error during posting - {post_err}")
             return False, {'error': f'Unexpected error during posting: {str(post_err)}'}

        # 5. Log Post (Synchronous)
        print(f"Logging manual post {tweet_id} to DB...")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                timestamp = datetime.datetime.utcnow().isoformat()
                content_type = "manual" # Indicate it was a manual post
                
                if IS_POSTGRES:
                    query = "INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type) VALUES (%s, %s, %s, %s, %s, %s)"
                else:
                    query = "INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type) VALUES (?, ?, ?, ?, ?, ?)"
                    
                cursor.execute(query, (tweet_id, tweet_text, timestamp, current_price, price_change_24h, content_type))
                conn.commit()
                cursor.close()
                print("Manual post logged successfully.")
                return True, {'tweet_id': tweet_id, 'content': tweet_text}
                
        except Exception as db_log_err:
            print(f"ERROR: Failed to log manual tweet {tweet_id} to database: {db_log_err}")
            # Tweet was posted, but logging failed. Return success but mention logging error.
            return True, {'tweet_id': tweet_id, 'content': tweet_text, 'warning': 'Tweet posted but failed to log to DB.'}

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in post_tweet function: {e}")
        return False, {'error': str(e)}

# Routes - Home and About
@app.route('/')
def home():
    """Home page with about information and recent tweets"""
    stats = get_basic_stats()
    recent_posts = get_recent_posts(limit=5)
    
    return render_template('home.html', 
                          title='BTCBuzzBot - Bitcoin Price Twitter Bot',
                          stats=stats,
                          recent_posts=recent_posts)

# Routes - Posts
@app.route('/posts')
def posts():
    """Posts page with tweet history and filtering"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get filter parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    content_type = request.args.get('content_type')
    
    # Get posts with pagination and filtering
    posts, total = get_posts_paginated(page, per_page, date_from, date_to, content_type)
    
    # Get basic stats
    stats = get_basic_stats()
    
    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('posts.html',
                          title='Tweet History',
                          posts=posts,
                          stats=stats,
                          page=page,
                          per_page=per_page,
                          total=total,
                          total_pages=total_pages,
                          date_from=date_from,
                          date_to=date_to,
                          content_type=content_type)

# Routes - Admin Panel
@app.route('/admin')
@limiter.limit("30 per minute")
def admin_panel():
    """Display the admin panel"""
    logger = logging.getLogger(__name__) # Ensure logger is available
    logger.info("Admin panel accessed.")
    
    # Fetch existing data
    bot_status = get_bot_status()
    schedule = get_scheduler_config()
    errors = get_recent_errors(limit=10) 
    price_history = get_price_history(days=7)
    recent_posts = get_recent_posts(limit=5)
    potential_news_raw = get_potential_news(limit=25) # Fetch a bit more for trend calc

    # --- START Parse News Analysis and Calculate Trend ---
    processed_news_list = []
    sentiment_by_day = defaultdict(lambda: {'sum': 0.0, 'count': 0})
    logger.info(f"Processing {len(potential_news_raw)} potential news items for analysis display.")
    now_utc = datetime.now(timezone.utc)
    cutoff_date = now_utc - timedelta(days=7) # Trend for last 7 days

    for news_item in potential_news_raw:
        # Ensure news_item is mutable if it's not already a dict (it should be from RealDictCursor)
        if not isinstance(news_item, dict):
             news_item = dict(news_item) # Convert if necessary

        # Initialize placeholders
        news_item['parsed_significance'] = None
        news_item['parsed_sentiment'] = None
        news_item['parsed_summary'] = 'N/A'

        raw_analysis = news_item.get('llm_raw_analysis')
        if raw_analysis:
            try:
                # Check if raw_analysis is already a dict (from psycopg2 jsonb)
                if isinstance(raw_analysis, dict):
                     analysis = raw_analysis
                else:
                     analysis = json.loads(raw_analysis) # Parse if it's a string

                # --- Adjust keys based on ACTUAL Groq JSON output --- 
                significance = analysis.get('significance_score')
                sentiment = analysis.get('sentiment_score')
                summary = analysis.get('summary', 'N/A')
                # --- End key adjustment ---
                
                # Attempt conversion and store
                try:
                    if significance is not None:
                        news_item['parsed_significance'] = int(significance)
                except (ValueError, TypeError): pass # Ignore conversion errors
                
                try:
                    if sentiment is not None:
                        news_item['parsed_sentiment'] = float(sentiment)
                except (ValueError, TypeError): pass # Ignore conversion errors
                
                news_item['parsed_summary'] = summary
                
                # --- Add to sentiment trend calculation --- 
                pub_date = news_item.get('published_at')
                if pub_date and news_item['parsed_sentiment'] is not None:
                    # Ensure pub_date is timezone-aware (UTC) for comparison
                    if isinstance(pub_date, str):
                        try:
                            pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        except ValueError:
                            pub_date = None # Ignore if parse fails
                            
                    if pub_date:
                         if pub_date.tzinfo is None:
                              # Assume naive db timestamp is UTC if not PostgreSQL TIMESTAMPTZ
                              pub_date = pub_date.replace(tzinfo=timezone.utc) 
                              
                         # Ensure comparison is valid (both offset-aware or both naive)
                         if now_utc.tzinfo is not None and pub_date.tzinfo is not None:
                              comparison_possible = True
                         elif now_utc.tzinfo is None and pub_date.tzinfo is None:
                              comparison_possible = True
                         else:
                              comparison_possible = False # Mixed aware/naive - avoid comparison
                              logger.warning(f"Skipping sentiment trend calc for tweet {news_item.get('id', 'N/A')}: Mixed timezone awareness.")
                              
                         if comparison_possible and pub_date >= cutoff_date:
                            day_str = pub_date.strftime('%Y-%m-%d')
                            sentiment_by_day[day_str]['sum'] += news_item['parsed_sentiment']
                            sentiment_by_day[day_str]['count'] += 1
                            
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse llm_raw_analysis JSON for tweet ID {news_item.get('id', 'N/A')}")
            except Exception as parse_err:
                logger.error(f"Error processing analysis for tweet ID {news_item.get('id', 'N/A')}: {parse_err}", exc_info=True)
                
        processed_news_list.append(news_item) # Add the (potentially modified) item

    # --- Calculate average sentiment trend --- 
    sentiment_trend = []
    # Iterate through the last 7 days to ensure all days are present
    for i in range(7):
        day_obj = now_utc - timedelta(days=i)
        day_str = day_obj.strftime('%Y-%m-%d')
        if day_str in sentiment_by_day and sentiment_by_day[day_str]['count'] > 0:
            avg_score = sentiment_by_day[day_str]['sum'] / sentiment_by_day[day_str]['count']
            sentiment_trend.append({'date': day_str, 'score': avg_score})
        else:
             sentiment_trend.append({'date': day_str, 'score': None}) # Use None for days with no data

    sentiment_trend.reverse() # Show oldest first for trend display
    logger.debug(f"Calculated sentiment trend: {sentiment_trend}")
    # --- END Parse News Analysis and Calculate Trend ---

    # --- Fetch Quotes and Jokes --- 
    logger.info("Fetching quotes and jokes for admin panel.")
    quotes = []
    jokes = []
    try:
        db = Database() # Instantiate our Database class
        quotes = asyncio.run(db.get_all_quotes())
        jokes = asyncio.run(db.get_all_jokes())
        # No need to manually close, Database methods handle connections.
    except Exception as e:
        app.logger.error(f"Error fetching quotes/jokes for admin panel: {e}", exc_info=True)
        flash(f'Error fetching quotes/jokes: {e}', 'danger')
    # --- End Fetch Quotes and Jokes ---

    return render_template(
        'admin.html',
        title='Admin Panel',
        bot_status=bot_status,
        schedule=schedule,
        errors=errors,
        price_history=price_history,
        recent_posts=recent_posts,
        potential_news=processed_news_list, # Pass the processed list
        sentiment_trend=sentiment_trend, # Pass the trend data
        quotes=quotes, # Pass quotes
        jokes=jokes    # Pass jokes
    )

@app.route('/control_bot/<action>', methods=['GET', 'POST'])
def control_bot(action):
    """
    Control the Twitter Bot - tweet now
    """
    try:
        if action == 'tweet' or action == 'tweet_now':
            # Manual tweet trigger might still be useful
            success, tweet_info = post_tweet()
            if success:
                flash(f'Tweet posted successfully! Tweet ID: {tweet_info["tweet_id"]}', 'success')
            else:
                flash(f'Failed to post tweet: {tweet_info["error"]}', 'danger')
        else:
            flash('Invalid action!', 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin_panel'))

@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    """
    Update the scheduler configuration (schedule times) in the database
    """
    schedule_times_str = request.form.get('schedule_times') # Restore original line
    # schedule_times_str = '14:00' # TEMPORARY: Hardcode for testing - Remove this
    # app.logger.warning(f"TEMPORARY: Hardcoding schedule update to: {schedule_times_str}") # Remove log

    if not schedule_times_str:
        flash('Schedule times cannot be empty.', 'danger')
        return redirect(url_for('admin_panel'))
        
    # Basic validation (e.g., check HH:MM format)
    times = [t.strip() for t in schedule_times_str.split(',')]
    valid_times = []
    try:
        for t in times:
            hour, minute = map(int, t.split(':'))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                valid_times.append(f"{hour:02d}:{minute:02d}")
            else:
                raise ValueError("Invalid time format")
        if not valid_times:
             raise ValueError("No valid times provided")
    except ValueError:
        flash('Invalid schedule format. Use comma-separated HH:MM times (e.g., 08:00,12:00,20:00).', 'danger')
        return redirect(url_for('admin_panel'))
        
    valid_schedule_str = ",".join(valid_times)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Use UPSERT logic (INSERT ON CONFLICT for Postgres, INSERT OR REPLACE for SQLite)
            if IS_POSTGRES:
                query = "INSERT INTO scheduler_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            else:
                query = "INSERT OR REPLACE INTO scheduler_config (key, value) VALUES (?, ?)"
                
            cursor.execute(query, ('schedule', valid_schedule_str))
            conn.commit()
            cursor.close()
            flash('Schedule updated successfully in database.', 'success')
    except Exception as e:
        flash(f'Error updating schedule in database: {str(e)}', 'danger')
    
    return redirect(url_for('admin_panel'))

def seed_price_data():
    """Seed the database with 7 days of price data for testing"""
    # Get real current price first
    current_price_data = fetch_bitcoin_price()
    if not current_price_data["success"]:
        return False
        
    current_price = current_price_data["price"]
    
    # Create 7 days of simulated price data
    with get_db_connection() as conn:
        # Start from 7 days ago
        for day in range(7, 0, -1):
            # Create 6 price points per day
            for hour in range(0, 24, 4):
                # Generate timestamp
                timestamp = (datetime.datetime.utcnow() - datetime.timedelta(days=day, hours=hour)).isoformat()
                
                # Generate slightly varied price
                # Price oscillates between -5% and +5% of current price
                variation = ((day * hour) % 10 - 5) / 100
                price = current_price * (1 + variation)
                
                # Insert into database
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    query = "INSERT INTO prices (timestamp, price, currency) VALUES (%s, %s, %s)" if IS_POSTGRES else "INSERT INTO prices (timestamp, price, currency) VALUES (?, ?, ?)"
                    cursor.execute(
                        query,
                        (timestamp, price, 'USD')
                    )
                    conn.commit()
                    cursor.close()
    
    return True

# Health check endpoint for monitoring
@app.route('/health')
@limiter.limit("60 per minute")
def health_check():
    """Health check endpoint for monitoring systems"""
    db_ok = False
    try:
        # Check database connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            db_ok = cursor.fetchone() is not None
            cursor.close()
    except Exception as db_e:
        print(f"Health check DB connection error: {db_e}")
        db_ok = False
        
    # Get bot status (handle potential errors)
    bot_status_data = {}
    try:
        bot_status_data = get_bot_status()
    except Exception as status_e:
        print(f"Health check bot status error: {status_e}")
        bot_status_data = {'status': 'Error', 'message': str(status_e)}

    # Check if bot has posted recently (within last 24h)
    recent_post_ok = False
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Use appropriate syntax for timestamp comparison
            if IS_POSTGRES:
                cursor.execute("SELECT COUNT(*) FROM posts WHERE timestamp > NOW() - interval '1 day'")
            else:
                cursor.execute("SELECT COUNT(*) FROM posts WHERE timestamp > datetime('now', '-1 day')")
            recent_post_ok = cursor.fetchone()[0] > 0
            cursor.close()
    except Exception as post_e:
        print(f"Health check recent post error: {post_e}")
        recent_post_ok = False
        
    response = {
        'status': 'healthy',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'database_type': 'PostgreSQL' if IS_POSTGRES else 'SQLite',
        'checks': {
            'database_connection': db_ok,
            'bot_status': bot_status_data.get('status', 'Unknown'),
            'recent_post_logged': recent_post_ok
        }
    }
    
    # If any check fails, mark as unhealthy
    status_code = 200
    if not db_ok or response['checks']['bot_status'] == 'Error':
        response['status'] = 'unhealthy'
        status_code = 503 # Service Unavailable
        
    return jsonify(response), status_code

# API endpoints
@app.route('/api/posts', methods=['GET'])
@limiter.limit("30 per minute")
def api_posts():
    """API endpoint to get recent posts"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)  # Limit max items per page
        
        posts, total = get_posts_paginated(
            page=page, 
            per_page=per_page, 
            date_from=request.args.get('date_from'),
            date_to=request.args.get('date_to'),
            content_type=request.args.get('content_type')
        )
        
        return jsonify({
            'success': True,
            'data': {
                'posts': posts,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/stats', methods=['GET'])
@limiter.limit("30 per minute")
def api_stats():
    """API endpoint to get bot statistics"""
    try:
        stats = get_basic_stats()
        
        # Get price history for specified days
        days = min(int(request.args.get('days', 7)), 30)  # Limit max days
        price_history = get_price_history(days=days)
        
        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'price_history': price_history
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/price/refresh', methods=['GET'])
@limiter.limit("10 per minute")
def refresh_price():
    """API endpoint to refresh Bitcoin price"""
    try:
        result = fetch_bitcoin_price()
        
        if result["success"]:
            # --- FIX: Use cursor for DB query ---
            latest_price = None # Initialize
            with get_db_connection() as conn:
                # Use RealDictCursor for dict access, consistent with other parts
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    'SELECT timestamp FROM prices ORDER BY timestamp DESC LIMIT 1' # Only need timestamp
                )
                latest_price_row = cur.fetchone()
                if latest_price_row:
                    latest_price = latest_price_row # Store the whole row (or just timestamp)
                cur.close()
            # --- END FIX ---
            
            return jsonify({
                'success': True,
                'price': f"${result['price']:,.2f}",
                'change': f"{result['price_change']:.2f}%",
                # Access timestamp safely from the fetched row
                'timestamp': latest_price['timestamp'] if latest_price else datetime.datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result["error"]
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/price/history', methods=['GET'])
@limiter.limit("20 per minute")
def price_history_api():
    """API endpoint to get price history"""
    try:
        days = min(int(request.args.get('days', 7)), 30)  # Limit max days
        price_data = get_price_history(days=days)
        
        # Format for chart.js
        prices = [{
            'timestamp': item['timestamp'],
            'price': item['price']
        } for item in price_data]
        
        return jsonify({
            'success': True,
            'prices': prices
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors"""
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': str(e.description)
    }), 429

# Initialize the database on startup
with app.app_context():
    init_db()

# --- START Content Management Routes ---

@app.route('/admin/add_quote', methods=['POST'])
@limiter.limit("15 per minute") # Limit add operations
def add_quote_route():
    quote_text = request.form.get('quote_text')
    logger = logging.getLogger(__name__) # Ensure logger is available
    logger.info(f"Attempting to add new quote. Text: '{quote_text[:30]}...'")
    category = request.form.get('category', 'motivational') # Default category
    if not quote_text:
        flash('Quote text cannot be empty.', 'warning')
        return redirect(url_for('admin_panel'))

    try:
        db = Database()
        quote_id = asyncio.run(db.add_quote(quote_text, category))
        if quote_id:
            flash(f'Quote added successfully (ID: {quote_id}).', 'success')
        else:
            flash('Failed to add quote. Check logs.', 'danger')
    except Exception as e:
        app.logger.error(f"Error in add_quote_route: {e}", exc_info=True)
        flash(f'Error adding quote: {e}', 'danger')
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_quote/<int:quote_id>', methods=['POST'])
@limiter.limit("15 per minute") # Limit delete operations
def delete_quote_route(quote_id):
    try:
        logger = logging.getLogger(__name__) # Ensure logger is available
        logger.info(f"Attempting to delete quote ID: {quote_id}")
        db = Database()
        success = asyncio.run(db.delete_quote(quote_id))
        if success:
            flash(f'Quote ID {quote_id} deleted successfully.', 'success')
        else:
            flash(f'Failed to delete quote ID {quote_id}. It might not exist or an error occurred.', 'warning')
    except Exception as e:
        app.logger.error(f"Error in delete_quote_route: {e}", exc_info=True)
        flash(f'Error deleting quote: {e}', 'danger')
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_joke', methods=['POST'])
@limiter.limit("15 per minute") # Limit add operations
def add_joke_route():
    joke_text = request.form.get('joke_text')
    logger = logging.getLogger(__name__) # Ensure logger is available
    logger.info(f"Attempting to add new joke. Text: '{joke_text[:30]}...'")
    category = request.form.get('category', 'humor') # Default category
    if not joke_text:
        flash('Joke text cannot be empty.', 'warning')
        return redirect(url_for('admin_panel'))

    try:
        db = Database()
        joke_id = asyncio.run(db.add_joke(joke_text, category))
        if joke_id:
            flash(f'Joke added successfully (ID: {joke_id}).', 'success')
        else:
            flash('Failed to add joke. Check logs.', 'danger')
    except Exception as e:
        app.logger.error(f"Error in add_joke_route: {e}", exc_info=True)
        flash(f'Error adding joke: {e}', 'danger')
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_joke/<int:joke_id>', methods=['POST'])
@limiter.limit("15 per minute") # Limit delete operations
def delete_joke_route(joke_id):
    try:
        logger = logging.getLogger(__name__) # Ensure logger is available
        logger.info(f"Attempting to delete joke ID: {joke_id}")
        db = Database()
        success = asyncio.run(db.delete_joke(joke_id))
        if success:
            flash(f'Joke ID {joke_id} deleted successfully.', 'success')
        else:
            flash(f'Failed to delete joke ID {joke_id}. It might not exist or an error occurred.', 'warning')
    except Exception as e:
        app.logger.error(f"Error in delete_joke_route: {e}", exc_info=True)
        flash(f'Error deleting joke: {e}', 'danger')
        
    return redirect(url_for('admin_panel'))

# --- END Content Management Routes ---

if __name__ == '__main__':
    app.run(debug=True) 