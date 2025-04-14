#!/bin/bash
# BTCBuzzBot Heroku Deployment Script

echo "BTCBuzzBot Heroku Deployment"
echo "==========================="
echo

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Heroku CLI not found. Please install it first:"
    echo "npm install -g heroku OR curl https://cli-assets.heroku.com/install.sh | sh"
    exit 1
fi

# Check if user is logged in to Heroku
heroku whoami &> /dev/null
if [ $? -ne 0 ]; then
    echo "You need to login to Heroku first."
    heroku login
fi

# Ask for app name
read -p "Enter Heroku app name (leave blank for 'btcbuzzbot-app'): " APP_NAME
APP_NAME=${APP_NAME:-btcbuzzbot-app}

# Check if app exists or create it
heroku apps:info $APP_NAME &> /dev/null
if [ $? -ne 0 ]; then
    echo "Creating Heroku app: $APP_NAME"
    heroku create $APP_NAME
    if [ $? -ne 0 ]; then
        echo "Failed to create app. The name might be taken or there was an error."
        exit 1
    fi
else
    echo "Using existing Heroku app: $APP_NAME"
fi

# Add PostgreSQL addon
echo "Adding PostgreSQL addon..."
heroku addons:create heroku-postgresql:hobby-dev --app $APP_NAME

# Set environment variables
echo "Setting up environment variables..."

# Load from .env file if it exists
if [ -f ".env" ]; then
    echo "Loading variables from .env file..."
    source .env
    
    # Set variables in Heroku
    [ ! -z "$TWITTER_API_KEY" ] && heroku config:set TWITTER_API_KEY=$TWITTER_API_KEY --app $APP_NAME
    [ ! -z "$TWITTER_API_SECRET" ] && heroku config:set TWITTER_API_SECRET=$TWITTER_API_SECRET --app $APP_NAME
    [ ! -z "$TWITTER_ACCESS_TOKEN" ] && heroku config:set TWITTER_ACCESS_TOKEN=$TWITTER_ACCESS_TOKEN --app $APP_NAME
    [ ! -z "$TWITTER_ACCESS_TOKEN_SECRET" ] && heroku config:set TWITTER_ACCESS_TOKEN_SECRET=$TWITTER_ACCESS_TOKEN_SECRET --app $APP_NAME
    [ ! -z "$COINGECKO_API_URL" ] && heroku config:set COINGECKO_API_URL=$COINGECKO_API_URL --app $APP_NAME
    [ ! -z "$COINGECKO_RETRY_LIMIT" ] && heroku config:set COINGECKO_RETRY_LIMIT=$COINGECKO_RETRY_LIMIT --app $APP_NAME
    [ ! -z "$SCHEDULE_TIMES" ] && heroku config:set SCHEDULE_TIMES=$SCHEDULE_TIMES --app $APP_NAME
    [ ! -z "$SECRET_KEY" ] && heroku config:set SECRET_KEY=$SECRET_KEY --app $APP_NAME
else
    echo "No .env file found. Please set environment variables manually using:"
    echo "heroku config:set KEY=VALUE --app $APP_NAME"
fi

# Set up Git remote for Heroku
echo "Setting up Git remote..."
heroku git:remote -a $APP_NAME

# Commit any local changes
echo "Committing changes..."
git add .
git commit -m "Heroku deployment preparation" || true

# Push to Heroku
echo "Deploying to Heroku..."
git push heroku main || git push heroku master

# Scale dynos
echo "Scaling dynos..."
heroku ps:scale web=1 worker=1 --app $APP_NAME

# Run database initialization
echo "Initializing database..."
heroku run python -m src.main --app $APP_NAME

echo
echo "Deployment complete! Your app should be available at:"
echo "https://$APP_NAME.herokuapp.com/"
echo
echo "Monitor your app with:"
echo "heroku logs --tail --app $APP_NAME"
echo
echo "Open your app with:"
echo "heroku open --app $APP_NAME" 