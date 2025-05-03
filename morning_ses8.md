# Morning Session 8: Stabilization Checkpoint & Automated Testing Plan

## 1. Session Goal

Confirm application stability after recent scheduler fixes, verify the updated 6-time tweet schedule (06:00, 08:00, 12:00, 16:00, 20:00, 22:00 UTC), decide on the news analysis strategy, and establish a plan for introducing automated tests to improve robustness and prevent regressions.

## 2. Current Status Recap (as of Apr 30th, ~11:00 UTC)

*   **Scheduler Stability:** **Confirmed Stable** after deployment v132. Worker started cleanly without initialization errors.
*   **Posting Logic:** Status **Pending Verification**. Need to observe the next scheduled post (12:00 UTC) to confirm the fix for the `AttributeError` in `main.py` is effective.
*   **News Fetching/Analysis:** Status **Pending Verification**. Need to observe the next `run_analysis_cycle_wrapper` task (~11:17 UTC) to confirm it runs without error.
*   **Schedule Update:** Verified.
*   **Database Refactoring:** Believed Complete. Verification pending successful execution of posting/analysis tasks.
*   **Content Management:** Backend OK, UI Needed.
*   **Automated Testing:** Needs expansion.

## 3. Review of Recent Fixes (Apr 27th)

*   **Issue:** Tweets stopped; scheduler logs showed jobs being added but not executed.
*   **Resolution:**
    1.  Corrected `Procfile` worker command from `python scheduler.py start` to `python src/scheduler_cli.py start`.
    2.  Modified `src/scheduler_tasks.py :: post_tweet_and_log` to call `src/main.py :: post_btc_update`, passing the `scheduled_time_str`.
    3.  Deleted the old, conflicting `src/scheduler.py`.
    4.  Updated the live schedule config in the database to include 06:00 and 22:00 UTC using a temporary script (`update_schedule.py`) run via `heroku run`.
    5.  Updated the default schedule in `src/database.py` methods (`_create_tables_postgres`, `_create_tables_sqlite`) for future consistency.
    *   **Note:** The `AttributeError` fixed on Apr 28th concerning `NewsRepository` has **reappeared** in a different context (`main.py`).

## 4. Phase 2 Progress & Next Steps

Let's revisit the Phase 2 plan from `morning_ses7.md`:

*   **Step 2.1: Define News Analysis Usage Strategy (Decision Made: Option C)**
    *   **Goal:** Decide how to use significance/sentiment/summary data.
    *   **Options Recap:** A) Dedicated Summary Tweets, B) Influence Existing Tweet Tone, C) Admin Panel Insight First, D) Hybrid.
    *   **Decision:** **Option C (Admin Panel Insight First)** selected. We will focus on parsing and displaying the analysis data in the admin panel before using it in live tweets.

*   **Step 2.2: Implement Content Management (Quotes/Jokes) (Partially Done)**
    *   **Goal:** Admin UI for managing quotes/jokes.
    *   **Status:** Backend logic moved to `ContentRepository`. Admin routes/UI in `app.py`/`templates/admin.html` still needed.
    *   **Action:** Implement the Flask routes and Jinja2 template forms/tables for adding/deleting/viewing quotes and jokes in the `/admin` section. This is a relatively isolated and lower-risk feature to implement next.

*   **Step 2.3: Implement Chosen News Analysis Feature (Admin Panel Display)**
    *   **Goal:** Parse stored JSON analysis (`news_tweets.llm_raw_analysis`) and display significance, sentiment, and summary in the admin panel.
    *   **Action:** Implement parsing logic (likely in `app.py` or a helper) and update the `/admin` route and `admin.html` template to display this data. Potentially add trend visualization.
    *   **Status:** Blocked by the `AttributeError` in the *deployed* `main.py`. The fix exists locally but needs deployment.

*   **Step 2.4: Enhance Admin Panel (Partially Blocked -> Ready for Content Management)**
    *   **Goal:** Consolidate features and improve usability.
    *   **Action:** Can implement the UI for Step 2.2 (Content Management) now. News analysis display (part of Step 2.3) is blocked.

*   **Step 2.5: Improve Logging & Monitoring (Ongoing)**
    *   **Goal:** Increase visibility.
    *   **Action:** Continue adding relevant logs as new features (like Content Management UI) are developed. We saw the benefit of detailed logs during the scheduler debugging.

*   **Step 2.6 (New): Complete Database Refactoring (NewsRepository)**
    *   **Goal:** Fix the `AttributeError` found during the 06:00 UTC post (Apr 28th) and complete the planned database refactoring for news logic.
    *   **Status:** **Locally Fixed, Pending Deployment.** The deployed version of `src/main.py :: post_btc_update` was missed during the initial refactoring, leading to the current `AttributeError`. The local code now correctly uses `NewsRepository`.
    *   **Actions Taken (Locally Complete):**
        1.  Created `src/db/news_repo.py`.
        2.  Moved news-related methods from `src/database.py` to `NewsRepository`.
        3.  Updated `src/main.py :: post_btc_update` to import and use `NewsRepository` for fetching news data. *(Correction applied locally)*.
        4.  Updated `src/news_fetcher.py` (Likely Done).
        5.  Updated `src/news_analyzer.py` (Likely Done).
    *   **Priority:** Deployment is the highest priority once on a secure network.

## 5. Automated Testing Progress (as of Apr 30th)

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

