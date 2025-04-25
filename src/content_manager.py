"""
Handles selection and management of tweet content (quotes, jokes).
"""
import random
import logging
# Replace Database import with ContentRepository
# from src.database import Database 
from src.db.content_repo import ContentRepository
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ContentManager:
    def __init__(self, db_path: str = "btcbuzzbot.db"):
        """Initializes the ContentManager with a ContentRepository instance."""
        # Instantiate ContentRepository instead of Database
        self.repo = ContentRepository(db_path=db_path)
        if not self.repo:
             logger.error("ContentManager failed to initialize ContentRepository.")
             # Handle error appropriately, maybe raise an exception

    async def add_quote(self, text: str, category: str = "motivational") -> int:
        """Add a new quote to the database"""
        try:
            result = await self.repo.add_quote(text, category)
            return result
        except Exception as e:
            print(f"Error adding quote: {e}")
            return -1
        
    async def add_joke(self, text: str, category: str = "humor") -> int:
        """Add a new joke to the database"""
        try:
            result = await self.repo.add_joke(text, category)
            return result
        except Exception as e:
            print(f"Error adding joke: {e}")
            return -1
        
    async def get_random_content(self) -> Optional[Dict[str, Any]]:
        """Gets a random quote or joke, preferring less used ones."""
        if not self.repo:
            logger.error("ContentRepository not available in ContentManager.")
            return None
            
        # Decide whether to fetch a quote or a joke (e.g., 50/50 chance)
        collection = 'quotes' if random.random() < 0.5 else 'jokes'
        logger.info(f"Attempting to fetch random content from: {collection}")
        try:
            # Call the method on the repository instance
            content = await self.repo.get_random_content(collection)
            if content:
                logger.info(f"Retrieved content ID {content.get('id')} from {collection}.")
                content['type'] = collection.rstrip('s') # Add type field (quote/joke)
                return content
            else:
                logger.warning(f"Could not retrieve random content from {collection}.")
                # Optional: Add fallback logic here if needed (e.g., try the other collection)
                return None
        except Exception as e:
             logger.error(f"Error in get_random_content: {e}", exc_info=True)
             return None
    
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
        
        try:
            # Check if we need to add content
            quotes_count = await self.repo.count_records("quotes")
            jokes_count = await self.repo.count_records("jokes")
            
            if quotes_count == 0:
                # Add quotes
                for quote in quotes:
                    await self.add_quote(quote)
                print(f"Added {len(quotes)} quotes to the database")
                
            if jokes_count == 0:
                # Add jokes
                for joke in jokes:
                    await self.add_joke(joke)
                print(f"Added {len(jokes)} jokes to the database")
                
            print(f"Database has {quotes_count} quotes and {jokes_count} jokes")
        except Exception as e:
            print(f"Error adding initial content: {e}") 