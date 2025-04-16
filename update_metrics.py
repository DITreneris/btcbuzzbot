#!/usr/bin/env python
"""
Update Tweet Metrics Tool for BTCBuzzBot.
This script updates tweet engagement metrics (likes, retweets) in the database using the Twitter API.
"""

import os
import sys
import sqlite3
import time
from datetime import datetime, timedelta
import argparse

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

def get_tweet_ids_to_update(days=30, only_zeros=False):
    """Get tweet IDs from the database that need engagement metrics updated"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate the date threshold
            threshold_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Build the query based on parameters
            query = """
                SELECT id, tweet_id, timestamp
                FROM posts
                WHERE
                    tweet_id NOT LIKE 'sim_%' AND
                    tweet_id NOT LIKE 'fail_%' AND
                    timestamp >= ?
            """
            
            # Add condition to only select tweets with zero engagement if required
            if only_zeros:
                query += " AND (likes = 0 OR retweets = 0 OR likes IS NULL OR retweets IS NULL)"
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, (threshold_date,))
            rows = cursor.fetchall()
            
            if not rows:
                print(f"No tweets found from the last {days} days that need updating")
                return []
            
            print(f"Found {len(rows)} tweets to update metrics for")
            return rows
    except Exception as e:
        print(f"Error getting tweet IDs: {e}")
        return []

def update_tweet_metrics(tweet_data, api_client):
    """Update engagement metrics for a single tweet"""
    try:
        db_id = tweet_data['id']
        tweet_id = tweet_data['tweet_id']
        
        print(f"Updating metrics for tweet ID: {tweet_id}...")
        
        # Fetch tweet from Twitter API
        tweet = api_client.get_tweet(tweet_id, tweet_fields=['public_metrics'])
        
        if tweet and hasattr(tweet, 'data') and 'public_metrics' in tweet.data:
            metrics = tweet.data['public_metrics']
            likes = metrics.get('like_count', 0)
            retweets = metrics.get('retweet_count', 0)
            
            # Update the database
            with get_db_connection() as conn:
                conn.execute(
                    'UPDATE posts SET likes = ?, retweets = ? WHERE id = ?',
                    (likes, retweets, db_id)
                )
                conn.commit()
            
            print(f"  ✅ Updated tweet {tweet_id}: {likes} likes, {retweets} retweets")
            return True
        else:
            print(f"  ⚠️ Could not fetch metrics for tweet {tweet_id}")
            return False
    except Exception as e:
        print(f"  ❌ Error updating metrics for tweet {tweet_id}: {e}")
        return False

def update_all_tweets(days=30, only_zeros=False, rate_limit=900):
    """Update metrics for all relevant tweets"""
    try:
        # Import Twitter API libraries
        try:
            import tweepy
        except ImportError:
            print("Error: tweepy library not found. Please install it with 'pip install tweepy'")
            return False
        
        # Try to load environment variables from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ Loaded environment variables from .env file")
        except ImportError:
            print("⚠️ python-dotenv not available, relying on system environment variables")
        
        # Get Twitter API credentials from environment variables
        api_key = os.environ.get('TWITTER_API_KEY')
        api_secret = os.environ.get('TWITTER_API_SECRET')
        access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        
        if not all([api_key, api_secret, access_token, access_token_secret]):
            print("❌ Missing Twitter API credentials in environment variables")
            print("Please set TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET")
            return False
        
        # Create Twitter API client
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Get tweets to update
        tweets = get_tweet_ids_to_update(days, only_zeros)
        
        if not tweets:
            return True
        
        # Update metrics for each tweet (with rate limit consideration)
        print(f"\nUpdating metrics for {len(tweets)} tweets...")
        
        success_count = 0
        fail_count = 0
        skipped_count = 0
        
        for i, tweet in enumerate(tweets):
            # Check if we need to sleep for rate limit
            if i > 0 and i % rate_limit == 0:
                sleep_time = 900  # 15 minutes in seconds
                print(f"\nReached Twitter API rate limit, sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)
            
            # Skip tweets with invalid IDs
            if not tweet['tweet_id'] or not tweet['tweet_id'].isdigit():
                skipped_count += 1
                continue
            
            # Update metrics
            success = update_tweet_metrics(tweet, client)
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            # Small delay between API calls
            time.sleep(1)
        
        print(f"\n✅ Metrics update completed")
        print(f"  Successful updates: {success_count}")
        print(f"  Failed updates: {fail_count}")
        print(f"  Skipped tweets: {skipped_count}")
        
        return success_count > 0
    except Exception as e:
        print(f"Error updating tweet metrics: {e}")
        return False

def simulate_metrics():
    """Simulate engagement metrics for testing when Twitter API is not available"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all tweets
            cursor.execute("""
                SELECT id, tweet_id, content_type
                FROM posts
                WHERE likes = 0 OR retweets = 0 OR likes IS NULL OR retweets IS NULL
            """)
            rows = cursor.fetchall()
            
            if not rows:
                print("No tweets found that need simulated metrics")
                return True
            
            print(f"Simulating metrics for {len(rows)} tweets...")
            
            # Import random for generating simulated metrics
            import random
            
            # Update each tweet with simulated metrics
            for row in rows:
                # Generate random engagement metrics based on content type
                content_type = row['content_type'] or 'regular'
                
                if content_type == 'quote':
                    # Quotes tend to get more engagement
                    likes = random.randint(5, 50)
                    retweets = random.randint(1, 15)
                elif content_type == 'joke':
                    # Jokes can be hit or miss
                    likes = random.randint(3, 100)
                    retweets = random.randint(0, 30)
                else:
                    # Regular tweets get less engagement
                    likes = random.randint(2, 20)
                    retweets = random.randint(0, 5)
                
                # Update the database
                conn.execute(
                    'UPDATE posts SET likes = ?, retweets = ? WHERE id = ?',
                    (likes, retweets, row['id'])
                )
            
            conn.commit()
            print(f"✅ Successfully simulated metrics for {len(rows)} tweets")
            return True
    except Exception as e:
        print(f"Error simulating metrics: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Update tweet engagement metrics in the database')
    
    parser.add_argument('--days', type=int, default=30, help='Number of days of tweets to update (default: 30)')
    parser.add_argument('--zeros-only', action='store_true', help='Only update tweets with zero engagement')
    parser.add_argument('--simulate', action='store_true', help='Simulate metrics for testing (no Twitter API needed)')
    parser.add_argument('--rate-limit', type=int, default=900, help='Number of API calls before rate limit pause (default: 900)')
    
    args = parser.parse_args()
    
    if args.simulate:
        print("Running in SIMULATION mode - will generate fake engagement data")
        simulate_metrics()
    else:
        print(f"Updating tweet metrics for the last {args.days} days")
        if args.zeros_only:
            print("Only updating tweets with zero engagement")
        
        update_all_tweets(days=args.days, only_zeros=args.zeros_only, rate_limit=args.rate_limit)

if __name__ == "__main__":
    main() 