#!/usr/bin/env python
"""
Diagnostic tool for BTCBuzzBot to check tweets in the database.
This script displays tweets from the database and can help diagnose issues with Twitter post generation.
"""

import os
import sqlite3
import sys
from datetime import datetime, timedelta

def get_db_connection():
    """Get a database connection"""
    db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
    print(f"Connecting to database at {db_path}")
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database file not found at {db_path}")
        sys.exit(1)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def check_database_structure():
    """Check if the database has the required tables for tweets"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check posts table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
            posts_table = cursor.fetchone()
            
            if not posts_table:
                print("❌ posts table not found in database")
                return False
            
            # Check table structure
            cursor.execute("PRAGMA table_info(posts)")
            columns = {row['name'] for row in cursor.fetchall()}
            
            required_columns = {'timestamp', 'content', 'content_type', 'tweet_id', 'likes', 'retweets'}
            missing_columns = required_columns - columns
            
            if missing_columns:
                print(f"❌ posts table is missing columns: {', '.join(missing_columns)}")
                return False
                
            print("✅ Database structure looks good")
            return True
    except Exception as e:
        print(f"Error checking database structure: {e}")
        return False

def display_tweets(limit=10, days=7):
    """Display tweets from the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate date filter
            date_filter = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM posts WHERE timestamp > ?", (date_filter,))
            total_count = cursor.fetchone()[0]
            
            # Get recent tweets
            cursor.execute(
                "SELECT * FROM posts WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?", 
                (date_filter, limit)
            )
            tweets = cursor.fetchall()
            
            if not tweets:
                print(f"No tweets found in the last {days} days")
                return
                
            print(f"Found {total_count} tweets in the last {days} days. Showing the {len(tweets)} most recent:")
            print("-" * 80)
            
            for i, tweet in enumerate(tweets, 1):
                tweet_time = datetime.fromisoformat(tweet['timestamp'])
                formatted_time = tweet_time.strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"[{i}] Posted at: {formatted_time}")
                print(f"    Tweet ID: {tweet['tweet_id'] or 'Not available'}")
                print(f"    Content type: {tweet['content_type']}")
                print(f"    Engagement: {tweet['likes']} likes, {tweet['retweets']} retweets")
                print(f"    Content: {tweet['content']}")
                print("-" * 80)
                
    except Exception as e:
        print(f"Error displaying tweets: {e}")

def display_price_history(limit=5):
    """Display price history from the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get recent prices
            cursor.execute(
                "SELECT * FROM prices ORDER BY timestamp DESC LIMIT ?", 
                (limit,)
            )
            prices = cursor.fetchall()
            
            if not prices:
                print("No price data found in the database")
                return
                
            print(f"Recent price history (last {len(prices)} entries):")
            print("-" * 50)
            
            for i, price in enumerate(prices, 1):
                price_time = datetime.fromisoformat(price['timestamp'])
                formatted_time = price_time.strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"[{i}] Time: {formatted_time}")
                print(f"    Price: ${price['price']:,.2f} {price['currency']}")
                print("-" * 50)
                
    except Exception as e:
        print(f"Error displaying price history: {e}")

def display_bot_status():
    """Display the current bot status"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get most recent status
            cursor.execute(
                "SELECT * FROM bot_status ORDER BY timestamp DESC LIMIT 1"
            )
            status = cursor.fetchone()
            
            if not status:
                print("No bot status found in the database")
                return
                
            status_time = datetime.fromisoformat(status['timestamp'])
            formatted_time = status_time.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"Current bot status (as of {formatted_time}):")
            print(f"Status: {status['status']}")
            print(f"Message: {status['message']}")
            
            # Get next scheduled run
            cursor.execute(
                "SELECT * FROM bot_status WHERE message LIKE '%next run%' ORDER BY timestamp DESC LIMIT 1"
            )
            next_run = cursor.fetchone()
            
            if next_run:
                print(f"Next scheduled run: {next_run['message']}")
                
    except Exception as e:
        print(f"Error displaying bot status: {e}")

def run_diagnostics():
    """Run diagnostics on the tweet system"""
    print("=" * 80)
    print(f"BTCBuzzBot Tweet Diagnostics - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Check database structure
    print("\n[1] Checking database structure...")
    if not check_database_structure():
        print("⚠️ Database structure issues detected. Tweets may not be properly stored.")
    
    # Display recent tweets
    print("\n[2] Recent tweets from database:")
    display_tweets(limit=5, days=1)
    
    # Display price history
    print("\n[3] Recent price history:")
    display_price_history(limit=3)
    
    # Display bot status
    print("\n[4] Bot status:")
    display_bot_status()
    
    print("\n" + "=" * 80)
    print("Diagnostic complete!")
    print("=" * 80)

if __name__ == "__main__":
    run_diagnostics() 