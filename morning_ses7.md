# Morning Session 7: Strategic Development Plan (Phase 2 Kick-off)

## 1. Session Goal

Define a clear, incremental plan for **Phase 2: Enhanced Content Generation & Analysis**, building upon the stable foundation achieved in Phase 1. The focus is on leveraging news analysis, improving content management, and enhancing the admin panel, all while maintaining application stability and aligning with the long-term vision in `roadmap.md`.

## 2. Current Status Recap (as of Apr 24th, ~20:00 UTC)

*   **Core Stability:** Application is stable on Heroku (`worker` and `web` dynos).
*   **Verified Functionality:**
    *   Scheduled tasks (rescheduling, analysis cycle) run correctly.
    *   Tweet posting (price, quote, joke) occurs reliably at configured times (08:00, 12:00, 16:00, 20:00 UTC).
    *   Database interactions (storing price/posts, fetching content) are operational.
    *   24-hour price change calculation is fixed and verified.
    *   Web UI (Home, Posts, Admin) loads and displays basic data.
*   **News Analysis Implemented:**
    *   `NewsFetcher` retrieves news tweets.
    *   `NewsAnalyzer` uses Groq (`llama3-8b-8192`) to assess significance, sentiment, and generate a summary for fetched tweets.
    *   Raw JSON analysis results are stored in the `news_tweets.llm_raw_analysis` column.
*   **Code Health:** Configuration externalized, obsolete code (Ollama) removed.
*   **Key Gap:** The generated news analysis data (significance, sentiment, summary) is stored but **not yet actively used** to influence tweet content or provide insights within the application.

## 3. Phase 2 Focus Areas (Derived from `roadmap.md`)

Based on the completion of Phase 1 and the goals outlined in `roadmap.md`, Phase 2 will focus on:

*   **Refining News Analysis Usage:** Deciding *how* to leverage the generated insights.
*   **Enhancing Tweet Content Generation:** Making tweets potentially more dynamic or insightful based on analysis.
*   **Improving Content Management:** Adding easier ways to manage static content (quotes, jokes).
*   **Basic Sentiment Trend Tracking:** Storing and potentially visualizing sentiment over time.
*   **Enhancing the Admin Panel:** Making it a more useful hub for monitoring and management.
*   **Improving Monitoring & Logging:** Increasing visibility into the bot's operations.

## 4. Proposed Development Steps (Incremental & Stability-Focused)

The following steps are proposed to tackle Phase 2 incrementally, prioritizing stability:

### Step 2.1: Define News Analysis Usage Strategy (Decision Point)

*   **Goal:** Determine the initial strategy for utilizing the significance, sentiment, and summary data from `news_tweets.llm_raw_analysis`. This decision is critical before implementation.
*   **Options:**
    *   **Option A: Dedicated Summary Tweets:** Create a new, separate scheduled task to post periodic summaries of significant crypto news based on the analysis (e.g., daily "Top News Summary").
    *   **Option B: Influence Existing Tweet Tone:** Modify the current `post_tweet_and_log` task. When posting a price update, subtly adjust the accompanying text or emoji based on the *overall market sentiment* derived from recent news analysis (e.g., use more bullish emoji/phrases if recent sentiment is positive).
    *   **Option C: Admin Panel Insight First:** Focus initially on parsing the stored JSON analysis and displaying the significance, sentiment, and summary clearly within the `/admin` panel. Add basic sentiment trend visualization (e.g., daily average sentiment). Defer using analysis in *live tweets* until monitoring via admin is established.
    *   **Option D: Hybrid Approach:** Combine elements, such as displaying details in the admin panel (Option C) *and* implementing a less intrusive live feature like Option B (Tone Influence).
*   **Recommendation:** Start with **Option C (Admin Panel Insight First)** or **Option A (Dedicated Summary Tweets)**.
    *   *Reasoning:* Option C is the safest, allowing us to visualize and validate the analysis data without affecting live tweets. Option A creates a *new* tweet type, isolating it from the currently stable price/quote/joke logic. Option B directly modifies existing core logic and carries a slightly higher risk of introducing regressions if not carefully implemented and tested.
*   **Action Required:** Discuss and finalize the chosen strategy.

