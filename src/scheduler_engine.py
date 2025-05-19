"""
Manages the APScheduler instance, job configuration, and start/stop controls.
"""

import logging
import os
import sys
import time
import asyncio
import pytz

# from apscheduler.schedulers.background import BackgroundScheduler # Remove this
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Import this
# Remove ThreadPoolExecutor import if no longer needed
# from apscheduler.executors.pool import ThreadPoolExecutor 
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.base import JobLookupError # Add this import

# Ensure src is in the path
if 'src' not in sys.path and os.path.exists('src'):
     sys.path.insert(0, os.path.abspath('.'))
elif os.path.basename(os.getcwd()) == 'src':
     sys.path.insert(0, os.path.abspath('..'))

# --- Initialize Shared Instances --- 

logger_init = logging.getLogger('btcbuzzbot.init') # Use a specific logger for init
db_instance = None
content_repo_instance = None
news_fetcher_instance = None # Define placeholder
news_analyzer_instance = None # Define placeholder
tweet_handler_instance = None # Define placeholder

try:
    from src.database import Database
    from src.db.content_repo import ContentRepository
    from src.news_fetcher import NewsFetcher # Add import
    from src.news_analyzer import NewsAnalyzer # Add import
    from src.tweet_handler import TweetHandler # Add import
    from src.content_manager import ContentManager # --> ADDED IMPORT
    from src import scheduler_tasks as tasks # Import the tasks module itself

    # 1. Database
    try:
        db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
        db_instance = Database(db_path=db_path)
        logger_init.info("Database instance created.")
        tasks.db_instance = db_instance # Assign to tasks module
    except Exception as e:
        logger_init.error(f"FATAL: Failed to initialize Database instance: {e}", exc_info=True)
        sys.exit("DB Initialization Failed")

    # 2. Content Repository (No longer needs DB passed explicitly)
    try:
        content_repo_instance = ContentRepository()
        logger_init.info("ContentRepository instance created.")
        # tasks.content_repo_instance = content_repo_instance # tasks module doesn't seem to use this directly
    except Exception as e:
        logger_init.error(f"Failed to initialize ContentRepository instance: {e}", exc_info=True)
        logger_init.warning("Content repository functions may fail.")
        content_repo_instance = None # Ensure it's None if failed
        # Allow continuing

    # 2b. Content Manager (Needs ContentRepository internally)
    content_manager_instance = None # Define before try block
    try:
        content_manager_instance = ContentManager()
        logger_init.info("ContentManager instance created.")
        tasks.content_manager_instance = content_manager_instance # Assign to tasks module if needed (NewsAnalyzer uses it)
    except Exception as e:
        logger_init.error(f"Failed to initialize ContentManager instance: {e}", exc_info=True)
        logger_init.warning("Quote/joke fallback may fail if CM is used directly by tasks.")
        # Allow continuing

    # 3. News Fetcher (Initializes NewsRepository internally)
    try:
        news_fetcher_instance = NewsFetcher()
        logger_init.info("NewsFetcher instance created.")
        tasks.news_fetcher_instance = news_fetcher_instance # Assign to tasks module
    except ImportError:
        logger_init.warning("NewsFetcher class not found or import failed. News fetching will be skipped.")
        tasks.news_fetcher_instance = None # Ensure it's None in tasks
    except Exception as e:
        logger_init.error(f"Failed to initialize NewsFetcher instance: {e}", exc_info=True)
        tasks.news_fetcher_instance = None # Ensure it's None in tasks

    # 4. News Analyzer (Needs ContentManager instance)
    try:
        if content_manager_instance:
            news_analyzer_instance = NewsAnalyzer(content_manager=content_manager_instance)
            logger_init.info("NewsAnalyzer instance created.")
            tasks.news_analyzer_instance = news_analyzer_instance # Assign to tasks module
        else:
             logger_init.warning("NewsAnalyzer instance NOT created: ContentManager instance was not available.")
             tasks.news_analyzer_instance = None # Ensure it's None in tasks
    except ImportError:
        logger_init.warning("NewsAnalyzer class not found or import failed. News analysis will be skipped.")
        tasks.news_analyzer_instance = None # Ensure it's None in tasks
    except Exception as e:
        logger_init.error(f"Failed to initialize NewsAnalyzer instance: {e}", exc_info=True)
        tasks.news_analyzer_instance = None # Ensure it's None in tasks

    # 5. Tweet Handler (needs DB)
    try:
        # TweetHandler only needs db_instance according to its __init__
        tweet_handler_instance = TweetHandler(db_instance=db_instance)
        logger_init.info("TweetHandler instance created.")
        tasks.tweet_handler_instance = tweet_handler_instance # Assign to tasks module
    except ImportError:
        logger_init.error("FATAL: TweetHandler class not found or import failed. Cannot post tweets.")
        sys.exit("Tweet Handler Import Failed") # Exit if handler fails
    except Exception as e:
        logger_init.error(f"FATAL: Failed to initialize TweetHandler instance: {e}", exc_info=True)
        sys.exit("Tweet Handler Initialization Failed") # Exit if handler fails

