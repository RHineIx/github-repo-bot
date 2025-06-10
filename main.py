import asyncio
import logging

from telebot.async_telebot import AsyncTeleBot
from bot import BotHandlers
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def run_periodic_cleanup(handlers, interval_seconds: int):
    """Runs the database cleanup task at a set interval."""
    while True:
        try:
            logger.info("Running periodic database cleanup...")
            await handlers.tracker.cleanup_orphaned_items()
            await asyncio.sleep(interval_seconds)
        except Exception as e:
            logger.error(f"Error in periodic cleanup task: {e}")
            # Wait for a shorter period before retrying in case of error
            await asyncio.sleep(60 * 60) # Wait 1 hour before retrying

async def main():
    """Main function to start the bot."""
    try:
        # Validate configuration
        config.validate()

        # Initialize bot
        bot = AsyncTeleBot(config.BOT_TOKEN, parse_mode=config.PARSE_MODE)

        # Initialize handlers
        handlers = BotHandlers(bot)

        # Initialize the tracking database
        await handlers.tracker.init_db() 

        # Start monitoring task
        monitor_task = asyncio.create_task(
            handlers.monitor.start_monitoring(interval=300)
        )  # Check every 5 minutes

        # Start the periodic database cleanup task (runs every 24 hours)
        cleanup_interval = 24 * 60 * 60  # 24 hours in seconds
        cleanup_task = asyncio.create_task(
        run_periodic_cleanup(handlers, cleanup_interval)
        )

        logger.info("GitHub Repository Preview Bot started successfully!")
        logger.info("Repository monitoring started!")
        logger.info("Periodic database cleanup scheduled!")
        logger.info("Bot is polling for messages...")

        # Start polling
        await bot.infinity_polling()

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set the BOT_TOKEN environment variable")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Stop monitoring
        if "handlers" in locals():
            handlers.monitor.stop_monitoring()
        if "monitor_task" in locals():
            monitor_task.cancel()
        if "cleanup_task" in locals():
            cleanup_task.cancel()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())