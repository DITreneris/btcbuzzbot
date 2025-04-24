"""
Module for analyzing fetched tweets to identify potential news.
"""

import logging
import os
import sys
import asyncio
import json # Import json module
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

# --- LLM Configuration Defaults ---
# DEFAULT_LLM_CLASSIFY_TEMP = 0.1 # No longer needed
# DEFAULT_LLM_CLASSIFY_MAX_TOKENS = 10 # No longer needed
DEFAULT_LLM_ANALYZE_TEMP = 0.2 # New temp for combined analysis
DEFAULT_LLM_ANALYZE_MAX_TOKENS = 150 # Adjusted max tokens for JSON + summary
DEFAULT_LLM_SUMMARIZE_TEMP = 0.5 # Keep for potential separate use? Or remove? Let's remove for now.
DEFAULT_LLM_SUMMARIZE_MAX_TOKENS = 100 # Keep for potential separate use? Or remove? Let's remove for now.
DEFAULT_NEWS_ANALYSIS_BATCH_SIZE = 30

# --- New Combined Analysis Prompt ---
_ANALYSIS_PROMPT_JSON = """
Analyze the provided tweet text about Bitcoin. Determine its significance for Bitcoin news and its overall sentiment towards Bitcoin's impact or price.

Provide your analysis ONLY in JSON format with the following keys:
- "significance": String. Rate the news significance as "Low", "Medium", or "High".
    - "High" for major events (regulation, adoption, large price swings >5%, exchange issues, major project launches).
    - "Medium" for notable updates (partnerships, minor technical updates, analyst predictions from reputable sources).
    - "Low" for generic price commentary, memes, minor news, or personal opinions without broad impact.
- "sentiment": String. Rate the sentiment towards Bitcoin's impact/price as "Positive", "Negative", or "Neutral".
- "summary": String. Provide a concise one-sentence summary (max 200 chars) of the key information, suitable for context.

Tweet Text:
\"\"\"
{text}
\"\"\"

JSON Analysis:
"""

