#!/usr/bin/env python
"""
Test Bitcoin Price Fetching Functionality for BTCBuzzBot.
This script tests the Bitcoin price fetching functionality without any Flask dependencies.
"""

import os
import sys
import sqlite3
import time
from datetime import datetime
import json

# Try to import requests, but handle the case when it's not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests module not available. Install using: pip install requests")
    sys.exit(1)

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not available, relying on system environment variables")

def get_db_connection():
    """Get a database connection"""
    db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
    print(f"Connecting to database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_bitcoin_price():
    """Fetch current Bitcoin price from CoinGecko API"""
    max_retries = int(os.environ.get("COINGECKO_RETRY_LIMIT", 3))
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            
            # Add CoinGecko API key to headers
            headers = {}
            api_key = os.environ.get("COINGECKO_API_KEY")
            if api_key:
                print(f"Using CoinGecko API key: {api_key[:4]}..." if api_key else "No API key provided")
                headers["x-cg-api-key"] = api_key
            
            print(f"Fetching Bitcoin price from {url}...")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            # Handle rate limiting
            if response.status_code == 429:
                print(f"Rate limit exceeded (429), attempt {attempt+1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    return {
                        "success": False,
                        "error": "Rate limit exceeded for CoinGecko API"
                    }
            
            # Handle other error status codes
            if response.status_code != 200:
                print(f"API error: {response.status_code}, response: {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}, {response.text}"
                }
            
            data = response.json()
            print(f"API response: {json.dumps(data, indent=2)}")
            
            if "bitcoin" in data:
                price = data["bitcoin"]["usd"]
                price_change = data["bitcoin"].get("usd_24h_change", 0)
                
                # Store in database
                try:
                    with get_db_connection() as conn:
                        conn.execute(
                            'INSERT INTO prices (timestamp, price, source, currency) VALUES (?, ?, ?, ?)',
                            (datetime.now().isoformat(), price, 'CoinGecko API', 'USD')
                        )
                        conn.commit()
                        print(f"✅ Saved price ${price:,.2f} to database")
                except Exception as db_error:
                    print(f"⚠️ Database error: {db_error}")
                    
                return {
                    "success": True,
                    "price": price,
                    "price_change": price_change,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"Error: Bitcoin data not found in API response")
                return {
                    "success": False,
                    "error": "Bitcoin data not found in API response"
                }
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            # Network error handling
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                return {
                    "success": False,
                    "error": f"Network error: {str(e)}"
                }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

def verify_price_table():
    """Verify the prices table exists and has the correct structure"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if prices table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prices'")
            if not cursor.fetchone():
                print("⚠️ 'prices' table does not exist, creating...")
                cursor.execute('''
                    CREATE TABLE prices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        price REAL NOT NULL,
                        source TEXT,
                        currency TEXT NOT NULL DEFAULT 'USD'
                    )
                ''')
                conn.commit()
                print("✅ Created 'prices' table")
            
            # Check structure
            cursor.execute("PRAGMA table_info(prices)")
            columns = [col['name'] for col in cursor.fetchall()]
            required_columns = ['id', 'timestamp', 'price', 'source', 'currency']
            
            missing_columns = [col for col in required_columns if col not in columns]
            if missing_columns:
                print(f"⚠️ Missing columns in 'prices' table: {', '.join(missing_columns)}")
                # Add missing columns
                for col in missing_columns:
                    if col == 'source':
                        cursor.execute("ALTER TABLE prices ADD COLUMN source TEXT")
                    elif col == 'currency':
                        cursor.execute("ALTER TABLE prices ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD'")
                conn.commit()
                print(f"✅ Added missing columns to 'prices' table")
            
            # Get existing data count
            cursor.execute("SELECT COUNT(*) FROM prices")
            count = cursor.fetchone()[0]
            print(f"Current price records: {count}")
            
            cursor.execute("SELECT * FROM prices ORDER BY timestamp DESC LIMIT 1")
            latest = cursor.fetchone()
            if latest:
                print(f"Latest price: ${latest['price']:,.2f} at {latest['timestamp']}")
                
            return True
    except Exception as e:
        print(f"Error verifying prices table: {e}")
        return False

def main():
    print("\n===== BITCOIN PRICE FETCHING TEST =====")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Verify database
    verify_price_table()
    
    # Fetch price
    print("\nFetching Bitcoin price...")
    result = fetch_bitcoin_price()
    
    # Display results
    print("\n===== RESULT =====")
    if result['success']:
        print(f"✅ SUCCESS: Bitcoin price is ${result['price']:,.2f}")
        print(f"24h change: {result['price_change']:.2f}%")
        print(f"Timestamp: {result['timestamp']}")
    else:
        print(f"❌ ERROR: {result['error']}")
    
if __name__ == "__main__":
    main() 