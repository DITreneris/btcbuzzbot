"""
Super simple test to verify tweepy is accessible
"""

import os
from dotenv import load_dotenv
import tweepy

# Load environment variables
load_dotenv()

def test_tweepy():
    """Test basic tweepy functionality"""
    try:
        print("Testing tweepy installation...")
        
        # Get Twitter API credentials
        api_key = os.environ.get('TWITTER_API_KEY')
        api_secret = os.environ.get('TWITTER_API_SECRET')
        access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        
        print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
        print(f"API Secret: {api_secret[:5]}...{api_secret[-5:] if api_secret else 'None'}")
        print(f"Access Token: {access_token[:5]}...{access_token[-5:] if access_token else 'None'}")
        print(f"Access Token Secret: {access_token_secret[:5]}...{access_token_secret[-5:] if access_token_secret else 'None'}")
        
        # Initialize client
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Try to get user information first to test authentication
        print("Testing authentication by getting user info...")
        me = client.get_me(user_auth=True)
        
        print(f"Authentication successful! Logged in as: @{me.data.username}")
        return True
        
    except Exception as e:
        print(f"Error testing tweepy: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_tweepy() 