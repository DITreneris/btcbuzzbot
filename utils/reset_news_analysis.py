import asyncio
import os
import sys
import logging

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.db.news_repo import NewsRepository
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print("Ensure you are running this script from the 'utils' directory or have the project root in PYTHONPATH.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def reset_news_analysis_flags(tweet_ids: list = None, reset_all: bool = False):
    """
    Resets the 'processed' flag to FALSE and clears analysis fields 
    for specified news_tweets or all of them.

    Args:
        tweet_ids (list, optional): A list of original_tweet_id strings to reset. 
                                    If None and reset_all is False, no action is taken.
        reset_all (bool, optional): If True, resets all news_tweets. Defaults to False.
    """
    load_dotenv(os.path.join(project_root, '.env')) # Load .env from project root

    news_repo = NewsRepository() # Initializes with DB connection based on .env
    
    if not news_repo.is_postgres and not news_repo.db_path: # Basic check
        logger.error("NewsRepository could not determine database configuration. Check .env and DB setup.")
        return

    updated_count = 0
    skipped_count = 0

    base_sql_update = """
        UPDATE news_tweets 
        SET processed = %s, 
            llm_analysis = NULL, 
            sentiment_score = NULL,
            sentiment_label = NULL,
            significance_score = NULL,
            significance_label = NULL,
            summary = NULL,
            sentiment_source = NULL
    """
    
    params_processed_val = False # For both Postgres and SQLite

    if reset_all:
        logger.info("Resetting analysis flags for ALL news tweets.")
        sql_query = base_sql_update
        params = (params_processed_val,)
        
        try:
            if news_repo.is_postgres:
                conn = news_repo._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(sql_query, params)
                updated_count = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
            else: # SQLite
                sql_query_sqlite = base_sql_update.replace("%s", "?")
                async with aiosqlite.connect(news_repo.db_path) as db:
                    cursor = await db.execute(sql_query_sqlite, params)
                    await db.commit()
                    updated_count = cursor.rowcount
            logger.info(f"Successfully reset {updated_count} tweets.")
        except Exception as e:
            logger.error(f"Error resetting all tweets: {e}", exc_info=True)

    elif tweet_ids and isinstance(tweet_ids, list):
        logger.info(f"Resetting analysis flags for {len(tweet_ids)} specific tweets.")
        sql_query_with_where = base_sql_update + " WHERE original_tweet_id = %s"
        
        if news_repo.is_postgres:
            conn = news_repo._get_postgres_connection()
            cursor = conn.cursor()
            for tweet_id in tweet_ids:
                try:
                    cursor.execute(sql_query_with_where, (params_processed_val, tweet_id))
                    if cursor.rowcount > 0:
                        updated_count += 1
                    else:
                        skipped_count +=1
                except Exception as e:
                    logger.error(f"Error resetting tweet ID {tweet_id}: {e}")
                    skipped_count += 1
            conn.commit()
            cursor.close()
            conn.close()
        else: # SQLite
            sql_query_sqlite_where = base_sql_update.replace("%s", "?") + " WHERE original_tweet_id = ?"
            async with aiosqlite.connect(news_repo.db_path) as db:
                for tweet_id in tweet_ids:
                    try:
                        cursor = await db.execute(sql_query_sqlite_where, (params_processed_val, tweet_id))
                        if cursor.rowcount > 0:
                            updated_count += 1
                        else:
                            skipped_count += 1
                    except Exception as e:
                        logger.error(f"Error resetting tweet ID {tweet_id} (SQLite): {e}")
                        skipped_count +=1
                await db.commit()
        logger.info(f"Finished. Reset: {updated_count}, Skipped/Not Found: {skipped_count}")
    else:
        logger.info("No tweet IDs provided and reset_all is False. No action taken.")

if __name__ == "__main__":
    # Example Usage:
    # To reset all tweets:
    # asyncio.run(reset_news_analysis_flags(reset_all=True))

    # To reset specific tweets:
    # specific_ids = ["12345", "67890"] # Replace with actual original_tweet_ids
    # asyncio.run(reset_news_analysis_flags(tweet_ids=specific_ids))

    # If no arguments, it will do nothing by default.
    # For command-line execution, you might want to parse arguments.
    
    # Simple command line argument parsing
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            asyncio.run(reset_news_analysis_flags(reset_all=True))
        elif sys.argv[1] == "--ids":
            if len(sys.argv) > 2:
                ids_to_reset = sys.argv[2].split(',')
                asyncio.run(reset_news_analysis_flags(tweet_ids=ids_to_reset))
            else:
                print("Usage: python utils/reset_news_analysis.py --ids <id1,id2,id3>")
        else:
            print("Invalid argument. Use --all or --ids <id1,id2,...>")
    else:
        print("No arguments provided. Use --all to reset all tweets or --ids <id1,id2,...> for specific ones.")
        print("Example: python utils/reset_news_analysis.py --all") 