#!/usr/bin/env python
"""
Test Tweet Script
This script sends a test tweet to validate the Twitter API functionality.
"""

import os
import sys
import tweepy
from dotenv import load_dotenv
import datetime

def send_test_tweet(message=None):
    """
    Send a test tweet using the configured Twitter API credentials.
    
    Args:
        message (str, optional): Custom message to tweet. If None, a default message is used.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    # Load environment variables
    load_dotenv()
    
    # Get Twitter API credentials
    api_key = os.environ.get('TWITTER_API_KEY')
    api_secret = os.environ.get('TWITTER_API_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    
    # Check if credentials are set
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("❌ ERROR: Twitter API credentials are not properly set in .env file")
        missing = []
        if not api_key:
            missing.append("TWITTER_API_KEY")
        if not api_secret:
            missing.append("TWITTER_API_SECRET")
        if not access_token:
            missing.append("TWITTER_ACCESS_TOKEN")
        if not access_token_secret:
            missing.append("TWITTER_ACCESS_TOKEN_SECRET")
        print(f"   Missing: {', '.join(missing)}")
        return False
    
    # Default test message if none provided
    if message is None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"This is a test tweet from BTCBuzzBot at {timestamp}. If you're seeing this, the Twitter API integration is working correctly! #TestTweet"
    
    # Set up authentication
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Send the tweet
        response = client.create_tweet(text=message)
        
        if response and hasattr(response, 'data') and 'id' in response.data:
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/user/status/{tweet_id}"
            print(f"✅ SUCCESS: Test tweet sent successfully!")
            print(f"   Tweet ID: {tweet_id}")
            print(f"   Tweet URL: {tweet_url}")
            return True
        else:
            print("❌ ERROR: Failed to send test tweet. Unexpected response format.")
            print(f"   Response: {response}")
            return False
    
    except tweepy.TweepyException as e:
        print(f"❌ ERROR: Twitter API error while sending test tweet")
        print(f"   Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error while sending test tweet")
        print(f"   Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("BTCBuzzBot - Test Tweet Utility")
    print("-" * 40)
    
    # Check if a custom message was provided
    message = None
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        print(f"Using custom message: {message}")
    else:
        print("Using default test message...")
    
    # Send the test tweet
    send_test_tweet(message) 