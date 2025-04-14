"""
Load Twitter credentials from .env file and test tweeting
"""
import os
import sys
import time
import traceback
from datetime import datetime

# First try to load from .env file
try:
    from dotenv import load_dotenv
    print("Loading credentials from .env file")
    load_dotenv()
except ImportError:
    print("python-dotenv not installed, trying to manually read .env file")
    # Manually read .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def post_tweet():
    """Post tweet with credentials from .env file"""
    print(f"\n==== TWEET TEST FROM .ENV ({datetime.now().isoformat()}) ====\n")
    
    # Import tweepy with error handling
    try:
        import tweepy
        print(f"Found tweepy version: {tweepy.__version__}")
    except ImportError as e:
        print(f"ERROR: Tweepy not available - {e}")
        return False
    
    # Get credentials from environment (loaded from .env)
    api_key = os.environ.get('TWITTER_API_KEY')
    api_secret = os.environ.get('TWITTER_API_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    
    # Print whether credentials were found
    print("\nCredential check:")
    print(f"API_KEY: {'FOUND' if api_key else 'MISSING'}")
    print(f"API_SECRET: {'FOUND' if api_secret else 'MISSING'}")
    print(f"ACCESS_TOKEN: {'FOUND' if access_token else 'MISSING'}")
    print(f"ACCESS_TOKEN_SECRET: {'FOUND' if access_token_secret else 'MISSING'}")
    
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("ERROR: Missing one or more Twitter API credentials in .env file")
        print("Make sure your .env file contains:")
        print("TWITTER_API_KEY=xxx")
        print("TWITTER_API_SECRET=xxx")
        print("TWITTER_ACCESS_TOKEN=xxx")
        print("TWITTER_ACCESS_TOKEN_SECRET=xxx")
        return False
    
    # Create unique tweet text
    timestamp = int(time.time())
    tweet_text = f"BTCBuzzBot test {timestamp}"
    
    print(f"\nAttempting to post tweet: '{tweet_text}'")
    
    # Set up auth and API
    try:
        auth = tweepy.OAuth1UserHandler(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        api = tweepy.API(auth)
        
        # Verify credentials
        try:
            me = api.verify_credentials()
            print(f"✓ Successfully authenticated as @{me.screen_name}")
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            traceback.print_exc()
            return False
        
        # Post the tweet
        try:
            status = api.update_status(tweet_text)
            print(f"\n✓ SUCCESS! Tweet posted with ID: {status.id}")
            print(f"Tweet URL: https://twitter.com/i/web/status/{status.id}")
            return True
        except Exception as e:
            print(f"\n✗ Failed to post tweet: {e}")
            traceback.print_exc()
            
            # Check for common errors
            err_msg = str(e).lower()
            if "duplicate" in err_msg:
                print("\nHINT: This looks like a duplicate tweet error. Twitter doesn't allow posting identical tweets.")
            elif "authenticat" in err_msg or "authoriz" in err_msg:
                print("\nHINT: This looks like an authentication error. Check if your tokens are valid and have the right permissions.")
            
            return False
    except Exception as e:
        print(f"✗ Error setting up Twitter API: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("====== TWITTER API TEST - USING .ENV CREDENTIALS ======")
    
    result = post_tweet()
    
    print("\n====== TEST RESULTS ======")
    if result:
        print("✓ SUCCESS: Tweet was posted!")
        sys.exit(0)
    else:
        print("✗ FAILURE: Tweet could not be posted")
        sys.exit(1) 