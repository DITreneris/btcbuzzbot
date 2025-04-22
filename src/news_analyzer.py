"""
Module for analyzing fetched tweets to identify potential news.
"""

import logging
import os
import sys
import asyncio
from typing import List, Dict, Any, Tuple, Optional

# Ensure src is in the path if running directly
if 'src' not in sys.path and os.path.exists('src'):
     sys.path.insert(0, os.path.abspath('.'))

# Project Imports
try:
    from src.database import Database
    DATABASE_CLASS_AVAILABLE = True
except ImportError as e:
    DATABASE_CLASS_AVAILABLE = False
    print(f"Error importing Database from src.database: {e}. NewsAnalyzer may fail.")
    Database = None # Placeholder

# Remove Config import - no longer needed here
# try:
#     from src.config import Config # Import Config
#     CONFIG_CLASS_AVAILABLE = True
# except ImportError as e:
#     CONFIG_CLASS_AVAILABLE = False
#     print(f"Error importing Config from src.config: {e}. NewsAnalyzer may fail.")
#     Config = None

# --- Analysis Libraries ---
# VADER Sentiment
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("Warning: vaderSentiment not installed. Sentiment analysis disabled.")

# Groq LLM Client
try:
    from groq import Groq, AsyncGroq # Use AsyncGroq for async calls
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Warning: groq package not installed. LLM analysis disabled.")

# TODO: Import LLM client if implementing LLM analysis

logger = logging.getLogger(__name__)

# --- Basic Analysis Parameters ---
# Example keywords that might indicate news (simple approach)
NEWS_KEYWORDS = ["breaking", "alert", "report", "announced", "launch", "partnership", "regulation", "sec", "etf", "fed"]
DEFAULT_GROQ_MODEL = "llama3-8b-8192" # Define a default model

