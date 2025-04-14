import os
import sqlite3
import datetime
import requests
import time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# LLM Integration - Import API module
try:
    from src.llm_api import register_llm_api
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Ollama LLM API import failed - LLM functionality will be disabled")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['DATABASE'] = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Database helper functions
def get_db_connection():
    """Get a SQLite database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with required tables for web interface"""
    with get_db_connection() as conn:
        # Create web_users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS web_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create bot_logs table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        
        # Create bot_status table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bot_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                next_scheduled_run TEXT,
                message TEXT
            )
        ''')
        
        # Create posts table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                tweet_id TEXT,
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0
            )
        ''')
        
        # Create quotes table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT NOT NULL,
                author TEXT,
                used BOOLEAN DEFAULT 0
            )
        ''')
        
        # Create jokes table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS jokes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                joke TEXT NOT NULL,
                used BOOLEAN DEFAULT 0
            )
        ''')
        
        # Create prices table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD'
            )
        ''')
        
        # Check if admin user exists, if not create default
        admin = conn.execute('SELECT * FROM web_users WHERE username = ?', ('admin',)).fetchone()
        if not admin:
            try:
                # Create default admin user with password 'changeme'
                conn.execute(
                    'INSERT INTO web_users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)',
                    ('admin', generate_password_hash('changeme'), True, datetime.datetime.utcnow().isoformat())
                )
            except sqlite3.IntegrityError:
                # If there's an integrity error (like the user already exists), just continue
                pass
        
        conn.commit()

# Authentication decorator - keeping for potential future use but not required anymore
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Removed admin_required decorator as it's no longer needed

# Helper functions for bot data
def get_bot_status():
    """Get the current bot status"""
    with get_db_connection() as conn:
        status = conn.execute(
            'SELECT * FROM bot_status ORDER BY timestamp DESC LIMIT 1'
        ).fetchone()
        
        # If no status exists, return a default
        if not status:
            return {
                'status': 'Unknown',
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'next_scheduled_run': None,
                'message': 'Bot status not available'
            }
            
        return dict(status)

def get_recent_posts(limit=10):
    """Get recent posts from the database"""
    with get_db_connection() as conn:
        posts = conn.execute(
            'SELECT * FROM posts ORDER BY timestamp DESC LIMIT ?', 
            (limit,)
        ).fetchall()
        return [dict(post) for post in posts]

def get_posts_paginated(page=1, per_page=10, date_from=None, date_to=None, content_type=None):
    """Get paginated posts with filtering"""
    with get_db_connection() as conn:
        query = 'SELECT * FROM posts WHERE 1=1'
        params = []
        
        # Apply filters
        if date_from:
            query += ' AND timestamp >= ?'
            params.append(date_from)
        if date_to:
            query += ' AND timestamp <= ?'
            params.append(date_to)
        if content_type:
            query += ' AND content_type = ?'
            params.append(content_type)
            
        # Count total matching records
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
        total = conn.execute(count_query, params).fetchone()[0]
        
        # Add pagination
        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        
        # Execute query
        posts = conn.execute(query, params).fetchall()
        return [dict(post) for post in posts], total

def get_price_history(days=7):
    """Get Bitcoin price history for the specified number of days"""
    with get_db_connection() as conn:
        timestamp = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
        prices = conn.execute(
            'SELECT * FROM prices WHERE timestamp >= ? ORDER BY timestamp ASC',
            (timestamp,)
        ).fetchall()
        return [dict(price) for price in prices]

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
                headers["x-cg-api-key"] = api_key
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            # Handle rate limiting
            if response.status_code == 429:
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
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
            
            data = response.json()
            
            if "bitcoin" in data:
                price = data["bitcoin"]["usd"]
                price_change = data["bitcoin"].get("usd_24h_change", 0)
                
                # Store in database
                with get_db_connection() as conn:
                    conn.execute(
                        'INSERT INTO prices (timestamp, price, currency) VALUES (?, ?, ?)',
                        (datetime.datetime.utcnow().isoformat(), price, 'USD')
                    )
                    conn.commit()
                    
                return {
                    "success": True,
                    "price": price,
                    "price_change": price_change
                }
            else:
                return {
                    "success": False,
                    "error": "Bitcoin data not found in API response"
                }
        except requests.exceptions.RequestException as e:
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
            return {
                "success": False,
                "error": str(e)
            }

def get_basic_stats():
    """Get basic statistics about the bot"""
    with get_db_connection() as conn:
        total_posts = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
        total_quotes = conn.execute('SELECT COUNT(*) FROM quotes').fetchone()[0]
        total_jokes = conn.execute('SELECT COUNT(*) FROM jokes').fetchone()[0]
        
        # Average engagement
        avg_likes = conn.execute('SELECT AVG(likes) FROM posts').fetchone()[0] or 0
        avg_retweets = conn.execute('SELECT AVG(retweets) FROM posts').fetchone()[0] or 0
        
        # Most recent price
        latest_price = conn.execute(
            'SELECT * FROM prices ORDER BY timestamp DESC LIMIT 1'
        ).fetchone()
        
        # If we don't have a price yet, fetch one now
        if not latest_price:
            price_data = fetch_bitcoin_price()
            if price_data["success"]:
                # Try to get the price again after fetch
                latest_price = conn.execute(
                    'SELECT * FROM prices ORDER BY timestamp DESC LIMIT 1'
                ).fetchone()
                
        result = {
            'total_posts': total_posts,
            'total_quotes': total_quotes,
            'total_jokes': total_jokes,
            'avg_likes': round(avg_likes, 1),
            'avg_retweets': round(avg_retweets, 1),
            'latest_price': dict(latest_price) if latest_price else None
        }
        
        # Add price_change to stats if we have a price
        if latest_price and 'price_change' not in result:
            # Try to get the latest bitcoin price with change data
            price_data = fetch_bitcoin_price()
            if price_data["success"]:
                result['price_change'] = price_data["price_change"]
        
        return result

def get_recent_errors(limit=5):
    """Get recent error logs"""
    with get_db_connection() as conn:
        errors = conn.execute(
            "SELECT * FROM bot_logs WHERE level = 'ERROR' ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(error) for error in errors]

def get_scheduler_config():
    """Get the scheduler configuration"""
    # This would typically read from the .env file or database
    # For now, we'll just use hardcoded values from .env
    from dotenv import load_dotenv
    load_dotenv()
    
    return {
        'post_times': os.environ.get('POST_TIMES', '08:00,12:00,16:00,20:00').split(','),
        'timezone': os.environ.get('TIMEZONE', 'UTC')
    }

# Routes - Home and About
@app.route('/')
def home():
    """Home page with about information and recent tweets"""
    stats = get_basic_stats()
    recent_posts = get_recent_posts(limit=5)
    
    return render_template('home.html', 
                          title='BTCBuzzBot - Bitcoin Price Twitter Bot',
                          stats=stats,
                          recent_posts=recent_posts)

# Routes - Posts
@app.route('/posts')
def posts():
    """Posts page with tweet history and filtering"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get filter parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    content_type = request.args.get('content_type')
    
    # Get posts with pagination and filtering
    posts, total = get_posts_paginated(page, per_page, date_from, date_to, content_type)
    
    # Get basic stats
    stats = get_basic_stats()
    
    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('posts.html',
                          title='Tweet History',
                          posts=posts,
                          stats=stats,
                          page=page,
                          per_page=per_page,
                          total=total,
                          total_pages=total_pages,
                          date_from=date_from,
                          date_to=date_to,
                          content_type=content_type)

# Routes - Authentication (keeping for reference but not required for admin access)
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        with get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM web_users WHERE username = ?',
                (username,)
            ).fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session.clear()
                session['user_id'] = user['id']
                flash('Login successful', 'success')
                
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('admin_panel') if user['is_admin'] else url_for('home')
                
                return redirect(next_page)
            
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', title='Login')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# Routes - Admin Panel
@app.route('/admin')
@limiter.limit("30 per minute")
def admin_panel():
    """Admin panel for bot control and monitoring"""
    # Get bot status
    bot_status = get_bot_status()
    
    # Get scheduled times
    schedule = get_scheduler_config()
    
    # Get recent errors
    errors = get_recent_errors(limit=5)
    
    # Get recent posts
    recent_posts = get_recent_posts(limit=5)
    
    # Get price history for chart
    price_history = get_price_history(days=7)
    
    return render_template('admin.html', 
                          title='Admin Panel',
                          bot_status=bot_status,
                          schedule=schedule,
                          errors=errors,
                          recent_posts=recent_posts,
                          price_history=price_history)

@app.route('/admin/llm')
@limiter.limit("30 per minute")
def llm_admin():
    """LLM Admin panel for managing Ollama integration"""
    # Check if Ollama LLM API is available
    if not app.config.get('OLLAMA_ENABLED', False):
        return render_template('llm_admin.html', 
                              title='LLM Admin - BTCBuzzBot',
                              error_message="Ollama LLM integration is not available",
                              llm_enabled=False)
    
    # Get LLM status if available
    try:
        # Import directly here in case the global import failed
        from src.llm_api import client, content_generator, prompt_manager, ensure_clients
        
        # Ensure clients are initialized
        if not ensure_clients():
            return render_template('llm_admin.html', 
                                 title='LLM Admin - BTCBuzzBot',
                                 error_message="Failed to initialize LLM clients",
                                 llm_enabled=False)
        
        # Get available models
        models = client.get_available_models()
        current_model = client.model
        
        # Get templates
        templates = prompt_manager.list_templates()
        
        # Get basic stats
        stats = get_basic_stats()
        
        return render_template('llm_admin.html',
                              title='LLM Admin - BTCBuzzBot',
                              llm_enabled=True,
                              current_model=current_model,
                              models=models,
                              templates=templates,
                              stats=stats)
    except Exception as e:
        return render_template('llm_admin.html', 
                              title='LLM Admin - BTCBuzzBot',
                              error_message=f"Error accessing LLM functionality: {str(e)}",
                              llm_enabled=False)

@app.route('/admin/control/<action>', methods=['POST'])
@limiter.limit("10 per minute")
def control_bot(action):
    """Control bot operation"""
    # This would interface with the bot functions
    # For now, just update the status in the database
    
    if action == 'start':
        message = 'Bot started'
        status = 'Running'
    elif action == 'stop':
        message = 'Bot stopped'
        status = 'Stopped'
    elif action == 'tweet_now':
        message = 'Manual tweet triggered'
        status = 'Running'
        # Trigger a manual tweet using our direct tweet handler
        try:
            import tweet_handler_direct
            price_data = fetch_bitcoin_price()
            if price_data["success"]:
                # Get a random quote
                quote = get_random_content()
                if quote:
                    # Post the tweet
                    result = tweet_handler_direct.post_tweet(
                        content=quote["text"],
                        content_type=quote["type"],
                        price=price_data["price"]
                    )
                    
                    if result["success"]:
                        message = f"Tweet posted successfully! Tweet ID: {result['tweet_id']}"
                        # Log the tweet in the database
                        with get_db_connection() as conn:
                            conn.execute(
                                'INSERT INTO posts (tweet_id, tweet, timestamp, price, price_change, content_type, likes, retweets) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                (result['tweet_id'], result['tweet'], datetime.datetime.utcnow().isoformat(), 
                                 price_data["price"], price_data["price_change"], quote["type"], 0, 0)
                            )
                            conn.commit()
                    else:
                        message = f"Failed to post tweet: {result.get('error', 'Unknown error')}"
                else:
                    message = "Failed to get random content"
            else:
                message = "Failed to fetch Bitcoin price"
        except Exception as e:
            message = f"Error posting tweet: {str(e)}"
            status = 'Error'
    elif action == 'seed_prices':
        # Seed the database with 7 days of price data for testing
        seed_price_data()
        message = 'Price data seeded successfully'
        status = 'Running'
    else:
        flash(f'Unknown action: {action}', 'danger')
        return redirect(url_for('admin_panel'))
    
    # Update bot status
    with get_db_connection() as conn:
        conn.execute(
            'INSERT INTO bot_status (timestamp, status, message) VALUES (?, ?, ?)',
            (datetime.datetime.utcnow().isoformat(), status, message)
        )
        conn.commit()
    
    flash(message, 'success')
    return redirect(url_for('admin_panel'))

def seed_price_data():
    """Seed the database with 7 days of price data for testing"""
    # Get real current price first
    current_price_data = fetch_bitcoin_price()
    if not current_price_data["success"]:
        return False
        
    current_price = current_price_data["price"]
    
    # Create 7 days of simulated price data
    with get_db_connection() as conn:
        # Start from 7 days ago
        for day in range(7, 0, -1):
            # Create 6 price points per day
            for hour in range(0, 24, 4):
                # Generate timestamp
                timestamp = (datetime.datetime.utcnow() - datetime.timedelta(days=day, hours=hour)).isoformat()
                
                # Generate slightly varied price
                # Price oscillates between -5% and +5% of current price
                variation = ((day * hour) % 10 - 5) / 100
                price = current_price * (1 + variation)
                
                # Insert into database
                conn.execute(
                    'INSERT INTO prices (timestamp, price, currency) VALUES (?, ?, ?)',
                    (timestamp, price, 'USD')
                )
        
        conn.commit()
    
    return True

# Health check endpoint for monitoring
@app.route('/health')
@limiter.limit("60 per minute")
def health_check():
    """Health check endpoint for monitoring systems"""
    try:
        # Check database connection
        with get_db_connection() as conn:
            db_status = conn.execute('SELECT 1').fetchone() is not None
        
        # Get bot status
        bot_status_data = get_bot_status()
        
        # Check if bot has posted recently (within last 24h)
        with get_db_connection() as conn:
            recent_post = conn.execute(
                "SELECT COUNT(*) FROM posts WHERE timestamp > datetime('now', '-1 day')"
            ).fetchone()[0] > 0
        
        response = {
            'status': 'healthy',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'checks': {
                'database': db_status,
                'bot_status': bot_status_data['status'],
                'recent_post': recent_post
            }
        }
        
        # If any check fails, mark as unhealthy
        if not db_status or bot_status_data['status'] == 'Error':
            response['status'] = 'unhealthy'
        
        return jsonify(response)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

# API endpoints
@app.route('/api/posts', methods=['GET'])
@limiter.limit("30 per minute")
def api_posts():
    """API endpoint to get recent posts"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)  # Limit max items per page
        
        posts, total = get_posts_paginated(
            page=page, 
            per_page=per_page, 
            date_from=request.args.get('date_from'),
            date_to=request.args.get('date_to'),
            content_type=request.args.get('content_type')
        )
        
        return jsonify({
            'success': True,
            'data': {
                'posts': posts,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/stats', methods=['GET'])
@limiter.limit("30 per minute")
def api_stats():
    """API endpoint to get bot statistics"""
    try:
        stats = get_basic_stats()
        
        # Get price history for specified days
        days = min(int(request.args.get('days', 7)), 30)  # Limit max days
        price_history = get_price_history(days=days)
        
        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'price_history': price_history
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/price/refresh', methods=['GET'])
@limiter.limit("10 per minute")
def refresh_price():
    """API endpoint to refresh Bitcoin price"""
    try:
        result = fetch_bitcoin_price()
        
        if result["success"]:
            # Also update the stats cache
            with get_db_connection() as conn:
                latest_price = conn.execute(
                    'SELECT * FROM prices ORDER BY timestamp DESC LIMIT 1'
                ).fetchone()
            
            return jsonify({
                'success': True,
                'price': f"${result['price']:,.2f}",
                'change': f"{result['price_change']:.2f}%",
                'timestamp': latest_price['timestamp'] if latest_price else datetime.datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result["error"]
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/price/history', methods=['GET'])
@limiter.limit("20 per minute")
def price_history_api():
    """API endpoint to get price history"""
    try:
        days = min(int(request.args.get('days', 7)), 30)  # Limit max days
        price_data = get_price_history(days=days)
        
        # Format for chart.js
        prices = [{
            'timestamp': item['timestamp'],
            'price': item['price']
        } for item in price_data]
        
        return jsonify({
            'success': True,
            'prices': prices
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors"""
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': str(e.description)
    }), 429

# Initialize the database on startup
with app.app_context():
    init_db()

# Register LLM API blueprint if available
if OLLAMA_AVAILABLE:
    try:
        register_llm_api(app)
        print("Ollama LLM API successfully registered")
        app.config['OLLAMA_ENABLED'] = True
    except Exception as e:
        print(f"Failed to register Ollama LLM API: {str(e)}")
        app.config['OLLAMA_ENABLED'] = False
else:
    app.config['OLLAMA_ENABLED'] = False

if __name__ == '__main__':
    app.run(debug=True) 