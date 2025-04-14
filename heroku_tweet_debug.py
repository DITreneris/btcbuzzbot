"""
Heroku tweet debugging script - logs detailed information
"""
import os
import sys
import time
import json
import traceback
import datetime

def log_message(msg):
    """Log a message with timestamp"""
    timestamp = datetime.datetime.now().isoformat()
    print(f"[{timestamp}] {msg}")
    sys.stdout.flush()  # Ensure the message is flushed to logs immediately

def check_environment():
    """Check environment variables and modules"""
    log_message("=== HEROKU TWEET DEBUG SCRIPT ===")
    
    # Check Python version
    log_message(f"Python version: {sys.version}")
    log_message(f"Platform: {sys.platform}")
    
    # Check if we're in Heroku
    log_message(f"Running in Heroku: {'DYNO' in os.environ}")
    
    # Check for Twitter credentials
    twitter_vars = [
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET'
    ]
    
    log_message("Checking Twitter environment variables:")
    for var in twitter_vars:
        value = os.environ.get(var, '')
        if value:
            # Mask most of it for security
            masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "[TOO SHORT]"
            log_message(f"✓ {var}: {masked}")
        else:
            log_message(f"✗ {var}: MISSING")
    
    # Check available modules
    try:
        import tweepy
        log_message(f"✓ tweepy is available (version: {tweepy.__version__})")
    except ImportError:
        log_message("✗ tweepy is not available")
    
    try:
        import requests
        log_message(f"✓ requests is available (version: {requests.__version__})")
    except (ImportError, AttributeError):
        log_message("✗ requests is not available or version info missing")

def test_tweet():
    """Test tweeting with various methods"""
    log_message("\n=== TESTING TWEET FUNCTIONALITY ===")
    
    # Get credentials
    api_key = os.environ.get('TWITTER_API_KEY', '')
    api_secret = os.environ.get('TWITTER_API_SECRET', '')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN', '')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
    
    # Check credentials
    if not all([api_key, api_secret, access_token, access_token_secret]):
        log_message("✗ Cannot test tweeting - missing credentials")
        return False
    
    # Test tweepy availability
    try:
        import tweepy
        log_message("✓ tweepy successfully imported")
    except ImportError:
        log_message("✗ tweepy not available, cannot test tweeting")
        return False
    
    # Test Twitter authentication
    log_message("\nTesting Twitter authentication:")
    try:
        auth = tweepy.OAuth1UserHandler(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        log_message("✓ Created OAuth handler")
        
        # Test API
        api = tweepy.API(auth)
        log_message("✓ Created API object")
        
        # Test credentials
        me = api.verify_credentials()
        log_message(f"✓ Successfully authenticated as @{me.screen_name}")
        
        # Test tweeting
        log_message("\nTesting tweet posting:")
        timestamp = int(time.time())
        tweet_text = f"Heroku Debug Test - timestamp: {timestamp} #BTCBuzzBot"
        
        log_message(f"Attempting to post tweet: '{tweet_text}'")
        status = api.update_status(tweet_text)
        
        if status and hasattr(status, 'id'):
            tweet_id = status.id
            log_message(f"✓ Tweet posted successfully! ID: {tweet_id}")
            log_message(f"✓ Tweet URL: https://twitter.com/i/web/status/{tweet_id}")
            return True
        else:
            log_message(f"✗ Invalid status response: {status}")
            return False
            
    except Exception as e:
        log_message(f"✗ Error: {str(e)}")
        log_message("Stack trace:")
        traceback.print_exc()
        
        # Check for common errors
        error_text = str(e).lower()
        if "duplicate" in error_text:
            log_message("This appears to be a duplicate tweet error")
        elif "authent" in error_text or "authoriz" in error_text or "401" in error_text:
            log_message("This appears to be an authentication error")
        elif "403" in error_text:
            log_message("This appears to be a permissions error")
            
        return False

def main():
    """Main entry point"""
    try:
        check_environment()
        
        # Test tweeting
        tweet_success = test_tweet()
        
        # Output results
        log_message("\n=== DEBUG RESULTS ===")
        if tweet_success:
            log_message("✓ TWEET TEST PASSED - able to post tweets")
        else:
            log_message("✗ TWEET TEST FAILED - unable to post tweets")
    except Exception as e:
        log_message(f"✗ Unexpected error in debug script: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 