except ImportError as e:
    # This catches imports at the top of the try block
    logger_init.error(f"FATAL: Failed to import one or more core components: {e}. Cannot initialize.")
    sys.exit("Core Component Import Failed")
except Exception as e:
    logger_init.error(f"FATAL: An unexpected error occurred during shared instance initialization: {e}", exc_info=True)
    sys.exit("Unexpected Initialization Error")

# --- End Shared Instance Initialization --- 

# Import tasks and DB related functions/classes
try:
    from src.scheduler_tasks import (
        post_tweet_and_log, 
        run_news_fetch_wrapper, 
        run_analysis_cycle_wrapper, 
        reschedule_tweet_jobs, 
        NEWS_FETCHER_CLASS_AVAILABLE,
        NEWS_ANALYZER_CLASS_AVAILABLE,
        TWEET_JOB_ID_PREFIX, # Need prefix for logging
        log_status_to_db # Use the task module's logger utility
    )
    TASKS_AVAILABLE = True
except ImportError as e:
    print(f"FATAL: Failed to import tasks from src.scheduler_tasks: {e}. Engine cannot run.")
    TASKS_AVAILABLE = False
    # Define placeholders if needed to prevent NameErrors later, though logic should check TASKS_AVAILABLE
    NEWS_FETCHER_CLASS_AVAILABLE = False
    NEWS_ANALYZER_CLASS_AVAILABLE = False
    TWEET_JOB_ID_PREFIX = 'scheduled_tweet_'
    def log_status_to_db(*args, **kwargs): pass # No-op

# Import central Database class for update_schedule
try:
    from src.database import Database
    DATABASE_CLASS_AVAILABLE = True
except ImportError as e:
    DATABASE_CLASS_AVAILABLE = False
    print(f"Error importing Database for engine: {e}. update_schedule may fail.")
    Database = None

# --- Constants & Config ---
RESCHEDULE_JOB_ID = 'reschedule_tweet_jobs'
NEWS_FETCH_JOB_ID = 'fetch_news_tweets'
NEWS_ANALYZE_JOB_ID = 'analyze_news_tweets'
DB_PATH = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db') 
SCHEDULER_TIMEZONE = pytz.utc 

# --- Externalize Intervals ---
DEFAULT_RESCHEDULE_MINUTES = 30
DEFAULT_NEWS_FETCH_MINUTES = 720
DEFAULT_NEWS_ANALYZE_MINUTES = 30
DEFAULT_RESCHEDULE_GRACE_SECONDS = 60
DEFAULT_NEWS_FETCH_GRACE_SECONDS = 300

# REMOVED: No longer need RESCHEDULE_INTERVAL_MINUTES since we'll run it only at startup
NEWS_FETCH_INTERVAL_MINUTES = int(os.environ.get('NEWS_FETCH_INTERVAL_MINUTES', DEFAULT_NEWS_FETCH_MINUTES))
NEWS_ANALYZE_INTERVAL_MINUTES = int(os.environ.get('NEWS_ANALYZE_INTERVAL_MINUTES', DEFAULT_NEWS_ANALYZE_MINUTES))
# REMOVED: No longer need RESCHEDULE_GRACE_SECONDS for interval trigger
NEWS_FETCH_GRACE_SECONDS = int(os.environ.get('NEWS_FETCH_GRACE_SECONDS', DEFAULT_NEWS_FETCH_GRACE_SECONDS))

