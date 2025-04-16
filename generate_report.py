import sqlite3
import os
from datetime import datetime, timedelta
import sys

def format_price(price):
    """Format price with commas and 2 decimal places"""
    try:
        if price is None:
            return "$0.00"
        return f"${float(price):,.2f}"
    except (ValueError, TypeError):
        return f"${price}" if price else "$0.00"

def safe_parse_datetime(dt_string):
    """Safely parse a datetime string in various formats"""
    if not dt_string:
        return datetime.now()
    
    # Try different formats
    formats = [
        '%Y-%m-%d %H:%M:%S',  # Standard format
        '%Y-%m-%dT%H:%M:%S',  # ISO format without milliseconds
        '%Y-%m-%dT%H:%M:%S.%f',  # ISO format with milliseconds
        '%Y-%m-%d',  # Date only
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_string, fmt)
        except ValueError:
            continue
    
    # If all formats fail, try to extract just the date part
    try:
        if 'T' in dt_string:
            date_part = dt_string.split('T')[0]
        else:
            date_part = dt_string.split(' ')[0]
        return datetime.strptime(date_part, '%Y-%m-%d')
    except (ValueError, IndexError):
        # Return current time if all parsing fails
        print(f"Warning: Could not parse datetime string: {dt_string}")
        return datetime.now()