class NewsAnalyzer:
    # Modify __init__ to accept db_instance and read env vars directly
    def __init__(self, db_instance: Optional[Database] = None):
        self.db = db_instance
        self.vader_analyzer = None
        self.groq_client = None
        self.groq_model = os.environ.get('GROQ_MODEL', DEFAULT_GROQ_MODEL)
        
        # --- Read LLM parameters from env vars ---
        self.llm_analyze_temp = float(os.environ.get('LLM_ANALYZE_TEMP', DEFAULT_LLM_ANALYZE_TEMP))
        self.llm_analyze_max_tokens = int(os.environ.get('LLM_ANALYZE_MAX_TOKENS', DEFAULT_LLM_ANALYZE_MAX_TOKENS))
        # Remove old classify/summarize params
        # self.llm_classify_temp = float(os.environ.get('LLM_CLASSIFY_TEMP', DEFAULT_LLM_CLASSIFY_TEMP))
        # self.llm_classify_max_tokens = int(os.environ.get('LLM_CLASSIFY_MAX_TOKENS', DEFAULT_LLM_CLASSIFY_MAX_TOKENS))
        # self.llm_summarize_temp = float(os.environ.get('LLM_SUMMARIZE_TEMP', DEFAULT_LLM_SUMMARIZE_TEMP))
        # self.llm_summarize_max_tokens = int(os.environ.get('LLM_SUMMARIZE_MAX_TOKENS', DEFAULT_LLM_SUMMARIZE_MAX_TOKENS))
        self.analysis_batch_size = int(os.environ.get('NEWS_ANALYSIS_BATCH_SIZE', DEFAULT_NEWS_ANALYSIS_BATCH_SIZE))
        # --- End LLM parameters ---
        
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

    # --- Remove old _classify_news_with_llm method ---
    # async def _classify_news_with_llm(self, text: str) -> Tuple[bool, float]:
    #     ... (old code) ...

    # --- Remove old _summarize_with_llm method ---
    # async def _summarize_with_llm(self, text: str) -> Optional[str]:
    #     ... (old code) ...

    # +++ New Combined Analysis Method +++
    async def _analyze_content_with_llm(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Uses Groq LLM to perform combined analysis (significance, sentiment, summary)
        and returns results as a dictionary parsed from JSON.
        """
        if not self.groq_client:
            return None # LLM disabled

        prompt = _ANALYSIS_PROMPT_JSON.format(text=text)

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.groq_model,
                temperature=self.llm_analyze_temp,      # Use new configured value
                max_tokens=self.llm_analyze_max_tokens, # Use new configured value
                # Add response_format for JSON output if supported and needed
                # response_format={"type": "json_object"}, # Check Groq API docs if needed
            )
            response_content = chat_completion.choices[0].message.content.strip()
            
            # --- Robust JSON Parsing ---
            try:
                # Try finding JSON block even if there's extra text
                json_start = response_content.find('{')
                json_end = response_content.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_string = response_content[json_start:json_end+1]
                    analysis_result = json.loads(json_string)
                    
                    # Validate expected keys
                    if all(k in analysis_result for k in ["significance", "sentiment", "summary"]):
                         logger.debug(f"LLM Analysis for '{text[:50]}...': {analysis_result}")
                         return analysis_result
                    else:
                        logger.warning(f"LLM JSON response missing expected keys for '{text[:50]}...': {json_string}")
                        return None
                else:
                     logger.warning(f"Could not find valid JSON object in LLM response for '{text[:50]}...': {response_content}")
                     return None
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse JSON from LLM response for '{text[:50]}...': {json_err}. Response: {response_content}")
                return None
            # --- End Robust JSON Parsing ---

        except Exception as e:
            # Check for rate limit errors specifically if possible (depends on Groq client exceptions)
            # Example: if isinstance(e, groq.RateLimitError): logger.warning(...)
            logger.error(f"Groq API error during combined analysis: {e}", exc_info=False) # Avoid full traceback spam
            return None # Default to None on error

    async def analyze_tweets(self, tweets: List[Dict[str, Any]]):
        """Analyzes a batch of tweets and updates the DB with results."""
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

            # Perform VADER sentiment analysis (keep for now)
            vader_sentiment_score = None
            if self.vader_analyzer:
                 vs = self.vader_analyzer.polarity_scores(tweet_text)
                 vader_sentiment_score = vs['compound'] # Use the compound score (-1 to 1)

            # Keyword check removed/simplified as LLM handles significance now
            # keyword_hits = [keyword for keyword in NEWS_KEYWORDS if keyword in tweet_text.lower()]
            # keyword_score = min(1.0, 0.1 * len(keyword_hits)) if keyword_hits else 0.0

            # Store initial results (placeholders for LLM output)
            analysis_data[original_id] = {
                'sentiment': vader_sentiment_score, # Store VADER score initially
                'news_score': 0.0, # Default score, LLM will provide significance
                'summary': None,   # LLM will provide
                'llm_significance': None, # Store raw LLM significance
                'llm_sentiment': None     # Store raw LLM sentiment
            }

            # Create LLM analysis tasks if client is available
            if self.groq_client:
                # Pass analysis_data dict to the task runner
                llm_tasks.append(self._run_single_llm_analysis(original_id, tweet_text, analysis_data[original_id]))

        # --- Stage 2: Run LLM Analysis Concurrently ---
        if llm_tasks:
            logger.info(f"Running LLM analysis for {len(llm_tasks)} tweets...")
            await asyncio.gather(*llm_tasks)
            logger.info("LLM analysis batch completed.")

        # --- Stage 3: Update Database ---
        logger.info(f"Updating database for {processed_count} processed tweets...")
        for original_id, results in analysis_data.items():
            # Prepare final results for DB update
            sentiment_to_store = results['sentiment'] # Use LLM sentiment if available, else VADER
            news_score_to_store = results['news_score']
            summary_to_store = results['summary']

            try:
                await self.db.update_tweet_analysis(
                    original_tweet_id=original_id,
                    sentiment=sentiment_to_store,
                    news_score=news_score_to_store,
                    summary=summary_to_store,
                    llm_raw_analysis=json.dumps({ # Store raw LLM output too for debugging/future use
                        'significance': results.get('llm_significance'),
                        'sentiment': results.get('llm_sentiment')
                    }) if results.get('llm_significance') else None 
                )
                updated_count += 1
                # logger.debug(f"Successfully updated analysis for tweet ID {original_id}") # DEBUG level
            except Exception as e:
                logger.error(f"Failed to update DB for tweet ID {original_id}: {e}", exc_info=False)


        logger.info(f"Finished analyzing batch. Processed: {processed_count}, Updated DB: {updated_count}")


    # Helper method to run LLM analysis for a single tweet and update results dict
    async def _run_single_llm_analysis(self, original_id: str, text: str, results_dict: Dict):
        """Runs the combined LLM analysis and updates the provided results dictionary."""
        llm_result = await self._analyze_content_with_llm(text)

        if llm_result:
            # Store raw LLM results
            results_dict['llm_significance'] = llm_result.get('significance')
            results_dict['llm_sentiment'] = llm_result.get('sentiment')
            results_dict['summary'] = llm_result.get('summary')

            # --- Map LLM Significance to news_score ---
            significance = results_dict['llm_significance']
            if significance == "High":
                results_dict['news_score'] = 1.0
            elif significance == "Medium":
                results_dict['news_score'] = 0.5
            elif significance == "Low":
                results_dict['news_score'] = 0.1
            else:
                 results_dict['news_score'] = 0.0 # Default if unexpected value

            # --- Map LLM Sentiment to sentiment score (override VADER) ---
            sentiment = results_dict['llm_sentiment']
            if sentiment == "Positive":
                results_dict['sentiment'] = 1.0
            elif sentiment == "Negative":
                results_dict['sentiment'] = -1.0
            elif sentiment == "Neutral":
                results_dict['sentiment'] = 0.0
            # Keep VADER score if LLM sentiment is missing/invalid

        # No need to return anything, modifies dict in place

    async def run_cycle(self):
        """Fetches unprocessed tweets, analyzes them, and updates the database."""
        if not self.initialized or not self.db:
            logger.error("NewsAnalyzer not initialized or DB unavailable. Skipping cycle.")
            return

        logger.info("Starting news analysis cycle...")
        try:
            # Fetch tweets requiring analysis (limit by batch size)
            tweets_to_analyze = await self.db.get_tweets_for_analysis(limit=self.analysis_batch_size)

            if not tweets_to_analyze:
                logger.info("No new tweets found requiring analysis.")
                return

            logger.info(f"Fetched {len(tweets_to_analyze)} tweets for analysis.")

            # Analyze the batch
            await self.analyze_tweets(tweets_to_analyze)

            logger.info("News analysis cycle finished.")

        except Exception as e:
            logger.error(f"Error during news analysis cycle: {e}", exc_info=True)

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