# BTCBuzzBot

<div align="center">
  <img src="static/img/favicon.png" alt="BTCBuzzBot Logo" width="120" height="120">
  <h3>A Bitcoin Price & News Twitter Bot</h3>
  <p>Monitoring Bitcoin trends and posting updates with insights and personality!</p>
  <p><a href="https://twitter.com/BTCBuzzBot" target="_blank"><strong>Follow the Bot on Twitter: @BTCBuzzBot</strong></a></p> 
</div>

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/TStaniulis/BTCBuzzBot)
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
  - [Local Development (Primarily for Web UI Testing)](#local-development-primarily-for-web-ui-testing)
  - [Heroku Deployment (Recommended)](#heroku-deployment-recommended)
- [⚙️ Environment Variables](#️-environment-variables)
- [🖥️ Web Interface](#️-web-interface)
- [🔄 Core Logic](#-core-logic)
- [🔧 Troubleshooting](#-troubleshooting)
- [⚠️ Disclaimer](#️-disclaimer)
- [📄 License](#-license)
- [📧 Contact](#-contact)

---

## 📊 Overview

**BTCBuzzBot** is an automated Twitter bot designed to:

1.  Post real-time Bitcoin price updates combined with motivational quotes or jokes.
2.  Fetch recent Bitcoin-related tweets from the Twitter Search API.
3.  Analyze fetched tweets using the Groq LLM API (currently Llama 3 8B) to determine sentiment, news significance, and generate summaries.
4.  Provide a web dashboard for monitoring bot activity, viewing analyzed news, and controlling operations.

## ✨ Features

- **Automated Price Tweets**: Fetches real-time Bitcoin prices (via CoinGecko) and posts scheduled updates including 24h price change.
- **Content Variety**: Rotates scheduled posts between price updates, motivational quotes, and crypto jokes fetched from an internal database.
- **News Fetching & Analysis**: Periodically fetches recent Bitcoin-related tweets using the Twitter Search API v2.
- **LLM Integration (Groq)**: Analyzes fetched news tweets for:
    - Sentiment (Positive/Negative/Neutral)
    - News Significance (Low/Medium/High)
    - Concise Summary
- **Twitter Integration**: Posts updates to Twitter via the Tweepy library using Twitter API v2.
- **Scheduled Operations**: Uses APScheduler running in a separate Heroku worker dyno. Posting schedule is configurable via the Admin dashboard.
- **Admin Dashboard**: Web interface (Flask) for monitoring bot status, viewing recent posts, analyzed news tweets, and updating the posting schedule.
- **Database**: Uses PostgreSQL on Heroku (or SQLite locally) to store prices, quotes, jokes, posts, fetched news tweets, analysis results, and configuration.
- **Configuration via Environment**: Key settings managed via environment variables for easy deployment.
- **Mobile-Responsive UI**: Dark-themed interface built with Bootstrap 5.

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, Flask, APScheduler
- **Database**: PostgreSQL (production via Heroku Postgres), SQLite (local dev)
- **Libraries**: Tweepy (Twitter), Requests (HTTP), Groq (LLM), Psycopg2 (Postgres), aiosqlite (Async SQLite), VADER Sentiment (basic sentiment fallback), python-dotenv
- **APIs**: Twitter API v2 (Search & Post), Groq API, CoinGecko API (via `price_fetcher`)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Deployment**: Heroku (web + worker dynos)

## 📋 Requirements

- Python 3.11+
- Twitter Developer Account with Elevated access (for API v2 Search) & App Keys/Tokens
- Groq API Key
- Heroku account with Heroku CLI installed (for deployment)
- PostgreSQL Add-on on Heroku (automatically provides `DATABASE_URL`)

## 🚀 Setup & Installation

### Local Development (Primarily for Web UI Testing)

*Note: Running the full scheduler and tweet posting locally requires careful environment setup matching production.*

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/btcbuzzbot.git # Replace with your repo URL
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
    Create a `.env` file in the root directory. See the **Environment Variables** section below for required keys. For local testing, you might only need `FLASK_APP`, `FLASK_ENV`, `SECRET_KEY`, and potentially `DATABASE_URL` pointing to a local Postgres instance or leave it blank to use the default `btcbuzzbot.db` SQLite file.

5.  **Run the Web Application**
    ```bash
    flask run
    ```
    This will start the Flask web server. Access the dashboard at `http://127.0.0.1:5000` (or the specified port).

### Heroku Deployment (Recommended)

1.  **Login to Heroku CLI**
    ```bash
    heroku login
    ```

2.  **Create a Heroku app**
    ```bash
    heroku create your-app-name # Replace with your desired app name
    ```

3.  **Add PostgreSQL Add-on**
    ```bash
    heroku addons:create heroku-postgresql:basic # Or other plan
    # This automatically sets the DATABASE_URL config var.
    ```

4.  **Configure Heroku Environment Variables**
    Use the Heroku Dashboard (Settings -> Config Vars) or the CLI (`heroku config:set KEY=VALUE`) to set **all** the required variables listed in the **Environment Variables** section below.

5.  **Deploy to Heroku**
    ```bash
    git push heroku your_local_branch:main # e.g., git push heroku master:main
    ```
    Heroku will build the app using `requirements.txt` and run it based on the `Procfile` (which defines the `web` and `worker` processes).

6.  **Scale Dynos**
    Ensure you have both `web` (for the dashboard) and `worker` (for the scheduler) dynos running. The `Procfile` defines these process types.
    ```bash
    heroku ps:scale web=1 worker=1
    ```

## ⚙️ Environment Variables

These variables are crucial for configuring the application, especially on Heroku.

**Required:**

-   `DATABASE_URL`: Connection string for the PostgreSQL database (automatically set by Heroku Postgres add-on).
-   `TWITTER_API_KEY`: Your Twitter App API Key (for authentication).
-   `TWITTER_API_SECRET`: Your Twitter App API Secret Key (for authentication).
-   `TWITTER_ACCESS_TOKEN`: Your Twitter App Access Token (for posting tweets).
-   `TWITTER_ACCESS_TOKEN_SECRET`: Your Twitter App Access Token Secret (for posting tweets).
-   `TWITTER_BEARER_TOKEN`: Your Twitter App Bearer Token (used for Twitter API v2 Search endpoint).
-   `GROQ_API_KEY`: Your Groq Cloud API Key (for LLM analysis).
-   `SECRET_KEY`: A random secret string for Flask session security (important for production).

**Optional (with Defaults):**

-   `GROQ_MODEL`: Groq model to use (default: `llama3-8b-8192`).
-   `LLM_ANALYZE_TEMP`: Temperature for LLM analysis (default: `0.2`).
-   `LLM_ANALYZE_MAX_TOKENS`: Max tokens for LLM analysis response (default: `150`).
-   `NEWS_FETCH_INTERVAL_MINUTES`: How often to fetch news (default: `720`).
-   `NEWS_FETCH_MAX_RESULTS`: Max tweets per fetch (default: `5`).
-   `NEWS_ANALYSIS_INTERVAL_MINUTES`: How often to run news analysis (default: `30`).
-   `NEWS_ANALYSIS_BATCH_SIZE`: Max tweets to analyze per cycle (default: `30`).
-   `TWEET_CONTENT_TYPES`: Comma-separated types (default: `price,quote,joke`).
-   `TWEET_CONTENT_WEIGHTS`: Comma-separated weights corresponding to types (default: `0.4,0.3,0.3`).
-   `DUPLICATE_POST_CHECK_MINUTES`: Interval to check for duplicate posts (default: `5`).
-   `CONTENT_REUSE_DAYS`: Minimum days before reusing quotes/jokes (default: `7`).
-   `PRICE_FETCH_MAX_RETRIES`: Retries for fetching BTC price (default: `3`).
-   `DEFAULT_TWEET_HASHTAGS`: Default hashtags added to tweets (default: `#Bitcoin #Crypto`).
-   `MAX_TWEET_LENGTH`: Max characters for tweets (default: `280`).
-   `SCHEDULER_GRACE_TIME_SECONDS`: APScheduler job grace time (default: `120`).
-   `LOG_LEVEL`: Log level for the application (e.g., `INFO`, `DEBUG`, default: `INFO`).

## 🖥️ Web Interface

The application includes a web interface accessible when deployed:

- **Home Page (`/`)**: View current Bitcoin price, basic bot statistics, and recent posts.
- **Tweet History (`/posts`)**: Browse logged posts.
- **Admin Panel (`/admin`)**: View basic stats, recent posts, analyzed news tweets (with sentiment/summary), and update the tweet schedule.
- **Health Check (`/health`)**: Simple health check endpoint.

## 🔄 Core Logic

- **Scheduler (`worker` dyno)**: Runs defined jobs using APScheduler.
    - `fetch_news_tweets`: Fetches recent tweets via `NewsFetcher`.
    - `analyze_news_tweets`: Analyzes fetched tweets using `NewsAnalyzer` (calls Groq API).
    - `scheduled_tweet_X`: Posts tweets (price/quote/joke) at scheduled times using `TweetHandler`.
    - `reschedule_tweet_jobs`: Periodically updates the scheduler based on the schedule stored in the database (editable via Admin panel).
- **Web App (`web` dyno)**: Serves the Flask dashboard, handles API requests, and allows schedule updates.
- **Database**: Central storage for all operational data and configuration.

## 🔧 Troubleshooting

If you encounter issues:

1.  **Check Heroku Logs:** The primary source for debugging.
    ```bash
    heroku logs --tail --app your-app-name
    # Filter by dyno if needed
    heroku logs --tail --app your-app-name --dyno worker
    heroku logs --tail --app your-app-name --dyno web
    ```
2.  **Check Heroku App Status:** Ensure both `web` and `worker` dynos are running (`heroku ps --app your-app-name`).
3.  **Verify Config Vars:** Double-check all required environment variables are set correctly in Heroku Dashboard -> Settings -> Config Vars.
4.  **Check Database Connection:** Use `heroku pg:psql --app your-app-name` to connect and inspect tables if necessary.
5.  **Review Code & Commits:** Check recent code changes if the issue started after a deployment.

## ⚠️ Disclaimer

BTCBuzzBot is for informational and entertainment purposes only. The content provided should not be construed as financial advice. Always do your own research before making investment decisions.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## 📧 Contact

For questions or support, please open an issue on this repository. 