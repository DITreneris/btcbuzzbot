#!/usr/bin/env python
"""
Manual tweet posting tool for BTCBuzzBot
This script allows you to manually post a tweet at any time using the direct_tweet_fixed.py module.
"""

import os
import sys
import importlib.util
import sqlite3
from datetime import datetime

def log_status(status, message):
    """Log current status to bot_status table"""
    try:
        conn = sqlite3.connect('btcbuzzbot.db')
        cursor = conn.cursor()
        
        # Check if bot_status table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_status'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE bot_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    next_scheduled_run TEXT,
                    message TEXT
                )
            ''')
        
        # Insert status
        cursor.execute('''
            INSERT INTO bot_status (timestamp, status, message)
            VALUES (?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'), status, message))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error logging status: {e}")

def main():
    print("\n======== BTCBUZZBOT MANUAL TWEET ========")
    print(f"Starting manual tweet post at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 45)
    
    # Check if direct_tweet_fixed.py exists
    if not os.path.exists('direct_tweet_fixed.py'):
        print("❌ Error: direct_tweet_fixed.py not found")
        log_status('Error', 'direct_tweet_fixed.py not found')
        return False
    
    try:
        # Import direct_tweet_fixed.py dynamically
        print("Importing direct_tweet_fixed.py...")
        module_name = 'direct_tweet_fixed'
        spec = importlib.util.spec_from_file_location(module_name, f"{module_name}.py")
        tweet_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tweet_module)
        
        # Log the attempt
        log_status('Posting', 'Manual tweet posting initiated')
        
        # Call the post_tweet function
        print("Calling post_tweet function...")
        result = tweet_module.post_tweet()
        
        if result:
            print("\n✅ Tweet posted successfully!")
            log_status('Success', 'Manual tweet posted successfully')
            return True
        else:
            print("\n❌ Tweet posting failed!")
            log_status('Failed', 'Manual tweet posting failed')
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        log_status('Error', f'Exception during manual tweet: {str(e)}')
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\nManual tweet operation completed successfully.")
        sys.exit(0)
    else:
        print("\nManual tweet operation failed.")
        sys.exit(1) 