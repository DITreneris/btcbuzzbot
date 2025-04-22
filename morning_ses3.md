# Morning Session 3: Debugging and Strategy Plan for BuzzBot

This document outlines the plan for analyzing and improving the BuzzBot Twitter bot.

**Goal:** Identify and fix issues causing unexpected stops and duplicate tweets, improve code quality, and enhance overall reliability.

**Key Issues Resolved:**
*   [X] Unexpected stops (Likely caused by SQLite concurrency, resolved by migrating to PostgreSQL).
*   [X] Duplicate tweets at scheduled times (Resolved by adding pre-send DB check).

**Analysis Findings (Summary):**
*   **Deployment:** Uses Heroku `web` (Flask/Gunicorn via `app.py`) and `worker` (`asyncio` scheduler via `src/scheduler.py`).
*   **Database:** Migrated from SQLite to PostgreSQL (using Heroku Postgres addon and `DATABASE_URL`) to resolve concurrency issues.
*   **Scheduler:** Active scheduler `src/scheduler.py` confirmed. Redundant root `scheduler.py` removed.
*   **Core Logic:** `src/main.py` handles fetching/tweeting for scheduled posts. `app.py` handles web UI, API, and manual tweets.
*   **Duplicate Tweets Cause:** Lack of pre-send check against DB (Now fixed in both `src/main.py` and `app.py`).
*   **Error Handling:** Basic error handling in place. Retries only for CoinGecko fetch.
*   **Code Structure:** Core logic mostly in `src`. Removed several obsolete tweeting scripts.

**Completed Actions:**

1.  **Codebase Exploration & Understanding:**
    *   [X] Reviewed `app.py`, `src/scheduler.py`, `requirements.txt`, `Procfile`, `src/config.py`, `src/database.py`, `src/main.py`, `src/twitter_client.py`.
    *   [X] Removed redundant scheduler loading from `app.py`.
    *   [X] Removed login functionality (`@login_required`, routes, templates, DB tables).
    *   [X] Removed obsolete tweeting scripts (`direct_tweet.py`, `fixed_tweet.py`, `tweet_handler_direct.py`, `tweet_now.py`, `simple_tweet.py`, `simple_tweet_v2.py`, `basic_tweet.py`, `hardcoded_tweet.py`, `heroku_tweet_debug.py`).

2.  **Issue Diagnosis & Resolution:**
    *   **Unexpected Stops (SQLite Concurrency):**
        *   [X] **Action:** Migrated database to PostgreSQL on Heroku.
        *   [X] **Action:** Modified `app.py` and `src/database.py` to use PostgreSQL via `DATABASE_URL`.
    *   **Duplicate Tweets:**
        *   [X] Root cause identified.
        *   [X] **Action:** Added `has_posted_recently` check to `src/database.py` and `src/main.py`.
        *   [X] **Action:** Added synchronous duplicate check to `app.py::post_tweet`.
    *   **Web Interface Errors:**
        *   [X] Fixed `KeyError` and `AttributeError` in `app.py` functions (`get_basic_stats`, `get_posts_paginated`, `post_tweet`) after Postgres migration.
        *   [X] Fixed `NameError` (missing imports `load_dotenv`, `tweepy`) in `app.py`.
        *   [X] Removed outdated interval display from `admin.html`.
        *   [X] Removed non-functional Start/Stop buttons from `admin.html`.

**Current Status & Remaining Items:**

*   **Scheduler Stability:** Worker dyno starts and loop runs, but may be restarting frequently due to Heroku free tier limits, potentially preventing scheduled posts. **(User monitoring required / Dyno upgrade recommended).**
*   **Code Cleanup:** Consider reviewing/removing potentially unused test files (`test_*.py`, `*.bat`).
*   **LLM Errors:** Startup errors related to LLM modules and deprecated `before_first_request` persist (Low priority unless LLM features are needed).
*   **Async PostgreSQL (Optional Improvement):** Worker (`src/database.py`) uses synchronous `psycopg2`. Could be upgraded to `asyncpg` for better async performance.
*   **Error Handling (Optional Improvement):** Consider adding retries to `src/twitter_client.py` for transient Twitter API errors.

