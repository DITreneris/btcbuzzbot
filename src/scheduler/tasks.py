import logging
import os
import random
from src.db.content_repo import ContentRepository # Import ContentRepo

logger = logging.getLogger(__name__)

# Shared instances (Initialized externally, e.g., in scheduler_engine or main script)
db_instance = None
news_fetcher_instance = None
news_analyzer_instance = None
tweet_handler_instance = None
content_repo_instance = None # ADDED: Instance for ContentRepository

# Assume NEWS_FETCHER_CLASS_AVAILABLE, NEWS_ANALYZER_CLASS_AVAILABLE, TWEET_JOB_ID_PREFIX are set externally if needed

async def fetch_news_tweets():
    """Scheduled task to fetch recent news tweets."""
    global news_fetcher_instance
    logger.info("Executing task: fetch_news_tweets (using shared instance)")
    if news_fetcher_instance is None:
        logger.error("NewsFetcher instance is not initialized in fetch_news_tweets task.")
        return
    try:
        max_results = int(os.environ.get('NEWS_FETCH_MAX_RESULTS', '5'))
        max_results = max(5, min(max_results, 100))
        # Assume fetch_and_store_tweets exists on news_fetcher_instance
        # It might need the query passed explicitly if not defaulted correctly there.
        default_query = "(#Bitcoin OR #BTC) -is:retweet lang:en"
        # Consider reading query from env var here if needed
        await news_fetcher_instance.fetch_and_store_tweets(query=default_query, max_results=max_results)
        logger.info(f"Task fetch_news_tweets completed successfully (max_results={max_results}).")
    except Exception as e:
        logger.error(f"Error during fetch_news_tweets task: {e}", exc_info=True)


async def run_analysis_cycle_wrapper():
    """Scheduled task wrapper to run analysis using the shared instance."""
    global news_analyzer_instance
    logger.info("Executing task: run_analysis_cycle_wrapper (using shared instance)")
    if news_analyzer_instance is None:
        logger.error("NewsAnalyzer instance is not initialized in run_analysis_cycle_wrapper task.")
        return
    try:
        await news_analyzer_instance.run_analysis_cycle()
        logger.info("News analysis cycle completed successfully via shared instance.")
    except Exception as e:
        logger.error(f"Error during run_analysis_cycle_wrapper task: {e}", exc_info=True)


async def reschedule_tweet_jobs(scheduler):
    """Removes old tweet jobs and adds new ones based on SCHEDULE_TIMES env var."""
    global db_instance # Need DB to get schedule times
    logger.info("Executing task: reschedule_tweet_jobs")
    if not db_instance:
        logger.error("DB instance not available in reschedule_tweet_jobs.")
        return

    try:
        # Get schedule times from DB (assuming a method exists)
        # This avoids direct env var access here, promoting single source of truth (DB)
        # schedule_times_str = await db_instance.get_config('SCHEDULE_TIMES', "08:00 12:00 16:00 20:00")
        # Fallback to env var if DB method doesn't exist yet
        schedule_times_str = os.environ.get('SCHEDULE_TIMES', "08:00 12:00 16:00 20:00")
        schedule_times = [t.strip() for t in schedule_times_str.split() if t.strip()]
        logger.info(f"Reschedule task: Using schedule times: {schedule_times}")

        # Remove existing tweet jobs
        removed_count = 0
        for job in scheduler.get_jobs():
            if job.id.startswith(TWEET_JOB_ID_PREFIX):
                scheduler.remove_job(job.id)
                removed_count += 1
        logger.info(f"Reschedule task: Found and removed {removed_count} existing tweet jobs.")

        # Add new jobs
        added_count = 0
        for time_str in schedule_times:
            try:
                hour, minute = map(int, time_str.split(':'))
                job_id = f"{TWEET_JOB_ID_PREFIX}{time_str.replace(':', '')}"
                scheduler.add_job(
                    post_tweet_and_log,
                    trigger='cron',
                    hour=hour,
                    minute=minute,
                    id=job_id,
                    name=f'Post Tweet at {time_str} UTC',
                    args=[job_id, time_str], # Pass job_id and time_str
                    replace_existing=True,
                    misfire_grace_time=60 # Allow 1 min grace period
                )
                logger.info(f"Reschedule task ADDED job: {job_id} for {time_str} UTC")
                added_count += 1
            except ValueError:
                logger.error(f"Reschedule task: Invalid time format '{time_str}' in SCHEDULE_TIMES. Skipping.")
            except Exception as add_err:
                logger.error(f"Reschedule task: Error adding job for {time_str}: {add_err}", exc_info=True)

        logger.info(f"Reschedule task finished. Added {added_count} tweet jobs.")

    except Exception as e:
        logger.error(f"Error during reschedule_tweet_jobs task: {e}", exc_info=True)


