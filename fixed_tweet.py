"""
Ultra-simplified tweeting module with hardcoded credentials
"""
import os
import sys
import time
from datetime import datetime

def post_tweet():
    """Attempt to post a tweet with hardcoded credentials"""
    print("\n==== FIXED TWEET ATTEMPT ====\n")
    
    try:
        import tweepy
        print(f"Using tweepy version: {tweepy.__version__}")
    except ImportError:
        print("ERROR: tweepy is not installed")
        return False
    
    # Hardcoded credentials that worked previously
    api_key = "8Cv7D8NHOyUwOFf1LJMwWMH2t"
    api_secret = "Mm5FP36hE6Ow1TuAzhZv81zTRHqwXiG0Y7wg1XVFPb0Xo9NU2o"
    access_token = "1640064704224899073-5ks80Qb6qJd01fMZm1f6N8JFoQDr2e"
    access_token_secret = "pUnUvz6hPWyMnDLXFOiODpFwXQvOoFnXYSucSB2yz"
    
    try:
        # Set up auth with known working credentials
        auth = tweepy.OAuth1UserHandler(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Create API
        api = tweepy.API(auth)
        
        # Create unique tweet
        timestamp = int(time.time())
        tweet_text = f"Fixed test tweet {timestamp} #BTCBuzzBot"
        
        # Post tweet
        print(f"Posting tweet: {tweet_text}")
        status = api.update_status(tweet_text)
        
        print(f"SUCCESS! Tweet posted with ID: {status.id}")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = post_tweet()
    if success:
        print("Tweet posted successfully!")
    else:
        print("Failed to post tweet.") 