"""
Twitter API diagnostic test script - direct and simple
"""
import os
import sys
import traceback

# Hard-code credentials for testing
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY', '')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')

def test_twitter_api():
    """Run direct Twitter API test with full error output"""
    print("\n=== TWITTER API DIAGNOSTIC TEST ===\n")
    
    # Display test environment info
    print(f"Python version: {sys.version}")
    print(f"Script path: {__file__}")
    
    # Check for tweepy
    try:
        import tweepy
        print(f"\n✅ TWEEPY AVAILABLE: Version {tweepy.__version__}")
    except ImportError as e:
        print(f"\n❌ TWEEPY NOT AVAILABLE: {e}")
        print("\nTo install tweepy: pip install tweepy")
        return False
    
    # Check for credentials
    print("\n--- API CREDENTIALS CHECK ---")
    credentials_ok = True
    
    # Mask most of the credentials but show first/last chars for debugging
    def mask_credential(cred):
        if not cred:
            return "MISSING"
        if len(cred) <= 8:
            return "TOO_SHORT"
        return f"{cred[:4]}...{cred[-4:]}"
    
    print(f"API Key: {mask_credential(TWITTER_API_KEY)}")
    print(f"API Secret: {mask_credential(TWITTER_API_SECRET)}")
    print(f"Access Token: {mask_credential(TWITTER_ACCESS_TOKEN)}")
    print(f"Access Token Secret: {mask_credential(TWITTER_ACCESS_TOKEN_SECRET)}")
    
    if not TWITTER_API_KEY:
        print("❌ API Key is missing")
        credentials_ok = False
    if not TWITTER_API_SECRET:
        print("❌ API Secret is missing")
        credentials_ok = False
    if not TWITTER_ACCESS_TOKEN:
        print("❌ Access Token is missing")
        credentials_ok = False
    if not TWITTER_ACCESS_TOKEN_SECRET:
        print("❌ Access Token Secret is missing")
        credentials_ok = False
        
    if not credentials_ok:
        print("\n❌ CREDENTIALS TEST FAILED: One or more credentials are missing")
        return False
    
    print("✅ All credentials are present")
    
    # Test Twitter API v1.1 (legacy)
    print("\n--- TESTING TWITTER API v1.1 (LEGACY) ---")
    try:
        print("Creating OAuth1 handler...")
        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET
        )
        
        print("Creating API instance...")
        api = tweepy.API(auth)
        
        print("Verifying credentials...")
        user = api.verify_credentials()
        print(f"✅ Successfully authenticated as @{user.screen_name}")
        
        # Try to post a simple test tweet
        test_tweet = f"This is a test tweet from BTCBuzzBot diagnostic tool. Delete me!"
        print(f"Posting test tweet: {test_tweet}")
        status = api.update_status(test_tweet)
        
        if status and hasattr(status, 'id'):
            print(f"✅ Tweet posted successfully! ID: {status.id}")
            return True
        else:
            print(f"❌ Failed to post tweet - unexpected response")
            print(f"Response: {status}")
            return False
            
    except tweepy.TweepyException as e:
        print(f"❌ Tweepy API error: {e}")
        traceback.print_exc()
        
        # Check for specific error types
        error_text = str(e).lower()
        if "authorization" in error_text or "authenticate" in error_text or "401" in error_text:
            print("\n🔑 AUTHENTICATION ERROR: Your credentials may be invalid or expired")
        elif "duplicate" in error_text:
            print("\n⚠️ DUPLICATE CONTENT: Twitter doesn't allow identical tweets")
        elif "rate limit" in error_text or "429" in error_text:
            print("\n⏱️ RATE LIMIT: You've hit Twitter's rate limits")
            
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_twitter_api()
    
    print("\n=== TEST SUMMARY ===")
    if success:
        print("✅ Twitter API test PASSED!")
        sys.exit(0)
    else:
        print("❌ Twitter API test FAILED!")
        sys.exit(1) 