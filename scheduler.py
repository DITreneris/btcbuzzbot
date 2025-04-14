"""
Tweet scheduler for BTCBuzzBot - handles automatic posting at configured intervals
"""
import os
import sys
import time
import sqlite3
import logging
import datetime
from threading import Thread
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('btcbuzzbot')

# Global state
scheduler_running = False
scheduler_thread = None
scheduled_times = ["08:00", "12:00", "16:00", "20:00"]  # Default schedule in UTC

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect('btcbuzzbot.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database tables needed for the scheduler"""
    try:
        with get_db_connection() as conn:
            # Create bot status table if it doesn't exist
            conn.execute('''
            CREATE TABLE IF NOT EXISTS bot_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL
            )
            ''')
            
            # Create scheduler config table if it doesn't exist
            conn.execute('''
            CREATE TABLE IF NOT EXISTS scheduler_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            ''')
            
            # Insert default schedule if not present
            config = conn.execute('SELECT value FROM scheduler_config WHERE key = "schedule"').fetchone()
            if not config:
                default_schedule = ','.join(scheduled_times)
                conn.execute(
                    'INSERT INTO scheduler_config (key, value) VALUES (?, ?)',
                    ('schedule', default_schedule)
                )
            
            conn.commit()
            logger.info("Database initialized for scheduler")
            return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def log_status(status, message):
    """Log status to the database and logger"""
    logger.info(f"Status update: {status} - {message}")
    
    try:
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)',
                (datetime.datetime.utcnow().isoformat(), status, message)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log status to database: {e}")

def get_last_status():
    """Get the most recent status from the database"""
    try:
        with get_db_connection() as conn:
            last_status = conn.execute(
                'SELECT * FROM bot_status ORDER BY timestamp DESC LIMIT 1'
            ).fetchone()
            
            if last_status:
                return {
                    'timestamp': last_status['timestamp'],
                    'status': last_status['status'],
                    'message': last_status['message']
                }
            else:
                return {
                    'timestamp': datetime.datetime.utcnow().isoformat(),
                    'status': 'Unknown',
                    'message': 'No status recorded'
                }
    except Exception as e:
        logger.error(f"Error getting last status: {e}")
        return {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'status': 'Error',
            'message': f'Failed to retrieve status: {str(e)}'
        }

def post_tweet_and_log():
    """Post a tweet using the direct_tweet module and log the result"""
    try:
        logger.info("Attempting to post scheduled tweet...")
        
        # First try to use the tweet_handler module for sophisticated content
        try:
            from src import tweet_handler
            logger.info("Using src.tweet_handler for sophisticated tweet content")
            
            # Generate a random content type
            import random
            content_types = ['quote', 'price', 'joke']
            content_type = random.choice(content_types)
            
            # Post the tweet using the handler
            handler = tweet_handler.get_instance()
            if handler:
                result = handler.post_tweet("", content_type=content_type)
                
                if isinstance(result, dict) and result.get('success', False):
                    log_status("Running", f"Posted {content_type} tweet successfully")
                    logger.info(f"Posted {content_type} tweet successfully")
                    return True
                else:
                    error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
                    logger.warning(f"Failed to post via tweet_handler: {error_msg}, trying fallback method")
                    # Continue to fallback method
            else:
                logger.warning("Tweet handler not initialized, using fallback method")
        except Exception as e:
            logger.warning(f"Error using tweet_handler: {e}, trying fallback method")
            # Continue to fallback method
        
        # Fallback to direct_tweet.py which has proper content with BTC price and quotes
        try:
            import direct_tweet
            logger.info("Using direct_tweet fallback for tweet content")
            
            # Try to post the tweet
            result = direct_tweet.post_tweet()
            
            if result:
                log_status("Running", "Scheduled tweet posted successfully via direct_tweet")
                logger.info("Scheduled tweet posted successfully via direct_tweet")
                return True
            else:
                logger.warning("Failed to post via direct_tweet, trying last resort method")
                # Continue to last resort method
        except Exception as e:
            logger.warning(f"Error using direct_tweet: {e}, trying last resort method")
            # Continue to last resort method
        
        # Last resort: Use fixed_tweet as a final fallback (but only if other methods fail)
        import fixed_tweet
        logger.info("Using fixed_tweet as last resort")
        
        # Try to post the tweet
        result = fixed_tweet.post_tweet()
        
        if result:
            log_status("Running", "Scheduled tweet posted successfully via fixed_tweet (last resort)")
            logger.info("Scheduled tweet posted successfully via fixed_tweet (last resort)")
            return True
        else:
            log_status("Error", "Failed to post scheduled tweet (all methods failed)")
            logger.error("Failed to post scheduled tweet (all methods failed)")
            return False
    except Exception as e:
        error_msg = f"Error posting scheduled tweet: {str(e)}"
        log_status("Error", error_msg)
        logger.error(error_msg)
        traceback.print_exc()
        return False

