"""
Scheduler LLM Integration Module for BTCBuzzBot

This module connects the Ollama LLM content generation system with the
bot's scheduler to generate tweets automatically based on the current
Bitcoin price and market conditions.
"""

import logging
import os
import random
import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scheduler_llm')

# Import required modules, with fallbacks for testing
try:
    from src.llm_integration import initialize_ollama, ContentGenerator
    from src.prompt_templates import PromptManager
    from src.tweet_handler import post_tweet, get_tweet_handler
    from src.database import get_db_connection
except ImportError:
    logger.warning("Running with mock imports - some functionality may be limited")
    try:
        from llm_integration import initialize_ollama, ContentGenerator
        from prompt_templates import PromptManager
        from tweet_handler import post_tweet, get_tweet_handler
        from database import get_db_connection
    except ImportError:
        logger.error("Could not import required modules for LLM scheduler integration")

class LLMTweetGenerator:
    """
    Integrates LLM content generation with the scheduler and tweet poster.
    This class handles the end-to-end process of generating and posting tweets.
    """
    
    def __init__(self):
        """Initialize the LLM tweet generator"""
        try:
            # Initialize LLM components
            self.client = initialize_ollama()
            self.content_generator = ContentGenerator(self.client)
            self.prompt_manager = PromptManager()
            self.initialized = True
            logger.info("Successfully initialized LLM tweet generator")
        except Exception as e:
            logger.error(f"Failed to initialize LLM tweet generator: {str(e)}")
            self.initialized = False
            
    def determine_content_type(self) -> str:
        """
        Determine what type of content to generate based on schedule or strategy.
        Currently uses a simple rotation pattern, but can be enhanced with more
        sophisticated strategies based on performance data.
        
        Returns:
            Content type to generate ('price_update', 'joke', 'motivation')
        """
        # Get recent posts to avoid repeating the same type
        conn = get_db_connection()
        recent_posts = conn.execute(
            'SELECT content_type FROM posts ORDER BY timestamp DESC LIMIT 2'
        ).fetchall()
        conn.close()
        
        content_types = ['price_update', 'joke', 'motivation']
        
        # Default to price update if no recent posts
        if not recent_posts:
            return 'price_update'
            
        # Avoid repeating the last content type
        last_type = recent_posts[0]['content_type']
        
        # If we have a specific mapping to LLM content types, apply it
        type_mapping = {
            'quote': 'motivation',
            'joke': 'joke',
            'price': 'price_update'
        }
        
        last_llm_type = type_mapping.get(last_type, 'price_update')
        
        # Remove the last type from options
        if last_llm_type in content_types:
            content_types.remove(last_llm_type)
            
        # Choose randomly from remaining types with higher weight for price updates
        weights = [0.7, 0.3] if 'price_update' in content_types else [0.5, 0.5]
        return random.choices(content_types, weights=weights)[0]
    
    def get_market_trend(self, price_change: float) -> str:
        """
        Determine market trend based on price change.
        
        Args:
            price_change: 24-hour price change percentage
            
        Returns:
            Market trend description ('bullish', 'bearish', or 'neutral')
        """
        if price_change > 3.0:
            return 'bullish'
        elif price_change < -3.0:
            return 'bearish'
        else:
            return 'neutral'
    
    def fetch_latest_price(self) -> Dict[str, Any]:
        """
        Fetch the latest Bitcoin price from the database.
        
        Returns:
            Dictionary with price data (price, change_pct)
        """
        try:
            conn = get_db_connection()
            
            # Get latest price
            latest_price = conn.execute(
                'SELECT * FROM prices ORDER BY timestamp DESC LIMIT 1'
            ).fetchone()
            
            # Get price from 24h ago for calculating change
            day_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat()
            previous_price = conn.execute(
                'SELECT * FROM prices WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1',
                (day_ago,)
            ).fetchone()
            
            conn.close()
            
            if not latest_price:
                logger.error("No price data found in database")
                return {
                    'price': 0,
                    'change_pct': 0,
                    'success': False
                }
                
            price = latest_price['price']
            
            # Calculate price change percentage
            if previous_price:
                prev_price = previous_price['price']
                change_pct = ((price - prev_price) / prev_price) * 100
            else:
                change_pct = 0
                
            return {
                'price': price,
                'change_pct': change_pct,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error fetching latest price: {str(e)}")
            return {
                'price': 0,
                'change_pct': 0,
                'success': False
            }
    
    def generate_tweet_content(self) -> Dict[str, Any]:
        """
        Generate tweet content using the LLM.
        
        Returns:
            Dictionary with generated content and metadata
        """
        if not self.initialized:
            logger.error("LLM tweet generator not initialized")
            return {
                'success': False,
                'error': 'LLM generator not initialized'
            }
            
        try:
            # Determine content type
            content_type = self.determine_content_type()
            logger.info(f"Generating content of type: {content_type}")
            
            # Get price data
            price_data = self.fetch_latest_price()
            
            if not price_data['success']:
                logger.error("Failed to fetch price data")
                return {
                    'success': False,
                    'error': 'Failed to fetch price data'
                }
                
            # Determine market trend
            market_trend = self.get_market_trend(price_data['change_pct'])
            
            # Generate content based on type
            result = None
            
            if content_type == 'price_update':
                result = self.content_generator.generate_price_update(
                    current_price=price_data['price'],
                    change_24h=price_data['change_pct'],
                    market_trend=market_trend
                )
                traditional_type = 'price'
                
            elif content_type == 'joke':
                result = self.content_generator.generate_crypto_joke()
                traditional_type = 'joke'
                
            elif content_type == 'motivation':
                result = self.content_generator.generate_motivational_content(
                    current_price=price_data['price'],
                    market_status=market_trend
                )
                traditional_type = 'quote'
                
            else:
                logger.error(f"Unknown content type: {content_type}")
                return {
                    'success': False,
                    'error': f'Unknown content type: {content_type}'
                }
                
            if not result or not result.get('success', False):
                error = result.get('error', 'Unknown error') if result else 'Generation failed'
                logger.error(f"Content generation failed: {error}")
                return {
                    'success': False,
                    'error': error
                }
                
            # Validate the content
            is_valid, reason = self.content_generator.validate_content(result['text'])
            
            if not is_valid:
                logger.warning(f"Generated content validation failed: {reason}")
                return {
                    'success': False,
                    'error': f'Content validation failed: {reason}'
                }
                
            # Return the result
            return {
                'success': True,
                'content': result['text'],
                'content_type': traditional_type,
                'llm_type': content_type,
                'completion_time': result.get('completion_time', 0),
                'price': price_data['price'],
                'model': result.get('model', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error generating tweet content: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def post_tweet(self) -> Dict[str, Any]:
        """
        Generate and post a tweet.
        
        Returns:
            Dictionary with result information
        """
        if not self.initialized:
            logger.error("LLM tweet generator not initialized")
            return {
                'success': False,
                'error': 'LLM generator not initialized'
            }
            
        try:
            # Generate content
            generated = self.generate_tweet_content()
            
            if not generated['success']:
                return generated
                
            # Post the tweet
            tweet_result = post_tweet(
                content=generated['content'],
                content_type=generated['content_type'],
                price=generated['price']
            )
            
            if not tweet_result.get('success', False):
                logger.error(f"Failed to post tweet: {tweet_result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'error': f"Failed to post tweet: {tweet_result.get('error', 'Unknown error')}"
                }
                
            # Update the post with LLM metadata
            try:
                conn = get_db_connection()
                conn.execute(
                    'UPDATE posts SET is_llm_generated = 1, generation_time = ? WHERE id = ?',
                    (generated['completion_time'], tweet_result['post_id'])
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning(f"Failed to update post with LLM metadata: {str(e)}")
                
            logger.info(f"Successfully posted LLM-generated tweet (ID: {tweet_result['post_id']})")
            
            return {
                'success': True,
                'post_id': tweet_result['post_id'],
                'tweet_id': tweet_result.get('tweet_id'),
                'content': generated['content'],
                'content_type': generated['content_type'],
                'llm_type': generated['llm_type'],
                'model': generated['model']
            }
            
        except Exception as e:
            logger.error(f"Error posting tweet: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Function to get a singleton instance
_instance = None

def get_llm_tweet_generator() -> LLMTweetGenerator:
    """Get the singleton instance of LLMTweetGenerator"""
    global _instance
    if _instance is None:
        _instance = LLMTweetGenerator()
    return _instance


# Test function for direct runs
def test_llm_tweet_generator():
    """Test the LLM tweet generator"""
    generator = LLMTweetGenerator()
    
    print("🔄 Generating tweet content...")
    content_result = generator.generate_tweet_content()
    
    if content_result['success']:
        print("✅ Content generated successfully!")
        print(f"Content type: {content_result['llm_type']}")
        print(f"Content: {content_result['content']}")
        print(f"Generation time: {content_result['completion_time']:.2f}s")
    else:
        print("❌ Content generation failed!")
        print(f"Error: {content_result.get('error', 'Unknown error')}")
        
    # Uncomment to test tweeting (caution: will actually post a tweet)
    """
    print("\n🔄 Posting tweet...")
    post_result = generator.post_tweet()
    
    if post_result['success']:
        print("✅ Tweet posted successfully!")
        print(f"Post ID: {post_result['post_id']}")
        print(f"Tweet ID: {post_result.get('tweet_id', 'N/A')}")
    else:
        print("❌ Tweet posting failed!")
        print(f"Error: {post_result.get('error', 'Unknown error')}")
    """


# For testing
if __name__ == "__main__":
    test_llm_tweet_generator() 