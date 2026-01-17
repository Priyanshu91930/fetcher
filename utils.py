"""
Utility functions for the Telegram Userbot.
Contains helper functions for button clicking, delays, and error handling.
"""

import asyncio
import logging
from typing import Optional, List
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardButton
from pyrogram.errors import FloodWait, MessageNotModified, ButtonDataInvalid

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def safe_sleep(seconds: float, reason: str = ""):
    """
    Sleep for specified seconds with logging.
    
    Args:
        seconds: Duration to sleep
        reason: Optional reason for the delay (for logging)
    """
    if reason:
        logger.debug(f"Sleeping {seconds}s: {reason}")
    await asyncio.sleep(seconds)


async def handle_flood_wait(e: FloodWait, session_manager=None):
    """
    Handle FloodWait exception by sleeping for the required duration.
    If wait time exceeds threshold and session manager is available, trigger session switch.
    
    Args:
        e: FloodWait exception
        session_manager: Optional SessionManager instance for session switching
        
    Raises:
        LongFloodWaitException: If wait time exceeds threshold and session switching is enabled
    """
    from config import Config
    from session_manager import LongFloodWaitException
    
    wait_time = e.value
    logger.warning(f"⚠️ FloodWait detected! Required wait: {wait_time} seconds ({wait_time / 60:.1f} minutes)")
    
    # Check if we should switch sessions instead of waiting
    if (Config.AUTO_SWITCH_SESSION and 
        session_manager and 
        session_manager.has_alternate_sessions() and 
        wait_time > Config.FLOOD_WAIT_THRESHOLD):
        
        logger.warning(
            f"🚨 FloodWait ({wait_time}s) exceeds threshold ({Config.FLOOD_WAIT_THRESHOLD}s). "
            f"Triggering session switch..."
        )
        raise LongFloodWaitException(wait_time, Config.FLOOD_WAIT_THRESHOLD)
    
    # Normal wait (with buffer)
    wait_with_buffer = wait_time + 5
    logger.info(f"Sleeping for {wait_with_buffer} seconds (wait time + 5s buffer)...")
    await asyncio.sleep(wait_with_buffer)


def find_button_by_text(
    message: Message,
    keywords: List[str],
    exact_match: bool = False
) -> Optional[InlineKeyboardButton]:
    """
    Find an inline button by matching text against keywords.
    
    Args:
        message: Message containing inline keyboard
        keywords: List of keywords to search for
        exact_match: If True, require exact match; otherwise, check if keyword is in text
        
    Returns:
        The matching button or None if not found
    """
    if not message.reply_markup or not message.reply_markup.inline_keyboard:
        return None
    
    for row in message.reply_markup.inline_keyboard:
        for button in row:
            button_text = button.text.lower().strip()
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if exact_match:
                    if button_text == keyword_lower:
                        return button
                else:
                    if keyword_lower in button_text:
                        return button
    
    return None


def find_all_buttons_by_text(
    message: Message,
    keywords: List[str]
) -> List[InlineKeyboardButton]:
    """
    Find all inline buttons matching any of the keywords.
    
    Args:
        message: Message containing inline keyboard
        keywords: List of keywords to search for
        
    Returns:
        List of matching buttons
    """
    buttons = []
    
    if not message.reply_markup or not message.reply_markup.inline_keyboard:
        return buttons
    
    for row in message.reply_markup.inline_keyboard:
        for button in row:
            button_text = button.text.lower().strip()
            for keyword in keywords:
                if keyword.lower() in button_text:
                    buttons.append(button)
                    break
    
    return buttons


def get_all_season_buttons(message: Message) -> List[InlineKeyboardButton]:
    """
    Get all season buttons from a message.
    Looks for buttons with "SEASON" or "S1", "S2", etc.
    Also matches quality indicators like "720p", "1080p", "x265"
    
    Examples of matched buttons:
    - "SEASON 1"
    - "SEASON 1 (720p x265)"
    - "S01", "S1"
    - "Season 2 1080p"
    
    Args:
        message: Message containing inline keyboard
        
    Returns:
        List of season buttons in order
    """
    import re
    season_buttons = []
    
    if not message.reply_markup or not message.reply_markup.inline_keyboard:
        return season_buttons
    
    # Pattern to match season buttons
    # Matches: SEASON 1, Season 2, S01, S1, etc.
    season_pattern = re.compile(
        r'(season\s*\d+|s\d+|s0\d+)',
        re.IGNORECASE
    )
    
    for row in message.reply_markup.inline_keyboard:
        for button in row:
            button_text = button.text.strip()
            
            # Check if button text matches season pattern
            if season_pattern.search(button_text):
                season_buttons.append(button)
                continue
            
            # Also check for quality-only buttons that might be seasons
            # e.g., "720p x265" if it comes after "Download Links"
            button_upper = button_text.upper()
            if any(q in button_upper for q in ["720P", "1080P", "480P", "2160P", "X265", "X264", "HEVC"]):
                # Could be a season with quality, check for numbers
                if re.search(r'\d+', button_text):
                    season_buttons.append(button)
    
    return season_buttons


