# Morning Session 5: Application Recovery Plan

## 1. Initial Situation Assessment (Post-Deployment Regressions)

The application deployment to Heroku, while technically successful (web and worker dynos run, `/admin` page loads), revealed significant regressions and broken core functionalities:

*   **Broken Tweeting:** The `worker` dyno posted only the BTC price, omitting quotes/jokes.
*   **Tweet History Missing/Broken:** The `posts` table was not being logged to correctly.
*   **Database Content Not Used:** Quotes and jokes from the database were not being retrieved.
*   **Analysis/Initialization Issues:** Sentiment/LLM analysis checks were failing, and tasks were incorrectly re-running startup logic.
*   **Admin Panel Limited:** Displayed inaccurate or outdated data.

**Conclusion:** The application required systematic debugging and restoration of core features.

## 2. Recovery Actions Taken (April 22nd)

Significant progress has been made addressing the issues identified:

*   **Database Schema Fixed:** Connected to Heroku PostgreSQL and executed `ALTER TABLE` commands to correct the `last_used` column type in `quotes` and `jokes` tables to `TIMESTAMP WITH TIME ZONE`.
*   **Asynchronous Calls Fixed:** Ensured `post_tweet_and_log` in `src/scheduler_tasks.py` was `async` and used `await` for database calls.
*   **Core Task Logic Refactored:**
    *   `NewsFetcher`, `NewsAnalyzer`, and `TweetHandler` were refactored to be initialized *once* with a shared database instance (`db_instance`) in `src/scheduler_tasks.py`.
    *   These classes now read API keys (`TWITTER_BEARER_TOKEN`, `GROQ_API_KEY`, Twitter App Keys/Tokens) and configuration directly from environment variables during initialization.
    *   Removed internal re-initialization loops, problematic `asyncio.run` calls, and redundant synchronous wrappers/singletons.
    *   This resolved the issue of tasks re-running application setup logic, fixed async event loop conflicts, and corrected `TypeError: object dict can't be used in 'await' expression`.
*   **Import Errors Fixed:** Corrected import errors in `src/scheduler_engine.py` related to renamed task availability flags (`NEWS_..._CLASS_AVAILABLE`).
*   **Environment Variables Set & Verified:** `TWITTER_BEARER_TOKEN`, `GROQ_API_KEY`, and Twitter App keys were confirmed set in Heroku Config Vars. Initial checks show the application recognizes them on startup.
*   **Schedule Logic Fixed:** Corrected temporary hardcoding in `app.py`'s `/update_schedule` route. Sent POST requests to update the schedule in the database back to `08:00,12:00,16:00,20:00`.
*   **Worker Status:** The worker dyno now starts successfully without crashing and correctly initializes all shared task components.

## 3. Current Status & Verification Plan (as of April 22nd, ~16:30 UTC)

*   **Current Status:** The latest code with all refactoring and fixes is deployed. The worker starts correctly and initializes components. The schedule configuration in the database is set to `08:00,12:00,16:00,20:00`, and the scheduler logs show these jobs are active.
*   **Immediate Verification Steps:** Confirm the fixes result in correct runtime behavior.
    1.  **Monitor News Fetch Authorization:** Check logs for the next `run_news_fetch_wrapper` execution (every 15 mins) to ensure the `401 Unauthorized` error is resolved by the updated Bearer Token.
    2.  **Monitor 20:00 UTC Tweet:** Observe logs around **20:00 UTC** for the execution of `post_tweet_and_log`. Verify:
        *   Successful execution without TypeErrors or event loop errors.
        *   Correct content type selection (price/quote/joke) and fetching.
        *   Successful tweet posting log message (`Successfully posted tweet with ID...`).
    3.  **Verify Tweet & History:** If the 20:00 UTC task runs successfully, check the bot's Twitter account for the tweet and refresh the `/admin` page to see if the tweet appears in the history.
*   **Pending Issues / Subsequent Steps:**
    *   **Groq Rate Limiting:** News analysis logs show `429 Too Many Requests`. If LLM analysis is desired, the analysis frequency or batch size needs adjustment, or the Groq plan needs upgrading.
    *   **Admin Panel Display:** Investigate and fix the "Next scheduled run: Not scheduled" display mismatch.
    *   **Frontend Display:** Update `admin.html` to display sentiment/summary from `news_tweets`.
    *   **Rate Limiting (Twitter):** Monitor news fetcher logs for potential Twitter API rate limit errors over time.
    *   **Configuration:** Move any remaining hardcoded config values (intervals, keywords) to environment variables.
    *   **LLM Registration Warning:** Fix the Flask `before_first_request` deprecation warning in `src/llm_api.py` if LLM features are actively used.

## 4. Debugging Session (April 23rd) - Scheduler, Web App & Deployment Issues

