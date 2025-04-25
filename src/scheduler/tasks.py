import logging
import os # Add import

logger = logging.getLogger(__name__)

# Shared instances (initialized in main scheduler script)
news_fetcher_instance = None
news_analyzer_instance = None
tweet_handler_instance = None
db_instance = None # Added for reschedule task

async def fetch_news_tweets():
    """Scheduled task to fetch recent news tweets."""
    global news_fetcher_instance # Use the shared instance
    logger.info("Executing task: fetch_news_tweets (using shared instance)")
    if news_fetcher_instance is None:
        logger.error("NewsFetcher instance is not initialized in fetch_news_tweets task.")
        return
    try:
        # Read max_results from environment variable, default to 5
        max_results = int(os.environ.get('NEWS_FETCH_MAX_RESULTS', '5'))
        # Ensure it's at least 5
        max_results = max(5, max_results)

        # Pass max_results to the fetcher function
        await news_fetcher_instance.fetch_and_store_tweets(max_results=max_results)
        logger.info(f"Task fetch_news_tweets completed successfully (max_results={max_results}).") # Log success with max_results
    except Exception as e:
        # Catch and log any exceptions during the fetch/store process
        logger.error(f"Error during fetch_news_tweets task: {e}", exc_info=True)

async def run_analysis_cycle_wrapper():
    """Scheduled task wrapper to run analysis using the shared instance."""
    # ... rest of file ... 