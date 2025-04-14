"""
Direct Tweet Handler for BTCBuzzBot.
Simplified implementation that doesn't rely on complex imports.
"""

import os
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('btcbuzzbot.direct_tweet_handler')

# Try to import tweepy
try:
    import tweepy
    TWEEPY_AVAILABLE = True
    logger.info("Tweepy imported successfully")
except ImportError:
    TWEEPY_AVAILABLE = False
    logger.error("Failed to import tweepy - Twitter functionality disabled")

# Try to import dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Environment variables loaded")
except ImportError:
    logger.warning("python-dotenv not available, environment variables must be set manually")

def post_tweet(content, content_type="general", price=None):
    """
    Post a tweet directly using tweepy.
    
    Args:
        content: Tweet content text
        content_type: Type of content (for logging)
        price: BTC price to include (optional)
        
    Returns:
        Dictionary with result information
    """
    if not TWEEPY_AVAILABLE:
        return {
            'success': False,
            'error': 'Tweepy module not available'
        }
        
    try:
        # Get Twitter API credentials
        api_key = os.environ.get('TWITTER_API_KEY')
        api_secret = os.environ.get('TWITTER_API_SECRET')
        access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        
        # Verify credentials
        if not all([api_key, api_secret, access_token, access_token_secret]):
            missing = []
            if not api_key: missing.append("TWITTER_API_KEY")
            if not api_secret: missing.append("TWITTER_API_SECRET")
            if not access_token: missing.append("TWITTER_ACCESS_TOKEN")
            if not access_token_secret: missing.append("TWITTER_ACCESS_TOKEN_SECRET")
            
            error_msg = f"Missing Twitter credentials: {', '.join(missing)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
            
        # Format tweet content
        if price is not None:
            tweet = f"BTC: ${price:,.2f} 📈\n{content}\n#Bitcoin #Crypto"
        else:
            tweet = f"{content}\n#Bitcoin #Crypto"
            
        # Initialize tweepy client
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Post the tweet
        logger.info(f"Posting tweet: {tweet}")
        response = client.create_tweet(text=tweet)
        
        # Handle response
        if response and hasattr(response, 'data') and 'id' in response.data:
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/user/status/{tweet_id}"
            
            logger.info(f"Tweet posted successfully! ID: {tweet_id}")
            logger.info(f"Tweet URL: {tweet_url}")
            
            return {
                'success': True,
                'tweet_id': tweet_id,
                'tweet': tweet,
                'url': tweet_url
            }
        else:
            logger.error("Failed to post tweet - unexpected response format")
            return {
                'success': False,
                'error': 'Failed to post tweet - unexpected response format'
            }
            
    except Exception as e:
        logger.error(f"Error posting tweet: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

# For direct testing
if __name__ == "__main__":
    print("Direct Tweet Handler Test")
    print("-" * 40)
    
    # Custom message from command line if provided
    message = "Testing the direct tweet handler! HODL to the moon! 🚀"
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        
    print(f"Posting tweet: {message}")
    result = post_tweet(message)
    
    if result['success']:
        print(f"✅ Tweet posted successfully!")
        print(f"Tweet ID: {result['tweet_id']}")
        print(f"Tweet URL: {result.get('url')}")
    else:
        print(f"❌ Tweet posting failed!")
        print(f"Error: {result.get('error', 'Unknown error')}") 