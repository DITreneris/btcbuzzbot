# BTCBuzzBot Deployment Guide

This guide provides step-by-step instructions for deploying BTCBuzzBot using different methods.

## Deployment Options

1. **Heroku Deployment** (Recommended for quick setup)
2. **Traditional Server Deployment** (For more control)

## Quick Deploy with Heroku

Heroku provides the easiest way to deploy BTCBuzzBot without managing servers.

### Prerequisites

- [Heroku Account](https://signup.heroku.com/)
- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
- Git

### Deployment Steps

#### Option 1: Automated Deployment Script

1. Ensure you have all prerequisites installed
2. Run the deployment script:
   ```
   # On Windows
   powershell -ExecutionPolicy Bypass -File deploy_heroku.ps1
   
   # On Linux/Mac
   ./deploy_heroku.sh
   ```

#### Option 2: Manual Deployment

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/btcbuzzbot.git
   cd btcbuzzbot
   ```

2. Login to Heroku:
   ```
   heroku login
   ```

3. Create a new Heroku app:
   ```
   heroku create btcbuzzbot-app
   ```

4. Add PostgreSQL database:
   ```
   heroku addons:create heroku-postgresql:hobby-dev
   ```

5. Configure environment variables:
   ```
   heroku config:set TWITTER_API_KEY=your_api_key
   heroku config:set TWITTER_API_SECRET=your_api_secret
   heroku config:set TWITTER_ACCESS_TOKEN=your_access_token
   heroku config:set TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
   heroku config:set COINGECKO_API_URL=https://api.coingecko.com/api/v3
   heroku config:set COINGECKO_RETRY_LIMIT=3
   heroku config:set SCHEDULE_TIMES=08:00,12:00,16:00,20:00
   heroku config:set SECRET_KEY=your_random_secret_key
   ```

6. Deploy the application:
   ```
   git push heroku main
   ```

7. Scale dynos:
   ```
   heroku ps:scale web=1 worker=1
   ```

8. Initialize the database:
   ```
   heroku run python -m src.main
   ```

9. Open your application:
   ```
   heroku open
   ```

## Traditional Server Deployment

For more control over your deployment, you can deploy BTCBuzzBot on your own server.

### Prerequisites

- Python 3.11+
- Git
- Web server (Nginx/Apache)
- Process manager (Supervisor/systemd)

### Deployment Steps

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/btcbuzzbot.git
   cd btcbuzzbot
   ```

2. Create and activate virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. Initialize the database:
   ```
   python -m src.main
   ```

6. Configure Supervisor for the bot scheduler:
   Create `/etc/supervisor/conf.d/btcbuzzbot.conf`:
   ```
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

7. Configure Gunicorn and systemd for the web interface:
   Create `/etc/systemd/system/btcbuzzbot-web.service`:
   ```
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

8. Configure Nginx as a reverse proxy:
   Create `/etc/nginx/sites-available/btcbuzzbot`:
   ```
   server {
       listen 80;
       server_name your-domain.com;

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

9. Enable and start services:
   ```
   # Enable Nginx site
   sudo ln -s /etc/nginx/sites-available/btcbuzzbot /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx

   # Start web interface
   sudo systemctl enable btcbuzzbot-web.service
   sudo systemctl start btcbuzzbot-web.service

   # Start bot scheduler
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start btcbuzzbot
   ```

## Monitoring and Maintenance

### Heroku

- View logs: `heroku logs --tail`
- Check status: `heroku ps`
- Restart application: `heroku restart`
- Backup database: `heroku pg:backups:capture`
- Schedule automatic backups: `heroku pg:backups:schedule --at '02:00 UTC'`

### Traditional Server

- View bot logs: `tail -f /var/log/btcbuzzbot/out.log`
- View error logs: `tail -f /var/log/btcbuzzbot/err.log`
- View web interface logs: `sudo journalctl -u btcbuzzbot-web.service`
- Restart services:
  ```
  sudo supervisorctl restart btcbuzzbot
  sudo systemctl restart btcbuzzbot-web.service
  ```

## Troubleshooting

### Heroku Issues

- **Application crashes**: Check logs with `heroku logs --tail`
- **Database issues**: Verify connection with `heroku pg:info`
- **Scheduler not running**: Check dyno status with `heroku ps`

### Traditional Server Issues

- **Web interface not loading**: Check Gunicorn status with `systemctl status btcbuzzbot-web.service`
- **Bot not posting**: Check Supervisor status with `supervisorctl status btcbuzzbot`
- **Database issues**: Verify SQLite database integrity with `sqlite3 btcbuzzbot.db "PRAGMA integrity_check;"` 