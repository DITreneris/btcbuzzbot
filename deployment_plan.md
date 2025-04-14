# BTCBuzzBot Deployment Plan

## Overview

This document outlines the complete deployment process for the BTCBuzzBot application, including environment setup, configuration, production deployment, monitoring, and maintenance procedures.

## 1. Environment Setup

### 1.1 System Requirements
- Python 3.11+
- SQLite 3
- Git
- Web server (for hosting the web interface)
- Process manager (Supervisor or systemd)

### 1.2 Application Dependencies
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Configuration
- Copy `.env.example` to `.env`
- Configure the following environment variables:
  - Twitter API credentials
  - CoinGecko API settings
  - Database paths
  - Scheduling times
  - Web interface settings

```bash
# Example .env configuration
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
SQLITE_DB_PATH=btcbuzzbot.db
COINGECKO_API_URL=https://api.coingecko.com/api/v3
COINGECKO_RETRY_LIMIT=3
SCHEDULE_TIMES=08:00,12:00,16:00,20:00
SECRET_KEY=your_random_secret_key
```

## 2. Database Initialization

### 2.1 Initialize Database
```bash
# Initialize database with schema
python -m src.main
```

### 2.2 Verify Database Tables
The following tables should be created:
- `prices` - Historical BTC price data
- `quotes` - Motivational crypto quotes
- `jokes` - Humorous crypto jokes
- `posts` - Tweet history
- `users` - Web interface users
- `bot_status` - Bot operational status

### 2.3 Add Initial Content
The database initialization should already populate initial content. Verify with:
```bash
# For SQLite
sqlite3 btcbuzzbot.db
> SELECT COUNT(*) FROM quotes;
> SELECT COUNT(*) FROM jokes;
```

## 3. Production Deployment

### 3.1 Bot Scheduler Setup

#### Using Supervisor (Linux)
```bash
# Install Supervisor
sudo apt-get install supervisor

# Create config file
sudo nano /etc/supervisor/conf.d/btcbuzzbot.conf
```

Add the following configuration:
```ini
[program:btcbuzzbot]
command=/path/to/venv/bin/python -m src.scheduler
directory=/path/to/btcbuzzbot
user=deployuser
autostart=true
autorestart=true
stderr_logfile=/var/log/btcbuzzbot/err.log
stdout_logfile=/var/log/btcbuzzbot/out.log
environment=PYTHONPATH="/path/to/btcbuzzbot"
```

```bash
# Create log directory
sudo mkdir -p /var/log/btcbuzzbot
sudo chown deployuser:deployuser /var/log/btcbuzzbot

# Reload supervisor configuration
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start btcbuzzbot
```

#### Using systemd (Linux alternative)
```bash
# Create service file
sudo nano /etc/systemd/system/btcbuzzbot.service
```

Add the following configuration:
```ini
[Unit]
Description=BTCBuzzBot Scheduler
After=network.target

[Service]
User=deployuser
WorkingDirectory=/path/to/btcbuzzbot
Environment="PATH=/path/to/btcbuzzbot/venv/bin"
ExecStart=/path/to/btcbuzzbot/venv/bin/python -m src.scheduler
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable btcbuzzbot.service
sudo systemctl start btcbuzzbot.service
```

### 3.2 Web Interface Deployment

#### Using Gunicorn and Nginx
```bash
# Install Gunicorn (should be in requirements.txt)
pip install gunicorn

# Create systemd service for web interface
sudo nano /etc/systemd/system/btcbuzzbot-web.service
```

Add the following configuration:
```ini
[Unit]
Description=BTCBuzzBot Web Interface
After=network.target

[Service]
User=deployuser
WorkingDirectory=/path/to/btcbuzzbot
Environment="PATH=/path/to/btcbuzzbot/venv/bin"
ExecStart=/path/to/btcbuzzbot/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable btcbuzzbot-web.service
sudo systemctl start btcbuzzbot-web.service
```

#### Nginx Configuration
```bash
# Install Nginx
sudo apt-get install nginx

# Create site configuration
sudo nano /etc/nginx/sites-available/btcbuzzbot
```

Add the following configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/btcbuzzbot/static;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/btcbuzzbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3.3 Heroku Deployment

Heroku provides a simpler deployment alternative to traditional server setup.

#### 3.3.1 Heroku Setup

```bash
# Install Heroku CLI
npm install -g heroku
# or
curl https://cli-assets.heroku.com/install.sh | sh

# Login to Heroku
heroku login

# Create a new Heroku app
heroku create btcbuzzbot

# Add Heroku PostgreSQL addon (instead of SQLite)
heroku addons:create heroku-postgresql:hobby-dev
```

