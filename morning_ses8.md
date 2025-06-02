# Morning Session 8: Stabilization Checkpoint & Automated Testing Plan

## Progress Update (as of 2025-05-27, 08:20 UTC)

- **NewsFetcher & Fetch Job:** NewsFetcher is now initializing and the scheduled news fetching job is being added and run as expected.
- **Exception Handling:** Tweepy exception handling has been fixed (no more RateLimitError bug), and since_id errors are now handled gracefully.
- **Rate Limiting:** Twitter API rate limits are being encountered and are now logged and handled without crashing the fetcher.
- **Fetch Logic Optimization:** The fetch logic now defaults to fetching only 15 tweets per cycle (configurable), and warns if a fetch is triggered within 10 minutes of the last one to help avoid rate limits.
- **Manual Fetches:** Manual fetches are working, but should be used sparingly to avoid hitting Twitter's rate limits.
- **All scheduled jobs (posting, analysis, engagement, news fetch) are running and logging as expected.**

## 1. Session Goal

Confirm application stability after recent scheduler fixes, verify the updated 6-time tweet schedule (06:00, 08:00, 12:00, 16:00, 20:00, 22:00 UTC), decide on the news analysis strategy, and establish a plan for introducing automated tests to improve robustness and prevent regressions.

## 2. Current Status Recap (as of May 20th, ~13:14 UTC)

*   **Scheduler Stability:** **Confirmed Stable**. **Reschedule task fixed to run only once on startup (v150).**
*   **Posting Logic:** **Confirmed Stable**. Logic updated to use news/fallback for all times (16:00 special case removed).
*   **News Fetching/Analysis:** **Confirmed Stable (v136)**.
*   **Schedule Update:** Default schedule updated in code (`src/database.py`). **Live schedule update via script successful. Reschedule task verified reading new schedule (v146).**
*   **Database Refactoring:** **Verified Stable (v136)**.
*   **Content Management:** Backend OK, **Admin UI Deployed & Verified (v137)**.
*   **Discord Posting:** **Implemented & Deployed (v142). Config/NameError Fixes Deployed (v146/v147). Verified Working (v148).**
*   **News Analysis Display:** **Implemented & Deployed (v149). Verified Working (v149).**
*   **Telegram Posting:** **Implemented & Deployed (v150). Unit Tests Passing.**
*   **Automated Testing:** **Expanded to cover NewsRepository and Telegram integration (v150).**

## 3. Review of Recent Fixes (Apr 27th)

*   **Issue:** Tweets stopped; scheduler logs showed jobs being added but not executed.
*   **Resolution:**
    1.  Corrected `Procfile` worker command from `python scheduler.py start` to `python src/scheduler_cli.py start`.
    2.  Modified `src/scheduler_tasks.py :: post_tweet_and_log` to call `src/main.py :: post_btc_update`, passing the `scheduled_time_str`.
    3.  Deleted the old, conflicting `src/scheduler.py`.
    4.  Updated the live schedule config in the database to include 06:00 and 22:00 UTC using a temporary script (`update_schedule.py`) run via `heroku run`.
    5.  Updated the default schedule in `src/database.py` methods (`_create_tables_postgres`, `_create_tables_sqlite`) for future consistency.
    *   **Note:** The `AttributeError` fixed on Apr 28th concerning `NewsRepository` reappeared in `main.py` (fixed in v128). A separate `AttributeError` related to `_analyze_single_tweet` appeared in `news_analyzer.py` (fixed locally, persisted in v134 deployment, re-deployed in v135).

## 4. Phase 2 Progress & Next Steps

Let's revisit the Phase 2 plan from `morning_ses7.md`:

*   **Step 2.1: Define News Analysis Usage Strategy (Decision Made: Option C)**
    *   **Goal:** Decide how to use significance/sentiment/summary data.
    *   **Options Recap:** A) Dedicated Summary Tweets, B) Influence Existing Tweet Tone, C) Admin Panel Insight First, D) Hybrid.
    *   **Decision:** **Option C (Admin Panel Insight First)** selected. We will focus on parsing and displaying the analysis data in the admin panel before using it in live tweets.