Following the fixes on April 22nd, monitoring revealed that scheduled tweets were still not posting correctly. A lengthy debugging session addressed several intertwined issues:

*   **Scheduler Failure (Root Cause Misdiagnosis):**
    *   Initial hypothesis focused on `replace_existing=True` causing issues with `CronTrigger` jobs in APScheduler. Debug logging was added to `reschedule_tweet_jobs`.
    *   **Identified:** The debug logging itself caused an `AttributeError: 'Job' object has no attribute 'next_run_time'` during the initial scheduler startup, crashing the `reschedule_tweet_jobs` task *before* it could properly set up jobs. This logging error was fixed.
*   **Web Application Crashes:**
    *   **Home Page DB Error:** The home page (`/`) showed `Error: 'psycopg2.extensions.connection' object has no attribute 'execute'`. Fixed by adding correct DB cursor usage in the `/api/price/refresh` endpoint in `app.py`.
    *   **JS Refresh Conflict:** Price updated via manual refresh button but then disappeared. Caused by `window.location.reload()` in `static/js/main.js` success handler, which was removed. Auto-refresh interval was also commented out to prevent interference.
    *   **Web App Crash (SyntaxError):** The `/admin` page and later the home page showed "Application Error" / "Internal Server Error". Caused by a `SyntaxError` introduced into `get_basic_stats` function in `app.py` during previous edits. This was corrected.
    *   **Web App Crash (Template TypeError):** Home page crashed again with `TypeError: unsupported format string passed to Undefined.__format__`. Caused by `home.html` template incorrectly accessing `stats.latest_price.price` instead of `stats.latest_price`. Template was fixed.
    *   **Web App Crash (HTML Layout):** Home page layout collapsed. Caused by a missing closing `</div>` tag in `templates/home.html`. Tag was added.
*   **Deployment Issues:** Several fixes (TypeError in `TweetHandler`, template fixes) appeared correct locally but were not reflected in the running Heroku application, indicated by repeat errors in logs. Required manual code replacement and/or forced pushes (`git push --force`) to ensure the latest code was deployed and active.
*   **Tweet Task Failure:** Logs for the 08:00 UTC run (after scheduler startup was fixed) revealed the actual root cause: a `TypeError: PriceFetcher.get_btc_price_with_retry() got an unexpected keyword argument 'retry_limit'` within `src/tweet_handler.py`.
    *   **Fixed:** Corrected the argument name to `max_retries=3` in `src/tweet_handler.py` and ensured this fix was successfully deployed via commit and push.
*   **Scheduler Logic Hardened:** Refactored `reschedule_tweet_jobs` in `src/scheduler_tasks.py` to use a more robust remove-then-add strategy instead of relying on `replace_existing=True`, which seemed problematic for cron jobs.
*   **Rate Limiting Mitigation:** Increased news fetch interval to 6 hours (360 mins) in `src/scheduler_engine.py` to further reduce Twitter API load.

## 5. Debugging Session (April 23rd - Continued) - Database & UI Timestamp Issues

Further investigation revealed deeper issues related to database interactions and UI display, causing immense user frustration due to repeated failed fixes and deployments.

*   **Persistent `SyntaxError`:** Despite previous fixes, the `worker` dyno continued to crash with a `SyntaxError: invalid syntax` pointing to the `except Exception as e:` line within `_create_tables_postgres` in `src/database.py`. Multiple attempts to fix indentation, add/remove `pass` statements, and purge the Heroku build cache failed.
    *   **Resolution:** The entire `_create_tables_postgres` function was regenerated and replaced, overwriting any potential hidden characters or line ending issues. This finally resolved the syntax error, allowing the worker to start successfully.
*   **Stale Timestamp in UI:** The web UI displayed an old date (`2025-04-22`) for the "Last updated" timestamp, even after refreshing the price, causing significant user distrust.
    *   **Initial Analysis:** Checked `app.py` (`get_basic_stats`, `/`) and `templates/home.html`, confirming the latest timestamp *should* be fetched and displayed using `{{ stats.last_updated }}`.
    *   **JavaScript Issue:** Identified that `static/js/main.js` was incorrectly modifying the timestamp display on refresh, targeting the wrong element and using the browser's time. Fixed the JS to target the correct element (`#last-updated-timestamp`) and use the timestamp provided by the `/api/price/refresh` endpoint.
    *   **Root Cause Identified:** Realized the core issue was how the timestamp was being *written* to the database. The `store_price` function in `src/database.py` was inserting `datetime.utcnow().isoformat()` (a string) instead of a proper database timestamp for PostgreSQL.
    *   **Resolution:** Modified `store_price` to use the SQL `NOW()` function when inserting into PostgreSQL, ensuring the correct data type and value are stored.
