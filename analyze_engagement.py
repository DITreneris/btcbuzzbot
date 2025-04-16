#!/usr/bin/env python
"""
Engagement Analysis Tool for BTCBuzzBot.
This script analyzes tweet engagement metrics and provides insights.
"""

import os
import sys
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
import argparse

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

def check_engagement_data():
    """Check if we have engagement data (likes, retweets) in the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if posts table has likes and retweets columns
            cursor.execute("PRAGMA table_info(posts)")
            columns = [col['name'] for col in cursor.fetchall()]
            
            if 'likes' not in columns or 'retweets' not in columns:
                print("Error: Posts table does not have engagement metrics columns (likes, retweets)")
                return False
            
            # Check if we have non-zero data
            cursor.execute("SELECT COUNT(*) as count FROM posts WHERE likes > 0 OR retweets > 0")
            count = cursor.fetchone()['count']
            
            if count == 0:
                print("Warning: No engagement data found - all tweets have 0 likes and 0 retweets")
                return False
                
            return True
    except Exception as e:
        print(f"Error checking engagement data: {e}")
        return False

def analyze_by_content_type(days=30):
    """Analyze engagement by content type"""
    try:
        with get_db_connection() as conn:
            # Calculate the date threshold
            threshold_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Query for engagement by content type
            query = """
                SELECT 
                    content_type,
                    COUNT(*) as post_count,
                    SUM(likes) as total_likes,
                    SUM(retweets) as total_retweets,
                    AVG(likes) as avg_likes,
                    AVG(retweets) as avg_retweets
                FROM posts
                WHERE 
                    timestamp >= ? AND
                    tweet_id NOT LIKE 'sim_%'
                GROUP BY content_type
                ORDER BY avg_likes DESC
            """
            
            cursor = conn.cursor()
            cursor.execute(query, (threshold_date,))
            rows = cursor.fetchall()
            
            if not rows:
                print(f"No posts found in the last {days} days with engagement data")
                return
            
            # Format and display results
            print(f"\n=== ENGAGEMENT BY CONTENT TYPE (Last {days} days) ===")
            print(f"{'Content Type':<15} {'Posts':<8} {'Total Likes':<15} {'Total RTs':<15} {'Avg Likes':<15} {'Avg RTs':<15}")
            print("-" * 80)
            
            for row in rows:
                print(f"{row['content_type']:<15} {row['post_count']:<8} {row['total_likes']:<15} {row['total_retweets']:<15} {row['avg_likes']:.2f:<15} {row['avg_retweets']:.2f:<15}")
            
            # Plot the data if we have multiple content types
            if len(rows) > 1:
                # Extract data for plotting
                content_types = [row['content_type'] for row in rows]
                avg_likes = [row['avg_likes'] for row in rows]
                avg_retweets = [row['avg_retweets'] for row in rows]
                
                # Create the plot
                plt.figure(figsize=(10, 6))
                
                x = range(len(content_types))
                width = 0.35
                
                plt.bar(x, avg_likes, width, label='Avg Likes')
                plt.bar([i + width for i in x], avg_retweets, width, label='Avg Retweets')
                
                plt.xlabel('Content Type')
                plt.ylabel('Average Count')
                plt.title(f'Average Engagement by Content Type (Last {days} days)')
                plt.xticks([i + width/2 for i in x], content_types)
                plt.legend()
                
                # Save the plot
                plt.savefig('engagement_by_content_type.png')
                print("\nChart saved as engagement_by_content_type.png")
                
    except Exception as e:
        print(f"Error analyzing engagement by content type: {e}")

def analyze_by_time_of_day():
    """Analyze engagement by time of day"""
    try:
        with get_db_connection() as conn:
            # Query for engagement by hour of day
            query = """
                SELECT 
                    SUBSTR(timestamp, 12, 2) as hour,
                    COUNT(*) as post_count,
                    AVG(likes) as avg_likes,
                    AVG(retweets) as avg_retweets
                FROM posts
                WHERE 
                    tweet_id NOT LIKE 'sim_%'
                GROUP BY hour
                ORDER BY hour
            """
            
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if not rows:
                print("No posts found with time data")
                return
            
            # Format and display results
            print("\n=== ENGAGEMENT BY TIME OF DAY ===")
            print(f"{'Hour':<8} {'Posts':<8} {'Avg Likes':<15} {'Avg RTs':<15}")
            print("-" * 50)
            
            for row in rows:
                # Format hour properly (add leading zero if needed)
                hour = row['hour']
                if not hour:  # If hour is empty or None
                    hour = "Unknown"
                else:
                    # Try to convert to int and then to 24-hour format
                    try:
                        hour_int = int(hour)
                        hour = f"{hour_int:02d}:00"
                    except (ValueError, TypeError):
                        hour = f"{hour}:00"
                
                print(f"{hour:<8} {row['post_count']:<8} {row['avg_likes']:.2f:<15} {row['avg_retweets']:.2f:<15}")
            
            # Plot the data
            hours = []
            avg_likes = []
            avg_retweets = []
            
            for row in rows:
                hour = row['hour']
                if hour and hour.isdigit():
                    hour_int = int(hour)
                    hours.append(f"{hour_int:02d}:00")
                    avg_likes.append(row['avg_likes'])
                    avg_retweets.append(row['avg_retweets'])
            
            if hours:  # Only plot if we have valid hour data
                plt.figure(figsize=(12, 6))
                
                plt.plot(hours, avg_likes, 'o-', label='Avg Likes')
                plt.plot(hours, avg_retweets, 's-', label='Avg Retweets')
                
                plt.xlabel('Hour of Day (24-hour format)')
                plt.ylabel('Average Count')
                plt.title('Average Engagement by Time of Day')
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.legend()
                
                # Save the plot
                plt.savefig('engagement_by_time.png')
                print("\nChart saved as engagement_by_time.png")
                
    except Exception as e:
        print(f"Error analyzing engagement by time of day: {e}")

def analyze_engagement_vs_price():
    """Analyze if there's a correlation between engagement and Bitcoin price/change"""
    try:
        with get_db_connection() as conn:
            # Query for engagement and price data
            query = """
                SELECT 
                    id,
                    tweet_id,
                    timestamp,
                    likes,
                    retweets,
                    price,
                    price_change,
                    content_type
                FROM posts
                WHERE 
                    tweet_id NOT LIKE 'sim_%' AND
                    price IS NOT NULL
                ORDER BY timestamp
            """
            
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if not rows:
                print("No posts found with both engagement and price data")
                return
            
            # Convert to pandas DataFrame for easier analysis
            data = []
            for row in rows:
                data.append({
                    'id': row['id'],
                    'tweet_id': row['tweet_id'],
                    'timestamp': row['timestamp'],
                    'likes': row['likes'] or 0,
                    'retweets': row['retweets'] or 0,
                    'price': row['price'] or 0,
                    'price_change': row['price_change'] or 0,
                    'content_type': row['content_type']
                })
            
            df = pd.DataFrame(data)
            
            # Calculate total engagement
            df['total_engagement'] = df['likes'] + df['retweets']
            
            # Classify price change direction
            df['price_direction'] = df['price_change'].apply(lambda x: 'up' if x > 0 else 'down' if x < 0 else 'unchanged')
            
            # Print summary statistics
            print("\n=== ENGAGEMENT VS PRICE ANALYSIS ===")
            
            # Analyze engagement by price direction
            direction_analysis = df.groupby('price_direction').agg({
                'likes': ['mean', 'max'],
                'retweets': ['mean', 'max'],
                'total_engagement': ['mean', 'count']
            })
            
            print("\nEngagement by Price Direction:")
            print(direction_analysis)
            
            # Check if price and engagement are correlated
            correlation = df[['price', 'price_change', 'likes', 'retweets', 'total_engagement']].corr()
            
            print("\nCorrelation Matrix:")
            print(correlation)
            
            # Plot price vs. engagement
            plt.figure(figsize=(10, 6))
            plt.scatter(df['price_change'], df['total_engagement'], alpha=0.6)
            
            # Add labels and title
            plt.xlabel('Price Change (%)')
            plt.ylabel('Total Engagement (Likes + Retweets)')
            plt.title('Bitcoin Price Change vs. Tweet Engagement')
            
            # Add a trend line
            z = np.polyfit(df['price_change'], df['total_engagement'], 1)
            p = np.poly1d(z)
            plt.plot(df['price_change'], p(df['price_change']), "r--")
            
            # Save the plot
            plt.tight_layout()
            plt.savefig('engagement_vs_price.png')
            print("\nChart saved as engagement_vs_price.png")
            
    except Exception as e:
        print(f"Error analyzing engagement vs price: {e}")

