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
    from src.database import Database # Keep for type hint? Or remove if not passed?
    DATABASE_CLASS_AVAILABLE = True
except ImportError as e:
    DATABASE_CLASS_AVAILABLE = False
    print(f"Error importing Database from src.database: {e}. NewsAnalyzer may have issues.")
    Database = None # Placeholder

# Import NewsRepository
try:
    from src.db.news_repo import NewsRepository
    NEWS_REPO_AVAILABLE = True
except ImportError as e:
    NEWS_REPO_AVAILABLE = False
    print(f"Error importing NewsRepository: {e}. NewsAnalyzer DB operations will fail.")
    NewsRepository = None

# --> ADDED IMPORT
from src.content_manager import ContentManager

# --> ADDED IMPORT
from src.config import Config

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
DEFAULT_NEWS_PROCESSING_TIMEOUT_SECONDS = 300 # Added default for timeout

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
    # Remove db_instance, add content_manager if needed for context?
    # Let's assume ContentManager is needed for enrich/analysis context.
    def __init__(self, content_manager: ContentManager):
        # self.db = db_instance # Remove old db instance property
        self.news_repo = None # Add news_repo property
        # --- Removed old ContentManager Init check, rely on type hint & shared instance creation ---
        self.content_manager = content_manager 
        self.llm_client = None # Assuming it uses an LLM client
        self.initialized = False
        # self.analysis_batch_size = 10 # Example batch size - Use Config?
        # self.processing_timeout = 300 # Example timeout in seconds - Use Config?

        # --- Load config for LLM client and other params ---
        try:
            self.config = Config()
            logger.info("Config loaded in NewsAnalyzer.")
            # Set attributes from config using getattr for safety
            self.groq_model = getattr(self.config, 'groq_model', DEFAULT_GROQ_MODEL)
            # Ensure default values are defined at module level
            self.llm_analyze_temp = float(getattr(self.config, 'llm_analyze_temp', DEFAULT_LLM_ANALYZE_TEMP))
            self.llm_analyze_max_tokens = int(getattr(self.config, 'llm_analyze_max_tokens', DEFAULT_LLM_ANALYZE_MAX_TOKENS))
            self.batch_size = int(getattr(self.config, 'news_analysis_batch_size', DEFAULT_NEWS_ANALYSIS_BATCH_SIZE))
            self.processing_timeout = int(getattr(self.config, 'news_processing_timeout_seconds', DEFAULT_NEWS_PROCESSING_TIMEOUT_SECONDS))
            self.groq_api_key = getattr(self.config, 'groq_api_key', None)

        except Exception as cfg_e:
            # This block might be less likely now if Config init handles errors
            logger.error(f"Failed during Config access in NewsAnalyzer: {cfg_e}. Using defaults.", exc_info=True)
            # Set defaults manually if config access fails
            self.groq_model = DEFAULT_GROQ_MODEL
            self.llm_analyze_temp = DEFAULT_LLM_ANALYZE_TEMP
            self.llm_analyze_max_tokens = DEFAULT_LLM_ANALYZE_MAX_TOKENS
            self.batch_size = DEFAULT_NEWS_ANALYSIS_BATCH_SIZE
            self.processing_timeout = DEFAULT_NEWS_PROCESSING_TIMEOUT_SECONDS
            self.groq_api_key = None # Ensure API key is None

        # Check dependencies
        if not GROQ_AVAILABLE or not NEWS_REPO_AVAILABLE:
            logger.error("NewsAnalyzer initialization failed due to missing dependencies (Groq or NewsRepository).")
            return
            
        # Initialize NewsRepository
        try:
            # NewsRepository now reads env var internally
            self.news_repo = NewsRepository()
            logger.info("NewsRepository initialized within NewsAnalyzer.")
        except Exception as repo_e:
             logger.error(f"NewsAnalyzer failed to initialize NewsRepository: {repo_e}", exc_info=True)
             return # Stop if repo fails

        if not self.content_manager:
            logger.error("NewsAnalyzer initialization failed: ContentManager instance not provided.")
            return
        
        # Initialize LLM client (Groq Example)
        # Check availability again
        if not GROQ_AVAILABLE:
             logger.error("NewsAnalyzer initialization failed: Groq library not available.")
             return
        
        try:
            # Use async client
            self.groq_client = AsyncGroq(
                api_key=self.groq_api_key # Use the attribute set from config
            )
            if self.groq_client and self.groq_api_key:
                 logger.info(f"AsyncGroq client initialized within NewsAnalyzer using model {self.groq_model}.")
                 self.initialized = True
            else:
                 logger.error("NewsAnalyzer initialization failed: Could not initialize AsyncGroq client (API key missing or client creation failed?).")
                 self.initialized = False # Ensure initialized is false

        except Exception as e:
            logger.error(f"Error during NewsAnalyzer Groq client initialization: {e}", exc_info=True)
            self.initialized = False # Ensure initialized is false

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

    # Update analyze_tweets to use news_repo
    async def analyze_tweets(self, tweets: List[Dict[str, Any]]) -> int:
        """Analyzes a batch of tweets and updates their status in the database via NewsRepository."""
        if not self.initialized or not self.news_repo or not self.llm_client:
            logger.error("NewsAnalyzer not initialized or dependencies missing.")
            return 0

        analyzed_count = 0
        analysis_tasks = []

        for tweet in tweets:
            # Schedule analysis for each tweet
            task = asyncio.create_task(self._analyze_single_tweet(tweet))
            analysis_tasks.append((task, tweet.get('id'))) # Track task and tweet db id

        results = []
        try:
            # Wait for tasks with a timeout
            done, pending = await asyncio.wait(
                [t for t, _ in analysis_tasks],
                timeout=self.processing_timeout,
                return_when=asyncio.ALL_COMPLETED
            )

            if pending:
                logger.warning(f"{len(pending)} analysis tasks timed out after {self.processing_timeout}s. Cancelling them.")
                for task in pending:
                    task.cancel()

            failed_updates = 0
            for task, tweet_db_id in analysis_tasks:
                if task in done and not task.cancelled():
                    try:
                        analysis_result = task.result()
                        if analysis_result and tweet_db_id is not None:
                            # Use news_repo to update
                            update_successful = await self.news_repo.update_tweet_analysis(
                                tweet_db_id=tweet_db_id,
                                analysis_data=analysis_result,
                                status="analyzed"
                            )
                            if update_successful:
                                analyzed_count += 1
                                logger.debug(f"Successfully analyzed and updated tweet DB ID: {tweet_db_id}")
                            else:
                                failed_updates += 1
                                logger.error(f"Failed to update analysis status in DB for tweet ID: {tweet_db_id}")
                        elif not analysis_result:
                            # Analysis failed internally, log is in _analyze_single_tweet
                            # Optionally mark as failed in DB?
                            logger.warning(f"Analysis returned None/empty for tweet DB ID: {tweet_db_id}. Marking as analysis_failed.")
                            # Use news_repo to update status to failed
                            await self.news_repo.update_tweet_analysis(
                                tweet_db_id=tweet_db_id,
                                analysis_data=None,
                                status="analysis_failed"
                            )
                            failed_updates += 1 # Count as failed if analysis didn't produce results
                        
                    except Exception as e:
                        logger.error(f"Error processing analysis result or updating DB for tweet ID {tweet_db_id}: {e}", exc_info=True)
                        failed_updates += 1
                        # Optionally mark as failed in DB?
                        if tweet_db_id is not None:
                            await self.news_repo.update_tweet_analysis(
                                tweet_db_id=tweet_db_id,
                                analysis_data=None,
                                status="analysis_failed"
                            )                            
                elif task.cancelled():
                    logger.warning(f"Analysis task for tweet ID {tweet_db_id} was cancelled (timeout).")
                    # Optionally mark as failed/timeout in DB
                    if tweet_db_id is not None:
                       await self.news_repo.update_tweet_analysis(
                            tweet_db_id=tweet_db_id,
                            analysis_data=None,
                            status="analysis_timeout"
                        )
                    failed_updates += 1
                else: # Task is pending but somehow not cancelled? Should not happen with ALL_COMPLETED.
                     logger.error(f"Task for tweet ID {tweet_db_id} finished in unexpected state.")
                     failed_updates += 1

            if failed_updates > 0:
                 logger.warning(f"Completed analysis run with {failed_updates} failures/timeouts.")

        except asyncio.CancelledError:
            logger.warning("analyze_tweets task itself was cancelled.")
            # Cancel running sub-tasks if any? asyncio.wait should handle this.
            return analyzed_count # Return count processed so far
        except Exception as e:
            logger.error(f"Unexpected error in analyze_tweets batch processing: {e}", exc_info=True)
            # Mark remaining tweets as failed?
            return analyzed_count

        logger.info(f"Finished analysis batch. Successfully analyzed and updated: {analyzed_count} tweets.")
        return analyzed_count

    # Update run_cycle to use news_repo
    async def run_cycle(self):
        """Runs a single cycle of fetching unprocessed tweets, analyzing, and updating them."""
        if not self.initialized or not self.news_repo:
            logger.error("Cannot run analysis cycle: NewsAnalyzer not initialized or NewsRepository unavailable.")
            return

        try:
            logger.info(f"Starting news analysis cycle. Fetching up to {self.batch_size} unprocessed tweets...")
            # Use news_repo to get tweets
            unprocessed_tweets = await self.news_repo.get_unprocessed_news_tweets(limit=self.batch_size)

            if not unprocessed_tweets:
                logger.info("No unprocessed news tweets found to analyze.")
                return

            logger.info(f"Fetched {len(unprocessed_tweets)} tweets for analysis.")
            
            # Tweets from repo should already be dicts
            processed_count = await self.analyze_tweets(unprocessed_tweets)
            
            logger.info(f"News analysis cycle finished. Processed {processed_count} tweets in this cycle.")

        except Exception as e:
            logger.error(f"Error during news analysis cycle execution: {e}", exc_info=True)

    # ... shutdown method (if any) might need news_repo.close() if repo holds connections ...
    # Add a close method
    async def close(self):
        """Closes resources like the news repository connection."""
        if self.news_repo:
            try:
                await self.news_repo.close()
                logger.info("NewsRepository connection closed within NewsAnalyzer.")
            except Exception as e:
                logger.error(f"Error closing NewsRepository in NewsAnalyzer: {e}", exc_info=True)
        # Close LLM client if needed
        # if self.llm_client and hasattr(self.llm_client, 'close'):
        #     await self.llm_client.close()
        self.initialized = False
        logger.info("NewsAnalyzer closed.")

if __name__ == '__main__':
    # Basic test execution if run directly
    logging.basicConfig(level=logging.INFO)
    # Load .env for direct execution if needed (e.g., for DB path)
    from dotenv import load_dotenv
    load_dotenv()
    
    logger.info("Running manual news analysis cycle...")
    asyncio.run(run_analysis_cycle())
    logger.info("Manual news analysis cycle finished.") 