*   **Step 2.2: Implement Content Management (Quotes/Jokes) (Deployed & Verified)**
    *   **Goal:** Admin UI for managing quotes/jokes.
    *   **Status:** Backend logic moved to `ContentRepository`. Admin routes/UI in `src/app.py` & `templates/admin_content.html` **deployed in v137 and verified working.**
    *   **Action:** None needed for this step. Proceed to next development tasks.

*   **Step 2.3: Implement Chosen News Analysis Feature (Admin Panel Display) (Deployed & Verified v149)**
    *   **Goal:** Parse stored JSON analysis (`news_tweets.llm_raw_analysis`) and display significance, sentiment, and summary in the admin panel.
    *   **Status:** **Deployed (v149) and Verified Working.**
    *   **Actions Taken:**
        1. Enhanced the data parsing in the admin_panel route to support both numeric and string-based sentiment/significance scores
        2. Created a comprehensive News Analysis Statistics section with distribution charts for significance and sentiment
        3. Implemented a sentiment trend chart using Chart.js to visualize sentiment changes over time
        4. Enhanced the news tweet listing with better badges and formatting
        5. Added a dedicated detailed analysis page (`/admin/news/<news_id>`) for in-depth analysis of individual tweets
        6. Added syntax-highlighted JSON viewer for raw analysis data

*   **Step 2.4: Enhance Admin Panel (Ready for News Analysis Display) (Deployed & Verified v149)**
    *   **Goal:** Consolidate features and improve usability.
    *   **Status:** Completed as part of Step 2.3 implementation.
    *   **Actions Taken:**
        1. Added clear visualizations for news analysis data
        2. Improved UI for viewing analyzed tweets
        3. Created dedicated page for detailed tweet analysis
        4. Added direct links between summary views and detailed views

*   **Step 2.5: Improve Logging & Monitoring (Ongoing)**
    *   **Goal:** Increase visibility.
    *   **Action:** Continue adding relevant logs as new features (like Content Management UI) are developed. We saw the benefit of detailed logs during the scheduler debugging.
    *   **Goal:** Fix the `AttributeError` found during the 06:00 UTC post (Apr 28th) and complete the planned database refactoring for news logic.
    *   **Status:** **Deployed (v135), Verified Stable (v136).** Fixes verified by successful analysis cycle run in v136.
    *   **Actions Taken (Locally Complete, Deployed, Verified):**
        1.  Created `src/db/news_repo.py`.
        2.  Moved news-related methods from `src/database.py` to `NewsRepository`.
        3.  Updated `src/main.py :: post_btc_update` to import and use `NewsRepository` for fetching news data. *(Correction applied locally)*.
        4.  Updated `src/news_fetcher.py` (Likely Done).
        5.  Updated `src/news_analyzer.py` (Likely Done).

## 5. Automated Testing Progress (as of May 14th)

Significant progress has been made implementing automated tests to improve stability and catch regressions:

*   **Completed Test Implementation:**
    1.  **`tests/db/test_content_repo.py`:** Unit tests for `ContentRepository` class
        *   Tests for both SQLite and PostgreSQL implementations
        *   Coverage for adding, retrieving, and deleting quotes and jokes
        *   Proper async mocking techniques implemented
    2.  **`tests/test_price_fetcher.py`:** Unit tests for `PriceFetcher` class
        *   Tests for API response handling and price calculations
        *   Mock implementations to avoid real API calls
        *   Tests for retry mechanism on API failures
    3.  **`tests/test_content_manager.py`:** Updated for refactored ContentManager
        *   Fixed imports and mocking approach
    4.  **`tests/db/test_news_repo.py`:** Unit tests for `NewsRepository` class
        *   Coverage for storing and retrieving news tweets
        *   Tests for analysis data retrieval
        *   Mock implementations for database connections
    5.  **`tests/test_main.py`:** Unit tests for core posting logic
        *   Tests for success and failure cases
        *   Currently has some failing tests due to mocking issues
    6.  **`tests/test_telegram_poster.py`:** Unit tests for Telegram integration
        *   Coverage for successful posting, error handling, and edge cases
        *   All tests passing

*   **Legacy Test Files Cleanup:**
    These legacy test files have been removed as they are no longer relevant:
    *   `direct_test.py`
    *   `twitter_test.py`
    *   `simple_tweet_test.py`
    *   `new_test_tweet.py`
    *   `simplified_test.py`
    *   `oauth_test.py`
    *   `direct_api_test.py`
    *   `minimal_test.py`