### Step 2.2: Implement Content Management (Quotes/Jokes)

*   **Goal:** Provide an admin interface for managing the `quotes` and `jokes` database tables, removing the need for direct database access or code changes for content updates.
*   **Actions:**
    1.  **Database:** Add necessary methods to `src/database.py` (e.g., `add_quote`, `delete_quote`, `get_all_quotes`, `add_joke`, `delete_joke`, `get_all_jokes`).
    2.  **Backend:** Create Flask routes in `src/app.py` under `/admin` to handle POST requests for adding/deleting and GET requests for displaying content. Ensure proper authentication/authorization if adding later.
    3.  **Frontend:** Design and implement simple forms and tables within the `/admin` Jinja template (`templates/admin.html`) to interact with the new backend routes.
*   **Stability:** This feature is relatively isolated from the core tweeting loop and poses a low risk to stability if implemented carefully.

### Step 2.3: Implement Chosen News Analysis Feature

*   **Goal:** Develop the feature based on the strategy chosen in Step 2.1.
*   **Actions (Contingent on Step 2.1 Decision):**
    *   *If Option A:* Design prompt for summary generation, create new task/schedule, update logging.
    *   *If Option B:* Determine sentiment aggregation logic, carefully modify `TweetHandler.post_tweet` to include sentiment-based adjustments, add relevant logging.
    *   *If Option C:* Implement JSON parsing logic (within Flask route or helper function), update `/admin` route and template to display parsed data and trends.
*   **Stability:** Risk varies by option. Requires thorough local testing before deployment.

### Step 2.4: Enhance Admin Panel (Supporting Steps 2.2 & 2.3)

*   **Goal:** Consolidate new features and improve the usability of the admin dashboard.
*   **Actions:**
    1.  Integrate the quote/joke management UI (from Step 2.2).
    2.  Implement the display for news analysis data/trends (from Step 2.3, especially if Option C is chosen).
    3.  Review overall layout and clarity of the admin page.
*   **Stability:** Low risk, primarily involves frontend and data retrieval logic.

### Step 2.5: Improve Logging & Monitoring (Ongoing)

*   **Goal:** Increase visibility into the application's decision-making processes and potential failure points throughout Phase 2 development.
*   **Actions:** While implementing Steps 2.1-2.4, proactively add detailed `logger.info`, `logger.debug`, and `logger.warning`/`error` statements covering:
    *   News analysis results (parsed values).
    *   Content selection logic (which news chosen for summary, why a certain tone was used).
    *   API call successes/failures (Groq, Twitter).
    *   Database operations related to new features.
*   **Stability:** Improves long-term stability by facilitating faster debugging. Low risk.

## 5. Next Immediate Action

**Discuss and Decide:** Finalize the **News Analysis Usage Strategy (Step 2.1)**. This decision is the prerequisite for starting the core implementation work of Phase 2.

## 6. Guiding Principles (Reiteration)

*   **Stability First:** Prioritize maintaining the current working state.
*   **Incremental Steps:** Implement changes in small, verifiable units.
*   **Clear Commits:** Use descriptive commit messages.
*   **Test Locally:** Verify changes locally before deploying to Heroku.

## Revised Plan (2025-04-25): Addressing Rate Limits & Tweet Reliability

**Goal:** Address Twitter API rate limiting issues (free tier monthly limit hit) and ensure tweet reliability.

**Tweet Schedule:** Keep 4 times: `['08:00', '12:00', '16:00', '20:00']` UTC.

**Tweet Content Strategy:**
*   `16:00 UTC`: Will be **price-only** tweet. This tweet will not depend on news fetching or analysis, making it immune to fetching rate limits.
*   `08:00, 12:00, 20:00 UTC`: Will attempt standard tweet (price + latest analyzed news). Requires robust fallback logic if recent news is unavailable (e.g., use older analyzed news from DB, fallback to price-only, or potentially use quote/joke).

**Code Implementation Steps:**
1.  **`src/news_fetcher.py`:**
    *   Change `tweepy.Client` initialization to use `wait_on_rate_limit=False`.
    *   Wrap the `search_recent_tweets` API call within `fetch_tweets` in a `try...except tweepy.errors.RateLimitError`:
        *   Log a warning upon catching the error.
        *   Return an empty list (`[]`) to signal failure without blocking the worker thread.
