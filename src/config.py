import os
from typing import Dict, Any, List
from dotenv import load_dotenv

class Config:
    """Configuration management class"""
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Database configuration
        self.sqlite_db_path = os.getenv("SQLITE_DB_PATH", "btcbuzzbot.db")
        
        # Twitter configuration
        self.twitter_api_key = os.getenv("TWITTER_API_KEY", "")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET", "")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
        
        # Bot configuration
        self.post_times = os.getenv("POST_TIMES", "08:00,12:00,16:00,20:00").split(",")
        self.timezone = os.getenv("TIMEZONE", "UTC")
        
        # CoinGecko configuration
        self.coingecko_api_url = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")
        self.coingecko_retry_limit = int(os.getenv("COINGECKO_RETRY_LIMIT", "3"))
        
        # Validate required settings
        self.validate()
    
    def validate(self):
        """Validate required settings"""
        if not self.twitter_api_key or not self.twitter_api_secret:
            raise ValueError("Twitter API key and secret are required")
        
        if not self.twitter_access_token or not self.twitter_access_token_secret:
            raise ValueError("Twitter access token and secret are required")
        
        # Validate post times format
        for time_str in self.post_times:
            try:
                hours, minutes = time_str.split(":")
                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                    raise ValueError(f"Invalid time format: {time_str}")
            except Exception:
                raise ValueError(f"Invalid time format: {time_str}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "sqlite_db_path": self.sqlite_db_path,
            "twitter_api_key": self.twitter_api_key[:4] + "..." if self.twitter_api_key else "",
            "twitter_api_secret": "***REDACTED***",
            "twitter_access_token": self.twitter_access_token[:4] + "..." if self.twitter_access_token else "",
            "twitter_access_token_secret": "***REDACTED***",
            "post_times": self.post_times,
            "timezone": self.timezone,
            "coingecko_api_url": self.coingecko_api_url,
            "coingecko_retry_limit": self.coingecko_retry_limit
        }
        
    def __str__(self) -> str:
        """String representation of config (with sensitive data redacted)"""
        config_dict = self.to_dict()
        return "\n".join([f"{k}: {v}" for k, v in config_dict.items()]) 