#### 3.3.2 Configuration for Heroku

Create a `Procfile` in the project root:
```
web: gunicorn app:app
worker: python -m src.scheduler
```

Create a `runtime.txt` file:
```
python-3.11.6
```

Update `src/database.py` to work with PostgreSQL on Heroku:
```python
# Add to the top of the file after imports
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# Update Database class to use PostgreSQL when DATABASE_URL is present
class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.connection = None
        self.db_url = os.environ.get('DATABASE_URL')
        self.is_postgres = self.db_url is not None

    async def connect(self):
        if self.is_postgres:
            # Parse the URL and connect to PostgreSQL
            result = urlparse(self.db_url)
            user = result.username
            password = result.password
            database = result.path[1:]
            hostname = result.hostname
            port = result.port
            
            self.connection = psycopg2.connect(
                database=database,
                user=user,
                password=password,
                host=hostname,
                port=port
            )
        else:
            # Use SQLite as before
            import aiosqlite
            self.connection = await aiosqlite.connect(self.db_path)
            await self.connection.execute("PRAGMA foreign_keys = ON")
            
        # Rest of the methods need to be updated similarly...
```

Add PostgreSQL dependency to `requirements.txt`:
```
psycopg2-binary==2.9.9
```

#### 3.3.3 Configure Environment Variables on Heroku

```bash
# Set environment variables
heroku config:set TWITTER_API_KEY=your_api_key
heroku config:set TWITTER_API_SECRET=your_api_secret
heroku config:set TWITTER_ACCESS_TOKEN=your_access_token
heroku config:set TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
heroku config:set COINGECKO_API_URL=https://api.coingecko.com/api/v3
heroku config:set COINGECKO_RETRY_LIMIT=3
heroku config:set SCHEDULE_TIMES=08:00,12:00,16:00,20:00
heroku config:set SECRET_KEY=your_random_secret_key
```

#### 3.3.4 Deploy to Heroku

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit for Heroku deployment"

# Add Heroku remote
heroku git:remote -a btcbuzzbot

# Push to Heroku
git push heroku master

# Scale workers (for scheduler)
heroku ps:scale web=1 worker=1

# Run database initialization
heroku run python -m src.main
```

#### 3.3.5 Monitoring on Heroku

```bash
# View logs
heroku logs --tail

# Check application status
heroku ps

# Open web interface
heroku open
```

#### 3.3.6 Heroku Database Management

```bash
# Connect to PostgreSQL database
heroku pg:psql

# Backup database
heroku pg:backups:capture

# Download latest backup
heroku pg:backups:download

# Schedule automatic backups
heroku pg:backups:schedule --at '02:00 UTC'
```

## 4. Monitoring Setup

### 4.1 Logging Configuration
Ensure logs are properly captured and rotated:

```bash
# Install logrotate (if not already installed)
sudo apt-get install logrotate

# Create logrotate configuration
sudo nano /etc/logrotate.d/btcbuzzbot
```

Add the following configuration:
```
/var/log/btcbuzzbot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 deployuser deployuser
}
```

### 4.2 Health Checks
Create a simple health check script:

```bash
# Create health check script
nano /path/to/btcbuzzbot/health_check.sh
```

Add the following script:
```bash
#!/bin/bash
# Check if web interface is running
curl -s http://localhost:8000/health > /dev/null
WEB_STATUS=$?

# Check if scheduler is running
pgrep -f "python -m src.scheduler" > /dev/null
SCHEDULER_STATUS=$?

if [ $WEB_STATUS -ne 0 ] || [ $SCHEDULER_STATUS -ne 0 ]; then
    echo "Service is down. Web: $WEB_STATUS, Scheduler: $SCHEDULER_STATUS"
    # Send notification (e.g. email)
    exit 1
else
    echo "Service is healthy"
    exit 0
fi
```

```bash
# Make script executable
chmod +x /path/to/btcbuzzbot/health_check.sh

# Add to crontab
crontab -e
```

Add the following line to run the health check every 15 minutes:
```
*/15 * * * * /path/to/btcbuzzbot/health_check.sh >> /var/log/btcbuzzbot/health.log 2>&1
```

### 4.3 Database Backups
Set up a daily backup of the SQLite database:

```bash
# Create backup script
nano /path/to/btcbuzzbot/backup.sh
```

Add the following script:
```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup SQLite database
sqlite3 /path/to/btcbuzzbot/btcbuzzbot.db ".backup $BACKUP_DIR/btcbuzzbot_$TIMESTAMP.db"

