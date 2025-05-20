import asyncio
import os
from src.telegram_poster import send_telegram_message

async def test_telegram_message():
    # Get configuration from environment variables
    bot_token = "7551096808:AAHhvgk5D3y0ZOz5eFUL1gkLNzri2xeDeeQ"
    chat_id = "-1002145381378"
    
    # Test message
    message = "🤖 BTCBuzzBot Test Message\n\nThis is a test message to verify Telegram integration is working correctly."
    
    print(f"Sending test message to Telegram...")
    success = await send_telegram_message(bot_token, chat_id, message)
    
    if success:
        print("✅ Message sent successfully!")
    else:
        print("❌ Failed to send message.")

if __name__ == "__main__":
    asyncio.run(test_telegram_message()) 