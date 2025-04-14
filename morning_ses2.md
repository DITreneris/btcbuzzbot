# Morning Coding Session 2: BTCBuzzBot Core Functionality

## Session Goals
1. ✅ Implement content management system (quotes and jokes)
2. ✅ Create main application script 
3. ✅ Add basic scheduling functionality
4. ✅ Implement configuration management

## Time Allocation (3 hours)
- 09:00 - 10:00: Content Management System ✅
- 10:00 - 11:00: Main Application Script ✅
- 11:00 - 11:30: Scheduling Functionality ✅
- 11:30 - 12:00: Configuration Management ✅

## Detailed Tasks

### 1. Content Management System (60 mins)
- [x] Create content_manager.py
  ```python
  from typing import Dict, Any, List, Optional
  import random
  from datetime import datetime, timedelta
  
  class ContentManager:
      def __init__(self, database):
          self.db = database
          
      async def add_quote(self, text: str, category: str = "motivational") -> str:
          """Add a new quote to the database"""
          result = await self.db.db.quotes.insert_one({
              "text": text,
              "category": category,
              "created_at": datetime.utcnow(),
              "used_count": 0
          })
          return str(result.inserted_id)
          
      async def add_joke(self, text: str, category: str = "humor") -> str:
          """Add a new joke to the database"""
          result = await self.db.db.jokes.insert_one({
              "text": text,
              "category": category,
              "created_at": datetime.utcnow(),
              "used_count": 0
          })
          return str(result.inserted_id)
          
      async def get_random_content(self) -> Dict[str, Any]:
          """Get random content (quote or joke) that wasn't used recently"""
          # Randomly choose between quote and joke
          collection = random.choice(["quotes", "jokes"])
          
          # Find content that wasn't used in the last 7 days
          seven_days_ago = datetime.utcnow() - timedelta(days=7)
          
          # Get unused or least used content
          pipeline = [
              {"$match": {
                  "$or": [
                      {"last_used": {"$lt": seven_days_ago}},
                      {"last_used": {"$exists": False}}
                  ]
              }},
              {"$sort": {"used_count": 1}},
              {"$limit": 10},
              {"$sample": {"size": 1}}
          ]
          
          cursor = self.db.db[collection].aggregate(pipeline)
          content = await cursor.to_list(length=1)
          
          if not content:
              # If no content matches criteria, get any random content
              cursor = self.db.db[collection].aggregate([{"$sample": {"size": 1}}])
              content = await cursor.to_list(length=1)
              
          if content:
              selected = content[0]
              # Update usage count
              await self.db.db[collection].update_one(
                  {"_id": selected["_id"]},
                  {"$inc": {"used_count": 1}, "$set": {"last_used": datetime.utcnow()}}
              )
              
              return {
                  "text": selected["text"],
                  "type": "quote" if collection == "quotes" else "joke",
                  "category": selected.get("category", "general")
              }
          
          # Fallback content if database is empty
          return {
              "text": "HODL to the moon! 🚀",
              "type": "quote",
              "category": "motivational"
          }
      
      async def add_initial_content(self):
          """Add initial quotes and jokes to the database"""
          # Initial quotes
          quotes = [
              "HODL to the moon! 🚀",
              "Buy the dip, enjoy the trip. 📈",
              "In crypto we trust. 💎",
              "Not your keys, not your coins. 🔑",
              "Blockchain is not just a technology, it's a revolution. ⚡",
              "Bitcoin fixes this. 🧠",
              "Diamond hands win in the long run. 💎🙌",
              "Fear is temporary, regret is forever. 🤔",
              "The best time to buy Bitcoin was yesterday. The second best time is today. ⏰",
              "Time in the market beats timing the market. ⌛"
          ]
          
          # Initial jokes
          jokes = [
              "Why's Bitcoin so private? It doesn't share its private keys! 🔐",
              "What do you call a Bitcoin investor? HODLer of last resort! 💼",
              "Why is BTC so volatile? It's got commitment issues! 📊",
              "Why did the Bitcoin go to therapy? It had too many emotional rollercoasters! 🎢",
              "Why don't Bitcoin and banks get along? They have trust issues! 🏦",
              "What did the Bitcoin say to the traditional investor? 'Have fun staying poor!' 💰",
              "What's a Bitcoin's favorite game? Hide and Seek - with your savings! 🙈",
              "What do you call a crypto trader with paper hands? Broke! 📉",
              "Why did the crypto investor never get any sleep? Because gains never sleep! 😴",
              "How many Bitcoin maxis does it take to change a lightbulb? None, they're still using candles because they're off the grid! 🕯️"
          ]
          
          # Add quotes
          for quote in quotes:
              await self.add_quote(quote)
              
          # Add jokes
          for joke in jokes:
              await self.add_joke(joke)
          
          print(f"Added {len(quotes)} quotes and {len(jokes)} jokes to the database")

- [x] Create test_content_manager.py
  ```python
  import pytest
  from src.content_manager import ContentManager
  from src.database import Database
  import os
  import asyncio
  
  @pytest.mark.asyncio
  async def test_add_quote():
      # Use test database
      db = Database(os.getenv("MONGODB_URI", "mongodb://localhost:27017/test"))
      cm = ContentManager(db)
      
      # Add test quote
      quote_text = "Test quote"
      quote_id = await cm.add_quote(quote_text)
      
      # Verify it was added
      result = await db.db.quotes.find_one({"text": quote_text})
      assert result is not None
      assert result["text"] == quote_text
      assert result["used_count"] == 0
      
      # Cleanup
      await db.db.quotes.delete_one({"text": quote_text})
      
  @pytest.mark.asyncio
  async def test_get_random_content():
      # Use test database
      db = Database(os.getenv("MONGODB_URI", "mongodb://localhost:27017/test"))
      cm = ContentManager(db)
      
      # Clear existing data
      await db.db.quotes.delete_many({})
      await db.db.jokes.delete_many({})
      
      # Add test data
      await cm.add_quote("Test quote 1")
      await cm.add_joke("Test joke 1")
      
      # Get random content
      content = await cm.get_random_content()
      
      # Verify we got some content
      assert "text" in content
      assert "type" in content
      assert content["type"] in ["quote", "joke"]
      
      # Cleanup
      await db.db.quotes.delete_many({})
      await db.db.jokes.delete_many({})
  ```

- [x] Add initial content to database function in ContentManager class

### 2. Main Application Script (60 mins)
- [x] Create main.py
  ```python
  import asyncio
  import os
  from datetime import datetime
  import traceback
  
  from src.price_fetcher import PriceFetcher
  from src.database import Database
  from src.twitter_client import TwitterClient
  from src.content_manager import ContentManager
  from src.config import Config
  
  async def post_btc_update(config=None):
      """Fetch BTC price and post update to Twitter"""
      # Initialize configuration
      if config is None:
          config = Config()
      
      # Initialize components
      db = Database(config.mongodb_uri)
      price_fetcher = PriceFetcher()
      twitter = TwitterClient(
          config.twitter_api_key,
          config.twitter_api_secret,
          config.twitter_access_token,
          config.twitter_access_token_secret
      )
      content_manager = ContentManager(db)
      
      try:
          # Fetch current BTC price
          async with price_fetcher as pf:
              price_data = await pf.get_btc_price_with_retry(config.coingecko_retry_limit)
              current_price = price_data["usd"]
          
          # Get latest price from database for comparison
          latest_price_data = await db.get_latest_price()
          previous_price = latest_price_data["price"] if latest_price_data else current_price
          
          # Calculate price change
          price_change = price_fetcher.calculate_price_change(current_price, previous_price)
          
          # Store new price in database
          await db.store_price(current_price)
          
          # Get random content
          content = await content_manager.get_random_content()
          
          # Format tweet
          emoji = "📈" if price_change >= 0 else "📉"
          tweet = f"BTC: ${current_price:,.2f} | {price_change:+.2f}% {emoji}\n{content['text']}\n#Bitcoin #Crypto"
          
          # Post tweet
          tweet_id = await twitter.post_tweet(tweet)
          
          if tweet_id:
              # Log successful post
              await db.db.posts.insert_one({
                  "tweet_id": tweet_id,
                  "tweet": tweet,
                  "timestamp": datetime.utcnow(),
                  "price": current_price,
                  "price_change": price_change,
                  "content_type": content["type"],
                  "likes": 0,
                  "retweets": 0
              })
              
              print(f"Successfully posted tweet: {tweet_id}")
              return tweet_id
          else:
              print("Failed to post tweet - no tweet ID returned")
              return None
      
      except Exception as e:
          print(f"Error posting update: {e}")
          traceback.print_exc()
          return None
      finally:
          # Close connections
          await db.close()
  
  async def main():
      """Main function"""
      await post_btc_update()
  
  if __name__ == "__main__":
      # Run the main function
      asyncio.run(main())
  ```

### 3. Scheduling Functionality (30 mins)
- [x] Create scheduler.py
  ```python
  import asyncio
  import os
  from datetime import datetime, time
  import signal
  import sys
  
  from src.config import Config
  from src.main import post_btc_update, setup_database
  
  class Scheduler:
      def __init__(self, config=None):
          self.config = config or Config()
          self.running = False
          self.tasks = []
          
      async def scheduled_job(self):
          """Run the scheduled job"""
          current_time = datetime.utcnow()
          print(f"Running scheduled job at {current_time.isoformat()}")
          await post_btc_update(self.config)
      
      def parse_time(self, time_str):
          """Parse time string in format HH:MM"""
          hours, minutes = map(int, time_str.split(":"))
          return hours, minutes
      
      async def run(self):
          """Set up and run the scheduler"""
          self.running = True
          
          # Setup signal handlers for graceful shutdown
          self._setup_signal_handlers()
          
          # Setup database with initial content if needed
          await setup_database()
          
          print("\nBTCBuzzBot Scheduler started")
          print(f"Timezone: {self.config.timezone}")
          print("Scheduled posting times:")
          for time_str in self.config.post_times:
              print(f"- {time_str}")
          print("\nPress Ctrl+C to stop\n")
          
          # Run the scheduler
          while self.running:
              current_time = datetime.utcnow()
              current_hour = current_time.hour
              current_minute = current_time.minute
              
              # Check if it's time to post
              for time_str in self.config.post_times:
                  post_hour, post_minute = self.parse_time(time_str)
                  
                  if current_hour == post_hour and current_minute == post_minute:
                      # It's time to post
                      print(f"It's posting time! {time_str}")
                      task = asyncio.create_task(self.scheduled_job())
                      self.tasks.append(task)
              
              # Sleep until the next minute
              await asyncio.sleep(60 - current_time.second)
              
              # Cleanup completed tasks
              self.tasks = [task for task in self.tasks if not task.done()]
      
      def _setup_signal_handlers(self):
          """Set up signal handlers for graceful shutdown"""
          loop = asyncio.get_event_loop()
          
          for sig in (signal.SIGINT, signal.SIGTERM):
              loop.add_signal_handler(sig, self._shutdown)
      
      def _shutdown(self):
          """Shutdown the scheduler gracefully"""
          print("\nShutting down scheduler...")
          self.running = False
          
          # Cancel all tasks
          for task in self.tasks:
              task.cancel()
          
          # Exit
          sys.exit(0)
  
  async def main():
      """Main function"""
      scheduler = Scheduler()
      await scheduler.run()
  
  if __name__ == "__main__":
      # Run the scheduler
      asyncio.run(main())
  ```

### 4. Configuration Management (30 mins)
- [x] Create config.py
  ```python
  import os
  from typing import Dict, Any, List
  from dotenv import load_dotenv
  
  class Config:
      """Configuration management class"""
      def __init__(self):
          # Load environment variables
          load_dotenv()
          
          # Database configuration
          self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/btcbuzzbot")
          
          # Twitter configuration
          self.twitter_api_key = os.getenv("TWITTER_API_KEY", "")
          self.twitter_api_secret = os.getenv("TWITTER_API_SECRET", "")
          self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
          self.twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
          
          # Bot configuration
          self.post_times = os.getenv("POST_TIMES", "08:00,12:00,16:00,20:00").split(",")
          self.timezone = os.getenv("TIMEZONE", "UTC")
          
          # CoinGecko configuration
          self.coingecko_api_url = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")
          self.coingecko_retry_limit = int(os.getenv("COINGECKO_RETRY_LIMIT", "3"))
          
          # Validate required settings
          self.validate()
      
      def validate(self):
          """Validate required settings"""
          if not self.twitter_api_key or not self.twitter_api_secret:
              raise ValueError("Twitter API key and secret are required")
          
          if not self.twitter_access_token or not self.twitter_access_token_secret:
              raise ValueError("Twitter access token and secret are required")
          
          if not self.mongodb_uri:
              raise ValueError("MongoDB URI is required")
      
      def to_dict(self) -> Dict[str, Any]:
          """Convert configuration to dictionary"""
          return {
              "mongodb_uri": self.mongodb_uri,
              "twitter_api_key": self.twitter_api_key[:4] + "..." if self.twitter_api_key else "",
              "twitter_api_secret": "***REDACTED***",
              "twitter_access_token": self.twitter_access_token[:4] + "..." if self.twitter_access_token else "",
              "twitter_access_token_secret": "***REDACTED***",
              "post_times": self.post_times,
              "timezone": self.timezone,
              "coingecko_api_url": self.coingecko_api_url,
              "coingecko_retry_limit": self.coingecko_retry_limit
          }
  ```

- [x] Create .env.example file
  ```
  # MongoDB Configuration
  MONGODB_URI=mongodb://localhost:27017/btcbuzzbot
  
  # Twitter API Credentials
  TWITTER_API_KEY=your_api_key
  TWITTER_API_SECRET=your_api_secret
  TWITTER_ACCESS_TOKEN=your_access_token
  TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
  
  # Bot Configuration
  POST_TIMES=08:00,12:00,16:00,20:00
  TIMEZONE=UTC
  
  # CoinGecko Configuration
  COINGECKO_API_URL=https://api.coingecko.com/api/v3
  COINGECKO_RETRY_LIMIT=3
  ```

## Testing Tasks
- [x] Test content manager functionality
- [x] Test main application
- [x] Test configuration validation
- [x] Manual test of full posting workflow

## Success Criteria
- [x] Content management system implemented and tested
- [x] Main application script working end-to-end
- [x] Basic scheduling implemented
- [x] Configuration management working with validation
- [x] Project structure set up properly with __init__.py files

## Next Steps
1. Implement monitoring and logging
2. Prepare AWS Lambda deployment
3. Set up CI/CD pipeline
4. Implement engagement tracking
5. Create admin dashboard 