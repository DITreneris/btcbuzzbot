"""
Hardcoded tweet script - most direct implementation possible
"""
import os
import sys
import time
from datetime import datetime

def post_tweet():
    """Post tweet with minimal dependencies and maximum error reporting"""
    print(f"\n==== HARDCODED TWEET ATTEMPT ({datetime.now().isoformat()}) ====\n")
    
    # Check if tweepy is available
    try:
        import tweepy
        print(f"Found tweepy version: {tweepy.__version__}")
    except ImportError as e:
        print(f"ERROR: Tweepy not available - {e}")
        return False
    
    # Get credentials directly from environment
    api_key = os.environ.get('TWITTER_API_KEY')
    api_secret = os.environ.get('TWITTER_API_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    
    # Verify credentials are available
    if not api_key or not api_secret or not access_token or not access_token_secret:
        print("ERROR: Missing Twitter credentials in environment variables!")
        print(f"API_KEY present: {'YES' if api_key else 'NO'}")
        print(f"API_SECRET present: {'YES' if api_secret else 'NO'}")
        print(f"ACCESS_TOKEN present: {'YES' if access_token else 'NO'}")
        print(f"ACCESS_TOKEN_SECRET present: {'YES' if access_token_secret else 'NO'}")
        return False
    
    # Create unique tweet text to avoid duplicate errors
    timestamp = int(time.time())
    tweet_text = f"BTC test {timestamp}"
    
    print(f"Attempting to post tweet: '{tweet_text}'")
    
    # Minimal implementation with maximum error reporting
    try:
        # Set up auth with detailed error checking
        try:
            auth = tweepy.OAuth1UserHandler(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            print("Created OAuth handler")
        except Exception as auth_err:
            print(f"ERROR creating OAuth handler: {auth_err}")
            import traceback
            traceback.print_exc()
            return False
        
        # Create API with detailed error checking
        try:
            api = tweepy.API(auth)
            print("Created API object")
        except Exception as api_err:
            print(f"ERROR creating API object: {api_err}")
            import traceback
            traceback.print_exc()
            return False
        
        # Try verify_credentials to validate auth
        try:
            user = api.verify_credentials()
            print(f"Authenticated as @{user.screen_name}")
        except Exception as verify_err:
            print(f"ERROR verifying credentials: {verify_err}")
            import traceback
            traceback.print_exc()
            
            # Credential details for debugging (first/last 4 chars only)
            def mask(text):
                if not text: return "NONE"
                if len(text) <= 8: return "TOO_SHORT"
                return f"{text[:4]}...{text[-4:]}"
            
            print(f"API_KEY: {mask(api_key)}")
            print(f"API_SECRET: {mask(api_secret)}")
            print(f"ACCESS_TOKEN: {mask(access_token)}")
            print(f"ACCESS_TOKEN_SECRET: {mask(access_token_secret)}")
            return False
        
        # Try to post tweet
        try:
            status = api.update_status(tweet_text)
            print(f"SUCCESS! Tweet posted with ID: {status.id}")
            return True
        except Exception as tweet_err:
            print(f"ERROR posting tweet: {tweet_err}")
            import traceback
            traceback.print_exc()
            
            # Check for common error types
            err_text = str(tweet_err).lower()
            if "duplicate" in err_text:
                print("ERROR appears to be a duplicate tweet. Try again with different text.")
            elif "auth" in err_text or "401" in err_text:
                print("ERROR appears to be authentication related. Check your credentials.")
            elif "403" in err_text:
                print("ERROR appears to be a permission issue. Check your app permissions.")
            return False
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = post_tweet()
    
    if result:
        print("\n✅ TWEET POSTED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\n❌ TWEET POSTING FAILED!")
        sys.exit(1) 