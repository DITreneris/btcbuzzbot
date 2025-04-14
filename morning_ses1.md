# Morning Coding Session 1: BTCBuzzBot Initial Setup

## Session Goals
1. ✅ Set up project structure and environment
2. ✅ Implement basic price fetching functionality
3. ✅ Create initial database connection
4. ✅ Test basic tweet posting

## Time Allocation (3 hours)
- 09:00 - 09:30: Project Setup ✅
- 09:30 - 10:30: Price Fetching Module ✅
- 10:30 - 11:00: Database Connection ✅
- 11:00 - 12:00: Twitter Integration ✅

## Detailed Tasks

### 1. Project Setup (30 mins)
- [x] Create project directory structure
  ```
  btcbuzzbot/
  ├── src/
  │   ├── __init__.py
  │   ├── price_fetcher.py
  │   ├── twitter_client.py
  │   └── database.py
  ├── tests/
  │   ├── __init__.py
  │   └── test_price_fetcher.py
  ├── requirements.txt
  ├── .gitignore
  └── README.md
  ```

- [x] Set up virtual environment
  ```bash
  python -m venv venv
  source venv/bin/activate  # or .\venv\Scripts\activate on Windows
  ```

- [x] Create requirements.txt
  ```
  tweepy==4.14.0
  requests==2.32.0
  pymongo==4.8.0
  python-dotenv==1.0.0
  pytest==7.4.0
  pytest-asyncio==0.23.5
  aiohttp==3.9.3
  ```

### 2. Price Fetching Module (60 mins)
- [x] Create price_fetcher.py with async support
  ```python
  import aiohttp
  from datetime import datetime
  from typing import Dict, Optional
  import asyncio

  class PriceFetcher:
      def __init__(self):
          self.base_url = "https://api.coingecko.com/api/v3"
          self.session: Optional[aiohttp.ClientSession] = None

      async def __aenter__(self):
          self.session = aiohttp.ClientSession()
          return self

      async def __aexit__(self, exc_type, exc_val, exc_tb):
          if self.session:
              await self.session.close()

      async def get_btc_price(self) -> Dict[str, float]:
          """Fetch current BTC price in USD asynchronously"""
          if not self.session:
              self.session = aiohttp.ClientSession()
          
          try:
              async with self.session.get(f"{self.base_url}/simple/price?ids=bitcoin&vs_currencies=usd") as response:
                  if response.status == 200:
                      data = await response.json()
                      return data["bitcoin"]
                  else:
                      print(f"Error fetching price: HTTP {response.status}")
                      return {"usd": 0.0}
          except Exception as e:
              print(f"Error fetching price: {e}")
              return {"usd": 0.0}
  ```

- [x] Add price change calculation
  ```python
  def calculate_price_change(self, current_price: float, previous_price: float) -> float:
      """Calculate percentage price change"""
      if previous_price == 0:
          return 0.0
      return ((current_price - previous_price) / previous_price) * 100
  ```

- [x] Add error handling and retries
  ```python
  async def get_btc_price_with_retry(self, max_retries: int = 3) -> Dict[str, float]:
      """Fetch BTC price with retry mechanism"""
      for attempt in range(max_retries):
          try:
              return await self.get_btc_price()
          except Exception as e:
              if attempt == max_retries - 1:
                  raise e
              await asyncio.sleep(2 ** attempt)  # Exponential backoff
  ```

### 3. Database Connection (30 mins)
- [x] Create database.py with async MongoDB support
  ```python
  from motor.motor_asyncio import AsyncIOMotorClient
  from datetime import datetime
  from typing import Dict, Any, Optional
  from bson import ObjectId

  class Database:
      def __init__(self, connection_string: str):
          self.client = AsyncIOMotorClient(connection_string)
          self.db = self.client.btcbuzzbot
          
      async def store_price(self, price: float) -> ObjectId:
          """Store BTC price with timestamp"""
          result = await self.db.prices.insert_one({
              "price": price,
              "timestamp": datetime.utcnow(),
              "source": "coingecko"
          })
          return result.inserted_id
          
      async def get_latest_price(self) -> Optional[Dict[str, Any]]:
          """Get most recent BTC price"""
          return await self.db.prices.find_one(
              sort=[("timestamp", -1)]
          )
  ```

### 4. Twitter Integration (60 mins)
- [x] Create twitter_client.py with async support
  ```python
  import tweepy
  from typing import Optional
  import asyncio
  from functools import partial

  class TwitterClient:
      def __init__(self, api_key: str, api_secret: str, 
                  access_token: str, access_token_secret: str):
          self.client = tweepy.Client(
              consumer_key=api_key,
              consumer_secret=api_secret,
              access_token=access_token,
              access_token_secret=access_token_secret
          )
          
      async def post_tweet(self, text: str) -> Optional[str]:
          """Post a tweet and return tweet ID"""
          try:
              # Run the synchronous tweepy call in a thread pool
              loop = asyncio.get_event_loop()
              response = await loop.run_in_executor(
                  None,
                  partial(self.client.create_tweet, text=text)
              )
              return response.data["id"]
          except Exception as e:
              print(f"Error posting tweet: {e}")
              return None
  ```

## Testing Tasks
- [x] Test price fetching
  ```python
  @pytest.mark.asyncio
  async def test_get_btc_price():
      async with PriceFetcher() as fetcher:
          price = await fetcher.get_btc_price()
          assert isinstance(price["usd"], float)
          assert price["usd"] > 0
  ```

- [x] Test database connection
  ```python
  @pytest.mark.asyncio
  async def test_database():
      db = Database("mongodb://localhost:27017")
      test_price = 50000.0
      db.store_price(test_price)
      latest = db.get_latest_price()
      assert latest["price"] == test_price
  ```

## Success Criteria
- [x] Project structure created and committed
- [x] Price fetcher working with retries
- [x] Database connection established
- [x] Twitter client implemented
- [x] Test cases created

## Next Steps
1. Create the main application script (main.py)
2. Implement content management system (quotes and jokes)
3. Add scheduling functionality
4. Set up CI/CD pipeline
5. Deploy to AWS Lambda 