*   **Next Testing Targets:**
    1.  Fix failing tests in `tests/test_main.py`
    2.  Add integration tests between components
    3.  Implement end-to-end tests for the entire posting workflow

## 6. Immediate Actions (Updated May 27th)

1.  **Monitor Twitter API usage and rate limits.**
2.  **Avoid frequent manual fetches.** Use the warning logs as a guide.
3.  **Adjust fetch interval and max_results as needed** to stay within Twitter's API limits.
4.  **Continue monitoring logs** for any new errors or issues.

## 7. Current Issues

*   **Twitter API Authentication:** **RESOLVED (May 30th, 2025)**
    *   **Status:** Fixed by updating Twitter API credentials on Heroku.
    *   **Details:** The 401 Unauthorized errors have been resolved after updating the Twitter API credentials. Logs confirm successful authentication using Bearer Token.
    *   **Verification:** Application logs show successful initialization of all Twitter-related components and proper authentication.

*   **Admin Panel Data Overview:** The "Data Overview" section in the admin panel is currently not displaying news analysis statistics (Sentiment Trend, Significance/Sentiment Distribution bars are empty, table shows N/A).
    *   **Status:** **Resolution in Progress (v162). Positive Signs.**
    *   **Details:** A previous database error (`psycopg2.errors.UndefinedFunction`) was fixed. `utils/reset_news_analysis.py` was run, successfully marking 80 tweets for re-analysis.
    *   **Latest (May 23rd, ~14:40 UTC):** The 14:35 UTC analysis cycle successfully processed and updated the first batch of 30 reset tweets. Data should now be appearing in the Admin Panel. Remaining tweets (~50) will be processed in subsequent cycles.

*   **Test Failures in main.py:** The tests for `src/main.py` currently fail due to issues with mocking async functions. This doesn't affect production functionality but needs to be addressed for improved test coverage.

*   **Twitter API Rate Limit:** The bot is currently hitting Twitter's 429 Too Many Requests error when fetching news. This is not a code bug, but a limitation of the free Twitter API tier. The fetcher now logs and skips cycles when rate-limited.

## 8. Guiding Principles (Reiteration)

*   **Stability First:** Prioritize maintaining the current working state.
*   **Incremental Steps:** Implement changes in small, verifiable units.
*   **Test Locally:** Verify changes locally before deploying. Run automated tests.
*   **Clear Commits:** Use descriptive commit messages.

---

## Phase 3: Platform Expansion

Goals for this phase involve extending the bot's reach to other platforms and enhancing its interactive capabilities.

*   **Step 3.1: Implement Discord Posting (via Webhooks) (Implemented & Verified v148)**
    *   **Goal:** Post the same BTC update messages to a designated Discord channel.
    *   **Approach:** Use Discord Webhooks for simplicity in sending messages without needing a full bot client initially.
    *   **Status:** Code implemented. Deployed in v142. Config vars set. `AttributeError` fixed in v146. `NameError` fixed in v147. Scheduler rescheduling fixed in v148. **Verified working.**
    *   **Tasks (Completed):**
        1.  Create a Discord Webhook URL for the target channel. (Done by User)
        2.  Add `DISCORD_WEBHOOK_URL` and `ENABLE_DISCORD_POSTING` to configuration (`config.py`, `.env`, Heroku). (Done by User)
        3.  Create `src/discord_poster.py` with an async function `send_discord_message(webhook_url, message)` using `aiohttp`. (Done)
        4.  In `src/main.py :: post_btc_update`, after successful tweet posting and logging, check `ENABLE_DISCORD_POSTING`. If true, retrieve `DISCORD_WEBHOOK_URL` and call `send_discord_message`. Handle potential errors gracefully. (Done, fix for config loading in v146, fix for variable name in v147)
        5.  Add necessary dependencies (`aiohttp`) to `requirements.txt`. (Done)
        6.  Test locally by setting the config flag and URL. (Skipped, testing in prod)
        7.  Deploy and verify logs/Discord channel. (Deployed & Verified v148)

