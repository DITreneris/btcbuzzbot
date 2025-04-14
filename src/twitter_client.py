import tweepy
from typing import Optional
import asyncio
from functools import partial
import json

class TwitterClient:
    def __init__(self, api_key: str, api_secret: str, 
                 access_token: str, access_token_secret: str):
        # Create v2 Client for Twitter API v2
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
    async def post_tweet(self, text: str) -> Optional[str]:
        """Post a tweet and return tweet ID using Twitter API v2"""
        try:
            # Run the synchronous tweepy call in a thread pool
            loop = asyncio.get_event_loop()
            
            # Use v2 API client.create_tweet which is working
            response = await loop.run_in_executor(
                None,
                partial(self.client.create_tweet, text=text)
            )
            
            # Return the tweet ID 
            if response and response.data:
                return response.data['id']
            else:
                print("No data returned from Twitter API")
                return None
                
        except Exception as e:
            print(f"Error posting tweet: {e}")
            # Log more detailed error info
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                try:
                    error_data = json.loads(e.response.text)
                    print(f"Twitter API error details: {error_data}")
                except:
                    print(f"Twitter API error response: {e.response.text}")
            return None 