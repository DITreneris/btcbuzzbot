# update_live_schedule.py
import asyncio
import logging
import os
import sys

# Ensure src directory is in path if running from root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir) # Assumes script is in root, adjust if moved
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the Database class
try:
    from src.database import Database
    DATABASE_CLASS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Database from src.database: {e}", file=sys.stderr)
    DATABASE_CLASS_AVAILABLE = False
    sys.exit(1)

# --- Configuration ---
# Define the NEW schedule string here
NEW_SCHEDULE = "06:00,08:00,10:00,12:00,14:00,16:00,18:00,20:00,22:00"
# --- End Configuration ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Connects to the database and updates the schedule config."""
    if not DATABASE_CLASS_AVAILABLE:
        logger.error("Database class not available. Exiting.")
        return

    logger.info("Initializing Database connection...")
    # Database class reads DATABASE_URL from environment automatically
    db = None
    try:
        # Initialize using the environment variable DATABASE_URL implicitly
        db = Database() 
        
        logger.info(f"Attempting to update schedule config in database to: '{NEW_SCHEDULE}'")
        await db.update_scheduler_config(NEW_SCHEDULE)
        logger.info("Successfully called update_scheduler_config.")
        
        # Optional: Verify by fetching the config back
        updated_schedule = await db.get_scheduler_config()
        if updated_schedule == NEW_SCHEDULE:
            logger.info(f"Verification successful: Schedule in DB is now '{updated_schedule}'")
        else:
            logger.warning(f"Verification mismatch: Schedule in DB is '{updated_schedule}', expected '{NEW_SCHEDULE}'")
            
    except Exception as e:
        logger.error(f"An error occurred during schedule update: {e}", exc_info=True)
    finally:
        # The current Database class manages connections per-operation, 
        # so an explicit close might not be needed here unless changed later.
        # if db and hasattr(db, 'close'):
        #     await db.close()
        #     logger.info("Database connection closed.")
        pass

if __name__ == "__main__":
    # Load .env variables if running locally and needed for DATABASE_URL
    # from dotenv import load_dotenv
    # load_dotenv() 
    
    # Check if DATABASE_URL is set (important for Heroku run or local testing)
    if not os.environ.get('DATABASE_URL'):
         logger.warning("DATABASE_URL environment variable not found. Script might fail if not targeting Heroku PostgreSQL.")
         # Optionally exit if local run requires it explicitly
         # sys.exit("DATABASE_URL not set. Exiting.")

    logger.info("Starting schedule update script...")
    asyncio.run(main())
    logger.info("Schedule update script finished.")