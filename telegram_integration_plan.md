# Telegram Integration Plan for BTCBuzzBot

## Overview

The goal is to extend BTCBuzzBot to post Bitcoin price updates to Telegram channels or groups, similar to the existing Discord integration. This follows the platform expansion strategy outlined in Phase 3 of our development plan.

## Implementation Approach

The implementation will follow a similar pattern to the Discord integration, using the official Python Telegram Bot API library (python-telegram-bot) to post messages to Telegram.

## Prerequisites

1. Create a Telegram bot via BotFather
2. Add the bot to the target channel/group
3. Make the bot an admin in the channel/group to allow posting

## Technical Steps

### 1. Add Configuration Variables

Add the following to `src/config.py`:
```python
# Telegram related settings
self.enable_telegram_posting = os.environ.get('ENABLE_TELEGRAM_POSTING', 'false').lower() == 'true'
self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
```

### 2. Create Telegram Poster Module

Create a new file `src/telegram_poster.py`:
```python
"""
Module for posting messages to Telegram.
"""
import logging
import json
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)

async def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Send a message to a Telegram chat using the Telegram Bot API.
    
    Args:
        bot_token: The Telegram bot token
        chat_id: The ID of the chat to send the message to
        message: The message to send
        
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    if not bot_token or not chat_id:
        logger.error("Cannot send Telegram message: Missing bot token or chat ID")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"  # Support HTML formatting
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        logger.info(f"Successfully sent message to Telegram chat (Chat ID: {chat_id}).")
                        return True
                    else:
                        error_desc = result.get("description", "Unknown error")
                        logger.error(f"Telegram API error: {error_desc}")
                        return False
                else:
                    logger.error(f"Failed to send message to Telegram: Status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}", exc_info=True)
        return False
```

### 3. Modify Main Module

Update `src/main.py` to include Telegram posting after Twitter and Discord:

```python
from src.telegram_poster import send_telegram_message

# In post_btc_update function, after Discord posting:
# Check if Telegram posting is enabled
if config.enable_telegram_posting and tweet_id:
    logger.info("Telegram posting enabled. Sending message...")
    telegram_success = await send_telegram_message(
        config.telegram_bot_token,
        config.telegram_chat_id,
        tweet_text
    )
    if telegram_success:
        logger.info("Successfully posted message to Telegram.")
    else:
        logger.warning("Failed to post message to Telegram.")
```

### 4. Update Requirements

Add the necessary dependency to `requirements.txt`:
```
aiohttp==3.8.4  # Already included for Discord posting
```

### 5. Update Environment Variables

Set the required environment variables in Heroku and for local development:
```
ENABLE_TELEGRAM_POSTING=true
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Implementation Plan

1. **Development Phase**
   - Create and register a test Telegram bot
   - Implement `telegram_poster.py`
   - Update `config.py` and `main.py`
   - Test locally with the test bot

2. **Testing Phase**
   - Verify message formatting is correct
   - Test error handling (invalid token, chat ID)
   - Test rate limiting behavior

3. **Deployment Phase**
   - Set environment variables in Heroku
   - Deploy changes
   - Monitor logs for successful posting

## Timeline

- Development: 1 day
- Testing: 1 day
- Deployment and Monitoring: 1 day

## Future Enhancements

1. **Interactive Commands**
   - Implement command handling (/price, /stats)
   - Store user preferences
   - Custom alerts based on price thresholds

2. **Rich Media**
   - Send price charts as images
   - Send formatted messages with inline buttons
   - Support for polls and other interactive elements

## Monitoring and Maintenance

1. Add dedicated logging for Telegram operations
2. Add metrics to track successful/failed posts
3. Implement rate limit handling if necessary

## Conclusion

This integration will expand BTCBuzzBot's reach to Telegram users, following the same pattern as the successful Discord integration. The implementation is straightforward and reuses much of the existing architecture, making it a low-risk, high-value addition to the platform. 