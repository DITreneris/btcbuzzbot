from typing import Dict, Any, List, Optional
import random
from datetime import datetime, timedelta

class ContentManager:
    def __init__(self, database):
        self.db = database
        
    async def add_quote(self, text: str, category: str = "motivational") -> int:
        """Add a new quote to the database"""
        try:
            result = await self.db.add_quote(text, category)
            return result
        except Exception as e:
            print(f"Error adding quote: {e}")
            return -1
        
    async def add_joke(self, text: str, category: str = "humor") -> int:
        """Add a new joke to the database"""
        try:
            result = await self.db.add_joke(text, category)
            return result
        except Exception as e:
            print(f"Error adding joke: {e}")
            return -1
        
    async def get_random_content(self) -> Dict[str, Any]:
        """Get random content (quote or joke) that wasn't used recently"""
        try:
            # Randomly choose between quote and joke
            collection = random.choice(["quotes", "jokes"])
            
            # Get random content from the database
            content = await self.db.get_random_content(collection)
            
            if content:
                return {
                    "text": content["text"],
                    "type": "quote" if collection == "quotes" else "joke",
                    "category": content.get("category", "general")
                }
        except Exception as e:
            print(f"Error getting random content: {e}")
        
        # Fallback content if database is empty or error occurs
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
        
        try:
            # Check if we need to add content
            quotes_count = await self.db.count_records("quotes")
            jokes_count = await self.db.count_records("jokes")
            
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