2.  **Heroku Environment Variable:**
    *   Set `NEWS_FETCH_MAX_RESULTS` to `5` (or potentially lower) to reduce API calls per fetch cycle.
3.  **`src/scheduler.py`:**
    *   Modify the main scheduling loop to detect which specific `time_str` (e.g., '08:00', '16:00') triggered the posting condition.
    *   Pass this `time_str` as an argument when calling `self.scheduled_job(time_str)`.
    *   Modify the `self.scheduled_job` method to accept the `time_str` argument.
    *   Pass the `time_str` down when calling the main posting function: `post_btc_update(self.config, time_str)`.
4.  **`src/main.py`:**
    *   Modify the `post_btc_update` function signature to accept the `scheduled_time_str` argument.
    *   Implement conditional logic within `post_btc_update`:
        *   `if scheduled_time_str == '16:00':` Call/implement logic to compose and return a **price-only** tweet string.
        *   `else:` Call/implement logic for the standard tweet composition (attempting news analysis first, with necessary fallbacks).
    *   Ensure the fallback logic for the standard tweet composition is robust (handles cases where news fetching failed or no suitable news was found). 

**Status (2025-04-25 ~11:30 UTC):**
*   Code implementation steps 1, 3, and 4 completed and deployed.
*   Heroku environment variable `NEWS_FETCH_MAX_RESULTS` set to `5` (Step 2).
*   Deployment successful, monitoring logs for expected behavior (especially the 16:00 price-only tweet). 

## Debugging News Fetching (2025-04-25 ~17:00-19:00 UTC)

**Goal:** Diagnose why the `fetch_news_tweets` task was not running and collecting new data since April 22nd.

**Findings & Resolutions:**

1.  **Initial Observation:** Logs confirmed the `fetch_news_tweets` job was being added by the scheduler on startup but never executed.
2.  **Code Fixes:**
    *   Identified and corrected a potential issue where the `run_news_fetch_wrapper` function was incorrectly specified or logged.
    *   Ensured the scheduler executor was set correctly (`AsyncIOExecutor`).
3.  **Diagnostic Test:**
    *   Temporarily changed the news fetch interval (`NEWS_FETCH_INTERVAL_MINUTES`) from `720` (12 hours) to `15` minutes to force execution.
    *   Restarted the worker dyno.
4.  **Root Cause Identified:**
    *   With the 15-minute interval, the `fetch_news_tweets` task **successfully executed** for the first time since the debugging began.
    *   The execution immediately failed with a `tweepy.errors.TooManyRequests: 429 Too Many Requests - Usage cap exceeded: Monthly product cap` error.
    *   **Conclusion:** The primary reason for no new data was hitting the **free tier's monthly API usage limit** for the Twitter v2 search endpoint. Previous code bugs may have masked this or contributed to hitting the limit faster.
5.  **Configuration Correction:**
    *   Discovered that the `fetch_and_store_tweets` function in `src/news_fetcher.py` had a default `max_results=100`, ignoring the `NEWS_FETCH_MAX_RESULTS` environment variable.
    *   Modified the scheduler task (`fetch_news_tweets` in `src/scheduler/tasks.py`) to correctly read the `NEWS_FETCH_MAX_RESULTS` environment variable (defaulting to `5`) and pass it to the fetcher function.
6.  **Mitigation:**
    *   Set `NEWS_FETCH_INTERVAL_MINUTES` back to `1440` (24 hours) to significantly reduce API calls.
    *   Verified `NEWS_FETCH_MAX_RESULTS` is set to `5` in Heroku config vars.
    *   Deployed code changes and restarted the worker dyno.

**Current State (End of Session):**
*   The scheduler is confirmed to be working correctly and triggers the `fetch_news_tweets` job.
*   The code now correctly respects the `NEWS_FETCH_MAX_RESULTS` setting.
*   The interval is set to 24 hours.
*   **The news fetching task remains blocked by the Twitter API's monthly usage cap.** It will likely fail with a 429 error on its next scheduled run (in ~24 hours).
*   The bot is otherwise operational, but will not have fresh news data until the Twitter API quota resets (likely at the start of the next calendar month).
*   Other scheduled tasks (analysis, posting) will continue to run, but analysis will operate on stale data, and tweet composition fallback logic will be used more often.