async def click_button(
    client: Client,
    message: Message,
    button: InlineKeyboardButton
) -> bool:
    """
    Click an inline button safely with error handling.
    
    Args:
        client: Pyrogram client
        message: Message containing the button
        button: Button to click
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Clicking button: '{button.text}'")
        
        if button.callback_data:
            # Callback button - request callback
            await message.click(button.callback_data)
        elif button.url:
            # URL button - handle differently (might be a deep link)
            logger.info(f"Button is URL: {button.url}")
            # If it's a t.me link, we might need to start a bot
            if "t.me/" in button.url and "start=" in button.url:
                # Extract bot username and start parameter
                # Format: https://t.me/botname?start=parameter
                parts = button.url.split("t.me/")[1]
                bot_username = parts.split("?")[0]
                start_param = parts.split("start=")[1] if "start=" in parts else ""
                
                logger.info(f"Starting bot @{bot_username} with param: {start_param}")
                await client.send_message(f"@{bot_username}", f"/start {start_param}")
            return True
        
        await safe_sleep(Config.BUTTON_CLICK_DELAY, "post button click")
        return True
        
    except FloodWait as e:
        await handle_flood_wait(e)
        return await click_button(client, message, button)  # Retry
    except MessageNotModified:
        logger.debug("Message not modified (button already clicked or no change)")
        return True
    except ButtonDataInvalid:
        logger.error(f"Invalid button data for: '{button.text}'")
        return False
    except Exception as e:
        logger.error(f"Error clicking button '{button.text}': {e}")
        return False


async def click_button_by_text(
    client: Client,
    message: Message,
    keywords: List[str],
    exact_match: bool = False
) -> bool:
    """
    Find and click a button by matching text.
    
    Args:
        client: Pyrogram client
        message: Message containing the button
        keywords: Keywords to search for in button text
        exact_match: Require exact match if True
        
    Returns:
        True if button found and clicked, False otherwise
    """
    button = find_button_by_text(message, keywords, exact_match)
    
    if button:
        return await click_button(client, message, button)
    
    logger.debug(f"No button found matching keywords: {keywords}")
    return False


def is_media_message(message: Message) -> bool:
    """
    Check if a message contains media that should be forwarded.
    
    Args:
        message: Message to check
        
    Returns:
        True if message contains forwardable media
    """
    if message.video:
        return True
    if message.document:
        # Check if it's a video file by mime type
        mime = message.document.mime_type or ""
        if "video" in mime or "mkv" in mime or "mp4" in mime or "avi" in mime:
            return True
        # Also forward other documents
        return True
    if message.audio:
        return True
    
    return False


def get_media_info(message: Message) -> str:
    """
    Get a description of the media in a message.
    
    Args:
        message: Message containing media
        
    Returns:
        String description of the media
    """
    if message.video:
        size = message.video.file_size or 0
        return f"Video: {message.video.file_name or 'unnamed'} ({size / 1024 / 1024:.2f} MB)"
    
    if message.document:
        size = message.document.file_size or 0
        return f"Document: {message.document.file_name or 'unnamed'} ({size / 1024 / 1024:.2f} MB)"
    
    if message.audio:
        size = message.audio.file_size or 0
        return f"Audio: {message.audio.file_name or 'unnamed'} ({size / 1024 / 1024:.2f} MB)"
    
    return "Unknown media"


async def forward_media(
    client: Client,
    message: Message,
    destination: str | int
) -> bool:
    """
    Forward a media message to the destination channel.
    
    Args:
        client: Pyrogram client
        message: Message to forward
        destination: Destination channel ID or username
        
    Returns:
        True if successful, False otherwise
    """
    try:
        media_info = get_media_info(message)
        logger.info(f"Forwarding: {media_info}")
        
        await message.forward(destination)
        await safe_sleep(Config.FORWARD_DELAY, "post forward")
        
        logger.info(f"Successfully forwarded: {media_info}")
        return True
        
    except FloodWait as e:
        await handle_flood_wait(e)
        return await forward_media(client, message, destination)  # Retry
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
        return False