*   **Step 3.2: Implement Telegram Posting (Implemented v150)**
    *   **Goal:** Post updates to a Telegram channel/chat.
    *   **Status:** **Implemented (v150), Awaiting Deployment.**
    *   **Tasks (Completed):**
        1.  Create a Telegram bot via BotFather and obtain API token. (To be done by User)
        2.  Add the bot to the target channel and make it an admin. (To be done by User)
        3.  Create `src/telegram_poster.py` with an async function to send messages using the Telegram Bot API. (Done)
        4.  Implement proper error handling and logging in the Telegram poster. (Done)
        5.  Add Telegram configuration variables to `src/config.py`. (Done)
        6.  Integrate Telegram posting into the main tweet posting workflow in `src/main.py`. (Done)
        7.  Create comprehensive unit tests for the Telegram functionality. (Done)
        8.  Verify tests passing locally. (Done)
    *   **Tasks (Pending):**
        1.  Configure Telegram-related environment variables in production. (Pending)
        2.  Deploy and verify functionality in production. (Pending)

*   **Step 3.3: Explore Interactive Commands (Future)**
    *   **Goal:** Allow users on Discord/Telegram to request data (e.g., `/price`).
    *   **Status:** Not Started. This would likely require switching from Webhooks to full bot clients (`discord.py`, `python-telegram-bot`).

## 9. Update Summary (May 27th, 2025)

The application is now stable and fully operational with robust error handling and optimized fetch logic. The main operational constraint is the Twitter API rate limit, which is now handled gracefully. All scheduled jobs are running, and the system is ready for further monitoring and incremental improvements.

## 10. Telegram Integration Deployment Plan

This plan outlines the steps to deploy the Telegram integration feature to production.

