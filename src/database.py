import sqlite3
import aiosqlite
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import sys
import asyncio
from urllib.parse import urlparse

# For PostgreSQL support on Heroku
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

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
        with self._get_postgres_connection() as conn:
            cursor = conn.cursor()
            
            # Create prices table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL
            )
            ''')
            
            # Create quotes table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                original_tweet_id TEXT UNIQUE NOT NULL,
                author TEXT,
                tweet_text TEXT NOT NULL,
                tweet_url TEXT,
                published_at TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                is_news BOOLEAN DEFAULT FALSE,
                news_score REAL DEFAULT 0.0,
                sentiment TEXT,
                summary TEXT
            );
            ''')
            
            # --- Add Scheduler/Web Interface Tables (PostgreSQL) ---
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_status (
                id SERIAL PRIMARY KEY,
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
            cursor.execute("SELECT value FROM scheduler_config WHERE key = %s", ('schedule',))
            if not cursor.fetchone():
                default_schedule = "08:00,12:00,16:00,20:00"
                cursor.execute("INSERT INTO scheduler_config (key, value) VALUES (%s, %s)", ('schedule', default_schedule))
            # --- End Scheduler Tables ---
            
            conn.commit()
    
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
                cursor.execute(
                    "INSERT INTO prices (price, timestamp, source) VALUES (%s, %s, %s) RETURNING id",
                    (price, datetime.utcnow().isoformat(), "coingecko")
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
    
    async def get_random_content(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get random content from either quotes or jokes table"""
        try:
            if self.is_postgres:
                # PostgreSQL implementation
                conn = self._get_postgres_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Get content that wasn't used in the last 7 days or was used least
                cursor.execute(
                    f"""
                    SELECT * FROM {collection_name} 
                    WHERE last_used IS NULL 
                    OR last_used < NOW() - INTERVAL '7 days'
                    ORDER BY used_count ASC
                    LIMIT 10
                    """
                )
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
                # SQLite implementation (unchanged)
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    
                    # Get content that wasn't used in the last 7 days or was used least
                    async with db.execute(
                        f"""
                        SELECT * FROM {collection_name} 
                        WHERE last_used IS NULL 
                        OR datetime(last_used) < datetime('now', '-7 days')
                        ORDER BY used_count ASC
                        LIMIT 10
                        """
                    ) as cursor:
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
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO jokes (text, category, created_at, used_count) VALUES (%s, %s, %s, %s) RETURNING id",
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
                        "INSERT INTO jokes (text, category, created_at, used_count) VALUES (?, ?, ?, ?)",
                        (text, category, datetime.utcnow().isoformat(), 0)
                    )
                    await db.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"Error adding joke: {e}")
            return -1
    
    async def log_post(self, tweet_id: str, tweet: str, price: float, price_change: float, content_type: str) -> int:
        """Log a successful post"""
        try:
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
            
    async def has_posted_recently(self, minutes: int = 5) -> bool:
        """Check if a tweet has been posted successfully within the last N minutes."""
        try:
            now = datetime.utcnow()
            cutoff_time = (now - datetime.timedelta(minutes=minutes)).isoformat()
            
            if self.is_postgres:
                # For PostgreSQL
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM posts WHERE timestamp > %s", (cutoff_time,))
                count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                return count > 0
            else:
                # For SQLite
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute("SELECT COUNT(*) FROM posts WHERE timestamp > ?", (cutoff_time,)) as cursor:
                        result = await cursor.fetchone()
                        return result[0] > 0 if result else False
        except Exception as e:
            print(f"Error checking for recent posts: {e}")
            # Default to False to avoid blocking posts if check fails
            return False

    # --- Scheduler/Status Specific Methods --- 

    async def log_bot_status(self, status: str, message: str):
        """Log bot status (e.g., Running, Error, Stopped) to the bot_status table."""
        timestamp = datetime.utcnow().isoformat() # Consider timezone consistency
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                # Assuming next_scheduled_run is managed elsewhere or not logged here
                cursor.execute(
                    "INSERT INTO bot_status (timestamp, status, message) VALUES (%s, %s, %s)",
                    (timestamp, status, message)
                )
                conn.commit()
                cursor.close()
                conn.close()
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)",
                        (timestamp, status, message)
                    )
                    await db.commit()
        except Exception as e:
            print(f"Error logging bot status: {e}", file=sys.stderr)

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

    async def update_news_tweet_analysis(self, original_tweet_id: str, analysis_results: Dict[str, Any]):
        """Updates a news tweet record with analysis results."""
        # Fields to potentially update
        fields_to_update = {
            'is_news': analysis_results.get('is_news'),
            'news_score': analysis_results.get('news_score'),
            'sentiment': analysis_results.get('sentiment'),
            'summary': analysis_results.get('summary')
        }
        
        # Filter out None values to avoid overwriting existing data unintentionally
        update_data = {k: v for k, v in fields_to_update.items() if v is not None}
        
        if not update_data:
            print(f"No analysis results provided to update for tweet ID {original_tweet_id}")
            return False # Nothing to update

        # Handle SQLite boolean conversion if is_news is present
        if 'is_news' in update_data and not self.is_postgres:
            update_data['is_news'] = 1 if update_data['is_news'] else 0
            
        set_clause = ", ".join([f"{key} = %s" if self.is_postgres else f"{key} = ?" for key in update_data.keys()])
        params = list(update_data.values())
        params.append(original_tweet_id) # For the WHERE clause
        
        sql = f"UPDATE news_tweets SET {set_clause} WHERE original_tweet_id = {'%s' if self.is_postgres else '?'};"
        
        try:
            if self.is_postgres:
                conn = self._get_postgres_connection()
                cursor = conn.cursor()
                cursor.execute(sql, tuple(params))
                updated_rows = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
            else:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(sql, tuple(params))
                    await db.commit()
                    updated_rows = cursor.rowcount
                    
            if updated_rows > 0:
                print(f"Successfully updated analysis for tweet ID {original_tweet_id}")
                return True
            else:
                print(f"No tweet found with ID {original_tweet_id} to update analysis.")
                return False
        except Exception as e:
            print(f"Error updating analysis for tweet ID {original_tweet_id}: {e}", file=sys.stderr)
            return False

    async def close(self):
        """Close the database connection if it's open"""
        # Currently connections are managed per-operation for async SQLite
        # and sync PostgreSQL, so this might not be strictly necessary
        # unless a persistent connection pattern is introduced.
        pass 