# Compress backup
gzip $BACKUP_DIR/btcbuzzbot_$TIMESTAMP.db

# Retain last 7 backups only
find $BACKUP_DIR -name "btcbuzzbot_*.db.gz" -type f -mtime +7 -delete
```

```bash
# Make script executable
chmod +x /path/to/btcbuzzbot/backup.sh

# Add to crontab
crontab -e
```

Add the following line to run the backup daily at 2 AM:
```
0 2 * * * /path/to/btcbuzzbot/backup.sh >> /var/log/btcbuzzbot/backup.log 2>&1
```

## 5. Security Considerations

### 5.1 Secure Environment Variables
- Ensure `.env` file has restricted permissions:
```bash
chmod 600 /path/to/btcbuzzbot/.env
```

### 5.2 Web Interface Security
- Implement HTTPS using Let's Encrypt:
```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com
```

### 5.3 Twitter API Credentials
- Use restricted API tokens with only necessary permissions
- Regularly rotate access tokens

## 6. Maintenance Procedures

### 6.1 Code Updates
```bash
# Stop services
sudo supervisorctl stop btcbuzzbot
sudo systemctl stop btcbuzzbot-web.service

# Backup database
sqlite3 /path/to/btcbuzzbot/btcbuzzbot.db ".backup /path/to/backups/pre_update_backup.db"

# Update code
cd /path/to/btcbuzzbot
git pull

# Install any new dependencies
source venv/bin/activate
pip install -r requirements.txt

# Apply database migrations (if any)
python -m src.database migrate

# Restart services
sudo supervisorctl start btcbuzzbot
sudo systemctl start btcbuzzbot-web.service
```

### 6.2 Monitoring Updates
- Regularly check logs for errors
- Monitor disk space usage
- Review Twitter API rate limit usage

### 6.3 Content Updates
To add new jokes/quotes to the database:
```bash
# Connect to database
sqlite3 /path/to/btcbuzzbot/btcbuzzbot.db

# Add new quote
INSERT INTO quotes (text, category) VALUES ('New motivational quote', 'motivation');

# Add new joke
INSERT INTO jokes (text, category) VALUES ('New funny joke', 'humor');
```

## 7. Troubleshooting Guide

### 7.1 Common Issues

#### Bot not posting tweets
- Check Twitter API credentials in `.env`
- Verify Twitter API rate limits
- Check error logs in `/var/log/btcbuzzbot/err.log`
- Ensure database is accessible

#### Web interface not loading
- Check if Gunicorn is running: `ps aux | grep gunicorn`
- Verify Nginx configuration: `sudo nginx -t`
- Check web interface logs: `sudo journalctl -u btcbuzzbot-web.service`

#### Database errors
- Check permissions on database file
- Verify database is not corrupted: `sqlite3 btcbuzzbot.db "PRAGMA integrity_check;"`
- Restore from backup if necessary

### 7.2 Log Analysis
Important log files to check:
- Bot scheduler logs: `/var/log/btcbuzzbot/err.log` and `/var/log/btcbuzzbot/out.log`
- Web interface logs: `sudo journalctl -u btcbuzzbot-web.service`
- Nginx access and error logs: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`

## 8. Scaling Considerations

### 8.1 Database Scaling
- For higher traffic or data volume, consider migrating from SQLite to PostgreSQL
- Implementation would require updating `src/database.py` to use `asyncpg` instead of `aiosqlite`

### 8.2 Web Interface Scaling
- Increase Gunicorn worker count for higher traffic
- Consider implementing a load balancer for multiple instances

### 8.3 Bot Performance
- Optimize database queries
- Consider implementing caching for frequently accessed data
- Monitor API rate limits closely

## 9. Disaster Recovery

### 9.1 Database Recovery
In case of database corruption:
```bash
# Stop services
sudo supervisorctl stop btcbuzzbot
sudo systemctl stop btcbuzzbot-web.service

# Restore from most recent backup
cp /path/to/backups/btcbuzzbot_<latest>.db.gz /tmp/
gunzip /tmp/btcbuzzbot_<latest>.db.gz
cp /tmp/btcbuzzbot_<latest>.db /path/to/btcbuzzbot/btcbuzzbot.db

# Restart services
sudo supervisorctl start btcbuzzbot
sudo systemctl start btcbuzzbot-web.service
```

### 9.2 Complete Restoration
In case of complete system failure:
1. Set up a new server with the required dependencies
2. Clone the repository from GitHub
3. Restore the database from backup
4. Configure environment variables
5. Follow the deployment steps from Section 3 