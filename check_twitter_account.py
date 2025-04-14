import tweepy
import os
from dotenv import load_dotenv

def check_twitter_account():
    """Check Twitter account access and permissions"""
    # Load environment variables
    load_dotenv()
    
    # Get Twitter credentials
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    
    print("\nTwitter Account Verification:")
    print("-" * 50)
    
    # Create OAuth1 handler
    auth = tweepy.OAuth1UserHandler(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    # Create API v1.1 instance
    api = tweepy.API(auth)
    
    try:
        # Try to get account info
        print("Checking account info...")
        user = api.verify_credentials()
        print(f"✅ Successfully authenticated as: @{user.screen_name}")
        print(f"Account ID: {user.id}")
        print(f"Account created at: {user.created_at}")
        print(f"Follower count: {user.followers_count}")
        print(f"Protected account: {user.protected}")
        print()
    except Exception as e:
        print(f"❌ Error verifying credentials: {e}")
        print()
    
    # Try to get rate limit status to check permissions
    try:
        print("Checking rate limits and permissions...")
        limits = api.rate_limit_status()
        
        # Check if we can read home timeline
        if '/statuses/home_timeline' in limits['resources']['statuses']:
            print("✅ Can read home timeline")
        
        # Check if we have enough search permissions
        if '/search/tweets' in limits['resources']['search']:
            print("✅ Can search tweets")
        
        # Check if app might have write access
        try:
            app_auth = api.get_settings()
            print("✅ Can access app settings")
        except:
            print("❌ Cannot access app settings")
        
        # Check if we can upload media (required for many actions)
        if '/media/upload' in limits['resources']['media']:
            print("✅ Can upload media")
        
        print("\nAPI Access Levels")
        print("-" * 50)
        print("To post tweets, your Twitter Developer App needs to have")
        print("the 'Read and Write' permission level at minimum.")
        print("\nSteps to enable write access:")
        print("1. Go to developer.twitter.com/portal/projects")
        print("2. Select your project and app")
        print("3. Go to 'User authentication settings'")
        print("4. Enable 'Read and Write' permissions")
        print("5. Save changes and regenerate tokens if needed")
        
    except Exception as e:
        print(f"❌ Error checking rate limits: {e}")
    
    print("\nDirect API Account Info")
    print("-" * 50)
    try:
        # Try a v2 API call that's available at basic tier
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        me = client.get_me(user_auth=True)
        if me and me.data:
            print(f"V2 API authenticated as: @{me.data.username}")
            print(f"Name: {me.data.name}")
            print(f"ID: {me.data.id}")
        else:
            print("❌ Could not get v2 account info")
            
    except Exception as e:
        print(f"❌ Error accessing v2 account info: {e}")

if __name__ == "__main__":
    check_twitter_account() 