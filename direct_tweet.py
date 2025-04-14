"""
Ultra-simple direct tweet script for BTCBuzzBot that uses only tweepy.
"""

import os
import sys
import time
from datetime import datetime

# Print status info
print(f"Direct Tweet Script - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

# Try importing tweepy - required for this script
try:
    import tweepy
    print("✅ Tweepy imported successfully!")
except ImportError:
    print("❌ Failed to import tweepy")
    print("Installing tweepy...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tweepy"])
    import tweepy
    print("✅ Tweepy installed successfully!")

# Twitter API credentials - manually specify them here if necessary
API_KEY = os.environ.get('TWITTER_API_KEY', '')
API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')

# Fetch current Bitcoin price from CoinGecko API
def get_bitcoin_price():
    try:
        import requests
        print("Fetching Bitcoin price from CoinGecko...")
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        data = response.json()
        price = data["bitcoin"]["usd"]
        print(f"Current BTC price: ${price:,.2f}")
        return price
    except Exception as e:
        print(f"Error fetching Bitcoin price: {e}")
        # Return a sample price for testing
        print("Using sample price: $84,500.00")
        return 84500.00

# Post the tweet
def post_tweet():
    # Verify Twitter credentials
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        print("❌ Missing Twitter API credentials")
        print("Please set the following environment variables:")
        print("TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET")
        return False
    
    try:
        # Create tweepy client
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        
        # Get current Bitcoin price
        btc_price = get_bitcoin_price()
        
        # Create tweet content
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
        
        print(f"\nPosting tweet: {tweet}")
        
        # Post the tweet
        response = client.create_tweet(text=tweet)
        
        if response and hasattr(response, 'data') and 'id' in response.data:
            tweet_id = response.data['id']
            print(f"✅ Tweet successfully posted with ID: {tweet_id}")
            print(f"Tweet URL: https://twitter.com/i/web/status/{tweet_id}")
            return True
        else:
            print("❌ Failed to post tweet - unexpected response")
            print(f"Response: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Error posting tweet: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = post_tweet()
    
    if success:
        print("\n✅ Tweet posted successfully!")
    else:
        print("\n❌ Tweet posting failed!")
        sys.exit(1) 