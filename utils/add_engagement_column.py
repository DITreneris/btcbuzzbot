import os
import sys
import logging
import asyncio

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.database import Database # For _get_postgres_connection
    import psycopg2 # Explicitly for ALTER TABLE
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print("Ensure you are running this script from the 'utils' directory or have the project root in PYTHONPATH.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def add_engagement_column_to_posts():
    load_dotenv() # Load environment variables, including DATABASE_URL
    
    db_manager = None
    conn = None
    
    try:
        # We need the Database class instance to use its _get_postgres_connection method
        # which correctly parses the DATABASE_URL.
        # The db_path argument is for SQLite, can be default for this usage.
        db_manager = Database(db_path="dummy.db") 

        if not db_manager.is_postgres:
            logger.info("This script is intended for PostgreSQL databases. No action taken for SQLite.")
            return

        logger.info("Attempting to connect to PostgreSQL database...")
        conn = db_manager._get_postgres_connection()
        cursor = conn.cursor()
        
        logger.info("Attempting to add 'engagement_last_checked' column to 'posts' table if it doesn't exist...")
        
        # Check if the column already exists to make the script idempotent
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'  -- Or your specific schema if not public
            AND table_name = 'posts'
            AND column_name = 'engagement_last_checked';
        """)
        
        if cursor.fetchone():
            logger.info("'engagement_last_checked' column already exists in 'posts' table.")
        else:
            alter_table_sql = """
            ALTER TABLE posts
            ADD COLUMN engagement_last_checked TIMESTAMP WITH TIME ZONE DEFAULT NULL;
            """
            cursor.execute(alter_table_sql)
            conn.commit()
            logger.info("Successfully added 'engagement_last_checked' column to 'posts' table.")
            
    except psycopg2.Error as db_err:
        logger.error(f"Database error occurred: {db_err}", exc_info=True)
        if conn:
            conn.rollback() # Rollback any partial changes
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(add_engagement_column_to_posts()) 