**Immediate Next Steps:**
1.  Monitor Heroku worker logs around scheduled times (e.g., 12:00 UTC) to verify if scheduled posts are occurring despite potential dyno cycling.
2.  Based on monitoring, decide whether to upgrade the Heroku worker dyno tier for guaranteed scheduler execution.

**Revised Plan:**

1.  **Codebase Exploration & Understanding:**
    *   [X] Review `app.py` for main logic (Flask web interface, API, uses sync `sqlite3`).
    *   [X] Review `src/scheduler.py` for task scheduling logic (asyncio, uses `src/main.py`).
    *   [X] Examine `requirements.txt` for dependencies (includes `psycopg2` but currently uses SQLite).
    *   [X] Analyze `Procfile` (defines `web` and `worker` processes correctly).
    *   [X] Understand env vars (`src/config.py` loads credentials, schedule, determines DB type).
    *   [X] Review database logic (`src/database.py` - dual SQLite/Postgres support, uses `aiosqlite` for worker).
    *   [X] Review core logic (`src/main.py` - orchestrates fetch, DB interaction, tweet).
    *   [X] Review Twitter client (`src/twitter_client.py` - Tweepy v2, async wrapper, no retries).
    *   [X] Removed redundant scheduler loading from `app.py`.
    *   [ ] Investigate remaining potentially redundant tweet scripts (`direct_tweet*.py`, `fixed_tweet.py`).

2.  **Issue Diagnosis & Resolution:**
    *   **Unexpected Stops (Primary Suspect: SQLite Concurrency):**
        *   [ ] **Action:** Review Heroku logs for `database is locked` errors or other exceptions pointing to concurrency issues. (Waiting for User Input)
        *   [ ] **Action:** **Strongly recommend switching to PostgreSQL.** Plan: Add Heroku Postgres addon, set `DATABASE_URL` env var. (Discuss with User)
        *   [ ] **Alternative (if SQLite must be kept):** Implement file-based locking or another mechanism around DB writes in `src/main.py` and potentially `app.py`. (Less Recommended)
    *   **Duplicate Tweets:**
        *   [X] Root cause identified: Lack of pre-send check in `src/main.py` to prevent posting if a tweet for the current time window already exists in the `posts` DB table. Combined with potential scheduler restarts or transient API errors, this is the likely cause.
        *   [ ] **Action:** Modify `src/main.py` (`post_btc_update`) to query the `posts` table for a recent successful post within a specific time window (e.g., last 5 minutes) *before* calling `twitter.post_tweet`.

3.  **Refactoring and Improvement:**
    *   [ ] **Action:** Consolidate tweeting logic. Remove unused/old modules (`direct_tweet.py`, `direct_tweet_fixed.py`, `fixed_tweet.py` if applicable) after ensuring `src/main.py` and `src/twitter_client.py` cover all needs.
    *   [ ] Evaluate breaking `app.py` into smaller blueprints/modules if desired.
    *   [ ] Improve error handling in `src/twitter_client.py` (e.g., consider adding 1-2 retries for specific, retry-safe Twitter API errors).
    *   [ ] If switching to PostgreSQL, update `src/database.py` to use an async adapter like `asyncpg` instead of synchronous `psycopg2` for better performance in the worker.

4.  **Architectural Review:**
    *   [X] Current architecture (web + separate worker) is standard for Heroku.
    *   [ ] Switching to PostgreSQL enhances robustness.

5.  **Reliability Enhancements:**
    *   [X] Health check endpoint (`/health`) already exists in `app.py`.
    *   [ ] Review logging in `src/scheduler.py` and `src/main.py` for sufficient detail.
    *   [ ] Consider adding external error tracking (e.g., Sentry) and log aggregation (e.g., Papertrail) via Heroku addons.

6.  **Documentation & Next Steps:**
    *   [ ] Document fixes and final architecture.

**Immediate Next Steps:**
1.  Review Heroku logs to confirm SQLite errors or find other issues.
2.  Discuss and decide on the database strategy (Switch to Postgres vs. SQLite locking).
3.  Implement the duplicate tweet prevention logic in `src/main.py`. 