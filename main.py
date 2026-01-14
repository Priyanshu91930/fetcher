"""
Telegram Userbot - File Fetcher & Forwarder
Main entry point for the userbot.

This bot automates the following flow:
1. Scan INDEX channel for series links
2. Join/access SERIES channels
3. Click "Download Links" and season buttons
4. Interact with FILE BOTS to get files
5. Forward media to DESTINATION channel
"""

import asyncio
import logging
from pyrogram import Client, idle

from config import Config
from handlers import create_handlers
from bot_controller import BotController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("userbot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the userbot."""
    
    # Validate configuration
    is_valid, errors = Config.validate()
    if not is_valid:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("Please check your .env file and try again.")
        return
    
    logger.info("=" * 60)
    logger.info("  Telegram Userbot - File Fetcher & Forwarder")
    logger.info("=" * 60)
    logger.info(f"  Index Channel    : {Config.INDEX_CHANNEL}")
    logger.info(f"  Destination      : {Config.DESTINATION_CHANNEL}")
    logger.info("=" * 60)
    
    # Create client using session string
    userbot = Client(
        name="userbot_session",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        session_string=Config.SESSION_STRING,
    )
    
    # Create Bot Controller
    controller = BotController(userbot)
    
    try:
        # Start both clients
        logger.info("Starting clients...")
        await userbot.start()
        await controller.start()
        
        # Get user info
        me = await userbot.get_me()
        logger.info(f"Userbot started as: {me.first_name} (@{me.username or 'N/A'})")
        
        # Refresh dialogs to populate peer cache (fixes "Peer id invalid" on fresh sessions)
        logger.info("Refreshing dialogs...")
        try:
            async for _ in userbot.get_dialogs(limit=50):
                pass
        except:
             pass

        # Verify access to destination channel
        try:
            dest = await userbot.get_chat(Config.DESTINATION_CHANNEL)
            logger.info(f"Verified access to Destination Channel: {dest.title} ({dest.id})")
        except Exception as e:
            logger.error(f"⚠️ Could not access Destination Channel ({Config.DESTINATION_CHANNEL}): {e}")
            logger.error("Make sure the userbot has joined this channel!")
            logger.error("Try sending /join <invite_link> to the Control Bot.")

        
        # Register real-time handlers for userbot
        create_handlers(userbot)
        
        logger.info("✅ System is ready!")
        logger.info("Send /start to your Control Bot to begin.")
        
        # Keep running
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        try:
            await userbot.stop()
            await controller.stop()
        except:
            pass
        logger.info("Stopped.")


if __name__ == "__main__":
    asyncio.run(main())
