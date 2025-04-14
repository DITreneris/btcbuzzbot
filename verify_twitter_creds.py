#!/usr/bin/env python
"""
Verify Twitter API credentials script.
This script tests if the Twitter API credentials in the .env file are valid.
"""

import os
import tweepy
from dotenv import load_dotenv

def verify_credentials():
    """Verify Twitter API credentials and print their status."""
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
    
    # Set up authentication
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Try to get user information to verify credentials
        user = client.get_me()
        
        if user:
            print(f"✅ SUCCESS: Twitter API credentials are valid")
            print(f"   User: @{user.data.username}")
            print(f"   Name: {user.data.name}")
            print(f"   ID: {user.data.id}")
            return True
        else:
            print("❌ ERROR: Could not retrieve user information")
            return False
    
    except tweepy.TweepyException as e:
        print(f"❌ ERROR: Twitter API authentication failed")
        print(f"   Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Verifying Twitter API credentials...")
    verify_credentials() 