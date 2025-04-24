# Morning Session 4: Code Analysis & Improvement Plan

## 1. Summary of Findings

Based on the code analysis, the application (`BTCBuzzBot`) is designed to:

*   Fetch the current Bitcoin price (from CoinGecko).
*   Generate tweet content based on the current price, recent price change, and potentially additional content (quotes, jokes, or LLM-generated text).
*   Post these *generated* tweets to a configured Twitter account.
*   Store a log of these *outgoing* posts in a database (`posts` table).
*   Display Bitcoin price history and the log of *generated* posts in a Flask-based admin web panel.

**Core Issue:** The user's observation that the "Recent Tweets" only show price-related messages and not "news" is accurate *by design*. The application currently **does not ingest or analyze external tweets from Twitter**. It only tracks and displays the tweets the bot itself creates, which are inherently focused on the price data it fetches.

**Key Components:**

*   **Web Framework:** Flask (`app.py`)
*   **Database:** SQLite or PostgreSQL (`src/database.py`, `app.py` helpers)
*   **Tweet Posting:** `src/tweet_handler.py` orchestrates formatting and posting, using `src/twitter_client.py`.
*   **Price Fetching:** `src/price_fetcher.py`
*   **Scheduling:** `scheduler.py` (likely runs `tweet_handler` tasks)
*   **LLM Integration:** Optional, via `src/llm_api.py`, `src/llm_integration.py`, `src/scheduler_llm.py`.

**Database Schema (`posts` table):**

*   `id`: Primary key
*   `tweet_id`: ID from Twitter API after posting
*   `tweet`: The **full text of the generated tweet** sent by the bot.
*   `timestamp`: Time the tweet was posted.
*   `price`: BTC price at the time of the tweet.
*   `price_change`: Calculated % change at the time of the tweet.
*   `content_type`: Type of extra content added (e.g., "quote", "joke", "manual", "llm").
*   `likes`, `retweets`: Engagement metrics (potentially updated later via `update_metrics.py`).

There is no mechanism or database field for storing or classifying external tweets as "news".

## 2. Improvement Plan

### 2.1. Goal Clarification

The first step is to decide the desired functionality:

*   **Option A (Status Quo):** Keep the bot posting only its generated price updates + extra content. No changes needed for core functionality, but the understanding of the "Recent Tweets" section is clarified.
*   **Option B (Hybrid):** Add functionality to *also* monitor Twitter for relevant BTC news, analyze it, store it, and display it alongside the bot's own posts.
*   **Option C (News Focus):** Shift the bot's primary purpose to finding, analyzing, and potentially summarizing/retweeting external BTC news. Generated price posts might become secondary or be removed.

**The following plan assumes Option B (Hybrid) is desired.**

### 2.2. Implementation Steps (for Option B)

1.  **Data Ingestion:**
    *   Modify `scheduler.py` or create a new `news_fetcher.py` module.
    *   Use `tweepy` or another Twitter API client to fetch tweets matching specific criteria (e.g., `#Bitcoin`, `$BTC`, mentions of keywords like "breaking news", "regulation", "adoption", potentially filtering by influential accounts).
    *   Implement robust error handling and rate limit management for Twitter API calls.

2.  **Database Schema Changes:**
    *   **Option 1 (New Table):** Create a `news_tweets` table:
        ```sql
        CREATE TABLE IF NOT EXISTS news_tweets (
            id SERIAL PRIMARY KEY, -- Or INTEGER PRIMARY KEY AUTOINCREMENT
            original_tweet_id TEXT UNIQUE NOT NULL,
            author TEXT,
            tweet_text TEXT NOT NULL,
            tweet_url TEXT,
            published_at TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            is_news BOOLEAN DEFAULT FALSE,
            news_score REAL DEFAULT 0.0, -- Optional score from analysis
            sentiment TEXT, -- Optional sentiment analysis
            summary TEXT -- Optional LLM summary
        );
        ```
    *   **Option 2 (Modify `posts`):** Add columns to the existing `posts` table to differentiate:
        *   `is_external BOOLEAN DEFAULT FALSE`
        *   `original_author TEXT`
        *   `original_tweet_text TEXT`
        *   (Potentially others from the `news_tweets` example above).
        *   *Consideration:* This might make the `posts` table less focused. A separate table is likely cleaner.

