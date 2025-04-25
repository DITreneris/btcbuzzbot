import sqlite3
import aiosqlite
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import sys
import asyncio
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# For PostgreSQL support on Heroku
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# Default configuration value
DEFAULT_DUPLICATE_POST_CHECK_MINUTES = 5
DEFAULT_CONTENT_REUSE_DAYS = 7 # Add default for content reuse

class Database:
    def __init__(self, db_path: str = "btcbuzzbot.db"):
        """Initialize database connection - supports both SQLite and PostgreSQL"""
        self.db_path = db_path
        self.connection = None
        
        # Heroku provides DATABASE_URL, but may use postgres:// prefix which psycopg2 doesn't support
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        self.db_url = db_url
        self.is_postgres = self.db_url is not None and PSYCOPG2_AVAILABLE
        
        if self.is_postgres:
            print(f"Using PostgreSQL database from DATABASE_URL")
            # Create tables synchronously during initialization for PostgreSQL
            try:
                self._create_tables_postgres()
                print("PostgreSQL database initialized successfully")
            except Exception as e:
                print(f"Error initializing PostgreSQL database: {e}", file=sys.stderr)
                raise
        else:
            print(f"Using SQLite database at: {os.path.abspath(db_path)}")
            # Ensure directory exists for SQLite
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            
            # Create tables synchronously during initialization for SQLite
            try:
                self._create_tables_sqlite()
                print("SQLite database initialized successfully")
            except Exception as e:
                print(f"Error initializing SQLite database: {e}", file=sys.stderr)
                raise
    
    def _get_postgres_connection(self):
        """Get PostgreSQL connection"""
        if not self.is_postgres:
            raise ValueError("PostgreSQL is not configured")
        
        try:
            # First try using the URL directly
            conn = psycopg2.connect(self.db_url)
            return conn
        except Exception as e:
            print(f"Error connecting with URL directly: {e}, trying with parsed components")
            # If that fails, parse the URL and connect with individual components
            result = urlparse(self.db_url)
            user = result.username
            password = result.password
            database = result.path[1:]
            hostname = result.hostname
            port = result.port
            
            try:
                conn = psycopg2.connect(
                    database=database,
                    user=user,
                    password=password,
                    host=hostname,
                    port=port
                )
                return conn
            except Exception as conn_error:
                print(f"Error connecting to PostgreSQL: {conn_error}")
                raise
    
    def _create_tables_postgres(self):
        """Create database tables in PostgreSQL if they don't exist"""
        conn = None  # Initialize conn
        try:
            conn = self._get_postgres_connection()
            with conn.cursor() as cursor:
            # Create prices table
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS prices (\n"
                    "    id SERIAL PRIMARY KEY,\n"
                    "    price REAL NOT NULL,\n"
                    "    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,\n"
                    "    source TEXT NOT NULL\n"
                    ");"
                )
            
            # Create quotes table
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS quotes (\n"
                    "    id SERIAL PRIMARY KEY,\n"
                    "    text TEXT NOT NULL,\n"
                    "    category TEXT NOT NULL,\n"
                    "    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n"
                    "    used_count INTEGER DEFAULT 0,\n"
                    "    last_used TIMESTAMP WITH TIME ZONE\n"
                    ");"
                )
            
            # Create jokes table
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS jokes (\n"
                    "    id SERIAL PRIMARY KEY,\n"
                    "    text TEXT NOT NULL,\n"
                    "    category TEXT NOT NULL,\n"
                    "    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n"
                    "    used_count INTEGER DEFAULT 0,\n"
                    "    last_used TIMESTAMP WITH TIME ZONE\n"
                    ");"
                )
            
            # Create posts table
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS posts (\n"
                    "    id SERIAL PRIMARY KEY,\n"
                    "    tweet_id TEXT NOT NULL,\n"
                    "    tweet TEXT NOT NULL,\n"
                    "    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,\n"
                    "    price REAL NOT NULL,\n"
                    "    price_change REAL NOT NULL,\n"
                    "    content_type TEXT NOT NULL,\n"
                    "    likes INTEGER DEFAULT 0,\n"
                    "    retweets INTEGER DEFAULT 0\n"
                    ");"
                )
                
                # Create news_tweets table
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS news_tweets (\n"
                    "    id SERIAL PRIMARY KEY,\n"
                    "    original_tweet_id TEXT UNIQUE NOT NULL,\n"
                    "    author_id TEXT,\n"
                    "    text TEXT NOT NULL,\n"
                    "    published_at TIMESTAMP WITH TIME ZONE,\n"
                    "    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n"
                    "    metrics JSONB, -- Storing public_metrics or organic_metrics\n"
                    "    source TEXT, -- e.g., 'twitter_search', 'influencer_feed'\n"
                    "    processed BOOLEAN DEFAULT FALSE, -- Flag for analysis processing\n"
                    "    sentiment_score REAL,\n"
                    "    sentiment_label TEXT,\n"
                    "    keywords TEXT, -- Comma-separated keywords\n"
                    "    summary TEXT,\n"
                    "    llm_analysis JSONB -- Store structured analysis from LLM\n"
                    ");"
                )
                
                # --- Add Scheduler/Web Interface Tables (PostgreSQL) ---
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS bot_status (\n"
                    "    id SERIAL PRIMARY KEY,\n"
                    "    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,\n"
                    "    status TEXT NOT NULL,\n"
                    "    next_scheduled_run TIMESTAMP WITH TIME ZONE,\n"
                    "    message TEXT NOT NULL\n"
                    ");"
                )
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS scheduler_config (\n"
                    "    key TEXT PRIMARY KEY,\n"
                    "    value TEXT NOT NULL\n"
                    ");"
                )
                # Insert default schedule if not present
                cursor.execute("SELECT value FROM scheduler_config WHERE key = %s", ('schedule',))
                if not cursor.fetchone():
                    default_schedule = "08:00,12:00,16:00,20:00"
                    cursor.execute("INSERT INTO scheduler_config (key, value) VALUES (%s, %s)", ('schedule', default_schedule))
                # --- End Scheduler Tables ---
            
            conn.commit()
            print("PostgreSQL tables checked/created.")
                
        except Exception as e:
            print(f"Error creating/checking PostgreSQL tables: {e}")
        finally:
            if conn:
                conn.close() # Ensure connection is closed even if cursor context manager fails
    
    def _create_tables_sqlite(self):
        """Create database tables in SQLite if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create prices table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL
            )
            ''')
            
            # Create quotes table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                used_count INTEGER DEFAULT 0,
                last_used TEXT
            )
            ''')
            
            # Create jokes table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS jokes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                used_count INTEGER DEFAULT 0,
                last_used TEXT
            )
            ''')
            
            # Create posts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT NOT NULL,
                tweet TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                price_change REAL NOT NULL,
                content_type TEXT NOT NULL,
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0
            )
            ''')
            
            # Create news_tweets table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_tweets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_tweet_id TEXT UNIQUE NOT NULL,
                author TEXT,
                tweet_text TEXT NOT NULL,
                tweet_url TEXT,
                published_at TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                is_news INTEGER DEFAULT 0, -- SQLite uses INTEGER for BOOLEAN (0/1)
                news_score REAL DEFAULT 0.0,
                sentiment TEXT,
                summary TEXT
            );
            ''')
            
            # --- Add Scheduler/Web Interface Tables (SQLite) ---
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                next_scheduled_run TEXT,
                message TEXT NOT NULL
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduler_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            ''')
             # Insert default schedule if not present
            cursor.execute("SELECT value FROM scheduler_config WHERE key = ?", ('schedule',))
            if not cursor.fetchone():
                default_schedule = "08:00,12:00,16:00,20:00"
                cursor.execute("INSERT INTO scheduler_config (key, value) VALUES (?, ?)", ('schedule', default_schedule))
            # --- End Scheduler Tables ---
            
            conn.commit()
    
    async def store_price(self, price: float) -> int:
        """Store BTC price with timestamp"""
        try:
            if self.is_postgres:
                # For PostgreSQL
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                # Use NOW() to let the database handle the timestamp correctly
                cursor.execute(
                    "INSERT INTO prices (price, timestamp, source) VALUES (%s, NOW(), %s) RETURNING id",
                    (price, "coingecko") # Pass only price and source
                )
                lastrowid = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                conn.close()
                return lastrowid
            else:
                # For SQLite
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "INSERT INTO prices (price, timestamp, source) VALUES (?, ?, ?)",
                        (price, datetime.utcnow().isoformat(), "coingecko")
                    )
                    await db.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"Error storing price: {e}")
            return -1
    
    async def get_latest_price(self) -> Optional[Dict[str, Any]]:
        """Get most recent BTC price"""
        try:
            if self.is_postgres:
                # For PostgreSQL
                conn = self._get_postgres_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM prices ORDER BY timestamp DESC LIMIT 1")
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if row:
                    return dict(row)
                return None
            else:
                # For SQLite
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        "SELECT * FROM prices ORDER BY timestamp DESC LIMIT 1"
                    ) as cursor:
                        row = await cursor.fetchone()
                        
                        if row:
                            return {
                                "id": row["id"],
                                "price": row["price"],
                                "timestamp": row["timestamp"],
                                "source": row["source"]
                            }
                        return None
        except Exception as e:
            print(f"Error getting latest price: {e}")
            return None

    async def get_price_from_approx_24h_ago(self) -> Optional[float]:
        """Fetches the price recorded closest to 24 hours prior to the current time."""
        try:
            if self.is_postgres:
                # PostgreSQL: Find the latest price recorded *before* or *at* 24 hours ago.
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                # Select the price from the most recent record older than 24 hours.
                sql_query = """
                    SELECT price 
                    FROM prices 
                    WHERE timestamp <= NOW() - INTERVAL '24 hours' 
                    ORDER BY timestamp DESC 
                    LIMIT 1;
                    """
                cursor.execute(sql_query)
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                return row[0] if row else None
            else:
                # SQLite: Similar logic using datetime function.
                async with aiosqlite.connect(self.db_path) as db:
                    # Select the price from the most recent record older than 24 hours.
                    sql_query = """
                        SELECT price 
                        FROM prices 
                        WHERE datetime(timestamp) <= datetime('now', '-24 hours') 
                        ORDER BY timestamp DESC 
                        LIMIT 1;
                        """
                    async with db.execute(sql_query) as cursor:
                        row = await cursor.fetchone()
                        return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting price from ~24h ago: {e}", exc_info=True) # Use logger
            return None
    
    async def get_random_content(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get random content from either quotes or jokes table"""
        # Get reuse interval from env var or use default
        reuse_days = int(os.environ.get('CONTENT_REUSE_DAYS', DEFAULT_CONTENT_REUSE_DAYS))
        
        try:
            if self.is_postgres:
                # PostgreSQL implementation
                conn = self._get_postgres_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Get content that wasn't used in the last X days or was used least
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
                    # If no matches, get any random content
                    cursor.execute(
                        f"SELECT * FROM {collection_name} ORDER BY RANDOM() LIMIT 1"
                    )
                    rows = cursor.fetchall()
                
                if rows:
                    # Pick random from results
                    import random
                    selected = dict(rows[random.randint(0, len(rows) - 1)])
                    
                    # Update usage count
                    cursor.execute(
                        f"UPDATE {collection_name} SET used_count = used_count + 1, last_used = %s WHERE id = %s",
                        (datetime.utcnow().isoformat(), selected["id"])
                    )
                    conn.commit()
                    
                    cursor.close()
                    conn.close()
                    return selected
                
                cursor.close()
                conn.close()
                return None
            else:
                # SQLite implementation
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    
                    # Get content that wasn't used in the last X days or was used least
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
                            # If no matches, get any random content
                            async with db.execute(
                                f"SELECT * FROM {collection_name} ORDER BY RANDOM() LIMIT 1"
                            ) as random_cursor:
                                rows = await random_cursor.fetchall()
                        
                        if rows:
                            # Pick random from results
                            import random
                            selected = dict(rows[random.randint(0, len(rows) - 1)])
                            
                            # Update usage count
                            await db.execute(
                                f"UPDATE {collection_name} SET used_count = used_count + 1, last_used = ? WHERE id = ?",
                                (datetime.utcnow().isoformat(), selected["id"])
                            )
                            await db.commit()
                            
                            return selected
                        
                        return None
        except Exception as e:
            print(f"Error getting random content: {e}")
            return None
    
    async def add_quote(self, text: str, category: str = "motivational") -> int:
        """Add a new quote to the database"""
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO quotes (text, category, created_at, used_count) VALUES (%s, %s, %s, %s) RETURNING id",
                    (text, category, datetime.utcnow().isoformat(), 0)
                )
                lastrowid = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                conn.close()
                return lastrowid
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "INSERT INTO quotes (text, category, created_at, used_count) VALUES (?, ?, ?, ?)",
                        (text, category, datetime.utcnow().isoformat(), 0)
                    )
                    await db.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"Error adding quote: {e}")
            return -1
    
    async def add_joke(self, text: str, category: str = "humor") -> int:
        """Add a new joke to the database"""
        timestamp = datetime.now().isoformat()
        sql = """
        INSERT INTO jokes (text, category, created_at) VALUES ($1, $2, $3) RETURNING id;
        """
        params = (text, category, timestamp)
        
        if not self.is_postgres:
            sql = """
            INSERT INTO jokes (text, category, created_at) VALUES (?, ?, ?);
            """
        
        try:
            async with self._get_db_cursor() as cursor:
                await cursor.execute(sql, params)
                if self.is_postgres:
                    result = await cursor.fetchone()
                    return result[0] if result else None
                else: # SQLite doesn't support RETURNING, get last row id
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding joke: {e}", exc_info=True)
            return None

    async def delete_quote(self, quote_id: int) -> bool:
        """Delete a quote by its ID."""
        sql = "DELETE FROM quotes WHERE id = $1"
        if not self.is_postgres:
            sql = "DELETE FROM quotes WHERE id = ?"
        
        try:
            async with self._get_db_cursor() as cursor:
                await cursor.execute(sql, (quote_id,))
                # cursor.rowcount might not be reliable across drivers/DBs for DELETE
                # Assuming success if no exception occurs and ID exists.
                # For more robust check, could SELECT first, but that adds overhead.
                # Return True for simplicity, relying on exception for failure.
                # A more robust implementation might check cursor.rowcount if available and > 0.
                # For now, if execute succeeds, assume deletion was successful or ID didn't exist.
                # await self.connection.commit() # Assuming context manager handles commit
                logger.info(f"Attempted deletion for quote ID: {quote_id}")
                # Let's try to check rowcount for confirmation
                deleted_count = cursor.rowcount if hasattr(cursor, 'rowcount') else -1 # Get rowcount if available
                if deleted_count > 0:
                     logger.info(f"Successfully deleted quote ID: {quote_id}")
                     return True
                elif deleted_count == 0:
                     logger.warning(f"No quote found with ID: {quote_id} to delete.")
                     return False
                else:
                     # rowcount not supported or returned -1, assume success if no exception
                     logger.info(f"Quote deletion query executed for ID: {quote_id} (rowcount unreliable). Assuming success.")
                     return True # Optimistic return if rowcount unavailable
        except Exception as e:
            logger.error(f"Error deleting quote ID {quote_id}: {e}", exc_info=True)
            return False

    async def get_all_quotes(self) -> List[Dict]:
        """Retrieve all quotes from the database."""
        # Include relevant fields for admin display
        sql = "SELECT id, text, category, created_at, used_count, last_used FROM quotes ORDER BY id"
        
        quotes = []
        try:
            async with self._get_db_cursor(dictionary=True) as cursor: # Request dict cursor
                await cursor.execute(sql)
                rows = await cursor.fetchall()
                if rows:
                     # Convert rows (which might be RealDictRow or similar) to plain dicts
                     quotes = [dict(row) for row in rows]
                     logger.info(f"Retrieved {len(quotes)} quotes.")
                else:
                     logger.info("No quotes found in the database.")
        except Exception as e:
            logger.error(f"Error getting all quotes: {e}", exc_info=True)
            # Return empty list on error
        return quotes

    async def delete_joke(self, joke_id: int) -> bool:
        """Delete a joke by its ID."""
        sql = "DELETE FROM jokes WHERE id = $1"
        if not self.is_postgres:
            sql = "DELETE FROM jokes WHERE id = ?"
        
        try:
            async with self._get_db_cursor() as cursor:
                await cursor.execute(sql, (joke_id,))
                logger.info(f"Attempted deletion for joke ID: {joke_id}")
                deleted_count = cursor.rowcount if hasattr(cursor, 'rowcount') else -1
                if deleted_count > 0:
                     logger.info(f"Successfully deleted joke ID: {joke_id}")
                     return True
                elif deleted_count == 0:
                     logger.warning(f"No joke found with ID: {joke_id} to delete.")
                     return False
                else:
                     logger.info(f"Joke deletion query executed for ID: {joke_id} (rowcount unreliable). Assuming success.")
                     return True
        except Exception as e:
            logger.error(f"Error deleting joke ID {joke_id}: {e}", exc_info=True)
            return False

    async def get_all_jokes(self) -> List[Dict]:
        """Retrieve all jokes from the database."""
        # Include relevant fields for admin display
        sql = "SELECT id, text, category, created_at, used_count, last_used FROM jokes ORDER BY id"
        
        jokes = []
        try:
            async with self._get_db_cursor(dictionary=True) as cursor: # Request dict cursor
                await cursor.execute(sql)
                rows = await cursor.fetchall()
                if rows:
                     jokes = [dict(row) for row in rows]
                     logger.info(f"Retrieved {len(jokes)} jokes.")
                else:
                     logger.info("No jokes found in the database.")
        except Exception as e:
            logger.error(f"Error getting all jokes: {e}", exc_info=True)
        return jokes

    async def get_recent_analyzed_news(self, hours_limit: int = 12) -> List[Dict]:
        """Retrieve recent news tweets that have LLM analysis data."""
        news_items = []
        try:
            # Calculate the timestamp for the cutoff
            cutoff_timestamp = datetime.utcnow() - timedelta(hours=hours_limit)
            
            if self.is_postgres:
                sql = """
                SELECT * FROM news_tweets 
                WHERE llm_raw_analysis IS NOT NULL 
                AND published_at >= %s 
                ORDER BY published_at DESC;
                """
                params = (cutoff_timestamp,)
            else: # SQLite
                sql = """
                SELECT * FROM news_tweets 
                WHERE llm_raw_analysis IS NOT NULL 
                AND datetime(published_at) >= datetime(?)
                ORDER BY published_at DESC;
                """
                params = (cutoff_timestamp.isoformat(),)
                
            async with self._get_db_cursor(dictionary=True) as cursor:
                await cursor.execute(sql, params)
                rows = await cursor.fetchall()
                if rows:
                     news_items = [dict(row) for row in rows]
                     logger.info(f"Retrieved {len(news_items)} analyzed news items from the last {hours_limit} hours.")
                else:
                     logger.info(f"No analyzed news items found in the last {hours_limit} hours.")
        except Exception as e:
            logger.error(f"Error getting recent analyzed news: {e}", exc_info=True)
            # Return empty list on error
        return news_items

    async def log_post(self, tweet_id: str, tweet: str, price: float, price_change: float, content_type: str) -> int:
        """Log a successful post"""
        try:
            if self.is_postgres:
                # PostgreSQL implementation
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO posts 
                    (tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets) 
                    VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (tweet_id, tweet, price, price_change, content_type, 0, 0)
                )
                lastrowid = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                conn.close()
                return lastrowid
            else:
                # SQLite implementation
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        """
                        INSERT INTO posts 
                        (tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tweet_id, tweet, datetime.utcnow().isoformat(), price, price_change, content_type, 0, 0)
                )
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error logging post: {e}")
            return -1
    
    async def count_records(self, table_name: str) -> int:
        """Count records in a given table"""
        try:
            if self.is_postgres:
                # For PostgreSQL
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                return count
            else:
                # For SQLite
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute(f"SELECT COUNT(*) FROM {table_name}") as cursor:
                        result = await cursor.fetchone()
                        return result[0] if result else 0
        except Exception as e:
            print(f"Error counting records in {table_name}: {e}")
            return 0
            
    async def has_posted_recently(self, minutes: Optional[int] = None) -> bool:
        """Check if a post was made within the last X minutes."""
        if minutes is None:
            # Read from environment variable or use default
            check_minutes = int(os.environ.get('DUPLICATE_POST_CHECK_MINUTES', DEFAULT_DUPLICATE_POST_CHECK_MINUTES))
        else:
            # Use the value passed as argument (e.g., for testing)
            check_minutes = minutes
            
        try:
            if self.is_postgres:
                # PostgreSQL implementation
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM posts WHERE timestamp > NOW() - INTERVAL '%s minutes' LIMIT 1",
                    (check_minutes,) # Use the determined check_minutes
                )
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result is not None
            else:
                # SQLite implementation
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute(
                        "SELECT 1 FROM posts WHERE datetime(timestamp) > datetime('now', ? || ' minutes') LIMIT 1",
                        (f"-{check_minutes}",) # Use the determined check_minutes
                    ) as cursor:
                        row = await cursor.fetchone()
                        return row is not None
        except Exception as e:
            print(f"Error checking recent posts: {e}")
            # Default to false to avoid blocking posts unnecessarily in case of error
            return False

    # --- Scheduler/Status Specific Methods --- 

    async def log_bot_status(self, status: str, message: str):
        """Log bot status updates, including scheduler heartbeats"""
        try:
            now_ts = datetime.utcnow()
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                # Get next scheduled run time if status is 'scheduled'
                next_run = None
                if status.lower() == 'scheduled':
                    # Placeholder: This might need adjustment based on how scheduler passes next run time
                    # For now, let's assume message might contain it or we fetch it
                    # If message contains ISO time string:
                    try:
                        # Attempt to parse from message if it's an ISO string
                        next_run = datetime.fromisoformat(message.split("Next run: ")[-1].replace('Z', '+00:00')) 
                    except (ValueError, IndexError):
                        next_run = None # Could not parse
                
                cursor.execute(
                    "INSERT INTO bot_status (timestamp, status, next_scheduled_run, message) VALUES (%s, %s, %s, %s)",
                    (now_ts, status, next_run, message)
                )
                conn.commit()
                cursor.close()
                conn.close()
            else:
                # SQLite implementation
                async with aiosqlite.connect(self.db_path) as db:
                    # Get next scheduled run time if status is 'scheduled'
                    next_run_str = None
                    if status.lower() == 'scheduled':
                        # Placeholder logic similar to above
                        try:
                            next_run_str = message.split("Next run: ")[-1]
                        except IndexError:
                            next_run_str = None
                    await db.execute(
                        "INSERT INTO bot_status (timestamp, status, next_scheduled_run, message) VALUES (?, ?, ?, ?)",
                        (now_ts.isoformat(), status, next_run_str, message)
                    )
                    await db.commit()
        except Exception as e:
            print(f"Error logging bot status: {e}")

    async def get_scheduler_config(self) -> Optional[str]:
        """Get the schedule string from scheduler_config table."""
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM scheduler_config WHERE key = %s", ('schedule',))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                return row[0] if row else None
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute("SELECT value FROM scheduler_config WHERE key = ?", ('schedule',)) as cursor:
                        row = await cursor.fetchone()
                        return row[0] if row else None
        except Exception as e:
            print(f"Error getting scheduler config: {e}", file=sys.stderr)
            return None # Return None on error

    async def update_scheduler_config(self, schedule_str: str):
        """Update the schedule string in scheduler_config table."""
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO scheduler_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                    ('schedule', schedule_str)
                )
                conn.commit()
                cursor.close()
                conn.close()
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO scheduler_config (key, value) VALUES (?, ?)",
                        ('schedule', schedule_str)
                    )
                    await db.commit()
        except Exception as e:
            print(f"Error updating scheduler config: {e}", file=sys.stderr)

    async def store_news_tweet(self, tweet_data: Dict[str, Any]) -> Optional[int]:
        """Store a fetched tweet into the news_tweets table, ignoring duplicates."""
        # Ensure required fields are present
        required_fields = ['original_tweet_id', 'author', 'tweet_text', 'tweet_url', 'published_at', 'fetched_at']
        if not all(field in tweet_data for field in required_fields):
            print(f"Error storing news tweet: Missing required fields in {tweet_data.keys()}", file=sys.stderr)
            return None

        # Optional fields with defaults
        is_news = tweet_data.get('is_news', False) # Default to False
        news_score = tweet_data.get('news_score', 0.0)
        sentiment = tweet_data.get('sentiment', None)
        summary = tweet_data.get('summary', None)
        
        # Convert boolean for SQLite
        is_news_db = 1 if is_news else 0 if not self.is_postgres else is_news

        try:
            if self.is_postgres:
                sql = """
                INSERT INTO news_tweets 
                (original_tweet_id, author, tweet_text, tweet_url, published_at, fetched_at, 
                 is_news, news_score, sentiment, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (original_tweet_id) DO NOTHING
                RETURNING id;
                """
                params = (
                    tweet_data['original_tweet_id'], tweet_data['author'], tweet_data['tweet_text'], 
                    tweet_data['tweet_url'], tweet_data['published_at'], tweet_data['fetched_at'],
                    is_news, news_score, sentiment, summary
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
                (original_tweet_id, author, tweet_text, tweet_url, published_at, fetched_at,
                 is_news, news_score, sentiment, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                params = (
                    tweet_data['original_tweet_id'], tweet_data['author'], tweet_data['tweet_text'], 
                    tweet_data['tweet_url'], tweet_data['published_at'], tweet_data['fetched_at'],
                    is_news_db, news_score, sentiment, summary
                )
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(sql, params)
                    await db.commit()
                    # Return lastrowid only if a row was inserted (changes > 0)
                    return cursor.lastrowid if db.total_changes > 0 else None
        except Exception as e:
            print(f"Error storing news tweet (ID: {tweet_data.get('original_tweet_id', 'N/A')}): {e}", file=sys.stderr)
            return None

    async def get_unprocessed_news_tweets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches tweets from news_tweets that haven't been marked as news yet."""
        tweets = []
        try:
            if self.is_postgres:
                sql = """
                SELECT * FROM news_tweets 
                WHERE is_news = FALSE OR is_news IS NULL 
                ORDER BY published_at DESC -- Process newer tweets first? Or oldest?
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
                # Fetch where is_news = 0 (SQLite boolean)
                sql = """
                SELECT * FROM news_tweets 
                WHERE is_news = 0 OR is_news IS NULL 
                ORDER BY published_at DESC 
                LIMIT ?;
                """
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute(sql, (limit,)) as cursor:
                        rows = await cursor.fetchall()
                        tweets = [dict(row) for row in rows]
        except Exception as e:
            print(f"Error fetching unprocessed news tweets: {e}", file=sys.stderr)
        
        return tweets

    async def update_tweet_analysis(
        self,
        original_tweet_id: str,
        sentiment: Optional[float],
        news_score: Optional[float],
        summary: Optional[str],
        llm_raw_analysis: Optional[str] = None # Add new optional parameter
    ):
        """Update the analysis fields for a specific tweet in news_tweets."""
        if not original_tweet_id:
            return False

        update_fields = []
        params = []

        if sentiment is not None:
            update_fields.append("sentiment = %s")
            params.append(sentiment)
        if news_score is not None:
            update_fields.append("news_score = %s")
            params.append(news_score)
        if summary is not None:
            update_fields.append("summary = %s")
            params.append(summary)
        # Add llm_raw_analysis to update if provided
        if llm_raw_analysis is not None:
            update_fields.append("llm_raw_analysis = %s") 
            params.append(llm_raw_analysis)

        update_fields.append("analysis_timestamp = NOW()") # Always update timestamp
        update_fields.append("needs_analysis = FALSE")    # Mark as analyzed

        if not params: # Only need timestamp/needs_analysis update if nothing else provided
            # This check might not be strictly necessary if we always expect some analysis
            # but it's safer. If llm_raw_analysis is the only thing, this handles it.
            pass

        params.append(original_tweet_id) # Add the ID for the WHERE clause

        sql_query = f"""
            UPDATE news_tweets 
            SET {', '.join(update_fields)}
            WHERE original_tweet_id = %s
            """

        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(sql_query, tuple(params))
                rows_affected = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
                if rows_affected > 0:
                    logger.debug(f"Successfully updated analysis for tweet ID {original_tweet_id}")
                    return True
                else:
                    logger.warning(f"No tweet found with original_tweet_id {original_tweet_id} to update analysis.")
                    return False
            else:
                # SQLite implementation (adjust placeholders)
                sql_query_sqlite = sql_query.replace("%s", "?").replace("NOW()", "datetime('now')")
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(sql_query_sqlite, tuple(params))
                    await db.commit()
                    if cursor.rowcount > 0:
                         logger.debug(f"Successfully updated analysis for tweet ID {original_tweet_id}")
                         return True
                    else:
                        logger.warning(f"No tweet found with original_tweet_id {original_tweet_id} to update analysis.")
                        return False
        except Exception as e:
            logger.error(f"Error updating tweet analysis for {original_tweet_id}: {e}", exc_info=True)
            return False

    async def get_tweets_for_analysis(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tweets marked as needing analysis."""
        # Renamed from get_unprocessed_news_tweets for clarity
        # ... (rest of method - no change needed here) ...

    async def close(self):
        """Close the database connection if it's open"""
        # Currently connections are managed per-operation for async SQLite
        # and sync PostgreSQL, so this might not be strictly necessary
        # unless a persistent connection pattern is introduced.
        pass 