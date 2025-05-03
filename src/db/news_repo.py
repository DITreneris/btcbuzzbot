"""
Repository for managing news tweet data.
"""
import logging
import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import json

# Setup logger
logger = logging.getLogger(__name__)

# Add DB driver imports with error handling (copied from database.py)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

class NewsRepository:
    def __init__(self, db_path: str = "btcbuzzbot.db"):
        """Initialize repository - copies connection logic from original Database class."""
        self.db_path = db_path

        # Heroku provides DATABASE_URL, check for PostgreSQL
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)

        self.db_url = db_url
        self.is_postgres = self.db_url is not None and PSYCOPG2_AVAILABLE

        if not self.is_postgres and not AIOSQLITE_AVAILABLE:
             raise RuntimeError("Database configuration error: Neither PostgreSQL (psycopg2) nor SQLite (aiosqlite) drivers are available.")

        logger.info(f"NewsRepository initialized. Using {'PostgreSQL' if self.is_postgres else 'SQLite'}.")

    # Copy of PostgreSQL connection helper from original Database class
    def _get_postgres_connection(self):
        """Get PostgreSQL connection (sync)."""
        if not self.is_postgres:
            raise ValueError("PostgreSQL is not configured or driver not available.")

        try:
            conn = psycopg2.connect(self.db_url)
            return conn
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL via NewsRepository: {e}", exc_info=True)
            # Attempt parsing URL components as fallback (copied logic)
            try:
                result = urlparse(self.db_url)
                user = result.username
                password = result.password
                database = result.path[1:]
                hostname = result.hostname
                port = result.port
                conn = psycopg2.connect(database=database, user=user, password=password, host=hostname, port=port)
                return conn
            except Exception as conn_error:
                 logger.error(f"Fallback PostgreSQL connection attempt failed: {conn_error}")
                 raise # Re-raise the final connection error

    # --- Methods related to News Tweets --- 

    async def store_news_tweet(self, tweet_data: Dict[str, Any]) -> Optional[int]:
        """Store a fetched tweet into the news_tweets table, ignoring duplicates."""
        required_fields = ['original_tweet_id', 'author_id', 'text', 'published_at', 'fetched_at', 'metrics', 'source']
        if not all(field in tweet_data for field in required_fields):
            missing = [field for field in required_fields if field not in tweet_data]
            logger.error(f"Error storing news tweet: Missing required fields {missing} in {tweet_data.keys()}", file=sys.stderr)
            return None

        # Extract data, handling potential Nones for non-required fields
        original_tweet_id = tweet_data['original_tweet_id']
        author_id = tweet_data['author_id']
        text = tweet_data['text']
        published_at = tweet_data['published_at']
        fetched_at = tweet_data['fetched_at']
        metrics = tweet_data.get('metrics') # JSONB
        source = tweet_data.get('source')

        # Fields to be populated by analysis later (default to NULL/False)
        processed = False
        sentiment_score = None
        sentiment_label = None
        keywords = None
        summary = None
        llm_analysis = None # JSONB

        try:
            if self.is_postgres:
                sql = """
                INSERT INTO news_tweets 
                (original_tweet_id, author_id, text, published_at, fetched_at, metrics, source, 
                 processed, sentiment_score, sentiment_label, keywords, summary, llm_analysis)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (original_tweet_id) DO NOTHING
                RETURNING id;
                """
                # Convert metrics and llm_analysis to JSON strings if they are dicts
                metrics_db = json.dumps(metrics) if metrics is not None else None
                llm_analysis_db = json.dumps(llm_analysis) if llm_analysis is not None else None
                params = (
                    original_tweet_id, author_id, text, published_at, fetched_at, metrics_db, source,
                    processed, sentiment_score, sentiment_label, keywords, summary, llm_analysis_db
                )
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(sql, params)
                result = cursor.fetchone() # Will be None if conflict occurred
                conn.commit()
                cursor.close()
                conn.close()
                return result[0] if result else None
            else:
                # Use INSERT OR IGNORE for SQLite
                sql = """
                INSERT OR IGNORE INTO news_tweets
                (original_tweet_id, author_id, text, published_at, fetched_at, metrics, source,
                 processed, sentiment_score, sentiment_label, keywords, summary, llm_analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                # Convert metrics and llm_analysis to JSON strings if they are dicts for SQLite TEXT columns
                metrics_db = json.dumps(metrics) if metrics is not None else None
                llm_analysis_db = json.dumps(llm_analysis) if llm_analysis is not None else None
                params = (
                    original_tweet_id, author_id, text, published_at, fetched_at, metrics_db, source,
                    processed, sentiment_score, sentiment_label, keywords, summary, llm_analysis_db
                )
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(sql, params)
                    await db.commit()
                    # Return lastrowid only if a row was inserted (changes > 0)
                    return cursor.lastrowid if db.total_changes > 0 else None
        except Exception as e:
            logger.error(f"Error storing news tweet (ID: {original_tweet_id}): {e}", exc_info=True)
            return None

    async def get_last_fetched_tweet_id(self) -> Optional[str]:
        """Retrieve the highest original_tweet_id stored in the news_tweets table."""
        sql = "SELECT MAX(original_tweet_id) FROM news_tweets;"
        last_id = None
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor() 
                cursor.execute(sql)
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                if result and result[0] is not None:
                    last_id = str(result[0])
                    # logger.info(f"[Postgres] Found last fetched tweet ID: {last_id}") # Reduced verbosity
                # else:
                    # logger.info("[Postgres] No existing tweets found.")
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute(sql) as cursor:
                        result = await cursor.fetchone()
                        if result and result[0] is not None:
                            last_id = str(result[0])
                            # logger.info(f"[SQLite] Found last fetched tweet ID: {last_id}") # Reduced verbosity
                        # else:
                             # logger.info("[SQLite] No existing tweets found.")
            return last_id
        except Exception as e:
            logger.error(f"Error getting last fetched tweet ID: {e}", exc_info=True)
            return None # Return None on error

    async def get_recent_analyzed_news(self, hours_limit: int = 12) -> List[Dict[str, Any]]:
        """Get recently analyzed news tweets (processed=True)."""
        tweets = []
        try:
            if self.is_postgres:
                sql = """
                SELECT original_tweet_id, llm_analysis 
                FROM news_tweets 
                WHERE processed = TRUE 
                AND fetched_at::timestamptz >= NOW() - INTERVAL '%s hours'
                ORDER BY fetched_at DESC;
                """
                conn = self._get_postgres_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(sql, (hours_limit,))
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                tweets = [dict(row) for row in rows]
            else:
                sql = """
                SELECT original_tweet_id, llm_analysis 
                FROM news_tweets 
                WHERE processed = 1 
                AND datetime(fetched_at) >= datetime('now', ? || ' hours')
                ORDER BY fetched_at DESC;
                """
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(sql, (f"-{hours_limit}",)) as cursor:
                        rows = await cursor.fetchall()
                        tweets = [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching recent analyzed news: {e}", exc_info=True)
            # Return empty list on error, let caller handle
        return tweets

    async def get_unprocessed_news_tweets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tweets that haven't been analyzed (processed=False)."""
        tweets = []
        try:
            if self.is_postgres:
                sql = """
                SELECT * FROM news_tweets 
                WHERE processed = FALSE OR processed IS NULL 
                ORDER BY fetched_at DESC -- Process newer tweets first? Or oldest?
                LIMIT %s;
                """
                conn = self._get_postgres_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(sql, (limit,))
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                tweets = [dict(row) for row in rows]
            else:
                # Fetch where processed = 0 (SQLite boolean)
                sql = """
                SELECT * FROM news_tweets 
                WHERE processed = 0 OR processed IS NULL 
                ORDER BY fetched_at DESC 
                LIMIT ?;
                """
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(sql, (limit,)) as cursor:
                        rows = await cursor.fetchall()
                        tweets = [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching unprocessed news tweets: {e}", exc_info=True)
            # Return empty list on error, let caller handle
        return tweets

    async def update_tweet_analysis(
        self,
        original_tweet_id: str,
        status: str, # Add status parameter ('analyzed', 'analysis_failed', 'analysis_timeout')
        analysis_data: Optional[Dict[str, Any]] = None, # Renamed llm_analysis for clarity
        error_message: Optional[str] = None # Optionally store error details
    ):
        """Update analysis fields and processing status based on provided status."""
        if not original_tweet_id:
            logger.warning("Attempted to update analysis with missing original_tweet_id.")
            return False

        update_fields = []
        params = []

        # Set llm_analysis field only if status is 'analyzed' and data is present
        if status == "analyzed" and analysis_data is not None:
            update_fields.append("llm_analysis = %s" if self.is_postgres else "llm_analysis = ?")
            params.append(json.dumps(analysis_data))
            update_fields.append("processed = TRUE" if self.is_postgres else "processed = 1")
        elif status in ["analysis_failed", "analysis_timeout"]:
            # Mark as processed=TRUE even on failure/timeout to avoid reprocessing
            update_fields.append("processed = TRUE" if self.is_postgres else "processed = 1")
            # Optionally store an error or status marker if schema allows
            # For now, just setting processed=TRUE
            # If error_message and a column exists:
            # update_fields.append("error_info = %s" if self.is_postgres else "error_info = ?")
            # params.append(error_message)
            logger.info(f"Marking tweet {original_tweet_id} as processed with status: {status}")
        else:
             logger.warning(f"Invalid status '{status}' provided for tweet {original_tweet_id}. Not updating.")
             return False # Invalid status

        # Always mark as processed and update timestamp
        # update_fields.append("processed = TRUE" if self.is_postgres else "processed = 1")
        # --- End removal ---

        if not update_fields:
            # This case should ideally not be reached with the new logic
            logger.warning(f"No fields to update for tweet {original_tweet_id} with status {status}.")
            return False

        params.append(original_tweet_id) # Add the ID for the WHERE clause

        sql_query = f"""
            UPDATE news_tweets 
            SET {', '.join(update_fields)}
            WHERE original_tweet_id = %s
            """ if self.is_postgres else f"""
            UPDATE news_tweets 
            SET {', '.join(update_fields)}
            WHERE original_tweet_id = ?
            """

        try:
            rows_affected = 0
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(sql_query, tuple(params))
                rows_affected = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(sql_query, tuple(params))
                    await db.commit()
                    rows_affected = cursor.rowcount
            
            if rows_affected > 0:
                logger.debug(f"Successfully updated status for tweet {original_tweet_id} to {status}.")
                return True
            else:
                logger.warning(f"No tweet found with original_tweet_id {original_tweet_id} to update status.")
                return False
        except Exception as e:
            logger.error(f"Error updating analysis status for tweet {original_tweet_id}: {e}", exc_info=True)
            return False

    # Add other news-related methods if necessary, e.g., getting analyzed tweets for display 