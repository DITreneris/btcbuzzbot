# BTCBuzzBot

<div align="center">
  <img src="static/img/favicon.png" alt="BTCBuzzBot Logo" width="120" height="120">
  <h3>A Bitcoin Price Twitter Bot with Personality</h3>
</div>

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3112/)
[![Flask](https://img.shields.io/badge/Flask-3.0.2-lightgrey)](https://flask.palletsprojects.com/)
[![Twitter API](https://img.shields.io/badge/Twitter%20API-v2-1DA1F2)](https://developer.twitter.com/en/docs/twitter-api)
[![CoinGecko API](https://img.shields.io/badge/CoinGecko-API-yellow)](https://www.coingecko.com/en/api)
[![Heroku](https://img.shields.io/badge/Heroku-Deployed-purple)](https://btcbuzzbot-7c02c485f88e.herokuapp.com/)

## 📊 Overview

**BTCBuzzBot** is an automated Twitter bot that posts real-time Bitcoin price updates combined with motivational quotes or jokes to engage the crypto community. The application includes a full web dashboard for monitoring bot activity, viewing analytics, and controlling operations.

## ✨ Features

- **Automated Bitcoin Price Updates**: Fetches real-time Bitcoin prices from CoinGecko API
- **Content Variety**: Rotates between price updates, motivational quotes, and crypto jokes
- **Twitter Integration**: Posts updates to Twitter via the Twitter API v2
- **Scheduled Operations**: Configurable posting schedule (defaults to 4 times daily)
- **Admin Dashboard**: Web interface for monitoring and controlling bot activity
- **Analytics**: View engagement statistics and price history charts
- **Mobile-Responsive UI**: Modern dark-themed interface built with Bootstrap 5
- **Robust Error Handling**: Graceful fallbacks for network and API issues
- **Flexible Database Schema**: Adapts to different database setups automatically
- **Export Capabilities**: CSV exports of all data with advanced filtering

## 🛠️ Technology Stack

- **Backend**: Python, Flask
- **Database**: SQLite (local) / PostgreSQL (production)
- **APIs**: Twitter API v2, CoinGecko API
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5, Chart.js
- **Deployment**: Heroku

## 📋 Requirements

- Python 3.11+
- Twitter Developer Account with API access
- CoinGecko API key (optional)
- Heroku account (for deployment)

## 🚀 Setup & Installation

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/btcbuzzbot.git
cd btcbuzzbot
```

2. **Set up a virtual environment**
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```
   # Twitter API Credentials
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_access_secret
   
   # CoinGecko API
   COINGECKO_API_KEY=your_coingecko_api_key
   
   # Bot Configuration
   POST_TIMES=08:00,12:00,16:00,20:00
   TIMEZONE=UTC
   
   # Flask Configuration
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   
   # Database Configuration
   SQLITE_DB_PATH=btcbuzzbot.db
   ```

5. **Initialize the database**
```bash
python app.py
```

6. **Run the application**
```bash
flask run
```

### Heroku Deployment

1. **Create a Heroku app**
```bash
heroku create btcbuzzbot-yourname
```

2. **Configure Heroku environment variables**
```bash
heroku config:set TWITTER_API_KEY=your_api_key
heroku config:set TWITTER_API_SECRET=your_api_secret
heroku config:set TWITTER_ACCESS_TOKEN=your_access_token
heroku config:set TWITTER_ACCESS_TOKEN_SECRET=your_access_secret
heroku config:set COINGECKO_API_KEY=your_coingecko_api_key
heroku config:set POST_TIMES=08:00,12:00,16:00,20:00
heroku config:set TIMEZONE=UTC
heroku config:set SECRET_KEY=your_secret_key
```

3. **Deploy to Heroku**
```bash
git push heroku master
```

## 🖥️ Web Interface

The application includes a web interface with the following features:

- **Home Page**: View current Bitcoin price, bot statistics, and recent tweets
- **Tweet History**: Browse all tweets with filtering and pagination
- **Admin Panel**: Control bot operation, view error logs, and manage content

### Dashboard URLs

- Home: `/`
- Tweet History: `/posts`
- Admin Panel: `/admin`
- Health Check: `/health`

## 🔄 API Endpoints

The application provides several API endpoints:

- **GET /api/posts**: Retrieve recent posts with pagination and filtering
- **GET /api/stats**: Get bot statistics and Bitcoin price history
- **GET /api/price/refresh**: Manually refresh Bitcoin price data
- **GET /api/price/history**: Get Bitcoin price history for charting

## 🔧 Utility Tools

BTCBuzzBot includes several utility tools for monitoring, analysis, and management:

### Core Tools

- **direct_tweet_fixed.py**: Main script for posting tweets with proper database logging
- **post_tweet_now.py**: Manually trigger a tweet post for testing or one-off posts

### Database Tools

- **list_tables.py**: Show all tables in the database
- **view_data.py**: Display detailed information about each table's structure and data
- **fix_database.py**: Fix database structure issues and ensure schema compatibility

### Reporting Tools

- **generate_report.py**: Generate a summary report of the bot's activity with robust error handling
- **export_data.py**: Export all database tables to CSV files with special character handling

## 📊 Data Analysis

### Viewing Database Structure

```bash
python list_tables.py
```

### Viewing Database Content

```bash
python view_data.py
```

### Generating Status Reports

```bash
python generate_report.py
```

### Exporting Data

```bash
python export_data.py
```

This will create CSV files in the `exports` directory with robust handling of special characters and date formats.

## ⚙️ Configuration

The system uses the following configuration sources:

1. **Environment Variables**: Twitter API credentials and application settings
2. **Database**: Scheduled posting times and content preferences

### Required Python Modules

- **Core Functionality**: sqlite3 (included in Python standard library)
- **Twitter Posting**: tweepy (optional - fallback to simulation mode if unavailable)
- **Price Fetching**: requests (optional - uses default values if unavailable)
- **Environment Loading**: python-dotenv (optional - for loading .env files)
- **Web Interface**: Flask and extensions

## 🔄 Operational Modes

- **Full Mode**: Posts to Twitter and updates the database
- **Simulation Mode**: For environments without Twitter API access, simulates posting and updates database
- **Scheduled Mode**: Runs on a schedule defined in the database
- **Manual Mode**: Trigger posts manually via web interface or `post_tweet_now.py`

## 🛠️ Troubleshooting

If you encounter issues:

1. Check the bot status in the database using the reporting tool
2. Verify that the database structure is correct with `view_data.py`
3. Use `fix_database.py` to repair any schema issues
4. Examine the logs in the web interface

## ⚠️ Disclaimer

BTCBuzzBot is for informational purposes only. The content provided should not be construed as financial advice. Always do your own research before making investment decisions.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📧 Contact

For questions or support, please open an issue on this repository.

# BTCBuzzBot Tools

A collection of tools for the BTCBuzzBot Twitter bot that posts Bitcoin price updates.

## Overview

BTCBuzzBot is a Twitter bot that automatically posts Bitcoin price updates with motivational quotes or jokes. It stores data in an SQLite database and can operate in two modes:

1. **Real Posting Mode**: Posts actual tweets to Twitter using the Twitter API
2. **Simulation Mode**: Simulates tweets and logs them to the database without actually posting to Twitter

## Available Tools

### Core Tools

- **direct_tweet_fixed.py**: Main script for posting tweets with proper database logging
- **post_tweet_now.py**: Manually trigger a tweet post for testing or one-off posts

### Database Tools

- **list_tables.py**: Show all tables in the database
- **view_data.py**: Display detailed information about each table's structure and data
- **fix_database.py**: Fix database structure issues

### Reporting Tools

- **generate_report.py**: Generate a summary report of the bot's activity
- **export_data.py**: Export all database tables to CSV files for external analysis

## Usage Instructions

### Viewing Database Structure

```
python list_tables.py
```

### Viewing Database Content

```
python view_data.py
```

### Manually Posting a Tweet

```
python post_tweet_now.py
```

### Generating a Status Report

```
python generate_report.py
```

### Exporting Data

```
python export_data.py
```
This will create CSV files in the `exports` directory.

## Configuration

The system uses the following configuration sources:

1. **Environment Variables**: Twitter API credentials should be set as environment variables
   - TWITTER_API_KEY
   - TWITTER_API_SECRET
   - TWITTER_ACCESS_TOKEN
   - TWITTER_ACCESS_TOKEN_SECRET

2. **Database Configuration**: Scheduled posting times are stored in the `scheduler_config` table

## Required Python Modules

- **Core Functionality**: sqlite3 (included in Python standard library)
- **Twitter Posting**: tweepy (optional - only required for actual Twitter posting)
- **Price Fetching**: requests (optional - only required for real-time price data)
- **Environment Loading**: python-dotenv (optional - for loading .env files)

## Automatic vs. Manual Operation

- For automatic scheduled operation, use the scheduler: `python scheduler.py start`
- For manual operation, use the post_tweet_now.py script

## Troubleshooting

If you encounter issues:

1. Check the bot status in the database using the report tool
2. Verify that the database structure is correct
3. Ensure Twitter API credentials are properly set if using real posting mode
4. Check for required Python modules

## Data Exports

The export_data.py script creates the following specialized reports:

- **price_history_*.csv**: Price data with calculated changes
- **post_activity_*.csv**: Tweet activity with additional metrics 