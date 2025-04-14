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
        self.db_url = os.environ.get('DATABASE_URL')
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
            
        result = urlparse(self.db_url)
        user = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port
        
        conn = psycopg2.connect(
            database=database,
            user=user,
            password=password,
            host=hostname,
            port=port
        )
        return conn
    
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
        """Count records in a table"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(f"SELECT COUNT(*) FROM {table_name}") as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            print(f"Error counting records in {table_name}: {e}")
            return 0
    
    async def close(self):
        """Close database connection if open"""
        # For SQLite, connections are already managed with context managers
        # For PostgreSQL, connections are opened and closed for each operation
        pass 