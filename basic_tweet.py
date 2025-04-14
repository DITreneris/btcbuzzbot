"""
Basic tweet functionality - stripped down to bare essentials
Using both new tweepy.Client and legacy API for maximum compatibility
"""

import os
import sys
import traceback
from datetime import datetime

# Twitter API credentials
API_KEY = os.environ.get('TWITTER_API_KEY', '')
API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')

def post_tweet_v2():
    """Post a tweet using the Twitter API v2 (tweepy.Client)"""
    try:
        import tweepy
        
        # Create the v2 client
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        
        # Generate simple tweet text
        timestamp = datetime.now().strftime('%H:%M:%S')
        tweet = f"Test tweet from BTCBuzzBot at {timestamp} #Bitcoin #Testing"
        
        # Post the tweet
        print(f"Attempting to post tweet via API v2: {tweet}")
        response = client.create_tweet(text=tweet)
        
        if response and hasattr(response, 'data') and 'id' in response.data:
            tweet_id = response.data['id']
            print(f"Success! Tweet ID: {tweet_id}")
            return True
        else:
            print(f"Failed to get tweet ID from response: {response}")
            return False
            
    except Exception as e:
        print(f"Error using Twitter API v2: {e}")
        traceback.print_exc()
        return False

def post_tweet_v1():
    """Post a tweet using the Twitter API v1.1 (legacy tweepy.API)"""
    try:
        import tweepy
        
        # Set up auth
        auth = tweepy.OAuth1UserHandler(
            API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
        )
        
        # Create API object
        api = tweepy.API(auth)
        
        # Generate simple tweet text
        timestamp = datetime.now().strftime('%H:%M:%S')
        tweet = f"Test tweet from BTCBuzzBot at {timestamp} (legacy API) #Bitcoin #Testing"
        
        # Post the tweet
        print(f"Attempting to post tweet via legacy API: {tweet}")
        status = api.update_status(tweet)
        
        if status and hasattr(status, 'id'):
            print(f"Success! Tweet ID: {status.id}")
            return True
        else:
            print(f"Failed to get tweet ID from status: {status}")
            return False
            
    except Exception as e:
        print(f"Error using Twitter API v1.1: {e}")
        traceback.print_exc()
        return False

def post_tweet():
    """Try both API versions to post a tweet"""
    print(f"=== BTCBuzzBot Basic Tweet Test ({datetime.now().isoformat()}) ===")
    
    # First try API v2
    print("\n> Trying Twitter API v2...")
    if post_tweet_v2():
        print("Successfully posted tweet using Twitter API v2!")
        return True
        
    # If v2 fails, try legacy API
    print("\n> Trying Twitter API v1.1 (legacy)...")
    if post_tweet_v1():
        print("Successfully posted tweet using Twitter API v1.1 (legacy)!")
        return True
        
    # Both failed
    print("\n❌ All tweet posting methods failed!")
    return False

if __name__ == "__main__":
    # Try to import tweepy, exit if it's not available
    try:
        import tweepy
        print(f"Tweepy version: {tweepy.__version__}")
    except ImportError:
        print("Error: tweepy is not installed. Please install it with 'pip install tweepy'")
        sys.exit(1)

    # Print tweet credentials (first few chars only)
    print(f"API_KEY: {API_KEY[:4]}...{API_KEY[-4:] if len(API_KEY) > 8 else ''}")
    print(f"API_SECRET: {API_SECRET[:4]}...{API_SECRET[-4:] if len(API_SECRET) > 8 else ''}")
    
    # Attempt to post
    success = post_tweet()
    
    if success:
        print("\n✅ Tweet posted successfully!")
        sys.exit(0)
    else:
        print("\n❌ Failed to post tweet.")
        sys.exit(1) 