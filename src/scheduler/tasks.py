import logging

logger = logging.getLogger(__name__)

async def fetch_news_tweets():
    """Scheduled task to fetch recent news tweets."""
    global news_fetcher_instance # Use the shared instance
    logger.info("Executing task: fetch_news_tweets (using shared instance)") # Log start
    if news_fetcher_instance is None:
        logger.error("NewsFetcher instance is not initialized in fetch_news_tweets task.")
        return
    try:
        await news_fetcher_instance.fetch_and_store_tweets()
        logger.info("Task fetch_news_tweets completed successfully.") # Log success
    except Exception as e:
        # Catch and log any exceptions during the fetch/store process
        logger.error(f"Error during fetch_news_tweets task: {e}", exc_info=True)

async def run_analysis_cycle_wrapper():
    """Scheduled task wrapper to run analysis using the shared instance."""
    # ... rest of file ... 