*   **Tweet Failure (12:00 UTC):** The scheduled 12:00 UTC tweet failed with `TypeError: Database.store_price() got an unexpected keyword argument 'price_change'`. This occurred because the call to `store_price` within `src/tweet_handler.py` was not updated after `store_price` itself was modified.
    *   **Resolution:** The call in `src/tweet_handler.py` was corrected to `await self.db.store_price(current_price)`, removing the incorrect `price_change` argument. Entry logging was also added to `post_tweet_and_log` and `TweetHandler.post_tweet` for better visibility.
*   **Tweet Failure (16:00 UTC):** The scheduled 16:00 UTC tweet failed with `AttributeError: 'Database' object has no attribute 'check_recent_post'`.
    *   **Cause:** The `post_tweet` method in `src/tweet_handler.py` was calling a non-existent method `check_recent_post` on the database object.
    *   **Resolution:** The call in `src/tweet_handler.py` (line 147) was corrected to use the actual method name: `await self.db.has_posted_recently(minutes=5)`.
*   **Worker Start Failure (Post-16:00 Fix):** After deploying the `AttributeError` fix, the worker dyno failed to start, reporting `SyntaxError: expected 'except' or 'finally' block` in `src/tweet_handler.py` (line 81).
    *   **Cause:** An error in a previous edit left the `self.initialized = True` line outside the `try` block in the `TweetHandler.__init__` method, breaking the required `try...except` structure.
    *   **Resolution:** The `try...except` block in `TweetHandler.__init__` was corrected, moving `self.initialized = True` and the corresponding `logger.info` call inside the `try` block, and ensuring `self.initialized = False` in the `except` block. This fix was deployed.
*   **User Frustration:** The user is understandably extremely disappointed and frustrated by the prolonged debugging process, multiple failed deployments, and the time taken to identify the root causes. User has expressed commitment to better mutual respect moving forward.

## 6. Current Status & Verification Plan (as of April 23rd, ~16:45 UTC)

*   **Current Status:**
    *   The worker dyno starts and initializes all components correctly after the `SyntaxError` fix in `TweetHandler.__init__`.
    *   All previously identified errors (`SyntaxError` in `database.py`, UI timestamp issues, `TypeError` calling `store_price`, `AttributeError` calling `has_posted_recently`) have corresponding fixes deployed.
*   **Immediate Verification Step:**
    1.  **Monitor 20:00 UTC Tweet:** Observe worker logs (`heroku logs --tail --app btcbuzzbot --dyno worker`) around **20:00 UTC** for the execution of `post_tweet_and_log`.
        *   Result: Task ran, but a new error occurred: `operator does not exist: text > timestamp with time zone` during the `has_posted_recently` check in `src/database.py`. This indicates the `posts.timestamp` column has the wrong data type (`TEXT` instead of `TIMESTAMP WITH TIME ZONE`).
        *   Result: Tweet **was successfully posted** (ID `1915133578188308951`) despite the check error.
        *   Result: Price storage message was not logged, but the tweet *was* logged to the `posts` table (ID `35`).
    2.  **Verify UI Timestamp Post-Tweet:** *After* the 20:00 UTC task has run successfully, hard refresh (Ctrl+Shift+R) the web UI. The "Last updated" timestamp should now reflect the time the 20:00 UTC price was stored (around 20:00:xx UTC). **Verification Needed.** **Result: SUCCESS**. UI timestamp `2025-04-23 20:00:00.748227+00` matches tweet time.
    3.  **Verify Tweet on Twitter:** Check the bot's Twitter account to confirm the tweet appeared correctly. **Verification Needed.** **Result: SUCCESS**. Tweet visible on Twitter.
*   **Post-20:00 UTC Fixes (April 23rd):**
    *   Executed `ALTER TABLE posts ALTER COLUMN timestamp TYPE TIMESTAMP WITH TIME ZONE USING timestamp::timestamp with time zone;` via Heroku PSQL to correct the data type.
*   **Pending Issues / Subsequent Steps (Post-Verification):**
    *   Investigate why the "Price stored in DB" log message didn't appear in `TweetHandler` logs. **Result:** Log level was `DEBUG`, which is hidden in production. No issue.
    *   **(Review all pending items from Section 3)** Rate limiting (Groq/Twitter), news fetch/analysis confirmation, admin panel display cleanup, configuration review (env vars), LLM warning. These can be addressed once core tweeting is confirmed stable.
        *   **Twitter Rate Limit (News Fetch):** Hit persistent rate limits on `search_recent_tweets` even with 6hr interval. **Mitigation Attempt (Apr 24):** Reduced `max_results` to 5 in `NewsFetcher.fetch_tweets` and increased fetch interval to 12 hours (720 mins) in `scheduler_engine.py`.
        *   **Groq Rate Limit:** Still needs monitoring/adjustment if LLM analysis is critical. 