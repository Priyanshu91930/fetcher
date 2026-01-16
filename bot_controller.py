
import asyncio
import logging
from typing import Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from handlers import run_full_scan, state, BotState

logger = logging.getLogger(__name__)

class BotController:
    """
    Controller for the Telegram Bot interface.
    """
    def __init__(self, userbot_client: Client):
        self.userbot = userbot_client
        self.bot = Client(
            "control_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        self.status_message: Optional[Message] = None
        self.cancel_task = False
        self.scan_task: Optional[asyncio.Task] = None  # Track the scan task for cancellation
        self._register_handlers()

    def _register_handlers(self):
        @self.bot.on_message(filters.command("start"))
        async def start_command(client, message):
            if not self._check_admin(message):
                return
            await message.reply_text(
                "**🤖 Userbot Control Panel**\n\n"
                "Commands:\n"
                "/scan - Start scanning Index Channel\n"
                "/scan [link] - Scan specific post\n"
                "/stop - Stop current operation\n"
                "/status - Check status",
                quote=True
            )

        @self.bot.on_message(filters.command("scan"))
        async def scan_command(client, message):
            if not self._check_admin(message):
                return
            
            if state.is_processing:
                await message.reply_text("⚠️ Already processing! Use /stop to cancel first.")
                return

            args = message.text.split(" ", 1)
            start_link = args[1].strip() if len(args) > 1 else None
            
            target = start_link if start_link else "Index Channel"
            status_msg = await message.reply_text(f"🚀 Starting scan: {target}...")
            self.status_message = status_msg
            self.cancel_task = False
            state.stop_requested = False # Reset stop flag
            
            # Start scan in background and track the task
            self.scan_task = asyncio.create_task(self._run_scan_task(start_link))


        @self.bot.on_message(filters.command("stop"))
        async def stop_command(client, message):
            if not self._check_admin(message):
                return
            
            if not state.is_processing and not self.scan_task:
                await message.reply_text("Nothing is running.")
                return
            
            # Request graceful stop
            state.stop_requested = True
            await message.reply_text("🛑 Stopping... (might take a moment to finish current item)")
            
            # Cancel the scan task if it exists
            if self.scan_task and not self.scan_task.done():
                self.scan_task.cancel()
                try:
                    await asyncio.wait_for(self.scan_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.info("Scan task cancelled")
                
                # Force reset state
                self._force_stop()
                await message.reply_text("✅ Stopped and reset. Ready for new scan.")

        @self.bot.on_message(filters.command("status"))
        async def status_command(client, message):
            if not self._check_admin(message):
                return
            
            if not state.is_processing:
                await message.reply_text("💤 Idle")
                return
            
            series = state.current_series or "None"
            season = state.current_season or "None"
            files = state.files_received
            await message.reply_text(
                f"**Current Status**\n"
                f"Series: `{series}`\n"
                f"Season: `{season}`\n"
                f"Files Collected (Current): {files}"
            )

        @self.bot.on_message(filters.command("join") & filters.user(Config.ADMIN_IDS) if Config.ADMIN_IDS else filters.command("join"))
        async def join_command(client, message):
            if not self._check_admin(message):
                return
            
            try:
                if len(message.command) < 2:
                    await message.reply_text("Usage: /join <link or username>")
                    return
                
                link = message.command[1]
                await message.reply_text(f"Trying to join {link}...")
                
                chat = await self.userbot.join_chat(link)
                await message.reply_text(f"✅ Successfully joined **{chat.title}**!")
            except Exception as e:
                await message.reply_text(f"❌ Failed to join: {e}")


    def _check_admin(self, message: Message) -> bool:
        if not Config.ADMIN_IDS:
            return True # Allow all if no admins set
        if message.from_user.id in Config.ADMIN_IDS:
            return True
        return False

    def _force_stop(self):
        """Force reset all state when server is stuck."""
        state.is_processing = False
        state.stop_requested = False
        state.waiting_for_files = False
        state.current_series = ""
        state.current_season = ""
        state.files_received = 0
        state.current_bot_chat_id = None
        state.progress_callback = None
        self.status_message = None
        self.scan_task = None
        logger.info("Force stopped and reset all state")

    async def _run_scan_task(self, start_link):
        try:
            # Inject callback for progress
            state.progress_callback = self.update_progress
            
            # Auto-fetch loop
            current_link = start_link
            posts_processed = 0
            
            while current_link or posts_processed == 0:
                if state.stop_requested:
                    logger.info("Stop requested, breaking auto-fetch loop")
                    break
                
                # Check if we've reached the max auto-fetch limit
                if posts_processed >= Config.MAX_AUTO_FETCH_POSTS:
                    logger.info(f"Reached max auto-fetch limit: {Config.MAX_AUTO_FETCH_POSTS} posts")
                    if self.status_message and self.bot.is_connected:
                        await self.status_message.edit_text(
                            f"⚠️ Reached auto-fetch limit ({Config.MAX_AUTO_FETCH_POSTS} posts)\n\n"
                            f"📊 Posts processed: {posts_processed}\n"
                            f"📁 Total files: {state.files_received}\n\n"
                            f"To continue, use /scan with next post link or increase MAX_AUTO_FETCH_POSTS"
                        )
                    break
                
                # Run scan and get next post link
                next_link = await run_full_scan(self.userbot, limit=100, start_link=current_link)
                posts_processed += 1
                
                # Check if we should continue to next post
                if next_link and Config.AUTO_FETCH_NEXT_POST and not state.stop_requested:
                    logger.info(f"Auto-fetching next post ({posts_processed + 1}): {next_link}")
                    if self.status_message and self.bot.is_connected:
                        await self.status_message.edit_text(
                            f"✅ Post {posts_processed} complete!\n\n"
                            f"🔄 Auto-fetching post {posts_processed + 1}...\n"
                            f"Total files: {state.files_received}"
                        )
                    await asyncio.sleep(2)  # Brief delay between posts
                    current_link = next_link
                else:
                    # No more posts or auto-fetch disabled
                    break
            
            # Final status message
            if self.status_message and not state.stop_requested and self.bot.is_connected:
                await self.status_message.edit_text(
                    f"✅ All scanning completed!\n\n"
                    f"📊 Posts processed: {posts_processed}\n"
                    f"📁 Total files: {state.files_received}"
                )
                
        except asyncio.CancelledError:
            logger.info("Scan task was cancelled")
            if self.status_message and self.bot.is_connected:
                try:
                    await self.status_message.edit_text("🛑 Scan cancelled by user")
                except:
                    pass  # Ignore errors if bot already disconnected
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            if self.status_message:
                await self.status_message.edit_text(f"❌ Scan failed: {e}")
        finally:
            self._force_stop()

    async def update_progress(self, message_text: str):
        """Callback to update progress message."""
        if not self.status_message:
            return
        
        try:
            # Debounce updates? For now just try to edit.
            # Only edit if content is different to avoid errors
            if self.status_message.text != message_text:
                await self.status_message.edit_text(message_text)
        except Exception as e:
            logger.debug(f"Failed to update status message: {e}")

    async def start(self):
        await self.bot.start()
        me = await self.bot.get_me()
        logger.info(f"Control Bot started as @{me.username}")

    async def stop(self):
        await self.bot.stop()
