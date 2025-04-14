import tweepy
import os
from dotenv import load_dotenv

def post_simple_tweet():
    """Post a simple tweet using the minimal required code"""
    # Load environment variables
    load_dotenv()
    
    # Get Twitter credentials
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    
    # Authentication
    auth = tweepy.OAuth1UserHandler(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    # Create API object
    api = tweepy.API(auth)
    
    try:
        # Post a simple tweet
        print("Attempting to post a tweet...")
        tweet_text = "Testing my new BTCBuzzBot! 🚀 #Bitcoin"
        result = api.update_status(status=tweet_text)
        
        print(f"Success! Tweet posted with ID: {result.id}")
        print(f"Tweet URL: https://twitter.com/user/status/{result.id}")
        
    except Exception as e:
        print(f"Error posting tweet: {e}")
        # Provide detailed error information
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Error details: {e.response.text}")
        
        print("\nTo post tweets, your Twitter Developer App needs the 'Read and Write' permissions.")
        print("1. Go to developer.twitter.com/portal/projects")
        print("2. Select your project and app")
        print("3. Go to 'User authentication settings'")
        print("4. Enable 'Read and Write' permissions")
        print("5. Save changes and regenerate tokens if needed")

if __name__ == "__main__":
    post_simple_tweet() 