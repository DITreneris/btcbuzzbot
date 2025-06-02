import tweepy
from typing import Optional, Dict
import asyncio
from functools import partial
import json

class TwitterClient:
    def __init__(self, api_key: str, api_secret: str, 
                 access_token: str, access_token_secret: str, bearer_token: Optional[str] = None):
        # Create v2 Client for Twitter API v2 with OAuth 1.0a (for posting)
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Create a separate client with Bearer Token for read-only operations (if available)
        self.bearer_client = None
        if bearer_token:
            try:
                self.bearer_client = tweepy.Client(bearer_token=bearer_token)
                print("TwitterClient: Bearer Token client initialized for read-only operations")
            except Exception as e:
                print(f"TwitterClient: Failed to initialize Bearer Token client: {e}")
                self.bearer_client = None
        
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
        # Try Bearer Token client first (if available), then fall back to OAuth client
        clients_to_try = []
        if self.bearer_client:
            clients_to_try.append(("Bearer Token", self.bearer_client))
        clients_to_try.append(("OAuth", self.client))
        
        for auth_type, client in clients_to_try:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    partial(client.get_tweet, id=tweet_id, tweet_fields=["public_metrics"])
                )

                if response and response.data and response.data.public_metrics:
                    metrics = response.data.public_metrics
                    print(f"Successfully fetched engagement for {tweet_id} using {auth_type} auth")
                    return {
                        "likes": metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0) 
                        # also available: impression_count, reply_count, quote_count, etc.
                    }
                else:
                    print(f"No public_metrics data returned from Twitter API for tweet ID {tweet_id} using {auth_type}")
                    if response:
                        print(f"Full response for {tweet_id}: {response}")
                    
            except Exception as e:
                print(f"Error getting tweet engagement for {tweet_id} using {auth_type}: {e}")
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    try:
                        error_data = json.loads(e.response.text)
                        print(f"Twitter API error details for {tweet_id} using {auth_type}: {error_data}")
                    except:
                        print(f"Twitter API error response for {tweet_id} using {auth_type}: {e.response.text}")
                
                # If this is not the last client to try, continue to the next one
                if auth_type != "OAuth":  # Continue if Bearer Token failed, try OAuth
                    print(f"Trying next authentication method for tweet {tweet_id}...")
                    continue
        
        # All authentication methods failed
        return None 