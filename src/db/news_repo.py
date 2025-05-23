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
        """Get recently analyzed news tweets, ordered by significance and recency."""
        tweets = []
        try:
            if self.is_postgres:
                sql = """
                SELECT original_tweet_id, text, summary, significance_label, significance_score, 
                       sentiment_label, sentiment_score, sentiment_source, llm_raw_analysis, published_at
                FROM news_tweets 
                WHERE processed = TRUE 
                  AND significance_score IS NOT NULL 
                  AND published_at::timestamp >= NOW() - INTERVAL '%s hours'
                ORDER BY significance_score DESC, published_at DESC;
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
                SELECT original_tweet_id, text, summary, significance_label, significance_score, 
                       sentiment_label, sentiment_score, sentiment_source, llm_raw_analysis, published_at
                FROM news_tweets 
                WHERE processed = 1 
                  AND significance_score IS NOT NULL 
                  AND datetime(published_at) >= datetime('now', ? || ' hours')
                ORDER BY significance_score DESC, published_at DESC;
                """
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row # Ensure results are dict-like
                    async with db.execute(sql, (f"-{hours_limit}",)) as cursor:
                        rows = await cursor.fetchall()
                        tweets = [dict(row) for row in rows] # Convert rows to dicts
        except Exception as e:
            logger.error(f"Error fetching recent analyzed news: {e}", exc_info=True)
        return tweets

    async def get_unprocessed_news_tweets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tweets that haven't been analyzed (processed=False)."""
        tweets = []
        try:
            if self.is_postgres:
                # Log count of tweets with processed = FALSE OR processed IS NULL
                count_sql_unprocessed = "SELECT COUNT(*) FROM news_tweets WHERE processed = FALSE OR processed IS NULL;"
                # Log count of tweets with processed = TRUE AND llm_analysis IS NULL
                count_sql_processed_null_analysis = "SELECT COUNT(*) FROM news_tweets WHERE processed = TRUE AND (llm_analysis IS NULL OR llm_analysis = 'null');"
                
                conn_count = self._get_postgres_connection()
                cursor_count = conn_count.cursor()
                
                cursor_count.execute(count_sql_unprocessed)
                unprocessed_count = cursor_count.fetchone()[0]
                logger.info(f"[DB LOG] Found {unprocessed_count} tweets marked as processed = FALSE or IS NULL.")

                cursor_count.execute(count_sql_processed_null_analysis)
                processed_null_analysis_count = cursor_count.fetchone()[0]
                logger.info(f"[DB LOG] Found {processed_null_analysis_count} tweets marked as processed = TRUE but llm_analysis IS NULL or 'null'.")
                
                cursor_count.close()
                conn_count.close()

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
            else: # SQLite
                # Log count of tweets with processed = 0 OR processed IS NULL
                count_sql_unprocessed = "SELECT COUNT(*) FROM news_tweets WHERE processed = 0 OR processed IS NULL;"
                # Log count of tweets with processed = 1 AND llm_analysis IS NULL
                count_sql_processed_null_analysis = "SELECT COUNT(*) FROM news_tweets WHERE processed = 1 AND (llm_analysis IS NULL OR llm_analysis = 'null');"

                async with aiosqlite.connect(self.db_path) as db_count:
                    async with db_count.execute(count_sql_unprocessed) as cursor_c_u:
                        result_unprocessed = await cursor_c_u.fetchone()
                        unprocessed_count = result_unprocessed[0] if result_unprocessed else 0
                        logger.info(f"[DB LOG] Found {unprocessed_count} tweets marked as processed = 0 or IS NULL (SQLite).")

                    async with db_count.execute(count_sql_processed_null_analysis) as cursor_c_pna:
                        result_processed_null = await cursor_c_pna.fetchone()
                        processed_null_analysis_count = result_processed_null[0] if result_processed_null else 0
                        logger.info(f"[DB LOG] Found {processed_null_analysis_count} tweets marked as processed = 1 but llm_analysis IS NULL or 'null' (SQLite).")

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
        status: str, 
        analysis_data: Optional[Dict[str, Any]] = None, 
        error_message: Optional[str] = None 
    ):
        """Update analysis fields and processing status based on provided status."""
        if not original_tweet_id:
            logger.warning("Attempted to update analysis with missing original_tweet_id.")
            return False

        update_fields_set = []
        params_list = []

        processed_val = True # Mark as processed for all handled statuses

        if status == "analyzed" and analysis_data:
            update_fields_set.append("processed = %s" if self.is_postgres else "processed = ?")
            params_list.append(processed_val)

            # Store raw LLM analysis (if primarily from Groq and available)
            # analysis_data itself is the dict from _analyze_content_with_llm
            update_fields_set.append("llm_analysis = %s" if self.is_postgres else "llm_analysis = ?")
            params_list.append(json.dumps(analysis_data))

            sentiment_label = analysis_data.get("sentiment")
            significance_label = analysis_data.get("significance")
            summary_text = analysis_data.get("summary")
            sentiment_src = analysis_data.get("sentiment_source", "unknown")

            update_fields_set.append("sentiment_label = %s" if self.is_postgres else "sentiment_label = ?")
            params_list.append(sentiment_label)
            update_fields_set.append("significance_label = %s" if self.is_postgres else "significance_label = ?")
            params_list.append(significance_label)
            update_fields_set.append("summary = %s" if self.is_postgres else "summary = ?")
            params_list.append(summary_text)
            update_fields_set.append("sentiment_source = %s" if self.is_postgres else "sentiment_source = ?")
            params_list.append(sentiment_src)

            # Map sentiment label to score
            sentiment_score_val = None
            if sentiment_label == "Positive":
                sentiment_score_val = 0.7
            elif sentiment_label == "Negative":
                sentiment_score_val = -0.7
            elif sentiment_label == "Neutral":
                sentiment_score_val = 0.0
            update_fields_set.append("sentiment_score = %s" if self.is_postgres else "sentiment_score = ?")
            params_list.append(sentiment_score_val)

            # Map significance label to score
            significance_score_val = None
            if significance_label == "High":
                significance_score_val = 1.0
            elif significance_label == "Medium":
                significance_score_val = 0.5
            elif significance_label == "Low":
                significance_score_val = 0.1
            update_fields_set.append("significance_score = %s" if self.is_postgres else "significance_score = ?")
            params_list.append(significance_score_val)

        elif status in ["analysis_failed", "analysis_timeout"]:
            update_fields_set.append("processed = %s" if self.is_postgres else "processed = ?")
            params_list.append(processed_val)
            # Set sentiment_source to reflect failure type if not already set by Groq/VADER path
            # The _analyze_content_with_llm should set a source even on failure, but this is a safety net.
            current_sentiment_source = analysis_data.get("sentiment_source") if analysis_data else status
            if error_message and not analysis_data: # If analysis_data is None, means a higher level failure before _analyze_content_with_llm
                 current_sentiment_source = status # e.g. analysis_failed from a higher level

            update_fields_set.append("sentiment_source = %s" if self.is_postgres else "sentiment_source = ?")
            params_list.append(current_sentiment_source) 
            logger.info(f"Marking tweet {original_tweet_id} as processed with status: {status}, source: {current_sentiment_source}")
            # Other analysis fields will remain NULL or their defaults
        else:
             logger.warning(f"Invalid status '{status}' provided for tweet {original_tweet_id}. Not updating.")
             return False

        if not update_fields_set:
            logger.warning(f"No fields to update for tweet {original_tweet_id} with status {status}. This might indicate an issue.")
            return False

        params_list.append(original_tweet_id) 

        sql_query = f"""
            UPDATE news_tweets 
            SET {', '.join(update_fields_set)}
            WHERE original_tweet_id = %s
            """ if self.is_postgres else f"""
            UPDATE news_tweets 
            SET {', '.join(update_fields_set)}
            WHERE original_tweet_id = ?
            """

        try:
            rows_affected = 0
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(sql_query, tuple(params_list))
                rows_affected = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(sql_query, tuple(params_list))
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