"""
Ultra-simple direct tweet script for BTCBuzzBot that uses only tweepy.
"""

import os
import sys
import time
import traceback
from datetime import datetime

def post_tweet():
    """Post a tweet directly using the Twitter API"""
    print(f"---- Direct Tweet Script - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ----")
    
    # Try importing tweepy - required for this script
    try:
        import tweepy
        print("✅ Tweepy imported successfully!")
    except ImportError as e:
        print(f"❌ Failed to import tweepy: {e}")
        print("Make sure tweepy is installed: pip install tweepy")
        return False
    
    # Try importing requests for price fetch
    try:
        import requests
        print("✅ Requests imported successfully!")
    except ImportError as e:
        print(f"❌ Failed to import requests: {e}")
        print("Will use sample price since requests module is unavailable")
        
    # Twitter API credentials - from environment variables
    try:
        API_KEY = os.environ.get('TWITTER_API_KEY', '')
        API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
        ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
        ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
        
        # Print first and last few chars of credentials for debugging
        print(f"API Key: {API_KEY[:3]}...{API_KEY[-3:] if len(API_KEY) > 6 else 'TOO SHORT'}")
        print(f"API Secret: {API_SECRET[:3]}...{API_SECRET[-3:] if len(API_SECRET) > 6 else 'TOO SHORT'}")
        print(f"Access Token: {ACCESS_TOKEN[:3]}...{ACCESS_TOKEN[-3:] if len(ACCESS_TOKEN) > 6 else 'TOO SHORT'}")
        print(f"Access Token Secret: {ACCESS_TOKEN_SECRET[:3]}...{ACCESS_TOKEN_SECRET[-3:] if len(ACCESS_TOKEN_SECRET) > 6 else 'TOO SHORT'}")
        
        # Check if credentials are set
        if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
            missing = []
            if not API_KEY: missing.append("TWITTER_API_KEY")
            if not API_SECRET: missing.append("TWITTER_API_SECRET")
            if not ACCESS_TOKEN: missing.append("TWITTER_ACCESS_TOKEN")
            if not ACCESS_TOKEN_SECRET: missing.append("TWITTER_ACCESS_TOKEN_SECRET")
            
            print(f"❌ Missing Twitter API credentials: {', '.join(missing)}")
            print("Please set these environment variables on Heroku")
            return False
    except Exception as e:
        print(f"❌ Error getting Twitter credentials: {e}")
        return False
    
    # Fetch Bitcoin price
    btc_price = 0
    try:
        print("Fetching Bitcoin price from CoinGecko...")
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", 
                              timeout=10)
        data = response.json()
        btc_price = data["bitcoin"]["usd"]
        print(f"✅ Current BTC price: ${btc_price:,.2f}")
    except Exception as e:
        print(f"❌ Error fetching Bitcoin price: {e}")
        # Use sample price
        btc_price = 84500.00
        print(f"Using sample price: ${btc_price:,.2f}")
    
    # Create tweet content
    try:
        quotes = [
            "HODL to the moon! 🚀",
            "Buy the dip, enjoy the trip. 📈",
            "In crypto we trust. 💎",
            "Not your keys, not your coins. 🔑",
            "Blockchain is not just a technology, it's a revolution. ⚡",
            "Bitcoin fixes this. 🧠",
            "Diamond hands win in the long run. 💎🙌",
            "Fear is temporary, regret is forever. 🤔",
            "The best time to buy Bitcoin was yesterday. The second best time is today. ⏰",
            "Time in the market beats timing the market. ⌛"
        ]
        
        import random
        quote = random.choice(quotes)
        
        # Format the tweet
        emoji = "📈" if datetime.now().second % 2 == 0 else "🚀"
        timestamp = datetime.now().strftime('%H:%M:%S')
        tweet = f"BTC: ${btc_price:,.2f} {emoji}\n{quote}\n#Bitcoin #Crypto #{timestamp}"
        
        print(f"Tweet content: {tweet}")
    except Exception as e:
        print(f"❌ Error creating tweet content: {e}")
        return False
    
    # Post the tweet
    try:
        print("Creating Twitter API client...")
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        
        print("Posting tweet...")
        response = client.create_tweet(text=tweet)
        
        if response and hasattr(response, 'data') and 'id' in response.data:
            tweet_id = response.data['id']
            print(f"✅ Tweet successfully posted with ID: {tweet_id}")
            print(f"Tweet URL: https://twitter.com/i/web/status/{tweet_id}")
            return True
        else:
            print(f"❌ Failed to post tweet - unexpected response format: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Error posting tweet: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = post_tweet()
    
    if success:
        print("\n✅ Tweet posted successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tweet posting failed!")
        sys.exit(1) 