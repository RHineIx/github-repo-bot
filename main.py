"""  
Main entry point for the GitHub Repository Preview Bot.  
"""  
import asyncio  
import logging  
from dotenv import load_dotenv  
  
from telebot.async_telebot import AsyncTeleBot  
from bot import MessageUtils
from bot import BotHandlers  
from config import config 

# Load environment variables  
load_dotenv()  
  
# Configure logging  
logging.basicConfig(  
    level=logging.INFO,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'  
)  
logger = logging.getLogger(__name__)  
  
  
async def main():  
    """Main function to start the bot."""  
    try:  
        # Validate configuration  
        config.validate()  
          
        # Initialize bot  
        bot = AsyncTeleBot(config.BOT_TOKEN, parse_mode=config.PARSE_MODE)  
          
        # Initialize handlers  
        handlers = BotHandlers(bot)  
          
        logger.info("GitHub Repository Preview Bot started successfully!")  
        logger.info("Bot is polling for messages...")  
          
        # Start polling  
        await bot.infinity_polling()  
          
    except ValueError as e:  
        logger.error(f"Configuration error: {e}")  
        logger.error("Please set the BOT_TOKEN environment variable")  
    except Exception as e:  
        logger.error(f"An error occurred: {e}")  
    finally:  
        logger.info("Bot stopped")  
  
  
if __name__ == "__main__":  
    asyncio.run(main())