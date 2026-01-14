
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
            
            # Start scan in background
            asyncio.create_task(self._run_scan_task(start_link))

        @self.bot.on_message(filters.command("stop"))
        async def stop_command(client, message):
            if not self._check_admin(message):
                return
            
            if not state.is_processing:
                await message.reply_text("Nothing is running.")
                return
            
            state.stop_requested = True
            await message.reply_text("🛑 Stopping... (might take a moment to finish current item)")

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

    def _check_admin(self, message: Message) -> bool:
        if not Config.ADMIN_IDS:
            return True # Allow all if no admins set
        if message.from_user.id in Config.ADMIN_IDS:
            return True
        return False

    async def _run_scan_task(self, start_link):
        try:
            # Inject callback for progress
            state.progress_callback = self.update_progress
            
            await run_full_scan(self.userbot, limit=100, start_link=start_link)
            
            if self.status_message:
                await self.status_message.edit_text("✅ Scan completed successfully!")
                
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            if self.status_message:
                await self.status_message.edit_text(f"❌ Scan failed: {e}")
        finally:
            self.status_message = None
            state.progress_callback = None

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