## Refactoring (2025-04-25 ~15:15 UTC)

**Goal:** Improve maintainability and code structure of `src/database.py` (over 1000 lines) by extracting responsibilities into separate repository classes.

**Step 1: Extract Content Repository**
*   **Action:** Created a new file `src/db/content_repo.py`.
*   **Action:** Moved methods related to quotes and jokes (`get_random_content`, `add_quote`, `get_all_quotes`, `delete_quote`, `add_joke`, `get_all_jokes`, `delete_joke`) from `src/database.py` into the new `ContentRepository` class.
*   **Action:** Updated `app.py` (admin panel routes) and `src/content_manager.py` to import and use `ContentRepository` instead of the original `Database` class for quote/joke operations.
*   **Status:** Refactoring step completed and deployed (`v119`). Initial verification pending.

**Next Refactoring Steps (Optional):**
*   Extract Price logic to `PriceRepository`.
*   Extract News logic to `NewsRepository`.
*   Extract Post logging logic to `PostRepository`.
*   Extract Status/Config logic to `StatusRepository`.
*   Refactor connection management into a dedicated module/utility.

**Note:** This refactoring is done in parallel with investigating the stale data issue. The primary focus remains on diagnosing the `fetch_news_tweets` failure via logs. 

## Debugging Scheduler Instability (2025-04-27)

**Issue:** Application instability observed again. Tweet posting stopped entirely after the morning of April 26th, despite logs showing the `reschedule_tweet_jobs` task running successfully and adding tweet jobs to the scheduler.

**Diagnosis:**
1.  **Log Analysis:** Examination of worker logs (`heroku logs --tail --app btcbuzzbot --source app --dyno worker`) confirmed that while `reschedule_tweet_jobs` and `run_analysis_cycle_wrapper` were executing, the actual tweet posting function (`post_tweet_and_log` as scheduled by `reschedule_tweet_jobs`) was **not** being triggered or logged.
2.  **Code Review:**
    *   Identified a conflict between the active APScheduler setup (`src/scheduler_engine.py`, `src/scheduler_tasks.py`) and an old, manual `asyncio` loop scheduler present in `src/scheduler.py`.
    *   Discovered that the `reschedule_tweet_jobs` task was scheduling `src/scheduler_tasks.py :: post_tweet_and_log`.
    *   Found that `src/scheduler_tasks.py :: post_tweet_and_log` contained simplified tweet logic (random price/quote/joke) and did **not** call the intended, more complex logic in `src/main.py :: post_btc_update` (which handles 16:00 price-only, news analysis, and proper fallbacks).
    *   The root cause of the scheduled task *not running* was still unclear but suspected to be related to the scheduler conflict or a subtle APScheduler issue.

**Resolution:**
1.  **Consolidate Logic:** Modified `src/scheduler_tasks.py :: post_tweet_and_log` to remove its simple tweet logic. It now acts as a wrapper that directly calls `src/main.py :: post_btc_update`, ensuring the correct posting logic is used.
2.  **Pass Arguments:** Updated `src/scheduler_tasks.py :: reschedule_tweet_jobs` to correctly pass the `time_str` (e.g., "08:00") as an argument when scheduling the `post_tweet_and_log` job. This `time_str` is needed by `post_btc_update` to handle time-specific logic (like the 16:00 price-only tweet).
3.  **Add Logging:** Added an entry log message at the beginning of `src/scheduler_tasks.py :: post_tweet_and_log` to definitively confirm if/when APScheduler executes the task.
4.  **Remove Conflict:** Deleted the old, conflicting scheduler file `src/scheduler.py`.

**Next Steps:**
1.  Commit and deploy the changes to Heroku.
2.  Monitor worker logs closely after deployment to confirm:
    *   The `post_tweet_and_log` task is now being triggered at the scheduled times (08:00, 12:00, 16:00, 20:00 UTC), indicated by the new entry log message.
    *   The logs from `src/main.py :: post_btc_update` show the correct execution flow (price fetching, time check, content generation, fallback logic, successful posting). 