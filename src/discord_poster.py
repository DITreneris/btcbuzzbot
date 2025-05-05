"""
Module for posting messages to Discord via Webhooks.
"""

import logging
import json
import aiohttp

logger = logging.getLogger(__name__)

async def send_discord_message(webhook_url: str, message: str):
    """Sends a message to the specified Discord Webhook URL.

    Args:
        webhook_url: The Discord Webhook URL.
        message: The message content to send (max 2000 characters).
    
    Returns:
        True if the message was sent successfully (status 2xx), False otherwise.
    """
    if not webhook_url:
        logger.error("Discord webhook URL is not configured. Cannot send message.")
        return False

    # Discord webhook expects a JSON payload with a 'content' key
    payload = {"content": message[:2000]} # Enforce Discord character limit

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if 200 <= response.status < 300:
                    logger.info(f"Successfully sent message to Discord webhook (Status: {response.status}).")
                    return True
                else:
                    # Log error response from Discord if possible
                    error_text = await response.text()
                    logger.error(f"Failed to send message to Discord webhook. Status: {response.status}, Response: {error_text}")
                    return False
    except aiohttp.ClientError as e:
        logger.error(f"Network or connection error sending message to Discord: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred sending message to Discord: {e}", exc_info=True)
        return False 