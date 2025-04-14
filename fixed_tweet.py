"""
Fixed tweet functionality - using only the stable v1.1 API
"""
import os
import sys
import traceback
from datetime import datetime

def post_tweet():
    """Post a tweet using Twitter API v1.1 with detailed debugging"""
    print(f"\n===== BTCBuzzBot Tweet Test ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) =====")
    
    # Try to import tweepy, with more detailed error handling
    try:
        import tweepy
        print(f"✅ Tweepy imported successfully (version: {tweepy.__version__})")
    except ImportError as e:
        print(f"❌ Failed to import tweepy: {e}")
        return False
    
    # Get Twitter API credentials with detailed validation
    API_KEY = os.environ.get('TWITTER_API_KEY', '')
    API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
    ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
    ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
    
    # Print partial credentials for verification
    print(f"API Key: {API_KEY[:5]}...{API_KEY[-5:] if len(API_KEY) >= 10 else ''}")
    print(f"API Secret: {API_SECRET[:5]}...{API_SECRET[-5:] if len(API_SECRET) >= 10 else ''}")
    print(f"Access Token: {ACCESS_TOKEN[:5]}...{ACCESS_TOKEN[-5:] if len(ACCESS_TOKEN) >= 10 else ''}")
    print(f"Access Token Secret: {ACCESS_TOKEN_SECRET[:5]}...{ACCESS_TOKEN[-5:] if len(ACCESS_TOKEN_SECRET) >= 10 else ''}")
    
    # Validate credentials
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        missing = []
        if not API_KEY: missing.append("TWITTER_API_KEY")
        if not API_SECRET: missing.append("TWITTER_API_SECRET") 
        if not ACCESS_TOKEN: missing.append("TWITTER_ACCESS_TOKEN")
        if not ACCESS_TOKEN_SECRET: missing.append("TWITTER_ACCESS_TOKEN_SECRET")
        
        print(f"❌ Missing credentials: {', '.join(missing)}")
        return False
    
    try:
        # Set up the v1.1 API auth
        print("Setting up OAuth 1.0a authentication...")
        auth = tweepy.OAuth1UserHandler(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        
        # Create API instance
        print("Creating tweepy.API instance...")
        api = tweepy.API(auth)
        
        # Verify credentials by getting account info
        print("Verifying credentials...")
        me = api.verify_credentials()
        print(f"✅ Successfully authenticated as @{me.screen_name}")
        
        # Create tweet content
        timestamp = datetime.now().strftime('%H:%M:%S')
        tweet = f"Test tweet from BTCBuzzBot at {timestamp} #Bitcoin #Testing"
        
        # Post the tweet
        print(f"Posting tweet: {tweet}")
        status = api.update_status(tweet)
        
        if status and hasattr(status, 'id'):
            tweet_id = status.id
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
            print(f"✅ Tweet posted successfully!")
            print(f"Tweet ID: {tweet_id}")
            print(f"Tweet URL: {tweet_url}")
            return True
        else:
            print("❌ Failed to post tweet - invalid response")
            print(f"Response: {status}")
            return False
    except tweepy.TweepyException as e:
        print(f"❌ Tweepy error: {str(e)}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = post_tweet()
    
    if success:
        print("\n✅ Tweet posted successfully!")
        sys.exit(0)
    else:
        print("\n❌ Failed to post tweet.")
        sys.exit(1) 