# --- Logging Setup ---
# Configure root logger or specific loggers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.getLogger('apscheduler').setLevel(logging.WARNING) # Reduce APScheduler noise
logger = logging.getLogger('btcbuzzbot.scheduler.engine')

# --- Scheduler Setup & Global Instance --- 
scheduler_instance = None

def create_scheduler():
    """Creates and configures the APScheduler instance."""
    if not TASKS_AVAILABLE:
        logger.error("Cannot create scheduler: Tasks module failed to import.")
        return None
        
    job_defaults = {
        'coalesce': False,
        'max_instances': 1 
    }
    scheduler = AsyncIOScheduler(
        job_defaults=job_defaults,
        timezone=SCHEDULER_TIMEZONE
    )

    # --- Add Core Jobs --- 
    # Note: reschedule_tweet_jobs will be called directly at startup,
    # not scheduled as a periodic job

    # 2. Job to fetch news periodically (if available)
    if NEWS_FETCHER_CLASS_AVAILABLE:
        scheduler.add_job(
            run_news_fetch_wrapper, # Async wrapper from tasks
            trigger='interval',
            minutes=NEWS_FETCH_INTERVAL_MINUTES,  # Use variable
            id=NEWS_FETCH_JOB_ID,
            name='Fetch News Tweets',
            replace_existing=True,
            misfire_grace_time=NEWS_FETCH_GRACE_SECONDS # Use variable
        )
        logger.info(f"News fetching job added (interval: {NEWS_FETCH_INTERVAL_MINUTES} minutes).")
    else:
        logger.warning("News fetching job NOT added: Task not available.")

    # 3. Job to analyze fetched news periodically (if available)
    if NEWS_ANALYZER_CLASS_AVAILABLE:
        scheduler.add_job(
            run_analysis_cycle_wrapper, # Async wrapper from tasks
            trigger='interval',
            minutes=NEWS_ANALYZE_INTERVAL_MINUTES, # Use variable
            id=NEWS_ANALYZE_JOB_ID,
            name='Analyze News Tweets',
            replace_existing=True
        )
        logger.info(f"News analysis job added (interval: {NEWS_ANALYZE_INTERVAL_MINUTES} minutes).")
    else:
        logger.warning("News analysis job NOT added: Task not available.")
    
    return scheduler

async def start():
    """Starts the scheduler and initializes all tasks."""
    global scheduler_instance
    
    if scheduler_instance and scheduler_instance.running:
        logger.warning("Scheduler already running. Ignoring start request.")
        return True # Already running
        
    try:
        # Create the scheduler
        scheduler_instance = create_scheduler()
        if not scheduler_instance:
            logger.error("Failed to create scheduler. Cannot start.")
            return False
            
        # Start the scheduler
        scheduler_instance.start()
        if not scheduler_instance.running:
            logger.error("APScheduler not running after start() called. Check configuration.")
            return False

        # Attempt to remove any lingering periodic job for reschedule_tweet_jobs
        try:
            scheduler_instance.remove_job(RESCHEDULE_JOB_ID)
            logger.info(f"Successfully removed any lingering periodic job with ID '{RESCHEDULE_JOB_ID}'.")
        except JobLookupError:
            logger.info(f"No lingering periodic job found with ID '{RESCHEDULE_JOB_ID}' to remove. This is expected if it was already cleaned up or never existed periodically.")
        except Exception as e_remove:
            logger.warning(f"Could not remove job '{RESCHEDULE_JOB_ID}', it might not exist or another error occurred: {e_remove}")
            
        await log_status_to_db("Running", "Scheduler started successfully.")
        logger.info("Scheduler started successfully.")
        
        # Run reschedule_tweet_jobs once at startup instead of scheduling it as a periodic job
        try:
            logger.info("Running reschedule_tweet_jobs once at startup to initialize tweet schedule.")
            await reschedule_tweet_jobs(scheduler_instance)
            logger.info("Initial tweet schedule successfully set up.")
        except Exception as e:
            logger.error(f"Failed to run initial reschedule_tweet_jobs: {e}", exc_info=True)
            await log_status_to_db("Warning", f"Initial tweet schedule setup failed: {e}")
            # Continue running even if initial reschedule fails
        
        return True
            
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}", exc_info=True)
        await log_status_to_db("Error", f"Scheduler start failed: {e}")
        # Attempt to clean up if partially started
        if scheduler_instance and scheduler_instance.running:
            try:
                scheduler_instance.shutdown()
            except:
                pass # Ignore shutdown errors during failed startup
        return False

