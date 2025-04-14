#!/usr/bin/env python
"""
Database Diagnostic Tool

This script helps diagnose database connection and initialization issues,
particularly for PostgreSQL on Heroku.
"""

import os
import sys
import asyncio
from urllib.parse import urlparse
from dotenv import load_dotenv

# For PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("Warning: psycopg2 is not installed. PostgreSQL diagnostics will be limited.")

async def run_diagnostics():
    """Run database diagnostics"""
    # Load environment variables
    load_dotenv()
    
    print("\n=== DATABASE DIAGNOSTIC TOOL ===\n")
    
    # Check for DATABASE_URL
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL is not set in environment variables")
        print("   This is required for PostgreSQL connections on Heroku")
        return
    
    print("✅ DATABASE_URL is set in environment variables")
    
    # Fix Heroku's postgres:// URL if needed
    if db_url.startswith('postgres://'):
        fixed_db_url = db_url.replace('postgres://', 'postgresql://', 1)
        print("⚠️ DATABASE_URL uses 'postgres://' scheme which is deprecated")
        print("   Automatically converting to 'postgresql://' for psycopg2 compatibility")
        db_url = fixed_db_url
    
    # Parse the DATABASE_URL
    try:
        result = urlparse(db_url)
        db_type = result.scheme
        username = result.username
        password = "***" if result.password else None
        hostname = result.hostname
        port = result.port
        database = result.path[1:] if result.path else None
        
        print(f"\n--- Connection Details ---")
        print(f"Database Type: {db_type}")
        print(f"Username: {username}")
        print(f"Password: {'Set' if password else 'Not set'}")
        print(f"Hostname: {hostname}")
        print(f"Port: {port}")
        print(f"Database: {database}")
        
        if not all([username, password, hostname, database]):
            print("⚠️ Some required connection parameters are missing")
    except Exception as e:
        print(f"❌ Error parsing DATABASE_URL: {e}")
        return
    
    # Check for PostgreSQL availability
    if not PSYCOPG2_AVAILABLE:
        print("❌ psycopg2 module is not available")
        print("   Install it with: pip install psycopg2-binary")
        return
    
    print("\n--- PostgreSQL Connection Test ---")
    
    # Test connection
    try:
        print("Attempting connection to PostgreSQL...")
        conn = psycopg2.connect(db_url)
        print("✅ Successfully connected to PostgreSQL database")
        
        # Test table creation
        cursor = conn.cursor()
        print("\nTesting table creation...")
        
        try:
            cursor.execute("CREATE TABLE IF NOT EXISTS diagnostic_test (id SERIAL PRIMARY KEY, test_data TEXT)")
            conn.commit()
            print("✅ Successfully created test table")
            
            # Test data insertion
            print("\nTesting data insertion...")
            cursor.execute("INSERT INTO diagnostic_test (test_data) VALUES (%s) RETURNING id", ("Test data from diagnostic tool",))
            row_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ Successfully inserted test data with ID: {row_id}")
            
            # Test data retrieval
            print("\nTesting data retrieval...")
            cursor.execute("SELECT * FROM diagnostic_test WHERE id = %s", (row_id,))
            row = cursor.fetchone()
            print(f"✅ Successfully retrieved test data: {row}")
            
            # List all tables
            print("\nListing all tables in database:")
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            if tables:
                for table in tables:
                    # Get row count for each table
                    try:
                        count_cursor = conn.cursor()
                        count_cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                        row_count = count_cursor.fetchone()[0]
                        print(f"  - {table[0]} ({row_count} rows)")
                    except Exception as count_error:
                        print(f"  - {table[0]} (Error getting row count: {count_error})")
            else:
                print("  No tables found in database")
            
            # Cleanup
            print("\nCleaning up test data...")
            cursor.execute("DROP TABLE diagnostic_test")
            conn.commit()
            print("✅ Successfully cleaned up test data")
            
        except Exception as db_error:
            print(f"❌ Database operation failed: {db_error}")
        
        cursor.close()
        conn.close()
        print("\n✅ Database connection closed")
        
    except Exception as e:
        print(f"❌ Connection to PostgreSQL failed: {e}")
        print("\nPossible causes:")
        print("  - Invalid DATABASE_URL format")
        print("  - Database server is not running")
        print("  - Network connectivity issues")
        print("  - Incorrect credentials")
        print("  - Database does not exist")

if __name__ == "__main__":
    asyncio.run(run_diagnostics()) 