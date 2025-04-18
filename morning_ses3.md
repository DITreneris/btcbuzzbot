# Morning Session 3: Debugging and Strategy Plan for BuzzBot

This document outlines the plan for analyzing and improving the BuzzBot Twitter bot.

**Goal:** Identify and fix issues causing unexpected stops and duplicate tweets, improve code quality, and enhance overall reliability.

**Key Issues:**
*   Occasional unexpected stops.
*   Duplicate tweets at scheduled times.

**Analysis Findings (Summary):**
*   **Deployment:** Uses Heroku `web` (Flask/Gunicorn via `app.py`) and `worker` (`asyncio` scheduler via `src/scheduler.py`).
*   **Database:** Configured to use SQLite (`btcbuzzbot.db` via `src/config.py` & `src/database.py`) by default if `DATABASE_URL` env var is not set. Both `web` (sync `sqlite3`) and `worker` (async `aiosqlite`) processes access the same SQLite file, causing **high risk of concurrency issues/stops**.
*   **Scheduler:** The active scheduler is `src/scheduler.py` (asyncio based). A redundant, threading-based scheduler (`scheduler.py` in root) was being loaded by `app.py` but has been removed.
*   **Core Logic:** `src/main.py` handles fetching (via `src/price_fetcher.py`) and tweeting (via `src/twitter_client.py` using Tweepy v2).
*   **Duplicate Tweets Cause:** No explicit check in `src/main.py` to prevent posting if a tweet for the current time window already exists in the `posts` DB table. Combined with potential scheduler restarts or transient API errors, this is the likely cause.
*   **Error Handling:** Basic `try/except` exists. `PriceFetcher` has retries. `TwitterClient` does *not* retry posting. A fallback `post_direct_tweet` exists but bypasses DB logging.
*   **Code Structure:** Multiple potentially redundant tweeting modules exist (`direct_tweet.py`, `direct_tweet_fixed.py`, `fixed_tweet.py`).

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
        *   [X] Root cause identified: Lack of pre-send check against DB.
        *   [ ] **Action:** Modify `src/main.py` (`post_btc_update`) to query the `posts` table for a recent successful post within a specific time window (e.g., last 5 minutes) *before* calling `twitter.post_tweet`.

3.  **Refactoring and Improvement:**
    *   [ ] **Action:** Consolidate tweeting logic. Remove unused/old modules (`direct_tweet.py`, `fixed_tweet.py`, `direct_tweet_fixed.py` if applicable) after ensuring `src/main.py` and `src/twitter_client.py` cover all needs.
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

**Next Steps:**
*   Start reading and analyzing `app.py`, `scheduler.py`, `requirements.txt`, and `Procfile`. 