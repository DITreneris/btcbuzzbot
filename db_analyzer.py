import sqlite3
import os
from datetime import datetime

def analyze_database(db_name='btcbuzzbot.db'):
    """Analyze the structure and content of the SQLite database"""
    try:
        # Check if database exists
        if not os.path.exists(db_name):
            print(f"Error: Database '{db_name}' not found")
            return

        # Get file size and modification date
        db_size = os.path.getsize(db_name) / (1024 * 1024)  # Size in MB
        mod_time = datetime.fromtimestamp(os.path.getmtime(db_name))
        
        print(f"\n=== DATABASE ANALYSIS: {db_name} ===")
        print(f"File size: {db_size:.2f} MB")
        print(f"Last modified: {mod_time}")

        # Connect to database
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        
        print(f"\nFound {len(tables)} tables:")
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table}")
        
        # Analyze each table
        for table in tables:
            analyze_table(conn, table)
            
        # Look for potential foreign key relationships
        find_potential_relationships(conn, tables)
            
        conn.close()
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def analyze_table(conn, table_name):
    """Analyze structure and content of a specific table"""
    cursor = conn.cursor()
    
    print(f"\n\n{'=' * 50}")
    print(f"TABLE: {table_name}")
    print(f"{'=' * 50}")
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name})")
    schema = cursor.fetchall()
    
    print("\nCOLUMNS:")
    print(f"{'Name':<20} {'Type':<15} {'Nullable':<10} {'Default':<15} {'Primary Key'}")
    print(f"{'-' * 20} {'-' * 15} {'-' * 10} {'-' * 15} {'-' * 11}")
    for col in schema:
        col_id, name, type_name, not_null, default_val, pk = col
        print(f"{name:<20} {type_name:<15} {'No' if not_null else 'Yes':<10} {str(default_val):<15} {'Yes' if pk else 'No'}")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    
    # Get data statistics
    print(f"\nROW COUNT: {count:,}")
    
    if count > 0:
        # Sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        
        # Only show sample if fewer than 20 columns to keep output manageable
        if len(schema) <= 20:
            print("\nSAMPLE DATA (up to 5 rows):")
            # Print column headers
            headers = [col[1] for col in schema]
            print(" | ".join(headers))
            print("-" * (sum(len(h) for h in headers) + 3 * len(headers)))
            
            # Print rows
            for row in rows:
                formatted_row = []
                for item in row:
                    if item is None:
                        formatted_row.append("NULL")
                    elif isinstance(item, str) and len(item) > 30:
                        formatted_row.append(f"{item[:27]}...")
                    else:
                        formatted_row.append(str(item))
                print(" | ".join(formatted_row))
        
        # Get min/max values for numeric/date columns
        for col in schema:
            col_name = col[1]
            col_type = col[2].lower()
            
            if any(numeric_type in col_type for numeric_type in ['int', 'real', 'float', 'double', 'num']):
                try:
                    cursor.execute(f"SELECT MIN({col_name}), MAX({col_name}), AVG({col_name}) FROM {table_name}")
                    min_val, max_val, avg_val = cursor.fetchone()
                    
                    if min_val is not None and max_val is not None:
                        print(f"\nColumn {col_name} (numeric):")
                        print(f"  Min: {min_val}, Max: {max_val}, Avg: {avg_val:.2f if avg_val is not None else 'N/A'}")
                except:
                    pass  # Skip if operation fails
            
            elif 'date' in col_type or 'time' in col_type:
                try:
                    cursor.execute(f"SELECT MIN({col_name}), MAX({col_name}) FROM {table_name}")
                    min_date, max_date = cursor.fetchone()
                    
                    if min_date and max_date:
                        print(f"\nColumn {col_name} (date/time):")
                        print(f"  Earliest: {min_date}")
                        print(f"  Latest: {max_date}")
                except:
                    pass  # Skip if operation fails

def find_potential_relationships(conn, tables):
    """Look for potential foreign key relationships between tables"""
    cursor = conn.cursor()
    
    print("\n\n" + "=" * 50)
    print("POTENTIAL TABLE RELATIONSHIPS")
    print("=" * 50)
    print("\nLooking for possible foreign key relationships...")
    
    found_relationships = []
    
    # Get all column names from all tables
    table_columns = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        table_columns[table] = columns
    
    # Look for columns with '_id' or 'id' suffix that might be foreign keys
    for table in tables:
        for column in table_columns[table]:
            if column.endswith('_id') or column == 'id':
                for other_table in tables:
                    if other_table != table:
                        # Check if the potential reference exists in the other table
                        if column in table_columns[other_table] or column == f"{other_table}_id" or (column == 'id' and other_table == column.replace('_id', '')):
                            found_relationships.append((table, column, other_table))
    
    if found_relationships:
        print("\nPossible relationships found:")
        for i, (table, column, other_table) in enumerate(found_relationships, 1):
            print(f"{i}. {table}.{column} might reference {other_table}")
    else:
        print("\nNo obvious relationships found based on column naming patterns.")

if __name__ == "__main__":
    analyze_database() 