*   **Legacy Test Files:**
    Several legacy test files exist in the root directory that are no longer relevant to the current implementation:
    *   `mongo_test.py`: References MongoDB which has been replaced with PostgreSQL/SQLite
    *   `test_direct.py`: Direct Twitter API tests (failing due to auth changes)
    *   `test_mongodb.py`: Old MongoDB tests
    *   `test_tweet.py`: Old implementation of tweet handler

*   **Next Testing Targets:**
    1.  `src/main.py`: Core tweet generation logic
    2.  `src/db/news_repo.py`: News repository functionality
    3.  Integration tests between components

## 6. Immediate Actions (Apr 30th - Post v132 Fixes)

Worker started cleanly, DB schema fixed. New errors found during task execution (SQL type error, Analyzer init check).

1.  **DEPLOY:** Deploy fixes for the SQL type error (`news_repo.py`) and the analyzer init check (`news_analyzer.py`). **(Highest Priority)**
2.  **VERIFY:** Monitor logs **EXTREMELY** closely after deployment:
    *   Confirm `run_analysis_cycle_wrapper` runs *without* the `NewsAnalyzer not initialized` error AND processes tweets (or logs analysis errors if API/parsing fails).
    *   Confirm `post_tweet_and_log` runs *without* the SQL `operator does not exist` error when checking for news.
    *   Confirm overall stability through several cycles.
3.  **UPDATE:** Update this document (`morning_ses8.md`) with verification results.
4.  **Develop:** Implement Admin UI for Content Management (Step 2.2 Frontend) - *once stability is fully confirmed*.
5.  **Develop:** Begin Discord Posting (Step 3.1) - *once stability is fully confirmed*.
6.  **Develop:** Implement News Analysis Admin Display (Step 2.3) - *once stability is fully confirmed*.
7.  **Test:** Continue expanding test coverage.
8.  **Cleanup:** Consider removing legacy test files.

## 7. Current Issues

*   **~~`psycopg2.errors.UndefinedFunction: operator does not exist: text >= timestamp`~~ (SQL Type Error - Fixed Locally):** Occurred in `news_repo.get_recent_analyzed_news`. Fixed by adding explicit `::timestamptz` cast to `fetched_at`.
*   **~~`ERROR - NewsAnalyzer not initialized or dependencies missing.`~~ (Logic Error - Fixed Locally):** Occurred in `news_analyzer.analyze_tweets` due to checking `self.llm_client` instead of `self.groq_client`. Fixed the check.
*   **~~`psycopg2.errors.UndefinedColumn: column "processed" does not exist`~~ (Resolved with ALTER TABLE):** Database schema mismatch fixed.
*   **~~`AttributeError: 'Config' object has no attribute 'get'`~~ (Resolved in v132):** Fixed by using `getattr`.
*   **~~`NameError` on Instance Creation~~ (Resolved in v131):** Fixed by adding missing imports.
*   **~~`TypeError` on Instance Creation~~ (Resolved in v130):** Fixed by correcting arguments.
*   **~~`NameError: ContentManager` in `news_analyzer.py`~~ (Resolved in v129):** Fixed by adding import.
*   **~~`AttributeError` in `main.py`~~ (Believed Resolved in v128):** Fix was deployed, verification occurred during 06:00 post (no error there).
*   **Twitter API Rate Limit:** Currently unknown status, likely still applies. Will become visible if news fetch/analysis runs successfully.
*   **Legacy Tests:** Cluttering root directory.

## 8. Guiding Principles (Reiteration)

*   **Stability First:** Prioritize maintaining the current working state.
*   **Incremental Steps:** Implement changes in small, verifiable units.
*   **Test Locally:** Verify changes locally before deploying. Run automated tests.
*   **Clear Commits:** Use descriptive commit messages.

---

## Phase 3: Platform Expansion

Goals for this phase involve extending the bot's reach to other platforms and enhancing its interactive capabilities.

*   **Step 3.1: Implement Discord Posting (via Webhooks)**
    *   **Goal:** Post the same BTC update messages to a designated Discord channel.
    *   **Approach:** Use Discord Webhooks for simplicity in sending messages without needing a full bot client initially.
    *   **Status:** Not Started. Blocked pending stability verification.
    *   **Tasks:**
        1.  Create a Discord Webhook URL for the target channel.
        2.  Add `DISCORD_WEBHOOK_URL` and `ENABLE_DISCORD_POSTING` to configuration (`config.py`, `.env`, Heroku).
        3.  Create `src/discord_poster.py` with an async function `send_discord_message(webhook_url, message)` using `aiohttp` (or `requests` if synchronous is preferred within `main.py`).
        4.  In `src/main.py :: post_btc_update`, after successful tweet posting and logging, check `ENABLE_DISCORD_POSTING`. If true, retrieve `DISCORD_WEBHOOK_URL` and call `send_discord_message`. Handle potential errors gracefully.
        5.  Add necessary dependencies (`aiohttp` or `requests`) to `requirements.txt`.
        6.  Test locally by setting the config flag and URL.
        7.  Deploy and verify logs/Discord channel.

*   **Step 3.2: Implement Telegram Posting (Future)**
    *   **Goal:** Post updates to a Telegram channel/chat.
    *   **Status:** Not Started.

*   **Step 3.3: Explore Interactive Commands (Future)**
    *   **Goal:** Allow users on Discord/Telegram to request data (e.g., `/price`).
    *   **Status:** Not Started. This would likely require switching from Webhooks to full bot clients (`discord.py`, `python-telegram-bot`). 