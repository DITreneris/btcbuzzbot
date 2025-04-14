# BTCBuzzBot

A Twitter bot that posts real-time Bitcoin price updates combined with motivational quotes or humorous content.

## Deployment Status

The application is now deployed to Heroku and accessible at:
[https://btcbuzzbot-7c02c485f88e.herokuapp.com/](https://btcbuzzbot-7c02c485f88e.herokuapp.com/)

## Features

- Real-time BTC price fetching from CoinGecko
- Asynchronous operations for better performance
- PostgreSQL database for production data persistence
- Scheduled Twitter posts (4 times daily)
- Quote and joke rotation system
- Error handling and fallback mechanisms
- Web admin panel for bot control and monitoring
- API endpoints for accessing post data and statistics

## Requirements

- Python 3.11+
- Twitter Developer account with API v2 access
- Heroku account (for deployment)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/btcbuzzbot.git
cd btcbuzzbot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your credentials (copy from `.env.example`):
```bash
cp .env.example .env
# Edit the .env file with your credentials
```

## Usage

### Local Web Interface

To run the web interface locally:

```bash
python app.py
```

Visit `http://localhost:5000` to access the web interface.

### One-time Post

To run a single Bitcoin price update post:

```bash
python -m src.main
```

### Scheduled Posts

To run the bot with scheduled posts (4 times daily):

```bash
python -m src.scheduler
```

### Testing

To run the tests:

```bash
pytest
```

## Project Structure

```
btcbuzzbot/
├── src/
│   ├── __init__.py
│   ├── price_fetcher.py    # BTC price fetching
│   ├── twitter_client.py   # Twitter API integration
│   ├── database.py         # Database operations
│   ├── content_manager.py  # Quote/joke management
│   ├── scheduler.py        # Scheduled posting
│   ├── config.py           # Configuration management
│   └── main.py             # Main application
├── static/                 # Static files (CSS, JS) - to be added
│   ├── css/
│   └── js/
├── templates/              # HTML templates for web interface
├── tests/
│   ├── __init__.py
│   ├── test_price_fetcher.py
│   └── test_content_manager.py
├── app.py                  # Flask web application
├── Procfile                # Heroku deployment configuration
├── requirements.txt
├── .env.example
├── .gitignore
├── deployment_summary.md   # Deployment status and todos
└── README.md
```

## Content Management

The bot uses two types of content:

1. **Quotes**: Motivational crypto-themed quotes
2. **Jokes**: Humorous Bitcoin/crypto jokes

Content is stored in the database and rotated to avoid repetition. The system ensures that content is not repeated within a 7-day period.

## Database

The application uses SQLite for local development and PostgreSQL for production with the following tables:
- `web_users` - Admin user accounts for web interface
- `bot_logs` - Application logs
- `bot_status` - Current status of the bot
- `prices` - Stores historical BTC price data
- `quotes` - Stores motivational crypto quotes
- `jokes` - Stores humorous crypto jokes
- `posts` - Records posted tweets and their performance

## Scheduled Posts

By default, the bot posts at the following times (UTC):
- 08:00
- 12:00
- 16:00
- 20:00

You can customize these times in the `.env` file.

## Recent Updates

- Deployed application to Heroku
- Fixed database initialization errors
- Added missing database tables
- Removed admin authentication requirement
- Set up worker dyno for scheduler

## Known Issues

- Static files (CSS/JS) are missing and need to be added
- Content population is minimal (only test quotes and jokes)
- Twitter integration needs to be validated in production

## API Rate Limiting

The application implements rate limiting to prevent abuse of the API endpoints. The following limits are enforced:

- Default limit: 200 requests per day and 50 requests per hour per IP address
- Admin panel: 30 requests per minute
- Admin control actions: 10 requests per minute
- Health check endpoint: 60 requests per minute
- API endpoints: 30 requests per minute

When a rate limit is exceeded, the API will return a 429 Too Many Requests response with a JSON error message.

## Heroku Deployment

The application is configured for Heroku deployment with:

```
web: gunicorn app:app
worker: python -m src.scheduler
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License 