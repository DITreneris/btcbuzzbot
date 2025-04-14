# BTCBuzzBot Web Interface Plan

## Overview
The BTCBuzzBot web interface will provide easy access to bot deployment, monitoring, and management through a simple but effective web application. The interface will include two main pages:

1. **Deployment & Control Page**: For managing bot operations, deployment, and monitoring
2. **Posts & About Page**: For viewing tweet history and information about the bot

## Technology Stack
- **Frontend**: HTML, CSS (Bootstrap), JavaScript
- **Backend**: Flask (Python)
- **Database**: SQLite (shared with the bot)
- **Authentication**: Simple password protection for admin functions
- **Hosting**: Heroku or similar PaaS

## Page 1: Deployment & Control Page

### Features
1. **Bot Status Dashboard**
   - Current status indicator (Running/Stopped)
   - Last tweet timestamp
   - Next scheduled tweet time
   - Success/failure rate chart
   - Error log summary

2. **Control Panel**
   - Start/Stop bot operation
   - Force immediate tweet button
   - Schedule management
   - API status indicators (Twitter, CoinGecko)

3. **Configuration**
   - Schedule time editor
   - Timezone settings
   - Database file path
   - API key management (hidden)

4. **Monitoring**
   - Price history chart (last 7 days)
   - Tweet performance metrics
   - System resource usage
   - Error rate visualization

### Implementation
```python
@app.route('/admin')
@requires_auth
def admin_panel():
    # Get bot status
    bot_status = get_bot_status()
    
    # Get scheduled times
    schedule = get_scheduler_config()
    
    # Get recent errors
    errors = get_recent_errors(limit=5)
    
    # Get price history
    price_history = get_price_history(days=7)
    
    return render_template('admin.html', 
                          bot_status=bot_status,
                          schedule=schedule,
                          errors=errors,
                          price_history=price_history)

@app.route('/admin/control/<action>', methods=['POST'])
@requires_auth
def control_bot(action):
    if action == 'start':
        start_bot()
    elif action == 'stop':
        stop_bot()
    elif action == 'tweet_now':
        trigger_immediate_tweet()
    
    return redirect(url_for('admin_panel'))
```

## Page 2: Posts & About Page

### Features
1. **Bot Information**
   - Description and purpose
   - Technical details (technologies used)
   - Setup instructions
   - API documentation

2. **Tweet History**
   - Complete history of all tweets
   - Filter by date range
   - Sort by engagement metrics
   - Content type filter (quotes/jokes)

3. **Statistics**
   - Total tweets posted
   - Most popular tweets
   - Average engagement metrics
   - Bitcoin price trends

4. **Content Browser**
   - Browse all quotes and jokes
   - Add new content through web form
   - Edit existing content
   - Preview tweet appearance

### Implementation
```python
@app.route('/')
def home():
    return render_template('about.html')

@app.route('/posts')
def posts():
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
    
    return render_template('posts.html',
                          posts=posts,
                          stats=stats,
                          page=page,
                          per_page=per_page,
                          total=total)
```

## Database Integration
The web interface will share the SQLite database with the bot, adding the following tables:

1. **web_users**: For authentication
   ```sql
   CREATE TABLE web_users (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       username TEXT NOT NULL,
       password_hash TEXT NOT NULL,
       is_admin BOOLEAN NOT NULL DEFAULT 0,
       created_at TEXT NOT NULL
   );
   ```

2. **bot_logs**: For operation logging
   ```sql
   CREATE TABLE bot_logs (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       timestamp TEXT NOT NULL,
       level TEXT NOT NULL,
       message TEXT NOT NULL
   );
   ```

3. **bot_status**: For tracking bot state
   ```sql
   CREATE TABLE bot_status (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       timestamp TEXT NOT NULL,
       status TEXT NOT NULL,
       next_scheduled_run TEXT,
       message TEXT
   );
   ```

## Frontend Design
The interface will use a clean, modern design with:
- Bootstrap 5 for responsive layout
- Chart.js for data visualization
- Font Awesome icons
- Mobile-friendly design

## Development Steps

### Phase 1: Setup
1. Create Flask application structure
2. Set up SQLite database integration
3. Create basic templates and static files
4. Implement authentication

### Phase 2: Core Features
1. Implement Posts & About page
2. Create tweet history display and filtering
3. Add basic statistics and visualizations
4. Design and implement content browser

### Phase 3: Admin Features
1. Create deployment control panel
2. Implement bot status monitoring
3. Add configuration management
4. Create error logging and display

### Phase 4: Integration & Testing
1. Connect to bot database
2. Implement API endpoints for bot interaction
3. Test all features
4. Add security measures

### Phase 5: Deployment
1. Prepare for production deployment
2. Set up hosting environment
3. Configure environment variables
4. Deploy and test in production

## Implementation Timeline
- **Week 1**: Setup and basic structure, database integration
- **Week 2**: Posts & About page implementation
- **Week 3**: Admin panel development
- **Week 4**: Testing, refinement, and deployment

## Future Enhancements
1. **Real-time updates** using WebSockets
2. **Advanced analytics** dashboard
3. **Content suggestion** system based on engagement
4. **Multi-user support** with different permission levels
5. **API access** for external integration 