3.  **Processing & Analysis:**
    *   Create a `news_analyzer.py` module.
    *   Implement logic to process fetched tweets:
        *   **Basic:** Filter based on keywords, author reputation, retweet/like counts.
        *   **Advanced:** Use NLP libraries (like `spaCy`, `NLTK`) or the existing LLM integration (`src/llm_integration.py`) to:
            *   Classify tweets as news vs. noise.
            *   Perform sentiment analysis.
            *   Generate summaries.
    *   Update the `news_tweets` table (or modified `posts` table) with the analysis results.

4.  **Frontend Display (`app.py` & Templates):**
    *   Modify `app.py` route (`/admin` or a new `/news` route).
    *   Create/update database helper functions (e.g., `get_recent_news_tweets()`).
    *   Update the admin panel template (`templates/admin.html` or similar) to display the ingested news tweets.
    *   Consider adding tabs or filters to switch between viewing generated posts and ingested news.

### 2.3. Refactoring Suggestions

*   **Database ORM:** Migrate from raw SQL strings in `src/database.py` and `app.py` to an ORM like SQLAlchemy. This improves code readability, maintainability, and reduces SQL injection risks. Define explicit models for `Post`, `Price`, `NewsTweet`, etc.
*   **Configuration:** Consolidate all configuration settings (API keys, DB paths, file paths, retry limits, schedule times) into `src/config.py` and load them consistently. Avoid scattering `os.environ.get` calls.
*   **`app.py` Size:** Break down the large `app.py` (985 lines). Move database interaction logic, tweet posting logic, and other business logic into dedicated modules within `src/`. `app.py` should primarily handle routes, request/response processing, and calling the appropriate service functions. Create blueprints for different sections (e.g., `admin`, `api`, `main`).
*   **Error Handling:** Implement more specific error handling and logging, especially around API calls (Twitter, CoinGecko) and database interactions.
*   **Async/Sync:** Review the use of `asyncio` (`tweet_handler.py`'s synchronous wrapper). Ensure it integrates correctly with Flask's request lifecycle or consider if full async (using `Quart` or Flask async support) is beneficial/necessary.
*   **Testing:** Improve test coverage (see Section 3).

## 3. Application Function Checks

### 3.1. Manual Testing Checklist

*   **Admin Panel:**
    *   [ ] Does `/admin` load correctly?
    *   [ ] Is the Bitcoin Price History chart displayed with data?
    *   [ ] Does the "Recent Errors" section display errors correctly (or show "No recent errors")?
    *   [ ] Does the "Recent Tweets" table load?
    *   [ ] Does the data in "Recent Tweets" (Time, Tweet, Type, Price, Engagement) look correct based on the `posts` table?
    *   [ ] Do the top buttons ("Post Tweet Now", "Seed Price Data", "LLM Admin") exist?
*   **Functionality:**
    *   [ ] Does clicking "Post Tweet Now" trigger a tweet (check Twitter account and `posts` table)?
    *   [ ] Does clicking "Seed Price Data" populate the `prices` table with historical data?
    *   [ ] If LLM is enabled, does the `/admin/llm` section load and function?
*   **Scheduling:**
    *   [ ] Does the bot post tweets automatically based on the schedule defined (check `scheduler_config` table and `scheduler.py` logs)?
    *   [ ] Is the bot status updated correctly in the `bot_status` table and reflected on the admin panel?
*   **API Endpoints:**
    *   [ ] Test `/health` endpoint.
    *   [ ] Test `/api/posts` endpoint.
    *   [ ] Test `/api/stats` endpoint.
    *   [ ] Test `/api/price/history` endpoint.
    *   [ ] Test `/api/price/refresh` endpoint.

### 3.2. Automated Testing Recommendations

*   **Unit Tests:**
    *   `src/price_fetcher.py`: Test price fetching logic (mock `requests`), price change calculation.
    *   `src/database.py`: Test database operations (store/retrieve prices, posts, etc.) using an in-memory SQLite DB or mocking.
    *   `src/tweet_handler.py`: Test tweet formatting logic, interaction with mocked `db` and `twitter_client`.
    *   `src/twitter_client.py`: Test interaction with the Twitter API (mock `tweepy`).
    *   `src/llm_integration.py` (if used): Test interaction with LLM API (mock API calls).
    *   Other utility functions/modules.
*   **Integration Tests:**
    *   Test the scheduling process (`scheduler.py`) by mocking time and checking if the correct handlers are called.
    *   Test the Flask API endpoints (`/api/*`) using the Flask test client, ensuring they interact correctly with the database and return expected JSON responses.
    *   Test the main user flows like posting a manual tweet through the web interface (if applicable beyond the admin panel).

This plan provides a roadmap for addressing the user's core concern and improving the overall quality and maintainability of the codebase. The next step is to prioritize these changes based on the desired application goals.

## 4. Implementation Progress (Option B - Hybrid)

Based on the initial plan, the following steps have been implemented:

*   [x] **Data Ingestion Framework:**
    *   [x] Created `src/news_fetcher.py` module.
    *   [x] Implemented fetching using `tweepy` (Twitter API v2 Search).
    *   [x] Added basic error handling and bearer token auth.
*   [x] **Database Schema Changes:**
    *   [x] Added `news_tweets` table to `src/database.py` (for SQLite & PostgreSQL).
    *   [x] Added `bot_status` and `scheduler_config` tables to central `src/database.py` initialization.
    *   [x] Added relevant methods (`store_news_tweet`, `get_unprocessed_news_tweets`, `update_news_tweet_analysis`, `log_bot_status`, `get_scheduler_config`, `update_scheduler_config`) to `src/database.py`.
*   [x] **Processing & Analysis:**
    *   [x] Created `src/news_analyzer.py` module.
    *   [x] Implemented basic keyword analysis.
    *   [x] Integrated VADER for sentiment analysis (requires package).
    *   [x] Integrated Groq LLM for news classification and summarization (requires package & API key).
    *   [x] Implemented logic to update `news_tweets` table with analysis results.
*   [x] **Scheduler Integration & Refactoring:**
    *   [x] Refactored the original `scheduler.py` into `src/scheduler_tasks.py`, `src/scheduler_engine.py`, and `src/scheduler_cli.py`.
    *   [x] Switched from manual loop to `APScheduler`.
    *   [x] Resolved numerous APScheduler + `asyncio` integration issues (`BackgroundScheduler` vs `AsyncIOScheduler`, `asyncio.run()` conflicts, `await` usage).
    *   [x] Integrated news fetcher and analyzer jobs into the APScheduler engine with appropriate intervals and async execution.
    *   [x] Refactored scheduler DB interactions to use the central `src/database.py` module.
*   [x] **Frontend Display:**
    *   [x] Added `get_potential_news` helper function to `app.py`.
    *   [x] Added a new "Potential News Tweets" table section to `templates/admin.html`.
*   [x] **Tweet Posting Logic:**
    *   [x] Modified `post_tweet_and_log` in `src/scheduler_tasks.py` to randomly select content type (price/quote/joke) and fetch content from DB.
*   [x] **Dependencies & Environment:**
    *   [x] Added `pytz`, `vaderSentiment`, `groq` to `requirements.txt`.
*   [x] **Deployment & Debugging:**
    *   [x] Resolved various environment setup issues (pip, venv).
    *   [x] Fixed Python import errors.
    *   [x] Corrected multiple `IndentationError`s.
    *   [x] Fixed Twitter API query issues (`$BTC` operator) by correcting default in `src/config.py`.
    *   [x] Fixed Twitter authentication issues (Bearer Token requirement, `get_me()` removal).
    *   [x] Improved logging accuracy (fetcher task wrapper, shutdown).
    *   [x] Verified Fetch/Store/Analyze pipeline is functional locally.
    *   [x] Fixed `Procfile` worker command to use `scheduler.py start`.
    *   [x] Fixed `NameError: name 'logger' is not defined` in `app.py`.
    *   [x] Fixed `jinja2.exceptions.UndefinedError: 'bot_status' is undefined` in `app.py`.
    *   [x] Fixed `jinja2.exceptions.UndefinedError: 'schedule' is undefined` in `app.py`.
    *   [x] **Successfully deployed to Heroku.**
    *   [x] **Confirmed `/admin` page loads correctly on Heroku.**

## 5. Current Status, Issues, and Next Steps

**Current Status:**

*   The application is **successfully deployed to Heroku**. 
*   The **`/admin` web interface is loading correctly**. 
*   The core pipeline for fetching external tweets, storing them, and running analysis placeholders **is functional on Heroku** (verified via local testing previously).
*   The **worker dyno is running the correct `APScheduler`-based scheduler code** due to the `Procfile` fix.
*   The tweet posting logic uses randomized content types (price/quote/joke).

**Current Issues/Areas for Improvement:**

1.  **Scheduled Tweet Verification (Heroku):** The primary user issue (repetitive tweets) has been addressed in code, but **not yet verified** by observing a scheduled tweet post running **on Heroku** with the new scheduler and logic.
2.  **Database Schema (PostgreSQL):** Logs from previous worker runs (using old code) indicated the `last_used` column in `quotes`/`jokes` might be `TEXT` instead of `TIMESTAMP WITH TIME ZONE` in the Heroku PostgreSQL DB. This *could* cause errors in the *new* `get_random_content` function if not fixed manually.
3.  **Analysis Activation:** Sentiment (VADER) and LLM (Groq) analysis are currently skipped due to missing packages/API keys by default.
4.  **Frontend Display Needs Update:** The "Potential News Tweets" table does not yet display `sentiment` or `summary` data.
5.  **LLM API Registration:** The `Failed to register Ollama LLM API: 'Flask' object has no attribute 'before_first_request'` error appears during startup (due to Flask deprecation). Needs fixing if LLM features are used.
6.  **Twitter API Rate Limiting (Monitoring):** The fetch frequency (15 min) might still be too high for the free API tier long-term. Needs monitoring on Heroku.
7.  **LLM Analysis Quality/Cost:** If enabled, LLM prompts and scoring need evaluation and refinement.
8.  **Configuration Hardcoding:** Some parameters (scheduler intervals, analysis keywords, fetcher `max_results`) remain hardcoded.

**Next Steps (Recommended Order):**

1.  **Verify Scheduled Tweet Posting (Heroku):**
    *   **Action:** Monitor Heroku logs for the `worker` dyno (`heroku logs --tail --app btcbuzzbot --dyno worker`) around the next scheduled post time (e.g., 12:00, 16:00, 20:00 UTC).
    *   **Observe:**
        *   Confirm the correct `post_tweet_and_log` task runs.
        *   Note the `content_type` selected (`price`, `quote`, or `joke`).
        *   Check the bot's Twitter account to see the actual tweet posted by Heroku.
        *   Confirm the tweet content is varied.
        *   Check the `posts` table in the database for the log entry.
    *   **Goal:** Confirm the randomized content logic resolves the original repetitive tweet issue **in the deployed environment**.

2.  **(Recommended) Fix DB Schema:**
    *   **Action:** Connect to Heroku Postgres (`heroku pg:psql --app btcbuzzbot`) and run the `ALTER TABLE` commands mentioned previously to change `last_used` columns in `quotes` and `jokes` to `TIMESTAMP WITH TIME ZONE`.
    *   **Goal:** Prevent potential errors when `get_random_content` is called by the scheduled tweet task.

3.  **Update Frontend Display:**
    *   **Action:** Modify `templates/admin.html` to add columns for "Sentiment" and "Summary" to the "Potential News Tweets" table.
    *   **Action:** Use Jinja templating to display `news_item.sentiment` and `news_item.summary` in the new columns. Commit & redeploy.

4.  **(Optional) Enable & Evaluate Analysis:**
    *   **Action:** Set `GROQ_API_KEY` in Heroku config vars. Ensure `vaderSentiment` installed correctly during build.
    *   **Action:** Monitor worker logs for successful analysis execution.
    *   **Action:** Evaluate the quality of classification/summaries.
    *   **Action:** Refine prompts/scoring in `src/news_analyzer.py` as needed. Commit & redeploy.

5.  **Monitor Rate Limiting:**
    *   **Action:** Check logs periodically for Twitter Rate Limit errors (429).
    *   **Action:** If errors occur, adjust fetch frequency/count and redeploy.

6.  **Fix LLM API Registration:**
    *   **Action:** Update the registration logic in `src/llm_api.py` to avoid the deprecated `before_first_request` if LLM features will be used.

7.  **Move Configuration:**
    *   **Action:** Move hardcoded values into `src/config.py` / Heroku config vars. 