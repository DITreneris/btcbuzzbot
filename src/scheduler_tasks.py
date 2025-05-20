"""
Contains the actual functions executed as scheduled jobs by APScheduler.
"""

import logging
import os
import sys
import asyncio
import datetime
import pytz
import random

# Ensure the project root (parent of 'src') is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.abspath(os.path.join(current_dir, '..'))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# --- Project Imports with error handling ---
try:
    from src.database import Database
    DATABASE_CLASS_AVAILABLE = True
except ImportError as e:
    DATABASE_CLASS_AVAILABLE = False
    print(f"Error importing Database from src.database: {e}. Scheduler tasks may fail.")
    Database = None # Placeholder

try:
    # Import post_btc_update from main
    from src.main import post_btc_update
    POST_BTC_UPDATE_AVAILABLE = True
except ImportError as e:
    POST_BTC_UPDATE_AVAILABLE = False
    print(f"Error importing post_btc_update from src.main: {e}. Scheduler tasks may fail.")
    post_btc_update = None # Placeholder

try:
    from src import tweet_handler as tweet_handler_module # Import the module
    TweetHandler = tweet_handler_module.TweetHandler # Get the class
    TWEET_HANDLER_CLASS_AVAILABLE = True
except (ImportError, AttributeError) as e:
    TWEET_HANDLER_CLASS_AVAILABLE = False
    print(f"Warning: Could not import TweetHandler class from src.tweet_handler: {e}. Tweet posting task may fail.")
    TweetHandler = None # Placeholder class

try:
    # Import the class, not the run_ function
    from src.news_fetcher import NewsFetcher # Import the class
    NEWS_FETCHER_CLASS_AVAILABLE = True
except ImportError as e:
    NEWS_FETCHER_CLASS_AVAILABLE = False
    print(f"Warning: Could not import NewsFetcher class from src.news_fetcher: {e} - News fetching disabled.")
    NewsFetcher = None # Placeholder

try:
    # Import the class, not the run_ function
    from src.news_analyzer import NewsAnalyzer # Import the class
    NEWS_ANALYZER_CLASS_AVAILABLE = True
except ImportError as e:
    NEWS_ANALYZER_CLASS_AVAILABLE = False
    print(f"Warning: Could not import NewsAnalyzer class from src.news_analyzer: {e} - News analysis disabled.")
    NewsAnalyzer = None # Placeholder

try:
    # Import the class, not the run_ function
    from src.content_manager import ContentManager
    CONTENT_MANAGER_CLASS_AVAILABLE = True
except ImportError as e:
    CONTENT_MANAGER_CLASS_AVAILABLE = False
    print(f"Warning: Could not import ContentManager class from src.content_manager: {e} - Content management disabled.")
    ContentManager = None # Placeholder

# --- Constants & Config ---
TWEET_JOB_ID_PREFIX = 'scheduled_tweet_'
DB_PATH = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db') 
SCHEDULER_TIMEZONE = pytz.utc # Should match engine timezone

# --- Logging Setup ---
# Basic logger for tasks - might be refined by engine's config
logger = logging.getLogger('btcbuzzbot.scheduler.tasks')

# --- Shared Instances ---
# Initialize DB instance for use within tasks
db_instance = None
if DATABASE_CLASS_AVAILABLE:
    try:
        # Note: Database() might need config passed or read env vars itself
        db_instance = Database() # Assuming Database() reads DATABASE_URL etc.
        logger.info("Task DB instance initialized.")
    except Exception as db_init_e:
        logger.error(f"Failed to initialize Task DB instance: {db_init_e}", exc_info=True)
else:
    logger.error("Task DB functions will fail: Database class not available.")

