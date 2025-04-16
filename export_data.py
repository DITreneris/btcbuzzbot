import sqlite3
import csv
import os
import sys
from datetime import datetime

def ensure_export_dir():
    """Create exports directory if it doesn't exist"""
    export_dir = "exports"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    return export_dir

def export_table(table_name, conn):
    """Export a table to CSV file with proper handling of special characters"""
    cursor = conn.cursor()
    
    # Get column names
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if not column_names:
            print(f"⚠️ No columns found for table {table_name}")
            return False
        
        # Get data
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"⚠️ No data found in table {table_name}")
            # Still create file with headers
            rows = []
        
        # Create export directory
        export_dir = ensure_export_dir()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{export_dir}/{table_name}_{timestamp}.csv"
        
        # Write to CSV with proper handling of special characters
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(column_names)  # Write header
                
                # Process rows to handle special characters and non-string values
                processed_rows = []
                for row in rows:
                    processed_row = []
                    for item in row:
                        if item is None:
                            processed_row.append("")
                        else:
                            processed_row.append(str(item))
                    processed_rows.append(processed_row)
                
                writer.writerows(processed_rows)  # Write data
            
            print(f"✅ Exported {len(rows)} rows from {table_name} to {filename}")
            return True
        except Exception as e:
            print(f"❌ Error writing CSV file for {table_name}: {e}")
            return False
    except Exception as e:
        print(f"❌ Error exporting {table_name}: {e}")
        return False

def export_price_history():
    """Export price history with additional calculated fields"""
    conn = None
    try:
        conn = sqlite3.connect('btcbuzzbot.db')
        cursor = conn.cursor()
        
        # Get price data ordered by timestamp
        cursor.execute("SELECT id, price, timestamp, source, currency FROM prices ORDER BY timestamp")
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️ No price data found")
            return False
        
        # Prepare data with additional calculated fields
        processed_data = []
        prev_price = None
        
        for row in rows:
            id, price, timestamp, source, currency = row
            
            # Ensure we have valid numeric values for calculations
            try:
                price = float(price) if price is not None else 0.0
                
                # Calculate change from previous price if available
                if prev_price and prev_price > 0:
                    price_change = ((price - prev_price) / prev_price) * 100
                else:
                    price_change = 0.0
                    
                # Add to processed data
                processed_data.append([
                    id, price, timestamp, 
                    source if source else "Unknown", 
                    currency if currency else "USD", 
                    round(price_change, 2)
                ])
                
                prev_price = price
            except (ValueError, TypeError) as e:
                print(f"⚠️ Error processing price data: {e}")
                # Still add the row with a placeholder for price_change
                processed_data.append([
                    id, price, timestamp, 
                    source if source else "Unknown", 
                    currency if currency else "USD", 
                    "N/A"
                ])
        
        # Create export directory
        export_dir = ensure_export_dir()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{export_dir}/price_history_{timestamp}.csv"
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            # Write header
            writer.writerow(['id', 'price', 'timestamp', 'source', 'currency', 'price_change_pct'])
            # Write data
            writer.writerows(processed_data)
        
        print(f"✅ Exported {len(processed_data)} rows of price history to {filename}")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error in price history export: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in price history export: {e}")
        return False
    finally:
        if conn:
            conn.close()

def export_post_activity():
    """Export post activity with additional analysis"""
    conn = None
    try:
        conn = sqlite3.connect('btcbuzzbot.db')
        cursor = conn.cursor()
        
        # Get post data ordered by timestamp
        cursor.execute("""
            SELECT id, tweet_id, tweet, timestamp, price, price_change, 
                   content_type, likes, retweets, content
            FROM posts 
            ORDER BY timestamp
        """)
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️ No post data found")
            return False
        
        # Prepare data with additional calculated fields
        processed_data = []
        
        for row in rows:
            try:
                id, tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets, content = row
                
                # Determine if this is a real or simulated post
                is_simulated = 1 if tweet_id and tweet_id.startswith('sim_') else 0
                
                # Truncate tweet content if too long
                tweet_short = (tweet[:100] + "..." if tweet and len(tweet) > 100 else tweet) if tweet else ""
                
                # Ensure numeric values are properly formatted
                price = float(price) if price is not None else 0.0
                price_change = float(price_change) if price_change is not None else 0.0
                likes = int(likes) if likes is not None else 0
                retweets = int(retweets) if retweets is not None else 0
                
                # Add to processed data
                processed_data.append([
                    id, 
                    tweet_id if tweet_id else "",
                    tweet_short,
                    timestamp if timestamp else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    price, 
                    round(price_change, 2), 
                    content_type if content_type else "regular", 
                    likes, 
                    retweets, 
                    is_simulated
                ])
            except Exception as e:
                print(f"⚠️ Error processing post data for ID {row[0] if row else 'unknown'}: {e}")
                # Skip problematic rows or add a placeholder
                continue
        
        # Create export directory
        export_dir = ensure_export_dir()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{export_dir}/post_activity_{timestamp}.csv"
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            # Write header
            writer.writerow([
                'id', 'tweet_id', 'tweet_content', 'timestamp', 'price', 
                'price_change', 'content_type', 'likes', 'retweets', 'is_simulated'
            ])
            # Write data
            writer.writerows(processed_data)
        
        print(f"✅ Exported {len(processed_data)} rows of post activity to {filename}")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error in post activity export: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in post activity export: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    conn = None
    try:
        # Connect to database
        conn = sqlite3.connect('btcbuzzbot.db')
        
        print("\n======== BTCBUZZBOT DATA EXPORT ========")
        print(f"Started on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 45)
        
        # Get list of tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            print("⚠️ No tables found in database")
            return False
            
        # Export each table
        for table in tables:
            table_name = table[0]
            export_table(table_name, conn)
        
        # Close the database connection before specialized exports
        conn.close()
        conn = None
        
        # Export specialized reports
        print("\n--- Generating Specialized Reports ---")
        export_price_history()
        export_post_activity()
        
        print("\n======== EXPORT COMPLETED ========")
        print(f"Finished on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Ensure connection is always closed
        if conn:
            conn.close()

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n⚠️ Failed to complete all exports.")
        sys.exit(1)
    else:
        print("\n✅ All exports completed successfully.")
        sys.exit(0) 