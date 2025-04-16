#!/usr/bin/env python
"""
List all tables in the SQLite database and their schema.
"""

import sqlite3

def main():
    try:
        # Connect to the database
        db_path = 'btcbuzzbot.db'
        print(f"Database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in database.")
        else:
            print(f"Found {len(tables)} tables:")
            
            for i, (table_name,) in enumerate(tables, 1):
                print(f"\n{i}. TABLE: {table_name}")
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                if columns:
                    print("   COLUMNS:")
                    for col in columns:
                        cid, name, type_, notnull, default_val, pk = col
                        print(f"   - {name} ({type_})")
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   ROWS: {count}")
                
                print("   " + "-" * 30)
                
        conn.close()
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 