# Initialize Content Manager instance (depends on ContentRepository)
content_manager_instance = None
if CONTENT_MANAGER_CLASS_AVAILABLE:
    try:
        # ContentManager initializes ContentRepository internally, which reads DB config
        content_manager_instance = ContentManager()
        logger.info("Task ContentManager instance initialized.")
    except Exception as cm_init_e:
        logger.error(f"Failed to initialize Task ContentManager instance: {cm_init_e}", exc_info=True)
else:
    logger.warning("Content Manager instance not created: Class not available.")

# Initialize News Fetcher instance
news_fetcher_instance = None
if NEWS_FETCHER_CLASS_AVAILABLE:
    try:
        # NewsFetcher now takes no arguments - initializes repo/client internally
        news_fetcher_instance = NewsFetcher()
        logger.info("Task NewsFetcher instance initialized.")
    except Exception as fetcher_init_e:
        logger.error(f"Failed to initialize Task NewsFetcher instance: {fetcher_init_e}", exc_info=True)
else:
    logger.warning("News Fetcher instance not created: Class not available.")

# Initialize News Analyzer instance
news_analyzer_instance = None
# Requires NewsAnalyzer class AND ContentManager instance
if NEWS_ANALYZER_CLASS_AVAILABLE and content_manager_instance:
    try:
        # NewsAnalyzer now requires ContentManager instance
        news_analyzer_instance = NewsAnalyzer(content_manager=content_manager_instance)
        logger.info("Task NewsAnalyzer instance initialized.")
    except Exception as analyzer_init_e:
        logger.error(f"Failed to initialize Task NewsAnalyzer instance: {analyzer_init_e}", exc_info=True)
else:
    if not NEWS_ANALYZER_CLASS_AVAILABLE:
        logger.warning("News Analyzer instance not created: Class not available.")
    elif not content_manager_instance:
        logger.warning("News Analyzer instance not created: ContentManager instance not available.")

# Initialize Tweet Handler instance
tweet_handler_instance = None
if TWEET_HANDLER_CLASS_AVAILABLE and db_instance:
    try:
        # Assuming TweetHandler needs db_instance and reads API keys from env
        tweet_handler_instance = TweetHandler(db_instance=db_instance)
        logger.info("Task TweetHandler instance initialized.")
    except Exception as handler_init_e:
        logger.error(f"Failed to initialize Task TweetHandler instance: {handler_init_e}", exc_info=True)
else:
    if not TWEET_HANDLER_CLASS_AVAILABLE:
        logger.warning("Tweet Handler instance not created: Class not available.")
    elif not db_instance:
        logger.warning("Tweet Handler instance not created: DB instance not available.")

# --- Utility Functions --- 
async def log_status_to_db(status: str, message: str):
    """Helper to log bot status updates to the database."""
    global db_instance
    if not db_instance:
        logger.warning("DB instance not available, cannot log status update.")
        return
    try:
        # logger.debug(f"Logging status to DB: {status} - {message}")
        # asyncio.run(db_instance.log_bot_status(status, message)) # Replace asyncio.run
        await db_instance.log_bot_status(status, message) # Use await
    except Exception as e:
        # Avoid logging loops if the DB logging itself fails
        print(f"CRITICAL: Failed to log bot status to DB: {e}")

