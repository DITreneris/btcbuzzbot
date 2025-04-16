#!/usr/bin/env python
"""
Data import tool for BTCBuzzBot.
This script allows importing data from various sources into the BTCBuzzBot database.
"""

import os
import sys
import sqlite3
import csv
import json
import argparse
from datetime import datetime

# Try to import requests, but handle the case when it's not available
REQUESTS_AVAILABLE = False
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    print("Warning: requests module not available - historical price import feature will be disabled")
    print("Install using: pip install requests")

def get_db_connection():
    """Get a database connection"""
    db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
    print(f"Connecting to database at {db_path}")
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database file not found at {db_path}")
        sys.exit(1)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def check_table_structure(conn, table_name):
    """Check if a table exists and return its column structure"""
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        return None
    
    # Get table columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return {col['name']: col for col in columns}

def import_quotes_from_csv(file_path):
    """Import quotes from a CSV file into the quotes table"""
    try:
        with get_db_connection() as conn:
            columns = check_table_structure(conn, 'quotes')
            if not columns:
                print("Error: quotes table does not exist")
                return False
            
            print(f"Importing quotes from {file_path}...")
            count = 0
            
            with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # Validate minimum required fields
                    if 'text' not in row or not row['text']:
                        print(f"Skipping row - missing text field: {row}")
                        continue
                    
                    # Prepare values
                    values = {
                        'text': row.get('text', '').strip(),
                        'category': row.get('category', 'motivational').strip(),
                        'created_at': datetime.now().isoformat(),
                        'used_count': 0
                    }
                    
                    # Insert into database
                    try:
                        conn.execute('''
                            INSERT INTO quotes (text, category, created_at, used_count)
                            VALUES (?, ?, ?, ?)
                        ''', (values['text'], values['category'], values['created_at'], values['used_count']))
                        count += 1
                    except sqlite3.IntegrityError as e:
                        print(f"Error inserting quote: {e} - {values['text'][:30]}...")
            
            conn.commit()
            print(f"✅ Successfully imported {count} quotes")
            return True
    except Exception as e:
        print(f"Error importing quotes: {e}")
        return False

def import_jokes_from_csv(file_path):
    """Import jokes from a CSV file into the jokes table"""
    try:
        with get_db_connection() as conn:
            columns = check_table_structure(conn, 'jokes')
            if not columns:
                print("Error: jokes table does not exist")
                return False
            
            print(f"Importing jokes from {file_path}...")
            count = 0
            
            with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # Validate minimum required fields
                    if 'text' not in row or not row['text']:
                        print(f"Skipping row - missing text field: {row}")
                        continue
                    
                    # Prepare values
                    values = {
                        'text': row.get('text', '').strip(),
                        'category': row.get('category', 'humor').strip(),
                        'created_at': datetime.now().isoformat(),
                        'used_count': 0
                    }
                    
                    # Insert into database
                    try:
                        conn.execute('''
                            INSERT INTO jokes (text, category, created_at, used_count)
                            VALUES (?, ?, ?, ?)
                        ''', (values['text'], values['category'], values['created_at'], values['used_count']))
                        count += 1
                    except sqlite3.IntegrityError as e:
                        print(f"Error inserting joke: {e} - {values['text'][:30]}...")
            
            conn.commit()
            print(f"✅ Successfully imported {count} jokes")
            return True
    except Exception as e:
        print(f"Error importing jokes: {e}")
        return False

