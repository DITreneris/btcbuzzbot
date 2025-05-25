import tweepy
from typing import Optional, Dict
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

    async def get_tweet_engagement(self, tweet_id: str) -> Optional[Dict[str, int]]:
        """Get engagement (likes, retweets) for a given tweet ID using Twitter API v2."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(self.client.get_tweet, id=tweet_id, tweet_fields=["public_metrics"])
            )

            if response and response.data and response.data.public_metrics:
                metrics = response.data.public_metrics
                return {
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0) 
                    # also available: impression_count, reply_count, quote_count, etc.
                }
            else:
                print(f"No public_metrics data returned from Twitter API for tweet ID {tweet_id}")
                # Log the full response if available and helpful
                if response:
                    print(f"Full response for {tweet_id}: {response}")
                return None
        except Exception as e:
            print(f"Error getting tweet engagement for {tweet_id}: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                try:
                    error_data = json.loads(e.response.text)
                    print(f"Twitter API error details for {tweet_id}: {error_data}")
                except:
                    print(f"Twitter API error response for {tweet_id}: {e.response.text}")
            return None 