# --- Task Functions --- 
async def post_tweet_and_log(job_id: str = "unknown", time_str: str = "unknown"):
    """Calls the main post_btc_update logic and logs the outcome."""
    logger.info(f"--- Task post_tweet_and_log ENTERED (Job ID: {job_id}, Time: {time_str}) ---") # Added entry log

    if not POST_BTC_UPDATE_AVAILABLE:
        logger.error("Cannot post tweet: post_btc_update function not available.")
        await log_status_to_db("Error", "post_btc_update function not available for posting.")
        return False # Indicate failure

    # Config object might be needed by post_btc_update - it reads env vars itself
    # If post_btc_update relies on a passed config object, we might need to adjust this
    # For now, assume it initializes its own config or uses shared config if available elsewhere
    
    try:
        logger.info(f"Executing task: Calling main.post_btc_update for scheduled time {time_str}")
        # Directly call the function from main.py
        # Pass the scheduled_time_str which post_btc_update expects
        tweet_id = await post_btc_update(scheduled_time_str=time_str)

        if tweet_id:
            # post_btc_update handles its own detailed logging and DB logging
            await log_status_to_db("Running", f"Tweet posting task for {time_str} completed successfully (Tweet ID: {tweet_id}).")
            logger.info(f"Tweet posting task for {time_str} completed successfully (Tweet ID: {tweet_id}).")
            return True
        else:
            # post_btc_update should log specific errors, this logs the task failure
            error_msg = f"Task for {time_str} failed: main.post_btc_update did not return a tweet ID."
            await log_status_to_db("Error", error_msg)
            logger.warning(error_msg) # Use warning as specific error should be logged by post_btc_update
            return False

    except Exception as e:
        error_msg = f"Critical error in post_tweet_and_log task for {time_str}: {str(e)}"
        await log_status_to_db("Error", error_msg)
        logger.error(error_msg, exc_info=True)
        return False

async def run_news_fetch_wrapper():
    """Async wrapper to run the news fetch cycle using the shared instance."""
    if not news_fetcher_instance:
        logger.warning("News fetcher instance not available, skipping fetch.")
        return
    # Log the correct task execution start
    logger.info("Executing task: run_news_fetch_wrapper -> fetch_and_store_tweets (using shared instance)")
    try:
        # Call the method that actually fetches AND stores
        await news_fetcher_instance.fetch_and_store_tweets()
        logger.info("News fetch_and_store_tweets task completed via wrapper.")
    except Exception as e:
        logger.error(f"Error during news fetch_and_store_tweets task execution (via wrapper): {e}", exc_info=True)
        # Log status using the helper
        await log_status_to_db("Error", f"News fetch cycle task failed: {e}")

async def run_analysis_cycle_wrapper():
    """Async wrapper to run the news analysis cycle using the shared instance."""
    if not news_analyzer_instance:
        logger.warning("News analyzer instance not available, skipping analysis.")
        return
    logger.info("Executing task: run_analysis_cycle_wrapper (using shared instance)")
    try:
        # Assuming NewsAnalyzer has a method like run_cycle()
        # We will create this method in NewsAnalyzer based on the old run_analysis_cycle function
        await news_analyzer_instance.run_cycle()
        logger.info("News analysis cycle completed successfully via shared instance.")
    except Exception as e:
        logger.error(f"Error during news analysis cycle task (shared instance): {e}", exc_info=True)
        await log_status_to_db("Error", f"News analysis cycle task failed: {e}")


