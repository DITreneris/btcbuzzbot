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

# Ensure src is in the path if running directly or imported
if 'src' not in sys.path and os.path.exists('src'):
     sys.path.insert(0, os.path.abspath('.'))
elif os.path.basename(os.getcwd()) == 'src':
     # If running from within src, need to go up one level for imports
     sys.path.insert(0, os.path.abspath('..'))

# --- Project Imports with error handling ---
try:
    from src.database import Database
    DATABASE_CLASS_AVAILABLE = True
except ImportError as e:
    DATABASE_CLASS_AVAILABLE = False
    print(f"Error importing Database from src.database: {e}. Scheduler tasks may fail.")
    Database = None # Placeholder

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

# Initialize News Fetcher instance
news_fetcher_instance = None
if NEWS_FETCHER_CLASS_AVAILABLE:
    try:
        # NewsFetcher likely needs API keys, potentially DB access
        # Assuming it reads from env vars or a config object internally
        news_fetcher_instance = NewsFetcher(db_instance=db_instance) # Pass db if needed
        logger.info("Task NewsFetcher instance initialized.")
    except Exception as fetcher_init_e:
        logger.error(f"Failed to initialize Task NewsFetcher instance: {fetcher_init_e}", exc_info=True)
else:
    logger.warning("News Fetcher instance not created: Class not available.")

# Initialize News Analyzer instance
news_analyzer_instance = None
if NEWS_ANALYZER_CLASS_AVAILABLE:
    try:
        # NewsAnalyzer likely needs API keys, VADER, potentially DB access
        # Assuming it reads from env vars or a config object internally
        news_analyzer_instance = NewsAnalyzer(db_instance=db_instance) # Pass db if needed
        logger.info("Task NewsAnalyzer instance initialized.")
    except Exception as analyzer_init_e:
        logger.error(f"Failed to initialize Task NewsAnalyzer instance: {analyzer_init_e}", exc_info=True)
else:
    logger.warning("News Analyzer instance not created: Class not available.")

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
async def post_tweet_and_log():
    """Posts a tweet using the shared tweet_handler instance and logs the result."""
    # Use the shared instance
    if not tweet_handler_instance:
        await log_status_to_db("Error", "Tweet handler or DB not available for posting.")
        logger.error("Cannot post tweet: Tweet handler instance not available.")
        return False

    try:
        logger.info("Executing task: post_tweet_and_log")
        
        # --- Choose content type and get content --- 
        content_types = ['price', 'quote', 'joke'] 
        # Adjust weighting? e.g., more price tweets
        # content_types = ['price', 'price', 'quote', 'joke'] 
        chosen_type = random.choice(content_types)
        
        tweet_content = ""
        content_data = None
        
        if chosen_type == 'quote':
            logger.debug("Attempting to fetch random quote...")
            content_data = await db_instance.get_random_content('quotes')
            if content_data:
                tweet_content = content_data.get('text', '')
                logger.info(f"Fetched quote: {tweet_content[:50]}...")
            else:
                logger.warning("Could not get random quote, falling back to price.")
                chosen_type = 'price' # Fallback if no quote found
        elif chosen_type == 'joke':
            logger.debug("Attempting to fetch random joke...")
            content_data = await db_instance.get_random_content('jokes')
            if content_data:
                tweet_content = content_data.get('text', '')
                logger.info(f"Fetched joke: {tweet_content[:50]}...")
            else:
                logger.warning("Could not get random joke, falling back to price.")
                chosen_type = 'price' # Fallback if no joke found
        
        # If chosen_type is still 'price' (or fallback), tweet_content remains ""
        logger.info(f"Selected content type: {chosen_type}")
        
        # --- Call the tweet handler instance --- 
        logger.debug(f"Calling tweet_handler_instance.post_tweet with type '{chosen_type}' and content: '{tweet_content[:50]}...'")
        # Call the method on the instance
        result = await tweet_handler_instance.post_tweet(tweet_content, content_type=chosen_type)

        if isinstance(result, dict) and result.get('success', False):
             # Logging is handled within tweet_handler now, but we log overall success
             await log_status_to_db("Running", f"Scheduled tweet ({chosen_type}) posted successfully ({result.get('tweet_id', 'N/A')})")
             logger.info(f"Scheduled tweet ({chosen_type}) posted successfully: ID {result.get('tweet_id', 'N/A')}")
             return True
        else:
             error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
             await log_status_to_db("Error", f"Failed to post scheduled {chosen_type} tweet: {error_msg}")
             logger.error(f"Failed to post scheduled {chosen_type} tweet via tweet_handler: {error_msg}")
             return False

    except Exception as e:
        error_msg = f"Critical error in post_tweet_and_log task: {str(e)}"
        await log_status_to_db("Error", error_msg)
        logger.error(error_msg, exc_info=True)
        return False

