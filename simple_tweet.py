"""
Ultra-simple compatibility Twitter module
"""
import os
import sys
import time
import traceback
import json
from datetime import datetime

def post_tweet():
    """Post a tweet to Twitter, with compatibility for different tweepy versions"""
    # Load environment variables directly for Twitter API credentials
    API_KEY = os.environ.get('TWITTER_API_KEY', '')
    API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
    ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
    ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
    
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        print("ERROR: Missing Twitter API credentials in environment variables")
        return False
        
    try:
        # Create a timestamped message to avoid duplicate tweet errors
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"BTCBuzzBot test ({timestamp}) #Bitcoin #Testing"
        
        # Now attempt to import tweepy and post
        try:
            import tweepy
            print(f"Using tweepy version: {tweepy.__version__}")
            
            # First try with v1.1 API (most reliable)
            try:
                # Create v1.1 API connection
                auth = tweepy.OAuth1UserHandler(
                    API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
                )
                api = tweepy.API(auth)
                
                # Verify credentials
                me = api.verify_credentials()
                print(f"Authenticated as: @{me.screen_name}")
                
                # Post the tweet
                status = api.update_status(message)
                
                if hasattr(status, 'id'):
                    print(f"Tweet posted successfully! ID: {status.id}")
                    print(f"Content: {message}")
                    return True
                else:
                    print(f"Error: Invalid status response: {status}")
                    # Fall through to v2 API
            except Exception as e1:
                print(f"Error with v1.1 API: {e1}")
                # Fall through to v2 API
                
            # Try with v2 API as fallback
            try:
                client = tweepy.Client(
                    consumer_key=API_KEY,
                    consumer_secret=API_SECRET,
                    access_token=ACCESS_TOKEN,
                    access_token_secret=ACCESS_TOKEN_SECRET
                )
                
                # Add a different timestamp to avoid duplicate error if v1 attempt failed
                message = f"BTCBuzzBot test ({timestamp} alt) #Bitcoin #Testing"
                
                # Post the tweet
                response = client.create_tweet(text=message)
                
                if response and hasattr(response, 'data') and 'id' in response.data:
                    tweet_id = response.data['id']
                    print(f"Tweet posted successfully with v2 API! ID: {tweet_id}")
                    print(f"Content: {message}")
                    return True
                else:
                    print(f"Error: Invalid v2 API response: {response}")
                    return False
            except Exception as e2:
                print(f"Error with v2 API: {e2}")
                # Both methods failed, report failure
                print("ALL TWEET METHODS FAILED")
                return False
                
        except ImportError as e:
            print(f"Error importing tweepy: {e}")
            print("Tweepy not installed - please install with 'pip install tweepy'")
            return False
            
    except Exception as e:
        print(f"Unexpected error in tweet function: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"=== Simple Tweet Test ({datetime.now().isoformat()}) ===")
    
    result = post_tweet()
    
    if result:
        print("SUCCESS: Tweet posted!")
        sys.exit(0)
    else:
        print("FAILURE: Tweet could not be posted")
        sys.exit(1) 