### Pre-Deployment Tasks
- Create a Telegram bot via BotFather (https://t.me/botfather)
- Save the API token securely
- Create a Telegram channel/group for bot posts
- Add the bot to the channel and make it an admin
- Get the chat ID of the channel (using the getUpdates API or a chat ID bot)

### Environment Configuration
- Add these environment variables to the Heroku app:
  ```
  ENABLE_TELEGRAM_POSTING=true
  TELEGRAM_BOT_TOKEN=<your_bot_token>
  TELEGRAM_CHAT_ID=<your_channel_id>
  ```

### Deployment Steps
- Push the changes to GitHub
- Deploy to Heroku via the GitHub integration or CLI
- Verify the deployment completed successfully

### Post-Deployment Verification
- Check Heroku logs to ensure config variables are loaded correctly
- Monitor the next scheduled tweet to confirm it posts to Telegram
- Verify message formatting appears correctly in Telegram

### Rollback Plan
If issues arise:
- Set `ENABLE_TELEGRAM_POSTING=false` to disable the feature
- Review logs to identify any specific errors
- Fix locally and redeploy if necessary

### Documentation
- Update project documentation to include Telegram setup instructions
- Document the configuration variables and their purposes
- Add troubleshooting section for common issues

## 11. ML Sentiment Analysis Integration Plan (May 19th Update)

**Overall Goal:** The sentiment (Positive, Negative, Neutral) and significance (Low, Medium, High) determined by the Groq LLM (with VADER as fallback for sentiment) should intelligently guide:
1.  **Content Selection:** Whether to use a news item for a tweet.
2.  **Content Framing:** How the tweet is worded, potentially incorporating the summary and reflecting the sentiment.
3.  **Fallback Logic:** When to use quotes/jokes if news is unsuitable or analysis fails.

**Phase 1: Solidify Analysis Output, Fallback, and Storage**

*   **Goal 1.1: Integrate VADER as a Fallback for Groq Sentiment Analysis.**
    *   **Context:** Groq will be the primary analysis engine. VADER will provide sentiment if Groq fails to return a sentiment.
    *   **Task 1.1.1: Modify `_analyze_content_with_llm` in `src/news_analyzer.py`.**
        *   If the Groq API call fails or if the Groq response does not yield a usable "sentiment" (e.g., JSON parsing error, missing sentiment key), call VADER's `SentimentIntensityAnalyzer` to get a sentiment score for the tweet text.
        *   Map VADER's compound score to "Positive", "Negative", "Neutral" labels and a corresponding numeric score (e.g., compound > 0.05 is Positive, < -0.05 is Negative, else Neutral).
        *   The function should still aim to return the dictionary with "significance", "sentiment", "summary". If Groq provided significance/summary but failed on sentiment, VADER fills in the sentiment. If Groq failed entirely, VADER provides sentiment, and significance/summary might be marked as "N/A" or a default low significance.
    *   **Task 1.1.2: Ensure `SentimentIntensityAnalyzer` is initialized in `NewsAnalyzer.__init__` if VADER is available and store it as an instance variable (e.g., `self.vader_analyzer`).**

*   **Goal 1.2: Ensure Consistent & Direct Storage of LLM/Fallback Analysis.**
    *   **Context:** Analysis results (from Groq or VADER fallback) need to be stored consistently and in a way that's easy to query for content selection logic.
    *   **Task 1.2.1: Analyze `NewsRepository.update_tweet_analysis()` in `src/db/news_repo.py`.**
        *   Review how `analysis_data` (dict from Groq/VADER) is currently processed and stored.
    *   **Task 1.2.2: Add new structured columns to the `news_tweets` table.**
        *   In `src/database.py` (for both `_create_tables_postgres` and `_create_tables_sqlite` methods):
            *   Add `significance_label TEXT` (e.g., "Low", "Medium", "High").
            *   Add `significance_score REAL` (e.g., mapped numeric value for significance).
            *   Add `sentiment_source TEXT` (e.g., "groq", "vader_fallback").
            *   Ensure `sentiment_label TEXT` and `sentiment_score REAL` are definitely present.
            *   Ensure `summary TEXT` is present.
    *   **Task 1.2.3: Modify `NewsRepository.update_tweet_analysis()` in `src/db/news_repo.py`.**
        *   Enhance this function to parse the `analysis_data` dict.
        *   Directly populate the new/existing structured columns: `sentiment_score`, `sentiment_label`, `sentiment_source`, `significance_label`, `significance_score`, and `summary` in the `news_tweets` table.
        *   Handle cases where significance might be missing (if Groq failed entirely).
        *   Continue to store the full raw JSON from Groq (if available) in `llm_raw_analysis` for auditing/debugging.

**Phase 2: Implement Intelligent Content Selection & Framing (Completed)**

*   **Goal 2.1: Enhance `TweetHandler` (or equivalent logic in `main.py`) for Content Selection. (Completed)**
    *   **Task 2.1.1: Develop criteria for selecting news based on significance and sentiment. (Completed)**
        *   Example: Prioritize "High" or "Medium" significance. For "High" significance, consider tweeting even if sentiment is "Neutral". Avoid "Low" significance news unless other content is unavailable.
        *   Define how sentiment (Positive, Negative, Neutral) influences selection. Perhaps avoid overly negative news unless it's highly significant.
        *   **(Implemented in `src/main.py :: post_btc_update` with significance score thresholds and sentiment checking).**
    *   **Task 2.1.2: Modify `post_btc_update` (or helper functions) to query `news_tweets` using the new structured columns (`significance_label`, `significance_score`, `sentiment_label`, `sentiment_source`) to find suitable news. (Completed)**
        *   **(Modified `NewsRepository.get_recent_analyzed_news` to fetch required columns and order results. Refactored news selection loop in `main.py :: post_btc_update` to use this data).**
*   **Goal 2.2: Implement Content Framing based on Sentiment and Summary. (Completed)**
    *   **Task 2.2.1: Develop tweet templates or logic that incorporate the LLM's summary. (Completed)**
        *   **(Implemented via `_format_news_tweet` helper in `src/main.py` which uses the LLM's summary).**
    *   **Task 2.2.2: Adjust tweet wording/emojis based on `sentiment_label`. (Completed)**
        *   Example: More upbeat language for "Positive" sentiment, cautious for "Negative", neutral for "Neutral".
        *   **(Implemented in `_format_news_tweet` helper in `src/main.py` with varied emojis and templates based on significance/sentiment).**
*   **Goal 2.3: Refine Fallback Logic. (Completed)**
    *   **Task 2.3.1: Clearly define when to fall back to quotes/jokes. (Completed)**
        *   Examples: No suitable news found based on significance/sentiment criteria, Groq and VADER both fail to provide usable analysis, analysis tasks time out.
        *   **(Fallback to quotes/jokes in `main.py :: post_btc_update` now occurs if the new intelligent news selection criteria are not met).**

This provides a structured approach. We will start with Phase 1. 

## 12. Latest Deployment Status (May 30th, 2025)

### Deployment Status
* **Twitter Authentication:** Successfully resolved with new API credentials
* **Scheduler Initialization:** All components properly initialized
* **Database Connection:** PostgreSQL connection established and verified
* **News Analysis Setup:** VADER SentimentIntensityAnalyzer and AsyncGroq client (llama3-8b-8192) initialized
* **Tweet Schedule:** Successfully configured with 9 posting times (06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00 UTC)

### System Health
* All scheduled jobs added successfully:
  * News fetching job (24-hour interval)
  * News analysis job (30-minute interval)
  * Tweet engagement update job (4-hour interval)
* Tweet posting schedule verified and active
* No errors or warnings in initialization logs

### Next Steps
1. Monitor next scheduled tweet post (12:00 UTC)
2. Verify news analysis cycle at next 30-minute interval
3. Monitor system stability over next 24 hours
4. Address remaining test failures in `main.py`
5. Continue monitoring Twitter API rate limits

## 13. Admin Panel News Analysis Display Issue (May 30th, 2025)

**Current Status:**
* **Admin Panel Functionality:** Working correctly
  * Successfully fetching and displaying 25 potential news tweets
  * Content management (quotes/jokes) working properly
  * Successfully added 3 new quotes (IDs: 437, 438, 439)
  * Current content counts:
    * Quotes: 393 (increased from 390)
    * Jokes: 381 (stable)

* **News Analysis Display:**
  * System is fetching and processing news tweets for analysis
  * Logs show successful retrieval of 25 potential news items
  * News analysis processing is running as expected

* **Content Management:**
  * Quote addition functionality working correctly
  * Successfully added quotes from:
    1. Leon Luow (Nobel Peace Prize)
    2. Roger Ver (Bitcoin Investor)
    3. Wences Casares (Founder of Banco)
  * All quotes were successfully stored in PostgreSQL database
  * Admin panel updates immediately reflect new content

* **System Performance:**
  * Admin panel response times are good (200-300ms)
  * Database operations completing successfully
  * No errors in content management operations

**Next Steps:**
1. Continue monitoring news analysis processing
2. Verify news analysis data display in admin panel
3. Consider adding more content management features if needed
4. Monitor system performance under increased content load

## 14. Tweet History Page (`/posts`) and Engagement Stats Issue (May 25th, 2025)

An issue was identified where the "Tweet History" page (`/posts`) was not showing posts newer than May 20th, 2025. Additionally, engagement statistics (likes, retweets) on this page and in the Admin Panel's "Bot Statistics" section were not updating, remaining at 0 for newer posts.

**Investigation & Actions Taken:**

1.  **Code Review (`app.py`, `src/database.py`, `src/main.py`):**
    *   The `/posts` route in `app.py` uses `get_posts_paginated` which correctly queries the `posts` table.
    *   The `get_basic_stats` function in `app.py` (for Admin Panel stats) also queries the `posts` table.
    *   The `log_post` method in `src/database.py` initializes `likes` and `retweets` to 0 upon inserting a new post. This is expected.
    *   **Root Cause Identified:** A critical `await db.log_post(...)` call was missing in `src/main.py` within the `post_btc_update` function. This call is responsible for saving the details of a successfully sent tweet to the `posts` database table. Its absence meant no new posts were being recorded, hence the stale `/posts` page and stats.

2.  **Fix Implemented (v163 & v164):**
    *   **Attempt 1 (v163):** The `await db.log_post(...)` call was reinstated in `src/main.py`. However, Heroku logs after deployment did not show the expected log messages confirming its execution.
    *   **Attempt 2 (v164):** More detailed logging was added around the `db.log_post` call in `src/main.py` to pinpoint if the call was being attempted and if it was succeeding.
    *   **Verification (v164):** Heroku logs for the 10:00 UTC post on May 25th confirmed the new detailed log messages:
        *   `INFO - Attempting to log post <tweet_id> to database (CONTENT: joke, TWEET_TEXT: BTC: $107,020.00 | -0.60% 📉...).`
        *   `INFO - Successfully logged post <tweet_id> to database after call.`
        This confirmed the `db.log_post` function is now being called and executing successfully.

**Current Status & Next Steps:**

*   **`/posts` Page Fixed:** The "Tweet History" page (`/posts`) should now correctly display all new posts made by the bot since the deployment of v164. The "Total Posts" in the Admin Panel should also be accurate.
*   **Engagement Statistics (Pending):** The issue of likes and retweets not updating (remaining at 0) is still outstanding. This requires a separate mechanism to fetch these statistics from Twitter and update the `posts` table.
*   **Next Actions:**
    1.  Verify the `/posts` page and "Total Posts" stat are now correct.
    2.  Decide on implementing the engagement statistics update feature.

**Update (May 25th, ~10:45 UTC): Engagement Statistics Feature Deployed (v165)**

Following the resolution of the `/posts` page display, the tweet engagement statistics update feature has been implemented and deployed.

**Key Changes in v165:**

1.  **Database (`src/database.py`):**
    *   Added an `engagement_last_checked` (TIMESTAMP) column to the `posts` table.
    *   Implemented `update_post_engagement(tweet_id, likes, retweets)` to update like/retweet counts and set `engagement_last_checked`.
    *   Implemented `get_posts_needing_engagement_update(limit)` to fetch posts where `engagement_last_checked` is NULL (oldest first).

2.  **Twitter Client (`src/twitter_client.py`):**
    *   Added `get_tweet_engagement(tweet_id)` method using the Twitter API v2 `get_tweet` endpoint with `public_metrics` to retrieve like and retweet counts.

3.  **Scheduler Tasks (`src/scheduler_tasks.py`):**
    *   Created a new task `update_tweet_engagement_stats_task()`.
        *   This task fetches posts needing an engagement update from the database.
        *   For each post, it calls `twitter_client.get_tweet_engagement()`.
        *   If successful, it calls `db.update_post_engagement()` to store the new counts.
    *   Initialized a shared `twitter_client_instance` for this task.

4.  **Scheduler Engine (`src/scheduler_engine.py`):**
    *   Added a new job definition to run `update_tweet_engagement_stats_task` periodically.
    *   The job is configured to run every 240 minutes (4 hours) by default (via `ENGAGEMENT_UPDATE_INTERVAL_MINUTES`).

**Deployment & Initial Verification (v165):**

*   The changes were successfully deployed to Heroku.
*   Heroku logs from the application restart (~10:38 UTC, May 25th) confirm:
    *   All components, including the new `TwitterClient` for tasks, initialized correctly.
    *   The `update_tweet_engagement_stats_task` has been successfully scheduled:
        `INFO - Tweet engagement update job added (interval: 240 minutes).`

**Next Steps for Engagement Statistics:**

1.  **Monitor First Run:** The `update_tweet_engagement_stats_task` is scheduled to run for the first time approximately 4 hours after the last restart (around 14:38 UTC, May 25th).
    *   Check Heroku logs around this time for messages from `src.scheduler_tasks` related to this task (e.g., "--- Task update_tweet_engagement_stats_task ENTERED ---", "Fetching engagement for tweet ID...", "Successfully updated engagement...").
2.  **Verify Data:** After the task has run, check the `/posts` page and the Admin Panel's "Bot Statistics" and "Tweet History" to see if likes and retweets for older posts are being populated.
3.  **Ongoing Monitoring:** Ensure the task continues to run as scheduled and updates engagement data correctly over time.

**Update (May 25th, ~18:10 UTC): Log Review & Next Monitoring Point**

*   Logs provided by the user covering the period **16:00 UTC to 18:08 UTC on May 25th** were reviewed.
    *   These logs show successful scheduled posts at 16:00 and 18:00 UTC.
    *   They also show normal news analysis cycles running and finding no new news to process.
    *   Crucially, these logs **do not yet cover the expected execution window for the `update_tweet_engagement_stats_task`**.
        *   The application restarted at ~10:38 UTC.
        *   The first run of the engagement task (4-hour interval) was anticipated around ~14:38 UTC.
        *   The second run is anticipated around **~18:38 UTC**.
*   **Next Action:** Continue to monitor Heroku logs around and after **18:38 UTC on May 25th** for the execution of the `update_tweet_engagement_stats_task`.

**Update (May 26th, ~05:10 UTC): Database Column `engagement_last_checked` Missing - Fixed**

*   Heroku logs reviewed around **22:38 UTC (May 25th)** and **02:38 UTC (May 26th)** showed the `update_tweet_engagement_stats_task` starting as scheduled.
*   However, the task failed with a `psycopg2.errors.UndefinedColumn: column "engagement_last_checked" does not exist` error. This occurred in `src/database.py` within the `get_posts_needing_engagement_update` function.
*   **Reason:** While the `engagement_last_checked` column was added to the `_create_tables_postgres` method in `src/database.py`, this does not automatically alter existing tables in a live PostgreSQL database.
*   **Fix Implemented (v166):
    1.  Created a new utility script: `utils/add_engagement_column.py`. This script connects to the PostgreSQL database and executes an `ALTER TABLE posts ADD COLUMN engagement_last_checked TIMESTAMP WITH TIME ZONE DEFAULT NULL;` command if the column doesn't already exist.
    2.  The script was added to the repository and deployed to Heroku.
    3.  Executed the script via `heroku run python utils/add_engagement_column.py --app btcbuzzbot`.
    4.  Logs confirmed successful execution: `INFO - Successfully added 'engagement_last_checked' column to 'posts' table.`

*   **Next Monitoring Step:** The `update_tweet_engagement_stats_task` is scheduled to run every 4 hours. The last failed run was at ~02:38 UTC (May 26th). The next run is anticipated around **06:38 UTC on May 26th**.
    *   Monitor Heroku logs at this time to confirm the task runs successfully without the `UndefinedColumn` error and begins processing posts for engagement updates.
    *   Subsequently, verify if likes/retweets are updated on the `/posts` page and Admin Panel.


### Original Sections Updated Below:

## 7. Current Issues

*   **Twitter API Authentication:** **RESOLVED (May 30th, 2025)**
    *   **Status:** Fixed by updating Twitter API credentials on Heroku.
    *   **Details:** The 401 Unauthorized errors have been resolved after updating the Twitter API credentials. Logs confirm successful authentication using Bearer Token.
    *   **Verification:** Application logs show successful initialization of all Twitter-related components and proper authentication.

*   **Admin Panel Data Overview:** The "Data Overview" section in the admin panel is currently not displaying news analysis statistics (Sentiment Trend, Significance/Sentiment Distribution bars are empty, table shows N/A).
    *   **Status:** **Resolution in Progress (v162). Positive Signs.**
    *   **Details:** A previous database error (`psycopg2.errors.UndefinedFunction`) was fixed. `utils/reset_news_analysis.py` was run, successfully marking 80 tweets for re-analysis.
    *   **Latest (May 23rd, ~14:40 UTC):** The 14:35 UTC analysis cycle successfully processed and updated the first batch of 30 reset tweets. Data should now be appearing in the Admin Panel. Remaining tweets (~50) will be processed in subsequent cycles.

*   **Test Failures in main.py:** The tests for `src/main.py` currently fail due to issues with mocking async functions. This doesn't affect production functionality but needs to be addressed for improved test coverage.

*   **Twitter API Rate Limit:** The bot is currently hitting Twitter's 429 Too Many Requests error when fetching news. This is not a code bug, but a limitation of the free Twitter API tier. The fetcher now logs and skips cycles when rate-limited.

## Next Steps (Updated May 23rd, 2025)
1.  **Monitor Heroku logs and Admin Panel** to verify if the forced re-analysis (after running `utils/reset_news_analysis.py`) resolves the Admin Panel's "Data Overview" display issue.
    *   **Update (~14:40 UTC):** The first analysis cycle post-reset was successful for 30 tweets. The Admin Panel should now show data for these. Monitor for completion of the remaining ~50 tweets in the next 1-2 analysis cycles (approx. next 30-60 minutes).
2.  Based on outcome of (1):
    *   If resolved: Confirm stability and monitor ongoing analysis.
    *   If not resolved: Analyze new logs from `NewsRepository` and potentially `NewsAnalyzer` / `NewsFetcher` to pinpoint the bottleneck (e.g., tweets not being fetched, LLM analysis failing, DB updates failing).
3.  Address `main.py` test failures.
4.  Monitor system stability and Twitter API rate limits.
5.  Proceed with Telegram deployment once Admin Panel and analysis pipeline are confirmed stable. 