def get_configured_schedule():
    """Get the configured schedule from the database"""
    try:
        with get_db_connection() as conn:
            # Check if we have a scheduler_config table
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduler_config'")
            if not cursor.fetchone():
                logger.warning("No scheduler_config table found, using default schedule")
                return scheduled_times
            
            # Get the schedule
            config = conn.execute('SELECT value FROM scheduler_config WHERE key = "schedule"').fetchone()
            if config:
                times = config['value'].split(',')
                logger.info(f"Loaded schedule from database: {times}")
                return times
            else:
                logger.warning("No schedule found in database, using default schedule")
                return scheduled_times
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        return scheduled_times

def _get_interval_config_internal():
    """Get the interval configuration based on scheduled times
    
    Returns:
        dict: Contains interval_hours and interval_minutes
    """
    try:
        schedule = get_configured_schedule()
        
        # If there are less than 2 times, return a default
        if len(schedule) < 2:
            return {
                'interval_hours': 4,
                'interval_minutes': 0
            }
        
        # Sort the schedule
        sorted_times = sorted(schedule)
        
        # Find the smallest interval between consecutive times
        intervals = []
        for i in range(len(sorted_times) - 1):
            time1 = datetime.datetime.strptime(sorted_times[i], "%H:%M")
            time2 = datetime.datetime.strptime(sorted_times[i+1], "%H:%M")
            diff = time2 - time1
            intervals.append(diff.seconds // 60)  # Convert to minutes
        
        # If we have a full day schedule (24h), also check the interval between last and first
        if len(sorted_times) > 1:
            time1 = datetime.datetime.strptime(sorted_times[-1], "%H:%M")
            time2 = datetime.datetime.strptime(sorted_times[0], "%H:%M")
            # Add 24 hours to the second time if it's earlier
            if time2 < time1:
                time2 = time2 + datetime.timedelta(days=1)
            diff = time2 - time1
            intervals.append(diff.seconds // 60)
        
        # Get the smallest interval (or the first if they're all the same)
        interval_minutes = min(intervals) if intervals else 240  # Default to 4 hours
        
        # Convert to hours and minutes
        interval_hours = interval_minutes // 60
        interval_minutes = interval_minutes % 60
        
        return {
            'interval_hours': interval_hours,
            'interval_minutes': interval_minutes
        }
    except Exception as e:
        logger.error(f"Error calculating interval config: {e}")
        return {
            'interval_hours': 4,
            'interval_minutes': 0
        }

def is_time_to_tweet():
    """Check if it's time to tweet based on the configured schedule"""
    current_time = datetime.datetime.utcnow()
    current_hour_min = current_time.strftime("%H:%M")
    
    # Get the current schedule
    schedule = get_configured_schedule()
    
    # Check if the current time matches any scheduled time
    for scheduled_time in schedule:
        scheduled_time = scheduled_time.strip()
        
        # Allow a 5-minute window for posting (to account for scheduler delays)
        scheduled_dt = datetime.datetime.strptime(scheduled_time, "%H:%M")
        scheduled_hour, scheduled_minute = scheduled_dt.hour, scheduled_dt.minute
        
        current_hour, current_minute = current_time.hour, current_time.minute
        
        # Check if we're within 5 minutes of the scheduled time
        if (current_hour == scheduled_hour and 
            current_minute >= scheduled_minute and 
            current_minute < scheduled_minute + 5):
            
            # Check if we've already tweeted in this window
            try:
                with get_db_connection() as conn:
                    # Look for tweets posted in the last 5 minutes for this scheduled time
                    five_min_ago = (current_time - datetime.timedelta(minutes=5)).isoformat()
                    tweet_check = conn.execute(
                        'SELECT COUNT(*) as count FROM bot_status WHERE timestamp > ? AND message LIKE ?',
                        (five_min_ago, f"Scheduled tweet for {scheduled_time}%")
                    ).fetchone()
                    
                    if tweet_check and tweet_check['count'] > 0:
                        return False  # Already tweeted in this window
                    
                    return scheduled_time
            except Exception as e:
                logger.error(f"Error checking recent tweets: {e}")
    
    return False

def scheduler_loop():
    """Main scheduler loop that runs continuously"""
    global scheduler_running
    
    logger.info("Starting scheduler loop")
    log_status("Running", "Tweet scheduler started")
    
    # Calculate and update the next scheduled run time
    update_next_scheduled_run()
    
    while scheduler_running:
        try:
            # Check if it's time to tweet
            scheduled_time = is_time_to_tweet()
            if scheduled_time:
                logger.info(f"It's time to tweet (scheduled for {scheduled_time})")
                
                # Post the tweet
                success = post_tweet_and_log()
                
                if success:
                    log_status("Running", f"Scheduled tweet for {scheduled_time} posted successfully")
                else:
                    log_status("Error", f"Failed to post scheduled tweet for {scheduled_time}")
                    
                # Update the next scheduled run time after posting
                update_next_scheduled_run()
                
                # Sleep for 5 minutes to avoid duplicate tweets in the same window
                time.sleep(300)
            else:
                # Check every minute
                time.sleep(60)
                
        except Exception as e:
            error_msg = f"Error in scheduler loop: {str(e)}"
            log_status("Error", error_msg)
            logger.error(error_msg)
            
            # Don't crash the loop
            time.sleep(60)

def update_next_scheduled_run():
    """Calculate and update the next scheduled run time in the database"""
    try:
        # Get the current schedule
        schedule = get_configured_schedule()
        
        # Get current time
        current_time = datetime.datetime.utcnow()
        
        # Find the next scheduled time
        next_time = None
        next_datetime = None
        
        # Convert scheduled times to datetime objects for today
        scheduled_times = []
        for time_str in schedule:
            time_str = time_str.strip()
            hour, minute = map(int, time_str.split(':'))
            scheduled_dt = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If this time is in the past, add a day
            if scheduled_dt < current_time:
                scheduled_dt += datetime.timedelta(days=1)
                
            scheduled_times.append((time_str, scheduled_dt))
        
        # Sort by datetime
        scheduled_times.sort(key=lambda x: x[1])
        
        # Get the next scheduled time
        if scheduled_times:
            next_time, next_datetime = scheduled_times[0]
            
            # Update the database with the next scheduled run
            logger.info(f"Next scheduled run: {next_time} ({next_datetime.isoformat()})")
            
            with get_db_connection() as conn:
                # Check if bot_status table has next_scheduled_run column
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(bot_status)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'next_scheduled_run' not in columns:
                    # Add the column if it doesn't exist
                    conn.execute("ALTER TABLE bot_status ADD COLUMN next_scheduled_run TEXT")
                    logger.info("Added next_scheduled_run column to bot_status table")
                
                # Insert a new status record with the next scheduled run
                conn.execute(
                    'INSERT INTO bot_status (timestamp, status, message, next_scheduled_run) VALUES (?, ?, ?, ?)',
                    (current_time.isoformat(), "Scheduled", f"Next tweet scheduled for {next_time}", next_datetime.isoformat())
                )
                conn.commit()
                
            return next_datetime.isoformat()
        else:
            logger.warning("No scheduled times found")
            return None
            
    except Exception as e:
        logger.error(f"Error updating next scheduled run: {e}")
        return None

def start_scheduler():
    """Start the scheduler thread"""
    global scheduler_running, scheduler_thread
    
    if scheduler_running:
        logger.warning("Scheduler already running")
        return False
    
    # Set the running flag
    scheduler_running = True
    
    # Create and start the thread
    scheduler_thread = Thread(target=scheduler_loop)
    scheduler_thread.daemon = True  # Allow the thread to exit when the main program exits
    scheduler_thread.start()
    
    logger.info("Scheduler started")
    
    # Explicitly update the next scheduled run
    # This ensures the admin panel shows it immediately
    next_run = update_next_scheduled_run()
    log_status("Running", f"Bot started, next tweet scheduled for {next_run}")
    
    return True

def stop_scheduler():
    """Stop the scheduler thread"""
    global scheduler_running, scheduler_thread
    
    if not scheduler_running:
        logger.warning("Scheduler not running")
        return False
    
    # Clear the running flag
    scheduler_running = False
    
    # Wait for the thread to exit (with timeout)
    if scheduler_thread:
        scheduler_thread.join(timeout=5.0)
    
    logger.info("Scheduler stopped")
    return True

def update_schedule(new_schedule):
    """Update the schedule in the database"""
    try:
        with get_db_connection() as conn:
            # Check if the table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduler_config'")
            if not cursor.fetchone():
                # Create the table
                conn.execute('''
                CREATE TABLE IF NOT EXISTS scheduler_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                ''')
                
            # Update the schedule
            schedule_str = ','.join(new_schedule)
            conn.execute(
                'INSERT OR REPLACE INTO scheduler_config (key, value) VALUES (?, ?)',
                ('schedule', schedule_str)
            )
            conn.commit()
            
        logger.info(f"Schedule updated: {new_schedule}")
        return True
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        return False

def _update_config_internal(interval_minutes=None):
    """Update the scheduler configuration based on interval minutes
    
    Args:
        interval_minutes: Minutes between each scheduled post
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        if not interval_minutes or interval_minutes < 5:
            logger.error(f"Invalid interval minutes: {interval_minutes}")
            return False
            
        # Generate a new schedule based on the interval
        # Start from midnight UTC and add intervals
        new_schedule = []
        minutes_in_day = 24 * 60
        current_minutes = 0
        
        while current_minutes < minutes_in_day:
            # Convert minutes to HH:MM format
            hours = current_minutes // 60
            minutes = current_minutes % 60
            time_str = f"{hours:02d}:{minutes:02d}"
            new_schedule.append(time_str)
            
            # Add the interval
            current_minutes += interval_minutes
        
        # Update the schedule in the database
        logger.info(f"Updating schedule with interval of {interval_minutes} minutes")
        success = update_schedule(new_schedule)
        
        # Update the next scheduled run time
        if success:
            update_next_scheduled_run()
            
        return success
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return False

# Module-level function to update configuration
# This is used by app.py directly
def update_config(interval_minutes=None):
    """Update the scheduler configuration with given interval minutes"""
    return _update_config_internal(interval_minutes)

# Module-level function to get interval configuration
def get_interval_config():
    """Get the interval configuration for the scheduler"""
    # This is a module-level wrapper around the internal function
    return _get_interval_config_internal()

# Module-level function to start the scheduler
# This is used by app.py directly
def start():
    """Start the scheduler"""
    return start_scheduler()

# Module-level function to stop the scheduler
# This is used by app.py directly
def stop():
    """Stop the scheduler"""
    return stop_scheduler()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "start":
            if start_scheduler():
                print("Scheduler started")
                
                # Keep running
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("Stopping scheduler...")
                    stop_scheduler()
                    
            else:
                print("Failed to start scheduler")
                
        elif command == "stop":
            if stop_scheduler():
                print("Scheduler stopped")
            else:
                print("Failed to stop scheduler")
                
        elif command == "status":
            if scheduler_running:
                print("Scheduler is running")
            else:
                print("Scheduler is not running")
                
        elif command == "tweet":
            # Post a tweet immediately
            if post_tweet_and_log():
                print("Tweet posted successfully")
            else:
                print("Failed to post tweet")
                
        else:
            print(f"Unknown command: {command}")
            print("Usage: python scheduler.py [start|stop|status|tweet]")
    else:
        print("Usage: python scheduler.py [start|stop|status|tweet]") 