# def stop(): # Change to async
async def stop():
    """Stops the global scheduler instance."""
    global scheduler_instance
    if not scheduler_instance or not scheduler_instance.running:
        logger.warning("Scheduler not running or not initialized.")
        return False

    logger.info("Shutting down scheduler engine...")
    try:
        scheduler_instance.shutdown()
        # await log_status_to_db("Stopped", "Scheduler engine shut down.") # Use await
        await log_status_to_db("Stopped", "Scheduler engine shut down.") 
        logger.info("Scheduler engine shut down successfully.")
        scheduler_instance = None
        return True
    except Exception as e:
        logger.error(f"Scheduler engine failed to shut down cleanly: {e}", exc_info=True)
        # Don't log stopped status to DB if shutdown fails?
        return False

def update_schedule(new_schedule):
    """Updates the schedule config in the DB and triggers immediate job rescheduling."""
    global scheduler_instance
    if not DATABASE_CLASS_AVAILABLE:
        logger.error("Cannot update schedule: Database class not available.")
        return False

    # Reuse the DB instance initialized by the tasks module if possible?
    # Or create a temporary one? Let's try reusing.
    task_db_instance = getattr(sys.modules.get('src.scheduler_tasks'), 'db_instance', None)

    if not task_db_instance:
        logger.warning("DB instance from tasks module not found. Creating temporary DB instance for update.")
        try:
            task_db_instance = Database(db_path=DB_PATH)
        except Exception as e:
            logger.error(f"Failed to create temporary DB instance for update: {e}")
            return False
            
    valid_schedule = []
    try:
        for t in new_schedule:
            t = t.strip()
            if t:
                try:
                    hour, minute = map(int, t.split(':'))
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        valid_schedule.append(f"{hour:02d}:{minute:02d}")
                    else:
                        logger.warning(f"Invalid time value '{t}' in schedule, skipping.")
                except ValueError:
                    logger.warning(f"Invalid time format '{t}' in schedule, skipping.")

        schedule_str = ','.join(valid_schedule)
        
        # Update DB using the instance
        asyncio.run(task_db_instance.update_scheduler_config(schedule_str))
        logger.info(f"Schedule updated in DB: {valid_schedule}")

        # Trigger immediate rescheduling if scheduler is running
        if scheduler_instance and scheduler_instance.running:
            logger.info("Triggering immediate reschedule of tweet jobs via engine.")
            scheduler_instance.add_job(
                reschedule_tweet_jobs,
                args=[scheduler_instance],
                id='manual_reschedule_trigger',
                name='Manual Reschedule Trigger',
                replace_existing=True,
                misfire_grace_time=None,
                trigger='date' # Run once immediately
            )
        else:
             logger.info("Engine: Scheduler not running, reschedule will happen on next start/periodic check.")
        return True
    except Exception as e:
        logger.error(f"Error updating schedule config via engine: {e}", exc_info=True)
        return False

# --- Direct Execution (for testing engine setup) ---
if __name__ == '__main__':
    print("This module manages the scheduler engine. Run scheduler_cli.py or scheduler.py to start.")
    # Example: Test scheduler creation
    # test_scheduler = create_scheduler()
    # if test_scheduler:
    #     print("Scheduler created successfully. Jobs:")
    #     test_scheduler.print_jobs()
    #     test_scheduler.shutdown(wait=False)
    # else:
    #     print("Scheduler creation failed.") 