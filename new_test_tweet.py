"""
Simple test script for the tweet_handler module.
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.abspath('.'))

async def main():
    try:
        print("Importing tweet_handler module...")
        from src.tweet_handler import post_tweet
        
        print("Module imported successfully!")
        
        # Test posting a tweet
        print("Posting a test tweet...")
        content = "Testing the tweet handler! HODL to the moon! 🚀 #Testing"
        
        result = post_tweet(content=content, content_type="test")
        
        if result['success']:
            print(f"✅ Tweet posted successfully! Tweet ID: {result['tweet_id']}")
            print(f"Tweet content: {result['tweet']}")
        else:
            print(f"❌ Tweet posting failed! Error: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test function
    print("Starting tweet test...")
    asyncio.run(main()) 