async def post_tweet_and_log(tweet_job_id: str, scheduled_time_str: str):
    """
    Handles the logic for posting a tweet based on schedule time and logging.
    Includes fallback logic for quote/joke if news fails.
    Forces quote/joke for specific times (06:00, 22:00).
    Forces price-only for 16:00.
    """
    global tweet_handler_instance, db_instance, news_analyzer_instance, content_repo_instance
    logger.info("--- Task post_tweet_and_log ENTERED ---")
    logger.info(f"Executing task: post_tweet_and_log for job {tweet_job_id} (scheduled: {scheduled_time_str})")

    if not all([tweet_handler_instance, db_instance, news_analyzer_instance, content_repo_instance]):
        logger.error("Critical error: One or more required instances are None.")
        return

    tweet_content = None
    post_type = "error"

    try:
        # --- Get Latest BTC Price (Needed for all tweet types) ---
        price_info = await tweet_handler_instance.get_latest_btc_price_info()
        if not price_info:
            logger.error("Failed to get BTC price info. Cannot compose tweet.")
            return

        # --- Compose Tweet Based on Schedule ---
        if scheduled_time_str in ['06:00', '22:00']:
            # Force Quote/Joke for these specific times
            logger.info(f"Scheduled time {scheduled_time_str}. Forcing quote/joke tweet.")
            try:
                content_type = random.choice(['quotes', 'jokes'])
                logger.info(f"Selected content type: {content_type}")
                content_data = await content_repo_instance.get_random_content(content_type)
                if content_data:
                    tweet_content = tweet_handler_instance.compose_fallback_tweet(price_info, content_data, content_type)
                    post_type = content_type
                else:
                    logger.warning(f"Force quote/joke failed: No content found for type '{content_type}'. Defaulting to price-only.")
                    tweet_content = tweet_handler_instance.compose_price_tweet(price_info)
                    post_type = "price_only_fallback"
            except Exception as forced_fallback_err:
                logger.error(f"Error during forced quote/joke composition: {forced_fallback_err}", exc_info=True)
                tweet_content = tweet_handler_instance.compose_price_tweet(price_info)
                post_type = "price_only_fallback_error"

        elif scheduled_time_str == '16:00':
            # Force Price-Only for 16:00
            logger.info("Scheduled time is 16:00. Composing price-only tweet.")
            tweet_content = tweet_handler_instance.compose_price_tweet(price_info)
            post_type = "price_only"

        else:
            # Standard Times (08:00, 12:00, 20:00): Try News then Fallback
            logger.info(f"Scheduled time {scheduled_time_str}. Attempting standard tweet (News/Fallback).")
            try:
                # Try news analysis
                latest_analyzed_news = await news_analyzer_instance.get_latest_analyzed_news_tweet()
                if latest_analyzed_news:
                    logger.info(f"Found latest analyzed news tweet ID: {latest_analyzed_news.get('id')}")
                    tweet_content = tweet_handler_instance.compose_standard_tweet(price_info, latest_analyzed_news)
                    post_type = "news_analysis"
                else:
                    logger.warning("No suitable analyzed news found. Falling back.")
            except Exception as analysis_err:
                logger.error(f"Error retrieving or composing with news analysis: {analysis_err}", exc_info=True)

            # Fallback Logic (if news failed or tweet_content is still None)
            if not tweet_content:
                logger.info("Falling back to quote/joke tweet composition.")
                try:
                    content_type = random.choice(['quotes', 'jokes'])
                    logger.info(f"Selected fallback content type: {content_type}")
                    content_data = await content_repo_instance.get_random_content(content_type)
                    if content_data:
                        tweet_content = tweet_handler_instance.compose_fallback_tweet(price_info, content_data, content_type)
                        post_type = content_type
                    else:
                        logger.warning(f"Fallback failed: No content found for type '{content_type}'. Defaulting to price-only.")
                        tweet_content = tweet_handler_instance.compose_price_tweet(price_info)
                        post_type = "price_only_fallback"
                except Exception as fallback_err:
                    logger.error(f"Error during fallback tweet composition: {fallback_err}", exc_info=True)
                    tweet_content = tweet_handler_instance.compose_price_tweet(price_info)
                    post_type = "price_only_fallback_error"

        # --- Post the composed tweet --- (Keep existing posting & logging logic)
        if tweet_content:
            logger.info(f"Attempting to post {post_type} tweet:")
            logger.info(f" > Content preview: {tweet_content[:100]}...")
            success, posted_tweet_info = await tweet_handler_instance.post_tweet(tweet_content)
            if success:
                tweet_id_str = str(posted_tweet_info.get('id')) if posted_tweet_info else None
                logger.info(f"Tweet successfully posted! Twitter ID: {tweet_id_str or 'N/A'}")
                # Log Post to Database
                await db_instance.log_post({
                    "tweet_type": post_type,
                    "tweet_content": tweet_content,
                    "scheduled_time_utc": scheduled_time_str,
                    "status": "success",
                    "twitter_post_id": tweet_id_str,
                    "notes": f"Posted via job {tweet_job_id}"
                })
            else:
                error_reason = posted_tweet_info.get('error', 'Unknown') if isinstance(posted_tweet_info, dict) else 'Unknown'
                logger.error(f"Failed to post tweet to Twitter API. Reason: {error_reason}")
                # Log failure to database
                await db_instance.log_post({
                    "tweet_type": post_type,
                    "tweet_content": tweet_content,
                    "scheduled_time_utc": scheduled_time_str,
                    "status": "failed",
                    "notes": f"Failed to post via job {tweet_job_id}. Reason: {error_reason}"
                })
        else:
            logger.error("Tweet composition failed for all strategies. No tweet posted.")
            # Log critical failure to database
            await db_instance.log_post({
                "tweet_type": "composition_failure",
                "tweet_content": None,
                "scheduled_time_utc": scheduled_time_str,
                "status": "failed",
                "notes": f"Failed to compose any tweet content via job {tweet_job_id}."
            })

    except Exception as e:
        logger.error(f"Critical error in post_tweet_and_log task: {e}", exc_info=True)
        # Log critical failure to database if possible
        try:
            await db_instance.log_post({
                "tweet_type": "task_exception",
                "tweet_content": None,
                "scheduled_time_utc": scheduled_time_str,
                "status": "failed",
                "notes": f"Unhandled exception in job {tweet_job_id}: {str(e)[:200]}"
            })
        except Exception as log_err:
            logger.error(f"Error logging TASK EXCEPTION to database: {log_err}", exc_info=True)
    finally:
        logger.info("--- Task post_tweet_and_log EXITED ---")


