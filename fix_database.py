#!/usr/bin/env python
"""
Database structure fix for BTCBuzzBot.
This script ensures that all required tables and columns exist.
"""

import os
import sqlite3
import sys
from datetime import datetime, timedelta
import random
import traceback

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

def fix_database_structure():
    """Fix the database structure to ensure all required tables and columns exist"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print("Checking and fixing database structure...")
            
            # 1. First, check if bot_status table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_status'")
            bot_status_exists = cursor.fetchone()
            
            if not bot_status_exists:
                print("Creating bot_status table...")
                cursor.execute('''
                CREATE TABLE bot_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    next_scheduled_run TEXT,
                    message TEXT
                )
                ''')
                # Insert initial status
                cursor.execute(
                    'INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)',
                    (datetime.utcnow().isoformat(), 'Initialized', 'Database structure fixed')
                )
                print("✅ bot_status table created")
            else:
                # Check if the next_scheduled_run column exists
                cursor.execute("PRAGMA table_info(bot_status)")
                columns = {row['name'] for row in cursor.fetchall()}
                
                if 'next_scheduled_run' not in columns:
                    print("Adding missing 'next_scheduled_run' column to bot_status table...")
                    try:
                        cursor.execute('ALTER TABLE bot_status ADD COLUMN next_scheduled_run TEXT')
                        print("✅ Added 'next_scheduled_run' column to bot_status table")
                    except sqlite3.OperationalError as e:
                        print(f"⚠️ Could not add column: {e}")
            
            # 2. Check posts table structure
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
            posts_exists = cursor.fetchone()
            
            # Get the posts table structure to understand what we're working with
            if posts_exists:
                # Extract the actual table definition
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'")
                posts_schema = cursor.fetchone()[0]
                print(f"Current posts table schema: {posts_schema}")
                
            if not posts_exists:
                print("Creating posts table...")
                cursor.execute('''
                CREATE TABLE posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_id TEXT NOT NULL,
                    tweet TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    price REAL NOT NULL,
                    price_change REAL NOT NULL,
                    content_type TEXT NOT NULL,
                    likes INTEGER DEFAULT 0,
                    retweets INTEGER DEFAULT 0,
                    content TEXT NOT NULL DEFAULT ""
                )
                ''')
                print("✅ posts table created")
                
                # Add a sample post so the interface has something to show
                sample_post = (
                    "sample_" + str(int(datetime.utcnow().timestamp())),
                    "BTC: $85,000.00 | +2.50% 📈\nHODL to the moon! 🚀\n#Bitcoin #Crypto",
                    datetime.utcnow().isoformat(),
                    85000.00,
                    2.5,
                    "quote",
                    0,
                    0,
                    "BTC: $85,000.00 | +2.50% 📈\nHODL to the moon! 🚀\n#Bitcoin #Crypto"
                )
                cursor.execute(
                    'INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    sample_post
                )
                print("✅ Added sample post to posts table")
            else:
                # Check if the content column exists
                cursor.execute("PRAGMA table_info(posts)")
                columns_info = cursor.fetchall()
                columns = {row[1] for row in columns_info}
                
                # If content column is missing, try to add it
                if 'content' not in columns:
                    print("Adding missing 'content' column to posts table...")
                    try:
                        cursor.execute('ALTER TABLE posts ADD COLUMN content TEXT DEFAULT ""')
                        print("✅ Added 'content' column to posts table")
                        
                        # Update any existing posts with default content
                        cursor.execute("UPDATE posts SET content = tweet WHERE content IS NULL OR content = ''")
                        print(f"✅ Updated {cursor.rowcount} posts with default content")
                    except sqlite3.OperationalError:
                        print("⚠️ Could not add 'content' column directly")
                
                # Check if we have any posts at all
                cursor.execute("SELECT COUNT(*) as count FROM posts")
                post_count = cursor.fetchone()[0]
                
                if post_count == 0:
                    print("No posts found, adding a sample post...")
                    # We need to check what columns we have so we can insert properly
                    if 'tweet' in columns and 'price' in columns and 'price_change' in columns:
                        sample_post = (
                            "sample_" + str(int(datetime.utcnow().timestamp())),
                            "BTC: $85,000.00 | +2.50% 📈\nHODL to the moon! 🚀\n#Bitcoin #Crypto",
                            datetime.utcnow().isoformat(),
                            85000.00,
                            2.5,
                            "quote",
                            0,
                            0,
                            "BTC: $85,000.00 | +2.50% 📈\nHODL to the moon! 🚀\n#Bitcoin #Crypto"
                        )
                        cursor.execute(
                            'INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            sample_post
                        )
                    else:
                        sample_post = (
                            datetime.utcnow().isoformat(),
                            "BTC: $85,000.00 | +2.50% 📈\nHODL to the moon! 🚀\n#Bitcoin #Crypto",
                            "quote",
                            "sample_" + str(int(datetime.utcnow().timestamp())),
                            0,
                            0
                        )
                        cursor.execute(
                            'INSERT INTO posts (timestamp, content, content_type, tweet_id, likes, retweets) VALUES (?, ?, ?, ?, ?, ?)',
                            sample_post
                        )
                    print("✅ Added sample post to posts table")
            
            # 3. Check prices table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prices'")
            prices_exists = cursor.fetchone()
            
            if not prices_exists:
                print("Creating prices table...")
                cursor.execute('''
                CREATE TABLE prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT DEFAULT 'USD'
                )
                ''')
                
                # Insert sample price data for the last 7 days
                print("Adding sample price data...")
                base_price = 85000.00
                for i in range(7):
                    days_ago = i
                    timestamp = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
                    # Add some random variation to the price
                    price_variation = base_price * (0.95 + (random.random() * 0.1))  # 5% down to 5% up
                    
                    cursor.execute(
                        'INSERT INTO prices (timestamp, price, currency) VALUES (?, ?, ?)',
                        (timestamp, price_variation, 'USD')
                    )
                
                print("✅ prices table created with sample data")
            else:
                # Check if the currency column exists
                cursor.execute("PRAGMA table_info(prices)")
                columns = {row[1] for row in cursor.fetchall()}
                
                if 'currency' not in columns:
                    print("Adding 'currency' column to prices table...")
                    try:
                        cursor.execute('ALTER TABLE prices ADD COLUMN currency TEXT DEFAULT "USD"')
                        print("✅ Added 'currency' column to prices table")
                    except sqlite3.OperationalError:
                        print("⚠️ Could not add 'currency' column to prices table - recreating")
                        
                        # Backup the old table
                        cursor.execute("ALTER TABLE prices RENAME TO prices_old")
                        
                        # Create the new table
                        cursor.execute('''
                        CREATE TABLE prices (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            price REAL NOT NULL,
                            currency TEXT DEFAULT 'USD'
                        )
                        ''')
                        
                        # Copy data
                        cursor.execute('''
                        INSERT INTO prices (id, timestamp, price, currency)
                        SELECT id, timestamp, price, 'USD' FROM prices_old
                        ''')
                        print(f"✅ Migrated {cursor.rowcount} rows from old prices table")
                
                # Check if we have any price data
                cursor.execute("SELECT COUNT(*) as count FROM prices")
                price_count = cursor.fetchone()[0]
                
                if price_count == 0:
                    print("No price data found, adding sample data...")
                    
                    # Insert sample price data for today
                    price = 85000.00
                    cursor.execute(
                        'INSERT INTO prices (timestamp, price, currency) VALUES (?, ?, ?)',
                        (datetime.utcnow().isoformat(), price, 'USD')
                    )
                    
                    # Also add a slightly different price for yesterday
                    yesterday = datetime.utcnow() - timedelta(days=1)
                    yesterday_price = price * 0.98  # 2% lower
                    cursor.execute(
                        'INSERT INTO prices (timestamp, price, currency) VALUES (?, ?, ?)',
                        (yesterday.isoformat(), yesterday_price, 'USD')
                    )
                    
                    print("✅ Added sample price data")
            
            # 4. Check scheduler_config table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduler_config'")
            scheduler_config_exists = cursor.fetchone()
            
            if not scheduler_config_exists:
                print("Creating scheduler_config table...")
                cursor.execute('''
                CREATE TABLE scheduler_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                ''')
                
                # Insert default schedule
                default_schedule = "08:00,12:00,16:00,20:00"
                cursor.execute(
                    'INSERT INTO scheduler_config (key, value) VALUES (?, ?)',
                    ('schedule', default_schedule)
                )
                
                print("✅ scheduler_config table created with default schedule")
            
            # Commit all changes
            conn.commit()
            
            print("Database structure fix complete!")
            return True
            
    except Exception as e:
        print(f"Error fixing database: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 80)
    print(f"BTCBuzzBot Database Structure Fix - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    success = fix_database_structure()
    
    print("\n" + "=" * 80)
    print(f"Database fix {'successful' if success else 'FAILED'}")
    print("=" * 80) 