async def reschedule_tweet_jobs(scheduler):
    """Reads schedule from DB and updates APScheduler jobs.
       Uses a remove-then-add strategy for reliability.
    """
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.base import JobLookupError # Import for specific exception handling
    logger.info("Executing task: reschedule_tweet_jobs")

    schedule_config_str = None
    if db_instance:
        try:
            schedule_config_str = await db_instance.get_scheduler_config()
            # Add INFO log to see what schedule string is actually retrieved
            logger.info(f"Reschedule task: Retrieved schedule string from DB: '{schedule_config_str}'")
        except Exception as e:
            logger.error(f"Reschedule task failed to get config from DB: {e}", exc_info=True)
            return # Stop if we can't get config
    else:
        logger.error("Reschedule task cannot get schedule: Database instance not available.")
        return # Stop if no DB

    schedule_times = []
    if schedule_config_str:
        schedule_times = [t.strip() for t in schedule_config_str.split(',') if t.strip()]
        logger.debug(f"Reschedule task loaded schedule: {schedule_times}")
    else:
         logger.warning("Reschedule task: No schedule loaded from DB.")

    try:
        # --- Strategy: Remove all existing tweet jobs first --- 
        existing_job_ids = {job.id for job in scheduler.get_jobs() if job.id.startswith(TWEET_JOB_ID_PREFIX)}
        logger.info(f"Reschedule task: Found {len(existing_job_ids)} existing tweet jobs to remove.")
        for job_id in existing_job_ids:
            try:
                scheduler.remove_job(job_id)
                logger.debug(f"Reschedule task removed job: {job_id}")
            except JobLookupError:
                 logger.warning(f"Reschedule task: Job {job_id} already gone before removal attempt.")
            except Exception as remove_e:
                logger.error(f"Reschedule task: Error removing job {job_id}: {remove_e}")
        # --- End Removal ---

        # --- Strategy: Add jobs based on the current schedule --- 
        added_count = 0
        if not schedule_times:
            logger.warning("Reschedule task: No schedule times found/loaded. No tweet jobs will be added.")
        else:
            logger.info(f"Reschedule task: Adding jobs for schedule: {schedule_times}")
            for time_str in schedule_times:
                try:
                    hour, minute = map(int, time_str.split(':'))
                    job_id = f"{TWEET_JOB_ID_PREFIX}{time_str.replace(':', '')}" # Use consistent ID format
                    scheduler.add_job(
                        post_tweet_and_log, # This is the target function
                        trigger='cron',
                        hour=hour,
                        minute=minute,
                        timezone=SCHEDULER_TIMEZONE, # Explicitly set timezone
                        id=job_id,
                        name=f'Post Tweet at {time_str} UTC',
                        args=[job_id, time_str], # Pass job_id and time_str as arguments
                        replace_existing=True, # Replace existing job with same ID
                        misfire_grace_time=60 # Allow 1 min grace period
                    )
                    logger.info(f"Reschedule task ADDED job: {job_id} for {time_str} UTC")
                    added_count += 1

                except ValueError:
                    logger.error(f"Reschedule task: Invalid time format '{time_str}' in schedule, skipping add.")
                except Exception as job_e:
                     logger.error(f"Reschedule task: Error adding job for {time_str}: {job_e}", exc_info=True)
        # --- End Adding ---

        logger.info(f"Reschedule task finished. Added {added_count} tweet jobs.")
        active_tweet_jobs = [j for j in scheduler.get_jobs() if j.id.startswith(TWEET_JOB_ID_PREFIX)]
        await log_status_to_db("Running", f"Tweet schedule refreshed. {len(active_tweet_jobs)} tweet jobs active.")

    except Exception as e:
        logger.error(f"Reschedule task failed during remove/add process: {e}", exc_info=True)
        log_status_to_db("Error", f"Reschedule task failed to refresh tweet schedule: {e}")

# --- Manual Trigger Functions (for CLI) ---

def trigger_post_tweet():
    print("Manually triggering tweet post...")
    return post_tweet_and_log()

async def trigger_fetch_news():
    print("Manually triggering news fetch...")
    if NEWS_FETCHER_CLASS_AVAILABLE:
        try:
            await run_news_fetch_wrapper()
            print("Manual news fetch completed.")
            return True
        except Exception as e:
            print(f"Error during manual news fetch: {e}")
            return False
    else:
        print("News fetcher is not available.")
        return False

async def trigger_analyze_news():
    print("Manually triggering news analysis...")
    if NEWS_ANALYZER_CLASS_AVAILABLE:
        try:
            await run_analysis_cycle_wrapper()
            print("Manual news analysis completed.")
            return True
        except Exception as e:
            print(f"Error during manual news analysis: {e}")
            return False
    else:
        print("News analyzer is not available.")
        return False

if __name__ == '__main__':
    # Allow testing individual tasks if needed
    print("This module contains scheduler tasks. Run scheduler_cli.py or scheduler.py to start.")
    # Example: Test fetching news
    # logging.basicConfig(level=logging.INFO)
    # from dotenv import load_dotenv
    # load_dotenv()
    # trigger_fetch_news()
    # trigger_analyze_news() 