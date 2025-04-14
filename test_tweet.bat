@echo off
rem Test tweet script - sets credentials and runs the tweet test

echo Setting Twitter API credentials...
rem Replace these with your actual Twitter API credentials
set TWITTER_API_KEY=your_api_key_here
set TWITTER_API_SECRET=your_api_secret_here
set TWITTER_ACCESS_TOKEN=your_access_token_here
set TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here

echo Running tweet test...
python hardcoded_tweet.py

echo Done!
pause 