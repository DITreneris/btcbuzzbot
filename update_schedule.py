import os
import asyncio
import sys

# Ensure src is in the path to import Database
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database import Database # Assumes database.py is in src
from dotenv import load_dotenv

async def update_live_schedule(new_schedule_str: str):
    """Connects to DB and updates the schedule config."""
    print(f"Attempting to update schedule to: {new_schedule_str}")
    load_dotenv() # Load environment variables (like DATABASE_URL)
    db = None
    try:
        db = Database() # Database init connects and checks tables
        await db.update_scheduler_config(new_schedule_str)
        print("Schedule updated successfully in the database.")
        print("The scheduler worker should pick up the change on its next reschedule cycle (within 30 mins).")
    except Exception as e:
        print(f"Error updating schedule: {e}", file=sys.stderr)
    finally:
        if db and hasattr(db, 'close'):
             # Check if close is async or sync based on Database implementation
             # Assuming sync close based on original code structure
             # await db.close() # Use await if close() is async
             pass # Original DB class didn't seem to have an async close

if __name__ == "__main__":
    # Define the new schedule here
    # Format: HH:MM comma-separated, no spaces
    NEW_SCHEDULE = "06:00,08:00,12:00,16:00,20:00,22:00"
    
    if len(sys.argv) > 1:
        NEW_SCHEDULE = sys.argv[1]
        print(f"Using schedule from command line argument: {NEW_SCHEDULE}")
    
    asyncio.run(update_live_schedule(NEW_SCHEDULE)) 