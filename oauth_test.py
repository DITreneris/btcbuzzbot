import tweepy
import os
from dotenv import load_dotenv
import json
import requests
from requests_oauthlib import OAuth1

def test_oauth():
    """Test OAuth 1.0a authentication directly"""
    # Load environment variables
    load_dotenv()
    
    # Get Twitter credentials
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    
    print("Credentials loaded:")
    print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
    print(f"API Secret: {api_secret[:5]}...{api_secret[-5:] if api_secret else 'None'}")
    print(f"Access Token: {access_token[:15]}...{access_token[-5:] if access_token else 'None'}")
    print(f"Access Token Secret: {access_token_secret[:5]}...{access_token_secret[-5:] if access_token_secret else 'None'}")
    
    print("\nTesting different authentication methods:")
    
    # Method 1: Direct API v1.1 call with OAuth1
    print("\n=== Method 1: Direct OAuth1 Request ===")
    try:
        auth = OAuth1(api_key, api_secret, access_token, access_token_secret)
        url = "https://api.twitter.com/1.1/account/verify_credentials.json"
        response = requests.get(url, auth=auth)
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            user_data = response.json()
            print(f"Authenticated as @{user_data.get('screen_name')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error with direct OAuth1: {e}")
    
    # Method 2: Tweepy API v1.1
    print("\n=== Method 2: Tweepy API v1.1 ===")
    try:
        auth = tweepy.OAuth1UserHandler(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        api = tweepy.API(auth)
        user = api.verify_credentials()
        print(f"Authenticated as @{user.screen_name}")
    except Exception as e:
        print(f"Error with Tweepy API v1.1: {e}")
    
    # Method 3: Tweepy Client v2
    print("\n=== Method 3: Tweepy Client v2 ===")
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        me = client.get_me(user_auth=True)
        print(f"Authenticated as @{me.data.username}")
    except Exception as e:
        print(f"Error with Tweepy Client v2: {e}")
    
    print("\nTroubleshooting tips:")
    print("1. Make sure your app has Write permissions on Twitter Developer Portal")
    print("2. Check that your token is not missing characters (sometimes they get cut off)")
    print("3. Try regenerating both API keys and access tokens together")
    print("4. Check your App's OAuth settings - make sure OAuth 1.0a is enabled")

if __name__ == "__main__":
    test_oauth() 