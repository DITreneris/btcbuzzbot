# BTCBuzzBot Heroku Deployment Script for Windows

Write-Host "BTCBuzzBot Heroku Deployment" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host

# Check if Heroku CLI is installed
try {
    $herokuVersion = heroku --version
    Write-Host "Heroku CLI found: $herokuVersion" -ForegroundColor Green
} catch {
    Write-Host "Heroku CLI not found. Please install it first:" -ForegroundColor Red
    Write-Host "npm install -g heroku" -ForegroundColor Yellow
    Write-Host "Or visit: https://devcenter.heroku.com/articles/heroku-cli" -ForegroundColor Yellow
    exit
}

# Check if user is logged in to Heroku
try {
    $herokuUser = heroku whoami
    Write-Host "Logged in as: $herokuUser" -ForegroundColor Green
} catch {
    Write-Host "You need to login to Heroku first." -ForegroundColor Yellow
    heroku login
}

# Ask for app name
$appName = Read-Host "Enter Heroku app name (leave blank for 'btcbuzzbot-app')"
if ([string]::IsNullOrEmpty($appName)) {
    $appName = "btcbuzzbot-app"
}

# Check if app exists or create it
try {
    $appInfo = heroku apps:info $appName
    Write-Host "Using existing Heroku app: $appName" -ForegroundColor Green
} catch {
    Write-Host "Creating Heroku app: $appName" -ForegroundColor Yellow
    try {
        heroku create $appName
    } catch {
        Write-Host "Failed to create app. The name might be taken or there was an error." -ForegroundColor Red
        exit
    }
}

# Add PostgreSQL addon
Write-Host "Adding PostgreSQL addon..." -ForegroundColor Yellow
try {
    heroku addons:create heroku-postgresql:hobby-dev --app $appName
} catch {
    Write-Host "PostgreSQL addon may already exist or there was an error." -ForegroundColor Yellow
}

# Set environment variables
Write-Host "Setting up environment variables..." -ForegroundColor Yellow

# Load from .env file if it exists
if (Test-Path ".env") {
    Write-Host "Loading variables from .env file..." -ForegroundColor Green
    
    # Read .env file and set variables in Heroku
    foreach($line in Get-Content .env) {
        if ($line -match '^([^=]+)=(.*)$') {
            $key = $matches[1]
            $value = $matches[2]
            
            # Remove quotes if present
            $value = $value -replace '^["'']|["'']$', ''
            
            if (-not [string]::IsNullOrWhiteSpace($key) -and -not [string]::IsNullOrWhiteSpace($value)) {
                Write-Host "Setting $key" -ForegroundColor Yellow
                heroku config:set "$key=$value" --app $appName
            }
        }
    }
} else {
    Write-Host "No .env file found. Please set environment variables manually using:" -ForegroundColor Yellow
    Write-Host "heroku config:set KEY=VALUE --app $appName" -ForegroundColor Yellow
}

# Set up Git remote for Heroku
Write-Host "Setting up Git remote..." -ForegroundColor Yellow
heroku git:remote -a $appName

# Commit any local changes
Write-Host "Committing changes..." -ForegroundColor Yellow
git add .
try {
    git commit -m "Heroku deployment preparation"
} catch {
    Write-Host "No changes to commit or git repository not initialized." -ForegroundColor Yellow
}

# Push to Heroku
Write-Host "Deploying to Heroku..." -ForegroundColor Yellow
try {
    git push heroku main
} catch {
    try {
        git push heroku master
    } catch {
        Write-Host "Failed to push to Heroku. Please check your git repository." -ForegroundColor Red
        exit
    }
}

# Scale dynos
Write-Host "Scaling dynos..." -ForegroundColor Yellow
heroku ps:scale web=1 worker=1 --app $appName

# Run database initialization
Write-Host "Initializing database..." -ForegroundColor Yellow
heroku run python -m src.main --app $appName

Write-Host
Write-Host "Deployment complete! Your app should be available at:" -ForegroundColor Green
Write-Host "https://$appName.herokuapp.com/" -ForegroundColor Cyan
Write-Host
Write-Host "Monitor your app with:" -ForegroundColor Green
Write-Host "heroku logs --tail --app $appName" -ForegroundColor Cyan
Write-Host
Write-Host "Open your app with:" -ForegroundColor Green
Write-Host "heroku open --app $appName" -ForegroundColor Cyan 