"""
Ultra-simplified tweeting module with hardcoded credentials - V2 API only
"""
import os
import sys
import time
from datetime import datetime

def post_tweet():
    """Attempt to post a tweet with hardcoded credentials using V2 API only"""
    print("\n==== FIXED TWEET ATTEMPT USING V2 API ====\n")
    
    try:
        import tweepy
        print(f"Using tweepy version: {tweepy.__version__}")
    except ImportError:
        print("ERROR: tweepy is not installed")
        return False
    
    # Hardcoded credentials that were recently set
    api_key = "nPvBEvUwgMIPyv0Jwj5UUwG2s"
    api_secret = "ujUsuP7kEL2BdAxkwrFAwlBsP0WgLVcrmiKlssTWkLsQw1rlXd"
    access_token = "1788140541122621440-krhXpQxSbSmTr3AQS0NAljM5ho13EH"
    access_token_secret = "sVfHrxgORIg2clYNaoNOD5Y1NGStkUPiUWVNnvWdnxuGt"
    
    try:
        # Set up client with V2 API (not API v1.1)
        print("Creating Client for V2 API...")
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Create unique tweet with timestamp
        timestamp = int(time.time())
        tweet_text = f"Fixed test tweet using V2 API {timestamp} #BTCBuzzBot"
        
        # Post tweet using V2 API
        print(f"Posting tweet using V2 API: {tweet_text}")
        response = client.create_tweet(text=tweet_text)
        
        if response and hasattr(response, 'data') and 'id' in response.data:
            tweet_id = response.data['id']
            print(f"SUCCESS! Tweet posted with ID: {tweet_id}")
            print(f"Tweet URL: https://twitter.com/i/web/status/{tweet_id}")
            return True
        else:
            print(f"ERROR: Unexpected response format: {response}")
            return False
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Check for common error types
        error_text = str(e).lower()
        if "access" in error_text or "permissions" in error_text or "403" in error_text:
            print("\nIMPORTANT: Your Twitter API account may not have access to post tweets.")
            print("Twitter/X has restricted tweet posting to paid API tiers.")
            print("You need to upgrade your Twitter Developer Account to Basic ($100/month) or higher.")
            print("Visit: https://developer.twitter.com/en/portal/products/basic")
        
        return False

if __name__ == "__main__":
    success = post_tweet()
    if success:
        print("Tweet posted successfully!")
    else:
        print("Failed to post tweet.") 