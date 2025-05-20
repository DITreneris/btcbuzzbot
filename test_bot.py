from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Your bot token from @BotFather
TOKEN = "7551096808:AAHhvgk5D3y0ZOz5eFUL1gkLNzri2xeDeeQ"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    chat = update.effective_chat
    print(f"Chat title: {chat.title}")
    print(f"Chat ID: {chat.id}")
    await update.message.reply_text(f"Hello! This chat's ID is: {chat.id}")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add command handler
    application.add_handler(CommandHandler("start", start))

    # Start the Bot
    print("Bot started. Add the bot to your group and send /start to get the chat ID.")
    application.run_polling()

if __name__ == '__main__':
    main()