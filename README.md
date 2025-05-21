# BTCBuzzBot

<div align="center">
  <img src="static/img/favicon.png" alt="BTCBuzzBot Logo" width="120" height="120">
  <h3>A Multi-Platform Bitcoin Price, News & Sentiment Bot</h3>
  <p>Real-time Bitcoin updates, news analysis, and cross-platform engagement with personality!</p>
  <p><a href="https://twitter.com/BTCBuzzBot" target="_blank"><strong>Follow the Bot on Twitter: @BTCBuzzBot</strong></a></p> 
</div>

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/DITreneris/btcbuzzbot)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3112/)
[![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey)](https://flask.palletsprojects.com/)
[![Twitter API](https://img.shields.io/badge/Twitter%20API-v2-1DA1F2)](https://developer.twitter.com/en/docs/twitter-api)
[![Groq API](https://img.shields.io/badge/Groq-LLM%20API-green)](https://groq.com/)
[![Heroku](https://img.shields.io/badge/Heroku-Deployed-purple)](https://btcbuzzbot-7c02c485f88e.herokuapp.com/)

---

**Table of Contents**

- [📊 Overview](#-overview)
- [✨ Features](#-features)
- [🛠️ Technology Stack](#️-technology-stack)
- [📋 Requirements](#-requirements)
- [🚀 Setup & Installation](#-setup--installation)
- [⚙️ Environment Variables](#️-environment-variables)
- [🖥️ Web Interface](#️-web-interface)
- [🔄 Core Logic](#-core-logic)
- [🔧 Troubleshooting](#-troubleshooting)
- [⚠️ Disclaimer](#️-disclaimer)
- [📄 License](#-license)
- [📧 Contact](#-contact)

---

## 📊 Overview

**BTCBuzzBot** is a multi-platform bot that:

- Posts real-time Bitcoin price updates, news, and sentiment analysis to **Twitter, Discord, and Telegram**.
- Analyzes Bitcoin-related news using the Groq LLM API (Llama 3 8B) for sentiment, significance, and summary.
- Provides a modern web dashboard for monitoring, analytics, and admin control.
- Offers robust scheduling, fallback logic, and automated testing for reliability.

## ✨ Features

- **Multi-Platform Posting**: Simultaneously posts to Twitter, Discord, and Telegram channels.
- **Automated Price & News Tweets**: Fetches real-time Bitcoin prices (CoinGecko) and posts scheduled updates, including 24h price change.
- **Content Variety**: Rotates posts between price updates, motivational quotes, and crypto jokes from an internal database.
- **News Fetching & LLM Analysis**: Periodically fetches Bitcoin-related tweets and analyzes them for:
    - Sentiment (Positive/Negative/Neutral)
    - News Significance (Low/Medium/High)
    - Concise Summary
- **Admin Dashboard**: Web interface for monitoring bot status, viewing recent posts, analyzed news, sentiment trends, and updating the posting schedule.
- **Sentiment Trend Visualization**: Displays 7-day sentiment trends and news analysis statistics in the admin panel.
- **Configurable Scheduler**: Flexible posting schedule, easily updated via the admin UI.
- **Database**: Uses PostgreSQL (Heroku) or SQLite (local) to store all operational data, news, analysis, and content.
- **Automated Testing**: Comprehensive unit and integration tests for all major components, including Telegram and Discord posting.
- **Status Panel**: Live status indicators for API, Twitter, Discord, Telegram, and database health.
- **Mobile-Responsive UI**: Modern, dark-themed interface built with Bootstrap 5.
- **Robust Error Handling**: Detailed logging, fallback logic, and admin alerts for failures.

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, Flask, APScheduler
- **Database**: PostgreSQL (Heroku), SQLite (local dev)
- **Libraries**: Tweepy, Requests, Groq, Psycopg2, aiosqlite, VADER Sentiment, python-dotenv, aiohttp
- **APIs**: Twitter API v2, Groq API, CoinGecko API
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Deployment**: Heroku (web + worker dynos)

## 📋 Requirements

- Python 3.11+
- Twitter Developer Account (API v2 access)
- Groq API Key
- Heroku account with Heroku CLI
- PostgreSQL Add-on on Heroku
- Discord Webhook URL (for Discord posting)
- Telegram Bot Token & Chat ID (for Telegram posting)

## 🚀 Setup & Installation

### Local Development

1.  **Clone the repository**
    ```bash
    git clone https://github.com/DITreneris/btcbuzzbot.git
    cd btcbuzzbot
    ```
2.  **Set up a virtual environment**
    ```bash
    python -m venv venv
    # On Windows: venv\Scripts\activate
    # On macOS/Linux: source venv/bin/activate
    ```
3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure environment variables**
    Create a `.env` file in the root directory. See the **Environment Variables** section below for required keys.
5.  **Run the Web Application**
    ```bash
    flask run
    ```

### Heroku Deployment

1.  **Login to Heroku CLI**
    ```bash
    heroku login
    ```
2.  **Create a Heroku app**
    ```bash
    heroku create your-app-name
    ```
3.  **Add PostgreSQL Add-on**
    ```bash
    heroku addons:create heroku-postgresql:basic
    ```
4.  **Configure Heroku Environment Variables**
    Use the Heroku Dashboard or CLI to set all required variables (see below).
5.  **Deploy to Heroku**
    ```bash
    git push heroku main
    ```
6.  **Scale Dynos**
    ```bash
    heroku ps:scale web=1 worker=1
    ```

## ⚙️ Environment Variables

**Required:**
- `DATABASE_URL`: PostgreSQL connection string
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`, `TWITTER_BEARER_TOKEN`: Twitter API credentials
- `GROQ_API_KEY`: Groq LLM API key
- `SECRET_KEY`: Flask session secret
- `DISCORD_WEBHOOK_URL`: Discord webhook for posting
- `ENABLE_DISCORD_POSTING`: Set to `true` to enable Discord posting
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Telegram channel/chat ID
- `ENABLE_TELEGRAM_POSTING`: Set to `true` to enable Telegram posting

**Optional:**
- `GROQ_MODEL`, `LLM_ANALYZE_TEMP`, `LLM_ANALYZE_MAX_TOKENS`, `NEWS_FETCH_INTERVAL_MINUTES`, `NEWS_FETCH_MAX_RESULTS`, `NEWS_ANALYSIS_INTERVAL_MINUTES`, `NEWS_ANALYSIS_BATCH_SIZE`, `TWEET_CONTENT_TYPES`, `TWEET_CONTENT_WEIGHTS`, `DUPLICATE_POST_CHECK_MINUTES`, `CONTENT_REUSE_DAYS`, `PRICE_FETCH_MAX_RETRIES`, `DEFAULT_TWEET_HASHTAGS`, `MAX_TWEET_LENGTH`, `SCHEDULER_GRACE_TIME_SECONDS`, `LOG_LEVEL`

## 🖥️ Web Interface

- **Home Page**: Current BTC price, bot stats, recent posts, and status panel
- **Tweet History**: Browse all posts with filters
- **Admin Panel**: Monitor bot status, view analyzed news, sentiment trends, update schedule, manage content
- **Health Check**: `/health` endpoint for uptime monitoring

## 🔄 Core Logic

- **Scheduler**: APScheduler jobs for news fetching, analysis, and scheduled posting
- **NewsFetcher**: Fetches Bitcoin news tweets
- **NewsAnalyzer**: Analyzes news with Groq LLM and VADER fallback
- **TweetHandler**: Formats and posts content to all platforms
- **Discord/Telegram Poster**: Async posting to Discord and Telegram
- **Fallback Logic**: Uses quotes/jokes if no suitable news is found
- **Admin UI**: Full-featured dashboard for monitoring and control
- **Database**: Stores all operational and analytics data

## 🔧 Troubleshooting

1. **Check Heroku Logs:**
    ```bash
    heroku logs --tail --app your-app-name
    ```
2. **Check App Status:**
    ```bash
    heroku ps --app your-app-name
    ```
3. **Verify Config Vars:**
    - Ensure all required environment variables are set (including Discord/Telegram)
4. **Check Database Schema:**
    - Ensure all required columns exist (see migration instructions in docs)
5. **Review Code & Commits:**
    - Check for recent changes if issues arise

## ⚠️ Disclaimer

BTCBuzzBot is for informational and entertainment purposes only. The content provided should not be construed as financial advice. Always do your own research before making investment decisions.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## 📧 Contact

For questions or support, please open an issue on this repository or contact the maintainer via GitHub. 