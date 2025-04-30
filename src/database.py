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
                    default_schedule = "06:00,08:00,12:00,16:00,20:00,22:00"
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
                default_schedule = "06:00,08:00,12:00,16:00,20:00,22:00"
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

    async def close(self):
        """Close the database connection if it's open"""
        # Currently connections are managed per-operation for async SQLite
        # and sync PostgreSQL, so this might not be strictly necessary
        # unless a persistent connection pattern is introduced.
        pass 