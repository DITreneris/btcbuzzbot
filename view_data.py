#!/usr/bin/env python
"""
View database structure and sample data
"""

import sqlite3
import os
from datetime import datetime

def display_table_info(conn, table_name, output_file):
    """Display information about a table"""
    cursor = conn.cursor()
    
    # Write table header
    output_file.write(f"\n=== {table_name.upper()} TABLE ===\n\n")
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    output_file.write("Columns:\n")
    for col in columns:
        col_id, name, type_name, not_null, default_val, pk = col
        pk_str = " PRIMARY KEY" if pk else ""
        output_file.write(f"  {name} ({type_name}){pk_str}\n")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    
    output_file.write(f"\nTotal rows: {count}\n")
    
    # If table has data, show sample
    if count > 0:
        # Only display up to 3 rows
        rows_to_display = min(3, count)
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {rows_to_display}")
        rows = cursor.fetchall()
        
        # Get column names
        column_names = [column[1] for column in columns]
        
        output_file.write("\nSample data:\n")
        
        # Format column headers (truncate long headers)
        header_line = " | ".join([name[:15] if len(name) > 15 else name for name in column_names])
        output_file.write(header_line + "\n")
        
        # Add separator line
        separator = "-" * len(header_line)
        output_file.write(separator + "\n")
        
        # Format data rows
        for row in rows:
            # Truncate data values to 15 chars max
            formatted_row = []
            for item in row:
                if item is None:
                    formatted_row.append("NULL")
                elif isinstance(item, str) and len(item) > 15:
                    formatted_row.append(f"{item[:15]}..")
                else:
                    formatted_row.append(str(item))
                    
            row_line = " | ".join(formatted_row)
            output_file.write(row_line + "\n")

def main():
    """Main function to display database information"""
    db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
    output_path = "db_structure.txt"
    
    try:
        with open(output_path, 'w') as output_file:
            # Connect to the database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get list of all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            output_file.write(f"Database: {db_path}\n")
            output_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output_file.write(f"Found {len(tables)} tables\n")
            
            # Display information for each table
            for table in tables:
                display_table_info(conn, table[0], output_file)
            
            # Close connection
            conn.close()
            
        print(f"Database structure and sample data saved to {output_path}")
            
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 