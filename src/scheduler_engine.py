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

# Ensure src is in the path
if 'src' not in sys.path and os.path.exists('src'):
     sys.path.insert(0, os.path.abspath('.'))
elif os.path.basename(os.getcwd()) == 'src':
     sys.path.insert(0, os.path.abspath('..'))

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
        
    # executors = {
    #     'default': AsyncIOExecutor() # Remove explicit executors
    # }
    job_defaults = {
        'coalesce': False,
        'max_instances': 1 
    }
    # scheduler = BackgroundScheduler( # Change class
    scheduler = AsyncIOScheduler( # Use AsyncIOScheduler
        # executors=executors, # Remove executors arg
        job_defaults=job_defaults,
        timezone=SCHEDULER_TIMEZONE
    )

    # --- Add Core Jobs --- 
    # Note: reschedule_tweet_jobs itself runs periodically and manages the tweet jobs.
    # We only need to schedule the rescheduler, fetcher, and analyzer here.

    # 1. Job to periodically refresh the tweet schedule from DB
    scheduler.add_job(
        reschedule_tweet_jobs,
        trigger='interval',
        minutes=30, # Check for schedule changes every 30 mins
        id=RESCHEDULE_JOB_ID,
        name='Refresh Tweet Schedule from DB',
        args=[scheduler], # Pass scheduler instance
        replace_existing=True,
        misfire_grace_time=60 # Allow some delay if missed
    )

    # 2. Job to fetch news periodically (if available)
    if NEWS_FETCHER_CLASS_AVAILABLE:
        scheduler.add_job(
            run_news_fetch_wrapper, # Async wrapper from tasks
            trigger='interval',
            # Increase interval to reduce Twitter rate limit issues
            minutes=60,
            id=NEWS_FETCH_JOB_ID,
            name='Fetch News Tweets',
            replace_existing=True
        )
        logger.info("News fetching job added (interval: 60 minutes).") # Updated log
    else:
        logger.warning("News fetching job NOT added: Task not available.")

    # 3. Job to analyze fetched news periodically (if available)
    if NEWS_ANALYZER_CLASS_AVAILABLE:
        scheduler.add_job(
            run_analysis_cycle_wrapper, # Async wrapper from tasks
            trigger='interval',
            # Increase interval to reduce Groq rate limit issues
            minutes=30,
            id=NEWS_ANALYZE_JOB_ID,
            name='Analyze News Tweets',
            replace_existing=True
        )
        logger.info("News analysis job added (interval: 30 minutes).") # Updated log
    else:
        logger.warning("News analysis job NOT added: Task not available.")

    return scheduler

# --- Control Functions --- 
# def start(): # Change to async
async def start(): 
    """Initializes and starts the global scheduler instance."""
    global scheduler_instance
    if scheduler_instance and scheduler_instance.running:
        logger.warning("Scheduler already running.")
        return False
        
    if not TASKS_AVAILABLE:
         logger.error("Cannot start scheduler: Tasks module not available.")
         return False

    logger.info("Initializing scheduler engine...")
    scheduler_instance = create_scheduler()
    if not scheduler_instance:
        log_status_to_db("Error", "Scheduler engine creation failed.")
        return False

    # Perform initial scheduling run immediately in this thread
    # This ensures tweet jobs are set up before the scheduler truly starts running them
    try:
        logger.info("Performing initial tweet job scheduling...")
        # reschedule_tweet_jobs(scheduler_instance) # Change to await
        await reschedule_tweet_jobs(scheduler_instance) 
    except Exception as e:
        logger.error(f"Initial reschedule failed: {e}. Continuing scheduler start, but tweet jobs might be missing.", exc_info=True)

    # Start the scheduler (non-blocking for AsyncIOScheduler)
    try:
        scheduler_instance.start(paused=False)
        # time.sleep(1) # No longer needed with await/asyncio
        if scheduler_instance.running:
            await log_status_to_db("Running", "Scheduler engine started successfully.") # Await if log_status_to_db is async
            logger.info("Scheduler engine started successfully.")
            jobs = scheduler_instance.get_jobs()
            logger.info(f"Active jobs ({len(jobs)}): {[(job.id, str(job.trigger)) for job in jobs]}")
            return True
        else:
            log_status_to_db("Error", "Scheduler engine failed to start (state is not running).")
            logger.error("Scheduler engine failed to start (state is not running).")
            return False
    except Exception as e:
        log_status_to_db("Error", f"Scheduler engine failed to start: {e}")
        logger.error(f"Scheduler engine failed to start: {e}", exc_info=True)
        if scheduler_instance: # Attempt cleanup
             try: scheduler_instance.shutdown(wait=False)
             except: pass
        scheduler_instance = None
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