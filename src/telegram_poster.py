"""
Module for posting messages to Telegram.
"""
import logging
import json
import aiohttp
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

async def _make_telegram_api_call(session, url: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """
    Make an API call to the Telegram API.
    
    Args:
        session: The aiohttp ClientSession to use
        url: The URL to send the request to
        payload: The payload to send with the request
        
    Returns:
        Tuple of (status_code, response_json)
    """
    try:
        async with session.post(url, json=payload) as response:
            status = response.status
            response_json = await response.json()
            return status, response_json
    except Exception as e:
        logger.error(f"Error during Telegram API call: {e}", exc_info=True)
        return 0, {"ok": False, "description": str(e)}

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