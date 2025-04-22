"""
Simple script to view recent entries in the news_tweets table.
"""

import sqlite3
import os
import sys
from datetime import datetime

# Database path (use environment variable or default)
DB_PATH = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
LIMIT = 20

def view_recent_news_tweets():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at '{DB_PATH}'")
        sys.exit(1)

    try:
        conn = sqlite3.connect(DB_PATH)
        # Use dictionary cursor for easier access by column name
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        print(f"Fetching last {LIMIT} entries from 'news_tweets' table in {DB_PATH}...")

        # Check if table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_tweets';")
        if not cursor.fetchone():
            print("Error: 'news_tweets' table does not exist in the database.")
            conn.close()
            sys.exit(1)

        # Fetch recent tweets
        query = "SELECT * FROM news_tweets ORDER BY fetched_at DESC LIMIT ?;"
        cursor.execute(query, (LIMIT,))
        rows = cursor.fetchall()

        if not rows:
            print("No tweets found in the 'news_tweets' table yet.")
        else:
            print(f"Found {len(rows)} tweets:")
            # Print header
            headers = rows[0].keys()
            print("\n---")
            print(" | ".join(headers))
            print("---")
            # Print rows
            for row in rows:
                # Format row data for better readability
                row_data = []
                for col in headers:
                    value = row[col]
                    if isinstance(value, str) and len(value) > 50:
                         value = value[:47] + "..."
                    elif isinstance(value, float):
                         value = f"{value:.2f}" # Format floats
                    elif value is None:
                         value = "NULL"
                    row_data.append(str(value))
                print(" | ".join(row_data))
            print("---")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    view_recent_news_tweets() 