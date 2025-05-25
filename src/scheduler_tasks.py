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

try:
    from src.twitter_client import TwitterClient # Added import for TwitterClient
    TWITTER_CLIENT_CLASS_AVAILABLE = True
except ImportError as e:
    TWITTER_CLIENT_CLASS_AVAILABLE = False
    print(f"Warning: Could not import TwitterClient class from src.twitter_client: {e}. Engagement update task may fail.")
    TwitterClient = None # Placeholder

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

# Initialize Twitter Client instance (needed for engagement updates)
twitter_client_instance = None
if TWITTER_CLIENT_CLASS_AVAILABLE:
    try:
        from src.config import Config # Import Config locally for API keys
        temp_config = Config()
        twitter_client_instance = TwitterClient(
            api_key=temp_config.twitter_api_key,
            api_secret=temp_config.twitter_api_secret,
            access_token=temp_config.twitter_access_token,
            access_token_secret=temp_config.twitter_access_token_secret
        )
        logger.info("Task TwitterClient instance initialized.")
    except Exception as tc_init_e:
        logger.error(f"Failed to initialize Task TwitterClient instance: {tc_init_e}", exc_info=True)
else:
    logger.warning("Twitter Client instance not created for tasks: Class not available.")

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

    # Fallback or default schedule if DB read fails or is empty
    if not schedule_config_str:
        schedule_config_str = os.environ.get('DEFAULT_SCHEDULE_TIMES', '08:00,12:00,16:00,20:00')
        logger.warning(f"Reschedule task: Using default/fallback schedule: '{schedule_config_str}'")

    # Remove existing tweet jobs
    removed_count = 0
    for job in scheduler.get_jobs():
        if job.id.startswith(TWEET_JOB_ID_PREFIX):
            try:
                scheduler.remove_job(job.id)
                removed_count += 1
                logger.info(f"Reschedule task REMOVED job: {job.id}")
            except JobLookupError:
                logger.warning(f"Reschedule task: Job {job.id} already removed or finished.")
            except Exception as e_remove:
                logger.error(f"Reschedule task: Error removing job {job.id}: {e_remove}", exc_info=True)
    logger.info(f"Reschedule task: Found {removed_count} existing tweet jobs to remove.")

    # Add new jobs based on the schedule string
    tweet_times = [t.strip() for t in schedule_config_str.split(',') if t.strip()]
    added_count = 0
    logger.info(f"Reschedule task: Adding jobs for schedule: {tweet_times}")
    for time_str in tweet_times:
        try:
            hour, minute = map(int, time_str.split(':'))
            job_id = f"{TWEET_JOB_ID_PREFIX}{time_str.replace(':','')}"
            
            # Ensure post_tweet_and_log is available
            if not POST_BTC_UPDATE_AVAILABLE:
                logger.error(f"Cannot schedule tweet for {time_str}: post_btc_update function not available.")
                continue # Skip this job

            scheduler.add_job(
                post_tweet_and_log,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=SCHEDULER_TIMEZONE),
                id=job_id,
                name=f'Scheduled Tweet Post at {time_str} UTC',
                replace_existing=True, # Replace if somehow exists
                args=[job_id, time_str] # Pass job_id and time_str to the task
            )
            added_count += 1
            logger.info(f"Reschedule task ADDED job: {job_id} for {time_str} UTC")
        except ValueError:
            logger.error(f"Reschedule task: Invalid time format '{time_str}' in schedule.")
        except Exception as e_add:
            logger.error(f"Reschedule task: Error adding job for {time_str}: {e_add}", exc_info=True)
    
    logger.info(f"Reschedule task finished. Added {added_count} tweet jobs.")
    await log_status_to_db("Scheduled", f"Scheduler reconfigured. Next tweets at: {schedule_config_str}")


async def update_tweet_engagement_stats_task():
    """Fetches engagement for posts and updates the database."""
    logger.info("--- Task update_tweet_engagement_stats_task ENTERED ---")
    
    if not db_instance or not twitter_client_instance:
        logger.error("Cannot update engagement: DB or TwitterClient instance not available.")
        return

    updated_count = 0
    failed_count = 0
    posts_to_check_limit = 20 # Process up to N posts per run to avoid long tasks / API limits

    try:
        posts = await db_instance.get_posts_needing_engagement_update(limit=posts_to_check_limit)
        if not posts:
            logger.info("No posts found needing engagement update at this time.")
            return

        logger.info(f"Found {len(posts)} posts to check for engagement updates.")

        for post in posts:
            tweet_id = post.get('tweet_id')
            if not tweet_id:
                logger.warning(f"Skipping post with no tweet_id: {post}")
                continue
            
            logger.debug(f"Fetching engagement for tweet ID: {tweet_id}")
            engagement_data = await twitter_client_instance.get_tweet_engagement(tweet_id)
            
            if engagement_data:
                likes = engagement_data.get('likes', 0)
                retweets = engagement_data.get('retweets', 0)
                logger.info(f"Tweet ID {tweet_id} - Likes: {likes}, Retweets: {retweets}")
                
                success = await db_instance.update_post_engagement(tweet_id, likes, retweets)
                if success:
                    logger.info(f"Successfully updated engagement for tweet ID {tweet_id} in DB.")
                    updated_count += 1
                else:
                    logger.error(f"Failed to update engagement for tweet ID {tweet_id} in DB.")
                    failed_count += 1
            else:
                logger.warning(f"Could not fetch engagement for tweet ID {tweet_id}. It might be deleted or API error.")
                # Optionally, update engagement_last_checked even if fetch fails to avoid re-checking immediately
                # await db_instance.update_post_engagement(tweet_id, 0, 0) # This would mark it as checked with 0s
                # For now, we'll just let it be re-checked next time.
                failed_count += 1
            
            await asyncio.sleep(1) # Small delay to be respectful to Twitter API

        logger.info(f"Engagement update task finished. Updated: {updated_count}, Failed/Skipped: {failed_count}.")

    except Exception as e:
        logger.error(f"Critical error in update_tweet_engagement_stats_task: {e}", exc_info=True)
        await log_status_to_db("Error", f"Engagement update task failed: {e}")


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