class NewsAnalyzer:
    # Modify __init__ to accept db_instance and read env vars directly
    def __init__(self, db_instance: Optional[Database] = None):
        self.db = db_instance
        self.vader_analyzer = None
        self.groq_client = None
        self.groq_model = os.environ.get('GROQ_MODEL', DEFAULT_GROQ_MODEL)
        self.initialized = False

        if not self.db:
            logger.error("NewsAnalyzer initialization failed: Database instance not provided.")
            return

        try:
            # Initialize VADER
            if VADER_AVAILABLE:
                self.vader_analyzer = SentimentIntensityAnalyzer()
                logger.info("VADER Sentiment Analyzer initialized.")
            else:
                logger.warning("VADER not available, skipping sentiment analysis.")

            # Initialize Groq Client (Async) using environment variable
            groq_api_key = os.environ.get('GROQ_API_KEY')
            if GROQ_AVAILABLE and groq_api_key:
                self.groq_client = AsyncGroq(api_key=groq_api_key)
                logger.info(f"Groq Async Client initialized for model: {self.groq_model}")
            else:
                logger.warning("Groq client not initialized (package missing or API key not set). LLM analysis disabled.")

            logger.info("NewsAnalyzer initialized successfully.")
            self.initialized = True
        except Exception as e:
            logger.error(f"Error during NewsAnalyzer initialization: {e}", exc_info=True)

    async def _classify_news_with_llm(self, text: str) -> Tuple[bool, float]:
        """Uses Groq LLM to classify if the text is significant news."""
        if not self.groq_client:
            return False, 0.0 # LLM disabled

        prompt = (
            "Analyze the following tweet text. Is it reporting potentially significant news related to Bitcoin (e.g., major price moves, adoption, regulation, technical updates, market events)? "
            "Ignore generic price updates unless they are unusually large or accompanied by significant context. Ignore spam, memes, or purely personal opinions unless they reflect a major event."
            "Respond with only YES or NO."
            "\n\nTweet Text: "
            f'"{text}"'
            "\n\nIs this significant news? (YES/NO):"
        )

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.groq_model, # Use self.groq_model read from env
                temperature=0.1, # Low temperature for classification
                max_tokens=10,
            )
            response_text = chat_completion.choices[0].message.content.strip().upper()
            logger.debug(f"LLM Classification for '{text[:50]}...': {response_text}")

            is_news = response_text.startswith("YES")
            # Simple confidence score based on YES/NO
            score = 1.0 if is_news else 0.1 # Assign low score if not news
            return is_news, score
        except Exception as e:
            logger.error(f"Groq API error during classification: {e}", exc_info=False) # Avoid full traceback spam
            return False, 0.0 # Default to not news on error

    async def _summarize_with_llm(self, text: str) -> Optional[str]:
        """Uses Groq LLM to summarize the text."""
        if not self.groq_client:
            return None # LLM disabled

        prompt = f"Summarize the key information in the following tweet regarding Bitcoin in one concise sentence:\n\nTweet Text: \"{text}\"\n\nSummary:"

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.groq_model, # Use self.groq_model read from env
                temperature=0.5,
                max_tokens=100, # Allow more tokens for summary
            )
            summary = chat_completion.choices[0].message.content.strip()
            logger.debug(f"LLM Summary for '{text[:50]}...': {summary}")
            return summary
        except Exception as e:
            logger.error(f"Groq API error during summarization: {e}", exc_info=False)
            return None

    async def analyze_tweets(self, tweets: List[Dict[str, Any]]):
        """Analyzes a batch of tweets and updates the DB with results."""
        # Remove initialization check here, it's done in run_cycle
        # if not self.initialized or not self.db:
        #     logger.error("NewsAnalyzer not initialized or DB unavailable.")
        #     return

        processed_count = 0
        updated_count = 0
        llm_tasks = [] # List to hold LLM analysis tasks

        # --- Stage 1: Initial Processing & Create LLM Tasks --- 
        analysis_data = {} # Store intermediate results by original_id
        for tweet in tweets:
            original_id = tweet.get('original_tweet_id')
            if not original_id:
                logger.warning(f"Skipping tweet analysis: Missing original_tweet_id in {tweet}")
                continue

            processed_count += 1
            tweet_text = tweet.get('tweet_text', '')
            
            # Perform VADER sentiment analysis (synchronous)
            sentiment_score = None
            if self.vader_analyzer:
                 vs = self.vader_analyzer.polarity_scores(tweet_text)
                 sentiment_score = vs['compound'] # Use the compound score (-1 to 1)
            
            # Perform basic keyword check (synchronous)
            keyword_hits = [keyword for keyword in NEWS_KEYWORDS if keyword in tweet_text.lower()]
            keyword_score = min(1.0, 0.1 * len(keyword_hits)) if keyword_hits else 0.0 # Lower weight for keywords

            # Store initial results
            analysis_data[original_id] = {
                'sentiment': sentiment_score,
                'keyword_score': keyword_score, # Store intermediate keyword score
                'is_news': False, # Default, LLM will override
                'news_score': keyword_score, # Default score, LLM might override
                'summary': None
            }

            # Create LLM analysis tasks if client is available
            if self.groq_client:
                llm_tasks.append(self._run_llm_analysis(original_id, tweet_text, analysis_data))

        # --- Stage 2: Run LLM Analysis Concurrently --- 
        if llm_tasks:
            logger.info(f"Running LLM analysis for {len(llm_tasks)} tweets...")
            await asyncio.gather(*llm_tasks)
            logger.info("LLM analysis batch completed.")

        # --- Stage 3: Update Database --- 
        logger.info(f"Updating database for {processed_count} processed tweets...")
        for original_id, results in analysis_data.items():
            # Prepare final results for DB update
            db_update_payload = {
                'is_news': results['is_news'],
                'news_score': results['news_score'],
                'sentiment': results['sentiment'],
                'summary': results['summary']
            }
            try:
                success = await self.db.update_news_tweet_analysis(original_id, db_update_payload)
                if success:
                    updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update analysis for tweet {original_id}: {e}", exc_info=True)
        
        logger.info(f"Finished analyzing batch. Processed: {processed_count}, Updated DB: {updated_count}")

    async def _run_llm_analysis(self, original_id: str, text: str, analysis_data: Dict):
        """Helper coroutine to run classification and optional summarization for one tweet."""
        try:
            is_llm_news, llm_score = await self._classify_news_with_llm(text)
            analysis_data[original_id]['is_news'] = is_llm_news
            analysis_data[original_id]['news_score'] = llm_score # Use LLM score as primary score

            # Summarize only if classified as news by LLM
            if is_llm_news:
                summary = await self._summarize_with_llm(text)
                analysis_data[original_id]['summary'] = summary
        except Exception as e:
             logger.error(f"Error during LLM analysis task for {original_id}: {e}", exc_info=False)

    # --- New run_cycle method --- 
    async def run_cycle(self):
        """Runs a single cycle of fetching unprocessed tweets and analyzing them using this instance."""
        if not self.initialized or not self.db:
            logger.error("Cannot run analysis cycle: NewsAnalyzer not initialized or DB unavailable.")
            return

        try:
            logger.info("Starting news analysis cycle...")
            # Fetch a batch of unprocessed tweets using self.db
            unprocessed_tweets = await self.db.get_unprocessed_news_tweets(limit=100)

            if unprocessed_tweets:
                logger.info(f"Fetched {len(unprocessed_tweets)} tweets for analysis.")
                # Call self.analyze_tweets
                await self.analyze_tweets(unprocessed_tweets)
            else:
                logger.info("No unprocessed tweets found to analyze.")

            logger.info("News analysis cycle finished.")

        except Exception as e:
            logger.error(f"Error during news analysis cycle execution: {e}", exc_info=True)

# --- Remove standalone run_analysis_cycle function --- 
# async def run_analysis_cycle():
#     """Runs a single cycle of fetching unprocessed tweets and analyzing them."""
#     analyzer = NewsAnalyzer()
#     if not analyzer.initialized or not analyzer.db:
#         logger.error("Cannot run analysis cycle: NewsAnalyzer failed to initialize or DB unavailable.")
#         return
#
#     try:
#         logger.info("Starting news analysis cycle...")
#         # Fetch a batch of unprocessed tweets
#         # TODO: Make limit configurable?
#         unprocessed_tweets = await analyzer.db.get_unprocessed_news_tweets(limit=100)
#
#         if unprocessed_tweets:
#             logger.info(f"Fetched {len(unprocessed_tweets)} tweets for analysis.")
#             await analyzer.analyze_tweets(unprocessed_tweets)
#         else:
#             logger.info("No unprocessed tweets found to analyze.")
#
#         logger.info("News analysis cycle finished.")
#
#     except Exception as e:
#         logger.error(f"Error during news analysis cycle execution: {e}", exc_info=True)

if __name__ == '__main__':
    # Basic test execution if run directly
    logging.basicConfig(level=logging.INFO)
    # Load .env for direct execution if needed (e.g., for DB path)
    from dotenv import load_dotenv
    load_dotenv()
    
    logger.info("Running manual news analysis cycle...")
    asyncio.run(run_analysis_cycle())
    logger.info("Manual news analysis cycle finished.") 