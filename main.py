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
    
    # Import session manager
    from session_manager import SessionManager, LongFloodWaitException
    
    # Initialize session manager with all available sessions
    all_sessions = Config.get_all_sessions()
    session_manager = SessionManager(all_sessions)
    
    logger.info(f"📱 Loaded {session_manager.get_total_sessions()} session(s)")
    if session_manager.has_alternate_sessions():
        logger.info(f"✅ Auto-switch enabled (threshold: {Config.FLOOD_WAIT_THRESHOLD}s)")
    else:
        logger.warning("⚠️ No alternate sessions configured. Add SESSION_STRING_2 in .env for auto-switching.")
    
    logger.info(f"⏱️ Global cooldown: {Config.GLOBAL_COOLDOWN}s between operations")
    
    userbot = None
    controller = None
    last_operation_time = 0  # Track time of last operation for cooldown
    
    while True:  # Session switching loop
        try:
            # Get current session
            current_session = session_manager.get_current_session()
            session_num = session_manager.get_current_session_number()
            
            logger.info(f"🔐 Using Session #{session_num}")
            
            # Create client using current session string
            userbot = Client(
                name=f"userbot_session_{session_num}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                session_string=current_session,
            )
            
            # Create Bot Controller
            controller = BotController(userbot, session_manager)
            
            # Start both clients
            logger.info("Starting clients...")
            await userbot.start()
            await controller.start()
            
            # Get user info
            me = await userbot.get_me()
            logger.info(f"Userbot started as: {me.first_name} (@{me.username or 'N/A'})")
            
            # Refresh dialogs in background to populate peer cache without blocking
            async def refresh_dialogs():
                logger.info("Refreshing dialogs in background...")
                try:
                    async for _ in userbot.get_dialogs(limit=50):
                        pass
                    logger.info("Dialog refresh complete.")
                except Exception as e:
                    logger.warning(f"Dialog refresh failed: {e}")

            asyncio.create_task(refresh_dialogs())

            # Verify access to destination channel (with a small delay to let cache warm up)
            await asyncio.sleep(2)
            try:
                dest = await userbot.get_chat(Config.DESTINATION_CHANNEL)
                logger.info(f"Verified access to Destination Channel: {dest.title} ({dest.id})")
            except Exception as e:
                logger.error(f"⚠️ Could not access Destination Channel ({Config.DESTINATION_CHANNEL}): {e}")
                logger.error("Make sure the userbot has joined this channel!")
                logger.error("Try sending /join <invite_link> to the Control Bot.")


            
            # Register real-time handlers for userbot
            # Pass session manager to handlers
            from handlers import set_session_manager
            set_session_manager(session_manager)
            create_handlers(userbot)
            
            logger.info("✅ System is ready!")
            logger.info("Send /start to your Control Bot to begin.")
            
            # Keep running
            await idle()
            
            # If we reach here, user stopped the bot gracefully
            break
            
        except LongFloodWaitException as e:
            # Long flood wait detected - switch session
            logger.warning(f"🚨 Long FloodWait detected: {e.wait_time}s (threshold: {e.threshold}s)")
            
            if not session_manager.has_alternate_sessions():
                logger.error("❌ No alternate sessions available! Waiting out the flood wait...")
                await asyncio.sleep(e.wait_time + 5)
                continue
            
            # Stop current client before switching
            try:
                if userbot:
                    await userbot.stop()
                if controller:
                    await controller.stop()
            except:
                pass
            
            # Switch to next session
            new_session, new_num = session_manager.switch_to_next_session()
            logger.info(f"🔄 Switched to Session #{new_num}. Reconnecting...")
            
            # Apply global cooldown before reconnecting
            await asyncio.sleep(Config.GLOBAL_COOLDOWN)
            
            # Continue loop to reconnect with new session
            continue
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
        finally:
            try:
                if userbot:
                    await userbot.stop()
                if controller:
                    await controller.stop()
            except:
                pass
    
    logger.info("Stopped.")


if __name__ == "__main__":
    asyncio.run(main())
