"""
Super simple tweet test with no dependencies on other project modules
"""

import os

# Try loading environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("ℹ️ dotenv module not found, using existing environment variables")

try:
    import tweepy
    print("✅ Tweepy imported successfully!")
except ImportError:
    print("❌ Failed to import tweepy. Please install it with 'pip install tweepy'")
    exit(1)

def post_simple_tweet():
    """Post a simple tweet using direct tweepy API calls"""
    try:
        # Get Twitter API credentials
        api_key = os.environ.get('TWITTER_API_KEY')
        api_secret = os.environ.get('TWITTER_API_SECRET')
        access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        
        # Log credentials (safely)
        print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
        print(f"API Secret: {api_secret[:5]}...{api_secret[-5:] if api_secret else 'None'}")
        print(f"Access Token: {access_token[:5]}...{access_token[-5:] if access_token else 'None'}")
        print(f"Access Token Secret: {access_token_secret[:5]}...{access_token_secret[-5:] if access_token_secret else 'None'}")
        
        # Check credentials
        if not all([api_key, api_secret, access_token, access_token_secret]):
            print("❌ Missing Twitter API credentials. Please check your .env file.")
            return False
        
        # Create tweepy client
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Try to verify credentials by getting account info
        print("Testing authentication by getting user info...")
        me = client.get_me(user_auth=True)
        print(f"✅ Successfully authenticated as @{me.data.username}")
        
        # Post the tweet
        tweet = "Testing BTCBuzzBot with direct tweepy implementation! #Bitcoin #Crypto #Test"
        print(f"\nPosting tweet: {tweet}")
        
        response = client.create_tweet(text=tweet)
        
        if response and hasattr(response, 'data') and 'id' in response.data:
            tweet_id = response.data['id']
            print(f"✅ Tweet successfully posted with ID: {tweet_id}")
            print(f"Tweet URL: https://twitter.com/user/status/{tweet_id}")
            return True
        else:
            print("❌ Failed to post tweet - no valid response")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("BTCBuzzBot - Simple Tweet Test")
    print("-" * 40)
    
    result = post_simple_tweet()
    
    if result:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!") 