async def run_news_fetch_wrapper():
    """Async wrapper to run the news fetch cycle using the shared instance."""
    if not news_fetcher_instance:
        logger.warning("News fetcher instance not available, skipping fetch.")
        return
    logger.info("Executing task: run_news_fetch_wrapper (using shared instance)")
    try:
        # Assuming NewsFetcher has a method like run_cycle() or fetch_and_store()
        # We might need to adjust NewsFetcher class later if this method doesn't exist
        await news_fetcher_instance.run_cycle() # Or appropriate method name
        logger.info("News fetch cycle task completed via shared instance.")
    except Exception as e:
        logger.error(f"Error during news fetch cycle task execution (shared instance): {e}", exc_info=True)
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
       Note: This task needs the scheduler instance passed to it.
    """
    from apscheduler.triggers.cron import CronTrigger # Import locally to avoid circular dep if engine imports this
    logger.info("Executing task: reschedule_tweet_jobs")

    schedule_config_str = None
    if db_instance:
        try:
            schedule_config_str = await db_instance.get_scheduler_config()
        except Exception as e:
            logger.error(f"Reschedule task failed to get config from DB: {e}", exc_info=True)
    else:
        logger.error("Reschedule task cannot get schedule: Database instance not available.")

    schedule_times = []
    if schedule_config_str:
        schedule_times = [t.strip() for t in schedule_config_str.split(',') if t.strip()]
        logger.debug(f"Reschedule task loaded schedule: {schedule_times}")
    else:
         logger.warning("Reschedule task: No schedule loaded from DB.")

    try:
        existing_job_ids = {job.id for job in scheduler.get_jobs() if job.id.startswith(TWEET_JOB_ID_PREFIX)}
        desired_job_ids = set()

        if not schedule_times:
            logger.warning("Reschedule task: No schedule times found/loaded. Removing all tweet jobs.")
        else:
            for time_str in schedule_times:
                try:
                    hour, minute = map(int, time_str.split(':'))
                    job_id = f"{TWEET_JOB_ID_PREFIX}{hour:02d}{minute:02d}"
                    desired_job_ids.add(job_id)

                    trigger = CronTrigger(hour=hour, minute=minute, timezone=SCHEDULER_TIMEZONE)

                    # --- Debugging: Log before replacement --- 
                    existing_job = scheduler.get_job(job_id)
                    if existing_job:
                        logger.debug(f"Reschedule DBG: Job {job_id} exists. Next run: {existing_job.next_run_time}. Trigger: {existing_job.trigger}")
                    else:
                        logger.debug(f"Reschedule DBG: Job {job_id} does not exist, will be added.")
                    # --- End Debugging ---

                    scheduler.add_job(
                        post_tweet_and_log,
                        trigger=trigger,
                        id=job_id,
                        name=f"Post Tweet {time_str} UTC",
                        replace_existing=True,
                        misfire_grace_time=60,
                        executor='default' # Assumes a 'default' ThreadPoolExecutor exists
                    )

                    # --- Debugging: Log after replacement --- \n                    updated_job = scheduler.get_job(job_id)\n                    if updated_job:\n                        # logger.debug(f"Reschedule DBG: Job {job_id} added/updated. Next run: {updated_job.next_run_time}. Trigger: {updated_job.trigger}") # Causes AttributeError\n                        logger.debug(f"Reschedule DBG: Job {job_id} found after add_job call. Trigger: {updated_job.trigger}") # Log trigger only\n                    else:\n                        # This should ideally not happen if add_job succeeded\n                        logger.warning(f"Reschedule DBG: Job {job_id} not found immediately after add_job call!")\n                    # --- End Debugging ---\n

                    logger.info(f"Reschedule task ensured job exists/updated: {job_id}")

                except ValueError:
                    logger.error(f"Reschedule task: Invalid time format '{time_str}' in schedule, skipping.")
                except Exception as job_e:
                     logger.error(f"Reschedule task: Error adding/updating job for {time_str}: {job_e}", exc_info=True)

        # Remove jobs that are no longer in the schedule
        jobs_to_remove = existing_job_ids - desired_job_ids
        for job_id in jobs_to_remove:
            try:
                scheduler.remove_job(job_id)
                logger.info(f"Reschedule task removed job: {job_id}")
            except Exception as remove_e:
                logger.error(f"Reschedule task: Error removing job {job_id}: {remove_e}")

        logger.info("Reschedule task finished.")
        active_tweet_jobs = [j for j in scheduler.get_jobs() if j.id.startswith(TWEET_JOB_ID_PREFIX)]
        await log_status_to_db("Running", f"Tweet schedule refreshed by task. {len(active_tweet_jobs)} tweet jobs active.")

    except Exception as e:
        logger.error(f"Reschedule task failed: {e}", exc_info=True)
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