def export_engagement_report(days=None):
    """Export a comprehensive engagement report to CSV"""
    try:
        with get_db_connection() as conn:
            # Build query based on days parameter
            if days:
                threshold_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                where_clause = f"WHERE timestamp >= '{threshold_date}'"
            else:
                where_clause = ""
            
            query = f"""
                SELECT 
                    id,
                    tweet_id,
                    timestamp,
                    content_type,
                    likes,
                    retweets,
                    price,
                    price_change
                FROM posts
                {where_clause}
                ORDER BY timestamp DESC
            """
            
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if not rows:
                print(f"No posts found {f'in the last {days} days' if days else ''}")
                return
            
            # Convert to pandas DataFrame
            data = []
            for row in rows:
                data.append({
                    'id': row['id'],
                    'tweet_id': row['tweet_id'],
                    'timestamp': row['timestamp'],
                    'content_type': row['content_type'],
                    'likes': row['likes'] or 0,
                    'retweets': row['retweets'] or 0,
                    'total_engagement': (row['likes'] or 0) + (row['retweets'] or 0),
                    'price': row['price'] or 0,
                    'price_change': row['price_change'] or 0,
                    'is_simulated': 1 if row['tweet_id'] and row['tweet_id'].startswith('sim_') else 0
                })
            
            df = pd.DataFrame(data)
            
            # Create timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"engagement_report_{timestamp}.csv"
            
            # Save to CSV
            df.to_csv(filename, index=False)
            print(f"\n✅ Engagement report exported to {filename}")
            
    except Exception as e:
        print(f"Error exporting engagement report: {e}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Analyze tweet engagement metrics')
    
    # Create subparsers for different analysis types
    subparsers = parser.add_subparsers(dest='command', help='Analysis type')
    
    # Content type analysis
    content_parser = subparsers.add_parser('content', help='Analyze engagement by content type')
    content_parser.add_argument('--days', type=int, default=30, help='Number of days to analyze')
    
    # Time of day analysis
    time_parser = subparsers.add_parser('time', help='Analyze engagement by time of day')
    
    # Price correlation analysis
    price_parser = subparsers.add_parser('price', help='Analyze correlation between price and engagement')
    
    # Export report
    export_parser = subparsers.add_parser('export', help='Export engagement report to CSV')
    export_parser.add_argument('--days', type=int, help='Number of days to include in report (all if not specified)')
    
    args = parser.parse_args()
    
    # First check if we have engagement data
    has_engagement = check_engagement_data()
    
    if not has_engagement:
        print("Note: Missing or zero engagement data. Analysis may not be meaningful.")
        print("You may need to update tweet metrics using the update_metrics.py script.")
    
    # Run the appropriate analysis based on the command
    if args.command == 'content':
        analyze_by_content_type(args.days)
    elif args.command == 'time':
        analyze_by_time_of_day()
    elif args.command == 'price':
        try:
            import numpy as np
            analyze_engagement_vs_price()
        except ImportError:
            print("Error: numpy is required for price correlation analysis")
            print("Install using: pip install numpy")
    elif args.command == 'export':
        export_engagement_report(args.days)
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        # Check if pandas is available
        import pandas as pd
        
        # Check if matplotlib is available
        import matplotlib.pyplot as plt
        
        main()
    except ImportError as e:
        print(f"Error: Required packages not available - {e}")
        print("This script requires pandas and matplotlib")
        print("Install using: pip install pandas matplotlib")
        sys.exit(1) 