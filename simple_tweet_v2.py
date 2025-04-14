import tweepy
import os
from dotenv import load_dotenv
import json

def post_tweet_v2():
    """Post a tweet using the v2 API with OAuth 1.0a"""
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
    
    try:
        # Create v2 Client
        print("\nCreating Twitter client...")
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Try to get user information first to test authentication
        print("Testing authentication by getting user info...")
        try:
            me = client.get_me(user_auth=True)
            print(f"Authenticated as @{me.data.username}")
        except Exception as e:
            print(f"Error getting user info: {e}")
            raise
        
        # Post tweet
        print("\nAttempting to post a tweet...")
        tweet_text = "Testing BTCBuzzBot with Twitter API v2! #Bitcoin #Crypto #Testing"
        
        response = client.create_tweet(text=tweet_text)
        
        if response and response.data:
            tweet_id = response.data['id']
            print(f"Success! Tweet posted with ID: {tweet_id}")
            print(f"Tweet URL: https://twitter.com/user/status/{tweet_id}")
            return tweet_id
        else:
            print("Failed to post tweet - no response data")
            return None
        
    except Exception as e:
        print(f"Error: {e}")
        # Try to extract more error details
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            try:
                error_data = json.loads(e.response.text)
                print(f"Twitter API error details: {error_data}")
            except:
                print(f"Twitter API error response: {e.response.text}")
        
        print("\nTroubleshooting tips:")
        print("1. Verify that your Twitter Developer App has 'Read and Write' permissions")
        print("2. Check that all credentials are correctly copied from the Twitter Developer Portal")
        print("3. Make sure your app is properly set up with OAuth 1.0a for user authentication")
        print("4. Try regenerating all tokens in the Twitter Developer Portal")
        return None

if __name__ == "__main__":
    post_tweet_v2() 