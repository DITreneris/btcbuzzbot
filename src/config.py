import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
import secrets

# Setup logging
def configure_logging():
    """Configure logging for the application"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_format = '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Log to stdout/stderr
        ]
    )
    
    # Create a logger for this application
    logger = logging.getLogger('btcbuzzbot')
    
    # Log startup information
    logger.info(f"Starting BTCBuzzBot with log level: {log_level}")
    
    return logger

class Config:
    """Configuration class for the application"""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Setup logging
        self.logger = configure_logging()
        
        # Twitter API credentials
        self.twitter_api_key = os.environ.get('TWITTER_API_KEY')
        self.twitter_api_secret = os.environ.get('TWITTER_API_SECRET')
        self.twitter_access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        self.twitter_access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        self.twitter_bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')
        self.twitter_search_query = os.environ.get('TWITTER_SEARCH_QUERY', '#Bitcoin -is:retweet')
        
        # Check basic credentials needed for posting
        if not all([self.twitter_api_key, self.twitter_api_secret, 
                   self.twitter_access_token, self.twitter_access_token_secret]):
            self.logger.warning("Some Twitter User auth API credentials (v1.1/v2 post) are missing. Tweet posting may fail.")
        # Check credentials needed for searching
        if not self.twitter_bearer_token:
             self.logger.warning("Twitter Bearer Token (v2 app-only) is missing. News fetching may fail.")
        
        # Database configuration
        self.sqlite_db_path = os.environ.get('SQLITE_DB_PATH', 'btcbuzzbot.db')
        self.db_url = os.environ.get('DATABASE_URL')
        
        # Fix Heroku's postgres:// URL if needed
        if self.db_url and self.db_url.startswith('postgres://'):
            self.db_url = self.db_url.replace('postgres://', 'postgresql://', 1)
            self.logger.info("Converted postgres:// to postgresql:// in DATABASE_URL")
        
        # Determine if PostgreSQL should be used
        self.use_postgres = bool(self.db_url)
        
        # CoinGecko API configuration
        self.coingecko_api_url = os.environ.get('COINGECKO_API_URL', 'https://api.coingecko.com/api/v3')
        self.coingecko_retry_limit = int(os.environ.get('COINGECKO_RETRY_LIMIT', '3'))
        
        # Groq LLM Configuration
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.groq_model = os.environ.get('GROQ_MODEL', 'llama3-8b-8192')
        if not self.groq_api_key:
            self.logger.warning("GROQ_API_KEY not found. LLM analysis will be disabled.")
        
        # Scheduler configuration
        post_times_str = os.environ.get('POST_TIMES', '08:00,12:00,16:00,20:00')
        self.post_times = [time.strip() for time in post_times_str.split(',')]
        self.timezone = os.environ.get('TIMEZONE', 'UTC')
        
        # Log configuration info
        self.logger.info(f"Database: {'PostgreSQL' if self.use_postgres else 'SQLite'}")
        self.logger.info(f"Scheduled posting times: {', '.join(self.post_times)} ({self.timezone})")
        
        # News Fetcher Config
        self.news_fetch_max_results = int(os.environ.get('NEWS_FETCH_MAX_RESULTS', '10'))
        
        # LLM Config (Groq Example)
        self.llm_analyze_temp = float(os.environ.get('LLM_ANALYZE_TEMP', '0.2'))
        self.llm_analyze_max_tokens = int(os.environ.get('LLM_ANALYZE_MAX_TOKENS', '150'))
        self.news_analysis_batch_size = int(os.environ.get('NEWS_ANALYSIS_BATCH_SIZE', '30'))
        self.news_processing_timeout_seconds = int(os.environ.get('NEWS_PROCESSING_TIMEOUT_SECONDS', '300'))
        self.news_hours_limit = int(os.environ.get('NEWS_HOURS_LIMIT', '12')) # How many hours back to look for analyzed news

        # Duplicate Post Check Config
        self.duplicate_post_check_minutes = int(os.environ.get('DUPLICATE_POST_CHECK_MINUTES', '5'))
        
        # Content Reuse Config
        self.content_reuse_days = int(os.environ.get('CONTENT_REUSE_DAYS', '7'))
        
        # Web Admin Config
        self.admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        self.admin_password_hash = os.environ.get('ADMIN_PASSWORD_HASH') # Store hash, not plain password
        self.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16)) # Flask session key
        
        # Add Discord Config Variables
        self.enable_discord_posting = os.environ.get('ENABLE_DISCORD_POSTING', 'False').lower() == 'true'
        self.discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        
        # Add Telegram Config Variables
        self.enable_telegram_posting = os.environ.get('ENABLE_TELEGRAM_POSTING', 'false').lower() == 'true'
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')

        # Call the correct validation method
        self.validate()

    def validate(self):
        """Validate the configuration"""
        errors = []
        
        # Check Twitter API credentials
        if not all([self.twitter_api_key, self.twitter_api_secret, 
                   self.twitter_access_token, self.twitter_access_token_secret]):
            errors.append("Twitter API credentials are incomplete")
        
        # Check database configuration
        if not self.use_postgres and not Path(self.sqlite_db_path).parent.exists():
            errors.append(f"SQLite database directory does not exist: {Path(self.sqlite_db_path).parent}")
        
        if errors:
            for error in errors:
                self.logger.error(f"Configuration error: {error}")
            return False
        
        self.logger.info("Configuration validation passed")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "sqlite_db_path": self.sqlite_db_path,
            "twitter_api_key": self.twitter_api_key[:4] + "..." if self.twitter_api_key else "",
            "twitter_api_secret": "***REDACTED***",
            "twitter_access_token": self.twitter_access_token[:4] + "..." if self.twitter_access_token else "",
            "twitter_access_token_secret": "***REDACTED***",
            "twitter_bearer_token": "Set" if self.twitter_bearer_token else "Not Set",
            "twitter_search_query": self.twitter_search_query,
            "groq_api_key": "Set" if self.groq_api_key else "Not Set",
            "groq_model": self.groq_model,
            "post_times": self.post_times,
            "timezone": self.timezone,
            "coingecko_api_url": self.coingecko_api_url,
            "coingecko_retry_limit": self.coingecko_retry_limit,
            "news_fetch_max_results": self.news_fetch_max_results,
            "llm_analyze_temp": self.llm_analyze_temp,
            "llm_analyze_max_tokens": self.llm_analyze_max_tokens,
            "news_analysis_batch_size": self.news_analysis_batch_size,
            "news_processing_timeout_seconds": self.news_processing_timeout_seconds,
            "news_hours_limit": self.news_hours_limit,
            "duplicate_post_check_minutes": self.duplicate_post_check_minutes,
            "content_reuse_days": self.content_reuse_days,
            "admin_username": self.admin_username,
            "admin_password_hash": "***REDACTED***",
            "secret_key": self.secret_key,
            "enable_discord_posting": self.enable_discord_posting,
            "discord_webhook_url": self.discord_webhook_url,
            "enable_telegram_posting": self.enable_telegram_posting,
            "telegram_bot_token": self.telegram_bot_token,
            "telegram_chat_id": self.telegram_chat_id
        }
        
    def __str__(self) -> str:
        """String representation of config (with sensitive data redacted)"""
        config_dict = self.to_dict()
        return "\n".join([f"{k}: {v}" for k, v in config_dict.items()]) 