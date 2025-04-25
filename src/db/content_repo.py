"""
Repository for managing static content like quotes and jokes.
"""
import logging
import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

# Setup logger
logger = logging.getLogger(__name__)

# Add DB driver imports with error handling
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

# Default configuration value from original Database class
DEFAULT_CONTENT_REUSE_DAYS = 7

class ContentRepository:
    def __init__(self, db_path: str = "btcbuzzbot.db"):
        """Initialize repository - copies connection logic from original Database class."""
        self.db_path = db_path
        self.connection = None # Keep for potential future use?

        # Heroku provides DATABASE_URL, check for PostgreSQL
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)

        self.db_url = db_url
        self.is_postgres = self.db_url is not None and PSYCOPG2_AVAILABLE

        if not self.is_postgres and not AIOSQLITE_AVAILABLE:
             raise RuntimeError("Database configuration error: Neither PostgreSQL (psycopg2) nor SQLite (aiosqlite) drivers are available.")

        logger.info(f"ContentRepository initialized. Using {'PostgreSQL' if self.is_postgres else 'SQLite'}.")

    # Copy of PostgreSQL connection helper from original Database class
    def _get_postgres_connection(self):
        """Get PostgreSQL connection (sync)."""
        if not self.is_postgres:
            raise ValueError("PostgreSQL is not configured or driver not available.")

        try:
            conn = psycopg2.connect(self.db_url)
            return conn
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL via ContentRepository: {e}", exc_info=True)
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

    # --- Methods related to Quotes and Jokes --- 

    async def get_random_content(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get random content from either quotes or jokes table"""
        reuse_days = int(os.environ.get('CONTENT_REUSE_DAYS', DEFAULT_CONTENT_REUSE_DAYS))
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                sql_query = f"""
                    SELECT * FROM {collection_name} 
                    WHERE last_used IS NULL 
                    OR last_used < NOW() - INTERVAL '%s days'
                    ORDER BY used_count ASC
                    LIMIT 10
                    """
                cursor.execute(sql_query, (reuse_days,))
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute(f"SELECT * FROM {collection_name} ORDER BY RANDOM() LIMIT 1")
                    rows = cursor.fetchall()
                if rows:
                    import random
                    selected = dict(rows[random.randint(0, len(rows) - 1)])
                    cursor.execute(
                        f"UPDATE {collection_name} SET used_count = used_count + 1, last_used = NOW() WHERE id = %s",
                        (selected["id"],)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return selected
                cursor.close()
                conn.close()
                return None
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    sql_query = f"""
                        SELECT * FROM {collection_name} 
                        WHERE last_used IS NULL 
                        OR datetime(last_used) < datetime('now', ? || ' days')
                        ORDER BY used_count ASC
                        LIMIT 10
                        """
                    async with db.execute(sql_query, (f"-{reuse_days}",)) as cursor:
                        rows = await cursor.fetchall()
                        if not rows:
                            async with db.execute(f"SELECT * FROM {collection_name} ORDER BY RANDOM() LIMIT 1") as random_cursor:
                                rows = await random_cursor.fetchall()
                        if rows:
                            import random
                            selected = dict(rows[random.randint(0, len(rows) - 1)])
                            await db.execute(
                                f"UPDATE {collection_name} SET used_count = used_count + 1, last_used = datetime('now') WHERE id = ?",
                                (selected["id"],)
                            )
                            await db.commit()
                            return selected
                        return None
        except Exception as e:
            logger.error(f"Error getting random content from {collection_name}: {e}", exc_info=True)
            return None

    async def add_quote(self, text: str, category: str = "motivational") -> Optional[int]:
        """Add a new quote to the database"""
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO quotes (text, category, created_at, used_count) VALUES (%s, %s, NOW(), %s) RETURNING id",
                    (text, category, 0)
                )
                lastrowid = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                conn.close()
                logger.info(f"Added quote ID: {lastrowid}")
                return lastrowid
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "INSERT INTO quotes (text, category, created_at, used_count) VALUES (?, ?, datetime('now'), ?)",
                        (text, category, 0)
                    )
                    await db.commit()
                    logger.info(f"Added quote ID: {cursor.lastrowid}")
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding quote: {e}", exc_info=True)
            return None # Return None on error
         
    async def get_all_quotes(self) -> List[Dict]:
        """Retrieve all quotes from the database."""
        sql = "SELECT id, text, category, created_at, used_count, last_used FROM quotes ORDER BY id"
        quotes = []
        try:
            if self.is_postgres:
                 conn = self._get_postgres_connection()
                 cursor = conn.cursor(cursor_factory=RealDictCursor)
                 cursor.execute(sql)
                 rows = cursor.fetchall()
                 cursor.close()
                 conn.close()
                 if rows:
                    quotes = [dict(row) for row in rows]
                    logger.info(f"[Postgres] Retrieved {len(quotes)} quotes.")
                 else:
                    logger.info("[Postgres] No quotes found.")
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row # Use Row factory for dict-like access
                    async with db.execute(sql) as cursor:
                        rows = await cursor.fetchall()
                        if rows:
                            quotes = [dict(row) for row in rows]
                            logger.info(f"[SQLite] Retrieved {len(quotes)} quotes.")
                        else:
                            logger.info("[SQLite] No quotes found.")
        except Exception as e:
            logger.error(f"Error getting all quotes: {e}", exc_info=True)
        return quotes

    async def delete_quote(self, quote_id: int) -> bool:
        """Delete a quote by its ID."""
        sql = "DELETE FROM quotes WHERE id = %s" if self.is_postgres else "DELETE FROM quotes WHERE id = ?"
        deleted = False
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(sql, (quote_id,))
                deleted_count = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
                if deleted_count > 0:
                    logger.info(f"[Postgres] Deleted quote ID: {quote_id}")
                    deleted = True
                else:
                    logger.warning(f"[Postgres] No quote found with ID: {quote_id} to delete.")
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(sql, (quote_id,))
                    await db.commit()
                    if cursor.rowcount > 0:
                        logger.info(f"[SQLite] Deleted quote ID: {quote_id}")
                        deleted = True
                    else:
                        logger.warning(f"[SQLite] No quote found with ID: {quote_id} to delete.")
        except Exception as e:
            logger.error(f"Error deleting quote ID {quote_id}: {e}", exc_info=True)
        return deleted

    async def add_joke(self, text: str, category: str = "humor") -> Optional[int]:
        """Add a new joke to the database"""
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO jokes (text, category, created_at, used_count) VALUES (%s, %s, NOW(), %s) RETURNING id",
                    (text, category, 0)
                )
                lastrowid = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                conn.close()
                logger.info(f"Added joke ID: {lastrowid}")
                return lastrowid
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "INSERT INTO jokes (text, category, created_at, used_count) VALUES (?, ?, datetime('now'), ?)",
                        (text, category, 0)
                    )
                    await db.commit()
                    logger.info(f"Added joke ID: {cursor.lastrowid}")
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding joke: {e}", exc_info=True)
            return None # Return None on error

    async def get_all_jokes(self) -> List[Dict]:
        """Retrieve all jokes from the database."""
        sql = "SELECT id, text, category, created_at, used_count, last_used FROM jokes ORDER BY id"
        jokes = []
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(sql)
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                if rows:
                    jokes = [dict(row) for row in rows]
                    logger.info(f"[Postgres] Retrieved {len(jokes)} jokes.")
                else:
                    logger.info("[Postgres] No jokes found.")
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(sql) as cursor:
                        rows = await cursor.fetchall()
                        if rows:
                             jokes = [dict(row) for row in rows]
                             logger.info(f"[SQLite] Retrieved {len(jokes)} jokes.")
                        else:
                             logger.info("[SQLite] No jokes found.")
        except Exception as e:
            logger.error(f"Error getting all jokes: {e}", exc_info=True)
        return jokes

    async def delete_joke(self, joke_id: int) -> bool:
        """Delete a joke by its ID."""
        sql = "DELETE FROM jokes WHERE id = %s" if self.is_postgres else "DELETE FROM jokes WHERE id = ?"
        deleted = False
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(sql, (joke_id,))
                deleted_count = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
                if deleted_count > 0:
                    logger.info(f"[Postgres] Deleted joke ID: {joke_id}")
                    deleted = True
                else:
                    logger.warning(f"[Postgres] No joke found with ID: {joke_id} to delete.")
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(sql, (joke_id,))
                    await db.commit()
                    if cursor.rowcount > 0:
                        logger.info(f"[SQLite] Deleted joke ID: {joke_id}")
                        deleted = True
                    else:
                        logger.warning(f"[SQLite] No joke found with ID: {joke_id} to delete.")
        except Exception as e:
            logger.error(f"Error deleting joke ID {joke_id}: {e}", exc_info=True)
        return deleted

    # Remove problematic _get_db_cursor placeholder
    # async def _get_db_cursor(self, dictionary=False): ... 