async def log_status_to_db(status, message):
    """Utility function to log status updates to the database."""
    global db_instance
    if not db_instance:
        # Cannot log to DB if instance isn't ready
        logger.warning(f"DB instance not available, cannot log status: {status} - {message}")
        return
    try:
        # Assuming Database class has an async method like log_app_status
        await db_instance.log_app_status({
            "component": "scheduler_engine", 
            "status": status,
            "message": message
        })
    except Exception as e:
        logger.error(f"Failed to log status '{status}' to database: {e}", exc_info=False) # Avoid traceback spam for logging failures

# --- Manual Trigger Functions (Simplified - Assumes instances are already initialized) ---

async def trigger_post_tweet():
    """Manually triggers a single tweet post using current logic (non-16:00)."""
    logger.info("--- Manual Trigger: post_tweet_and_log --- ")
    # Use a dummy job ID and determine a non-16:00 time
    # This simulates a standard run, attempting news then fallback
    await post_tweet_and_log(tweet_job_id="manual_trigger", scheduled_time_str="manual_12:00")
    return True # Assume success for trigger itself

async def trigger_fetch_news():
    """Manually triggers the news fetch task."""
    logger.info("--- Manual Trigger: fetch_news_tweets --- ")
    await fetch_news_tweets()
    return True

async def trigger_analyze_news():
    """Manually triggers the news analysis task."""
    logger.info("--- Manual Trigger: run_analysis_cycle_wrapper --- ")
    await run_analysis_cycle_wrapper()
    return True

# Note: No explicit initialize_shared_instances function here.
# Initialization MUST happen externally before scheduler starts tasks.
# Typically in the main script that starts the scheduler engine. 