def generate_report():
    """Generate a summary report of the BTCBuzzBot activity and Bitcoin price trends"""
    # Check if database exists
    if not os.path.exists('btcbuzzbot.db'):
        print("Error: btcbuzzbot.db not found")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect('btcbuzzbot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("\n======== BTCBUZZBOT ACTIVITY REPORT ========")
        print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 45)
        
        # Get latest price and change
        cursor.execute("SELECT price, timestamp FROM prices ORDER BY id DESC LIMIT 1")
        latest_price_data = cursor.fetchone()
        if latest_price_data:
            latest_price = latest_price_data['price']
            price_timestamp = latest_price_data['timestamp']
            print(f"\n📊 Latest Bitcoin Price: {format_price(latest_price)}")
            print(f"   Recorded at: {price_timestamp}")
            
            # Calculate price change over last 24 hours if possible
            try:
                # Parse the timestamp safely
                dt_obj = safe_parse_datetime(price_timestamp)
                day_ago = dt_obj - timedelta(days=1)
                day_ago_str = day_ago.strftime('%Y-%m-%d')
                
                cursor.execute("SELECT price FROM prices WHERE timestamp LIKE ? ORDER BY id LIMIT 1", 
                             (f"{day_ago_str}%",))
                prev_day_price = cursor.fetchone()
                
                if prev_day_price and prev_day_price['price'] and float(prev_day_price['price']) > 0:
                    prev_price = float(prev_day_price['price'])
                    current_price = float(latest_price)
                    day_change = ((current_price - prev_price) / prev_price) * 100
                    change_emoji = "📈" if day_change >= 0 else "📉"
                    print(f"   24h Change: {day_change:+.2f}% {change_emoji}")
                else:
                    print("   24h Change: Not available (insufficient price history)")
            except Exception as e:
                print(f"   Unable to calculate 24h change: {e}")
        else:
            print("\n❌ No price data available")
        
        # Get post stats
        cursor.execute("SELECT COUNT(*) as count FROM posts")
        total_posts = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM posts WHERE tweet_id LIKE 'sim_%'")
        simulated_posts = cursor.fetchone()['count']
        
        real_posts = total_posts - simulated_posts
        
        print(f"\n📝 Post Statistics:")
        print(f"   Total Posts: {total_posts}")
        print(f"   Real Twitter Posts: {real_posts}")
        print(f"   Simulated Posts: {simulated_posts}")
        
        # Get most recent posts
        print("\n🔄 Recent Activity:")
        try:
            # Check which columns exist in posts table
            cursor.execute("PRAGMA table_info(posts)")
            post_columns = [col['name'] for col in cursor.fetchall()]
            
            # Build query based on available columns
            select_columns = ["id"]
            if "tweet_id" in post_columns: select_columns.append("tweet_id")
            if "price" in post_columns: select_columns.append("price")
            if "price_change" in post_columns: select_columns.append("price_change")
            if "timestamp" in post_columns: select_columns.append("timestamp")
            if "content_type" in post_columns: select_columns.append("content_type")
            
            # Create query
            query = f"""
                SELECT {', '.join(select_columns)} 
                FROM posts 
                ORDER BY id DESC 
                LIMIT 5
            """
            
            cursor.execute(query)
            recent_posts = cursor.fetchall()
            
            if recent_posts:
                for i, post in enumerate(recent_posts):
                    # Extract values with proper fallbacks
                    post_id = post['id'] if 'id' in post else i+1
                    tweet_id = post['tweet_id'] if 'tweet_id' in post else "unknown"
                    price = post['price'] if 'price' in post else 0
                    price_change = post['price_change'] if 'price_change' in post else 0
                    timestamp = post['timestamp'] if 'timestamp' in post else "unknown"
                    content_type = post['content_type'] if 'content_type' in post else "regular"
                    
                    post_type = "Twitter" if tweet_id and not str(tweet_id).startswith("sim_") else "Simulated"
                    change_emoji = "📈" if price_change and float(price_change) >= 0 else "📉"
                    
                    # Format and print the post info
                    price_str = format_price(price)
                    try:
                        change_str = f"{float(price_change):+.2f}%" if price_change else "N/A"
                    except (ValueError, TypeError):
                        change_str = "N/A"
                    
                    print(f"   {i+1}. [{post_type}] {price_str} | {change_str} {change_emoji if price_change else ''}")
                    print(f"      Posted at: {timestamp} (Type: {content_type})")
            else:
                print("   No recent posts found")
        except Exception as e:
            print(f"   Error retrieving recent posts: {e}")
        
        # Get content usage stats
        print("\n📊 Content Usage:")
        
        # Check if quotes table exists and has the required structure
        try:
            # Check if quotes table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quotes'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) as count FROM quotes")
                total_quotes = cursor.fetchone()['count']
                
                # Check if the posts table has content_type column
                if "content_type" in post_columns:
                    cursor.execute("SELECT COUNT(*) as count FROM posts WHERE content_type = 'quote'")
                    used_quotes = cursor.fetchone()['count']
                else:
                    used_quotes = 0
                
                print(f"   Quotes: {used_quotes} used out of {total_quotes} available")
            else:
                print("   Quotes: Table not found")
                
            # Check if jokes table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jokes'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) as count FROM jokes")
                total_jokes = cursor.fetchone()['count']
                
                # Check if the posts table has content_type column
                if "content_type" in post_columns:
                    cursor.execute("SELECT COUNT(*) as count FROM posts WHERE content_type = 'joke'")
                    used_jokes = cursor.fetchone()['count']
                else:
                    used_jokes = 0
                
                print(f"   Jokes: {used_jokes} used out of {total_jokes} available")
            else:
                print("   Jokes: Table not found")
        except Exception as e:
            print(f"   Error retrieving content usage stats: {e}")
        
        # Get bot status
        try:
            cursor.execute("PRAGMA table_info(bot_status)")
            bot_status_columns = [col['name'] for col in cursor.fetchall()]
            
            # Build query based on available columns
            select_columns = []
            if "status" in bot_status_columns: select_columns.append("status")
            if "timestamp" in bot_status_columns: select_columns.append("timestamp")
            if "next_scheduled_run" in bot_status_columns: select_columns.append("next_scheduled_run")
            if "message" in bot_status_columns: select_columns.append("message")
            
            if select_columns:
                query = f"""
                    SELECT {', '.join(select_columns)} 
                    FROM bot_status 
                    ORDER BY id DESC LIMIT 1
                """
                
                cursor.execute(query)
                status_data = cursor.fetchone()
                
                if status_data:
                    try:
                        print(f"\n🤖 Bot Status: {status_data['status'] if 'status' in status_data else 'Unknown'}")
                        if 'timestamp' in status_data:
                            print(f"   Last Updated: {status_data['timestamp']}")
                        if 'next_scheduled_run' in status_data and status_data['next_scheduled_run']:
                            print(f"   Next Scheduled Run: {status_data['next_scheduled_run']}")
                        if 'message' in status_data and status_data['message']:
                            print(f"   Message: {status_data['message']}")
                    except Exception as e:
                        print(f"\n🤖 Bot Status: Available but format issue: {e}")
                else:
                    print("\n🤖 Bot Status: Not available")
            else:
                print("\n🤖 Bot Status: Not available (table schema issue)")
        except Exception as e:
            print(f"\n🤖 Bot Status: Error retrieving status: {e}")
        
        # Get scheduler config
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduler_config'")
            if cursor.fetchone():
                cursor.execute("SELECT value FROM scheduler_config WHERE key = 'schedule'")
                schedule_data = cursor.fetchone()
                
                if schedule_data and schedule_data['value']:
                    schedule_times = schedule_data['value'].split(',')
                    print(f"\n⏰ Scheduled Times: {', '.join(schedule_times)}")
                else:
                    print("\n⏰ No scheduled times found")
            else:
                print("\n⏰ Scheduler config not available")
        except Exception as e:
            print(f"\n⏰ Error retrieving scheduler config: {e}")
        
        print("\n" + "=" * 45)
        print("Report completed successfully")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error generating report: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = generate_report()
    
    if success:
        print("\nReport generated successfully.")
        sys.exit(0)
    else:
        print("\nFailed to generate complete report.")
        sys.exit(1) 