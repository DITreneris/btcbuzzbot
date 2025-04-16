@echo off
echo ================================================================
echo BTCBuzzBot Twitter Integration Test
echo ================================================================
echo.

REM First fix the database structure
echo [1/4] Fixing database structure...
python fix_database.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Database fix failed.
    pause
    exit /b 1
)
echo.

REM Run the diagnostic tool to check initial state
echo [2/4] Running initial diagnostic check...
python check_tweets.py
echo.

REM Test direct tweet posting
echo [3/4] Testing tweet posting with database integration...
python direct_tweet_fixed.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Tweet posting returned an error code, but may have still logged to database.
    echo          This is normal if you don't have Twitter API credentials configured.
    echo          Check the next step to see if a simulated tweet was logged.
    echo.
)
echo.

REM Run diagnostic again to verify tweet was logged
echo [4/4] Verifying tweet was logged in database...
python check_tweets.py
echo.

echo ================================================================
echo Test summary:
echo ================================================================
echo If you see tweets in the database in the previous step, the integration
echo is working correctly. Even if actual Twitter posting fails, the system
echo should create database entries that will appear in the web interface.
echo.
echo What to check:
echo 1. Posts table should have tweets (either real or simulated)
echo 2. Prices table should have price data
echo 3. Bot status should be properly set
echo.
echo Next steps:
echo - Update the scheduler with 'python scheduler.py start'
echo - Check the web interface to see posts
echo ================================================================
echo.
pause 