def import_historical_prices(days=30):
    """Import historical Bitcoin prices from CoinGecko API"""
    if not REQUESTS_AVAILABLE:
        print("Error: requests module is required for importing historical prices")
        print("Install using: pip install requests")
        return False
        
    try:
        with get_db_connection() as conn:
            columns = check_table_structure(conn, 'prices')
            if not columns:
                print("Error: prices table does not exist")
                return False
            
            print(f"Importing historical Bitcoin prices for the last {days} days...")
            
            # Get existing timestamps to avoid duplicates
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp FROM prices ORDER BY timestamp DESC")
            existing_timestamps = {row['timestamp'][:10] for row in cursor.fetchall()}
            
            # Fetch from CoinGecko API
            url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily'
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                print(f"Error: API request failed with status code {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            data = response.json()
            
            if 'prices' not in data:
                print("Error: API response does not contain price data")
                return False
            
            count = 0
            for timestamp_ms, price in data['prices']:
                # Convert timestamp from milliseconds to seconds
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
                
                # Skip if we already have this date
                if timestamp in existing_timestamps:
                    continue
                
                # Insert into database
                try:
                    conn.execute('''
                        INSERT INTO prices (timestamp, price, source, currency)
                        VALUES (?, ?, ?, ?)
                    ''', (timestamp, price, 'CoinGecko API', 'USD'))
                    count += 1
                except sqlite3.IntegrityError as e:
                    print(f"Error inserting price: {e} - {timestamp}: ${price}")
            
            conn.commit()
            print(f"✅ Successfully imported {count} historical prices")
            return True
    except Exception as e:
        print(f"Error importing historical prices: {e}")
        return False

def import_dummy_data():
    """Import dummy data for testing purposes"""
    try:
        with get_db_connection() as conn:
            # Add sample quotes if needed
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM quotes")
            quote_count = cursor.fetchone()['count']
            
            if quote_count < 5:
                print("Adding sample quotes...")
                sample_quotes = [
                    "HODL to the moon! 🚀",
                    "Buy the dip, enjoy the trip. 📈",
                    "In crypto we trust. 💎",
                    "Not your keys, not your coins. 🔑",
                    "Blockchain is not just a technology, it's a revolution. ⚡"
                ]
                
                for quote in sample_quotes:
                    conn.execute('''
                        INSERT INTO quotes (text, category, created_at, used_count)
                        VALUES (?, ?, ?, ?)
                    ''', (quote, 'motivational', datetime.now().isoformat(), 0))
                print(f"✅ Added {len(sample_quotes)} sample quotes")
            
            # Add sample jokes if needed
            cursor.execute("SELECT COUNT(*) as count FROM jokes")
            joke_count = cursor.fetchone()['count']
            
            if joke_count < 5:
                print("Adding sample jokes...")
                sample_jokes = [
                    "Why don't Bitcoin miners get scurvy? Because they always find byte-a-mins.",
                    "How does a Bitcoin user introduce their girlfriend? 'This is my blockchain girlfriend'",
                    "What's a crypto trader's favorite exercise? HODL-ing.",
                    "Why did the Bitcoin cross the road? To get to the other side... chain.",
                    "What's the difference between Bitcoin and my paycheck? My paycheck goes down every year."
                ]
                
                for joke in sample_jokes:
                    conn.execute('''
                        INSERT INTO jokes (text, category, created_at, used_count)
                        VALUES (?, ?, ?, ?)
                    ''', (joke, 'humor', datetime.now().isoformat(), 0))
                print(f"✅ Added {len(sample_jokes)} sample jokes")
            
            conn.commit()
            print("✅ Successfully imported dummy data")
            return True
    except Exception as e:
        print(f"Error importing dummy data: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Import data into BTCBuzzBot database')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Import quotes
    quotes_parser = subparsers.add_parser('quotes', help='Import quotes from CSV')
    quotes_parser.add_argument('file', help='Path to CSV file containing quotes')
    
    # Import jokes
    jokes_parser = subparsers.add_parser('jokes', help='Import jokes from CSV')
    jokes_parser.add_argument('file', help='Path to CSV file containing jokes')
    
    # Import historical prices
    prices_parser = subparsers.add_parser('prices', help='Import historical Bitcoin prices')
    prices_parser.add_argument('--days', type=int, default=30, help='Number of days of historical data to import')
    
    # Import dummy data
    dummy_parser = subparsers.add_parser('dummy', help='Import dummy data for testing')
    
    args = parser.parse_args()
    
    if args.command == 'quotes':
        if os.path.exists(args.file):
            import_quotes_from_csv(args.file)
        else:
            print(f"Error: File not found: {args.file}")
    elif args.command == 'jokes':
        if os.path.exists(args.file):
            import_jokes_from_csv(args.file)
        else:
            print(f"Error: File not found: {args.file}")
    elif args.command == 'prices':
        if REQUESTS_AVAILABLE:
            import_historical_prices(args.days)
        else:
            print("Error: Cannot import historical prices - requests module not available")
            print("Install using: pip install requests")
    elif args.command == 'dummy':
        import_dummy_data()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 