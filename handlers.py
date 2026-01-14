"""
Message handlers for the Telegram Userbot.
Handles the multi-step flow:
1. Index Channel - Contains series links
2. Series Channel - Contains Download Links + Season buttons  
3. File Bot - Sends files after clicking START
"""

import asyncio
import logging
import re
from typing import Set, Optional, List
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton
from pyrogram.errors import FloodWait, ChannelPrivate, UserAlreadyParticipant

from config import Config
from utils import (
    safe_sleep,
    handle_flood_wait,
    find_button_by_text,
    get_all_season_buttons,
    click_button,
    click_button_by_text,
    is_media_message,
    get_media_info,
    forward_media,
    find_all_buttons_by_text,
)

import os

logger = logging.getLogger(__name__)

# File to store processed series URLs
PROCESSED_FILE = "processed_series.txt"

# Track processed items to avoid duplicates
processed_series: Set[str] = set()  # Track series channel usernames
processed_seasons: Set[str] = set()  # Track season identifiers
collected_media: dict[int, int] = {} # Map message_id -> edit_date (timestamp)



def load_processed_data():
    """Load successfully processed series from file."""
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        processed_series.add(line.strip())
            logger.info(f"Loaded {len(processed_series)} processed series from {PROCESSED_FILE}")
        except Exception as e:
            logger.error(f"Error loading processed data: {e}")

def save_processed_series(series_link: str):
    """Save a processed series to file."""
    try:
        with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
            f.write(f"{series_link}\n")
    except Exception as e:
        logger.error(f"Error saving processed data: {e}")


class BotState:
    """Track the current state of the userbot."""
    is_processing: bool = False
    current_series: str = ""
    current_season: str = ""
    waiting_for_files: bool = False
    current_bot_chat_id: Optional[int] = None
    files_received: int = 0
    stop_requested: bool = False
    progress_callback = None # Callable



state = BotState()

# Load data on module import
load_processed_data()


async def join_channel(client: Client, channel_link: str) -> Optional[int | str]:
    """
    Join a channel from an invite link or username.
    
    Args:
        client: Pyrogram client
        channel_link: Channel link (t.me/xxx, @xxx, or invite link)
        
    Returns:
        Channel identifier (int ID or str username) if successful, None otherwise
    """
    try:
        # Extract channel identifier from link
        channel_id = channel_link
        
        # Handle t.me links
        if "t.me/" in channel_link:
            # Could be t.me/channelname or t.me/+invitehash or t.me/joinchat/xxx
            parts = channel_link.split("t.me/")[-1].split("?")[0].split("/")[0]
            
            if parts.startswith("+") or "joinchat" in channel_link:
                # It's an invite link
                try:
                    chat = await client.join_chat(channel_link)
                    logger.info(f"Joined channel via invite: {chat.title}")
                    await safe_sleep(Config.JOIN_CHANNEL_DELAY, "after joining channel")
                    return chat.id
                except UserAlreadyParticipant:
                    pass
                except Exception as e:
                    logger.debug(f"Could not join via link {channel_link}: {e}")
                    # If we can't join, maybe we are already in it or it's not a join link?
                    pass
            else:
                channel_id = f"@{parts}" if not parts.startswith("@") else parts
        
        # Ensure username format
        if isinstance(channel_id, str) and not channel_id.startswith("@") and not channel_id.startswith("-") and not channel_id.startswith("+"):
             # If it looks like a username but no @, add it
             if not "/" in channel_id:
                 channel_id = f"@{channel_id}"

        # Try to get chat info (also works if already joined)
        try:
            chat = await client.get_chat(channel_id)
            logger.info(f"Accessed channel: {chat.title} ({chat.id})")
            return chat.id
        except ChannelPrivate:
            # Need to join first
            try:
                chat = await client.join_chat(channel_id)
                logger.info(f"Joined channel: {chat.title}")
                await safe_sleep(Config.JOIN_CHANNEL_DELAY, "after joining channel")
                return chat.id
            except Exception as e:
                logger.error(f"Failed to join private channel {channel_id}: {e}")
                return None
            
    except FloodWait as e:
        await handle_flood_wait(e)
        return await join_channel(client, channel_link)
    except Exception as e:
        logger.error(f"Error joining channel {channel_link}: {e}")
        return None


async def process_index_channel(client: Client, limit: int = 50, start_link: str = None):
    """
    Process the index channel to find series links.
    
    Args:
        client: Pyrogram client
        limit: Number of messages to scan
        start_link: Specific message link to process (e.g., https://t.me/c/123/456)
    """
    logger.info(f"Scanning index channel: {Config.INDEX_CHANNEL}")
    
    series_count = 0
    max_series = Config.MAX_SERIES_TO_PROCESS
    
    messages_to_process = []
    
    if start_link:
        # Process specific message
        try:
            # Link format: https://t.me/channel/123 or https://t.me/c/123456789/123
            parts = start_link.split("/")
            msg_id = int(parts[-1])
            
            chat_id = Config.INDEX_CHANNEL
            # If link has /c/, it might be a private channel ID, but we rely on Config.INDEX_CHANNEL
            
            logger.info(f"Fetching specific message: {msg_id}")
            message = await client.get_messages(chat_id, msg_id)
            if message:
                messages_to_process.append(message)
            else:
                logger.error("Could not fetch the specified message.")
        except Exception as e:
            logger.error(f"Error parsing link {start_link}: {e}")
            return
    else:
        # Scan history
        async for message in client.get_chat_history(Config.INDEX_CHANNEL, limit=limit):
            messages_to_process.append(message)
            
    # Process messages
    for message in messages_to_process:
        if max_series > 0 and series_count >= max_series:
            logger.info(f"Reached max series limit: {max_series}")
            break
            
        if state.stop_requested:
            logger.info("Stop requested by user.")
            break

        
        # Look for series links in the message
        series_links = extract_series_links(message)
        
        if not series_links:
            continue
            
        logger.info(f"Found {len(series_links)} series in message {message.id}")
        
        for link_info in series_links:
            if max_series > 0 and series_count >= max_series:
                break
                
            series_name = link_info.get("name", "Unknown")
            series_link = link_info.get("link", "")
            
            if not series_link:
                continue
            
            # Skip if already processed
            if series_link in processed_series:
                logger.debug(f"Already processed: {series_name}")
                continue
            
            logger.info(f"Found series: {series_name}")
            await report_status(f"🔄 Processing: {series_name}\nFiles: {state.files_received}")

            
            # Process this series
            success = await process_series_channel(client, series_link, series_name)
            
            if success:
                processed_series.add(series_link)
                save_processed_series(series_link)
                series_count += 1
            
            # Delay between series
            await safe_sleep(3, "between series")
            
    logger.info(f"Finished processing. Processed {series_count} series.")
    await report_status(f"✅ Scan Complete!\nProcessed {series_count} series.")

async def report_status(text: str):
    """Helper to report status via callback."""
    if state.progress_callback:
        try:
            await state.progress_callback(text)
        except:
            pass



def extract_series_links(message: Message) -> List[dict]:
    """
    Extract series links from a message.
    """
    links = []
    
    # Check for inline buttons with URLs
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for button in row:
                if button.url and "t.me/" in button.url:
                    links.append({
                        "name": button.text,
                        "link": button.url
                    })
    
    # Check for entities (text links)
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    
    for entity in entities:
        # Check for TEXT_LINK (hidden URL) using reliable string check
        entity_type = str(entity.type)
        
        
        # Check for TEXT_LINK (hidden URL)
        if "TEXT_LINK" in entity_type and entity.url:
            if "t.me/" in entity.url:
                name = text[entity.offset:entity.offset + entity.length]
                links.append({
                    "name": name,
                    "link": entity.url
                })
        # Check for URL (visible URL)
        elif "URL" in entity_type and "TEXT_LINK" not in entity_type:
            # Plain URL in text
            url = text[entity.offset:entity.offset + entity.length]
            if "t.me/" in url:
                links.append({
                    "name": url.split("/")[-1],
                    "link": url
                })
    
    return links


async def process_series_channel(
    client: Client, 
    channel_link: str,
    series_name: str
) -> bool:
    """
    Process a series channel to find and click season buttons.
    
    Args:
        client: Pyrogram client
        channel_link: Link to the series channel
        series_name: Name of the series
        
    Returns:
        True if successfully processed
    """
    logger.info(f"Processing series channel: {series_name}")
    state.current_series = series_name
    state.is_processing = True
    
    try:
        # Join/access the series channel
        channel_id = await join_channel(client, channel_link)
        if not channel_id:
            logger.error(f"Could not access series channel: {channel_link}")
            return False
        
        await safe_sleep(1, "after accessing channel")
        
        # Find the message with Download Links / Season buttons
        download_message = await find_download_message(client, channel_id)
        
        if not download_message:
            logger.warning(f"No download message found in {series_name}")
            return False
        
        # Click "Download Links" if present
        download_clicked = await click_button_by_text(
            client, download_message, Config.DOWNLOAD_BUTTON_KEYWORDS
        )
        
        if download_clicked:
            logger.info("Clicked 'Download Links' button")
            await safe_sleep(Config.BUTTON_CLICK_DELAY, "waiting for season buttons")
            
            # Refresh the message to get updated buttons
            download_message = await client.get_messages(
                channel_id, 
                download_message.id
            )
        
        # Process season buttons
        await process_season_buttons(client, download_message, channel_id)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing series channel: {e}")
        return False
    finally:
        state.is_processing = False
        state.current_series = ""


async def find_download_message(
    client: Client, 
    channel_id: int | str,
    limit: int = 30
) -> Optional[Message]:
    """
    Find the message with Download Links or Season buttons.
    
    Args:
        client: Pyrogram client
        channel_id: Channel to search in
        limit: Number of messages to scan
        
    Returns:
        Message with buttons, or None
    """
    try:
        async for message in client.get_chat_history(channel_id, limit=limit):
            if not message.reply_markup or not message.reply_markup.inline_keyboard:
                continue
            
            # Check for download or season buttons
            has_download = find_button_by_text(message, Config.DOWNLOAD_BUTTON_KEYWORDS)
            has_season = get_all_season_buttons(message)
            
            if has_download or has_season:
                logger.info(f"Found download message: {message.id}")
                return message
        
        # Also check pinned message
        try:
            chat = await client.get_chat(channel_id)
            if chat.pinned_message:
                pinned = await client.get_messages(channel_id, chat.pinned_message.id)
                if pinned and pinned.reply_markup:
                    return pinned
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error finding download message: {e}")
    
    return None


async def process_season_buttons(
    client: Client, 
    message: Message,
    channel_id: str
):
    """
    Process all season buttons in a message.
    
    Args:
        client: Pyrogram client
        message: Message with season buttons
        channel_id: Channel ID for refreshing message
    """
    season_buttons = get_all_season_buttons(message)
    
    if not season_buttons:
        logger.info("No season buttons found")
        return
    
    logger.info(f"Found {len(season_buttons)} season(s)")
    
    for i, button in enumerate(season_buttons):
        season_id = f"{channel_id}_{button.text}"
        
        if season_id in processed_seasons:
            logger.debug(f"Already processed season: {button.text}")
            continue
        
        state.current_season = button.text
        logger.info(f"Processing {button.text} ({i + 1}/{len(season_buttons)})")
        await report_status(
            f"🔄 Processing: {state.current_series}\n"
            f"Season: {button.text} ({i + 1}/{len(season_buttons)})\n"
            f"Files: {state.files_received}"
        )

        
        # Click the season button
        success = await click_season_button(client, message, button)
        
        if success:
            processed_seasons.add(season_id)
        
        # Delay between seasons
        await safe_sleep(Config.SEASON_BUTTON_DELAY, "between seasons")
        
        # Refresh message for next season
        try:
            message = await client.get_messages(channel_id, message.id)
        except:
            pass


async def click_season_button(
    client: Client,
    message: Message, 
    button: InlineKeyboardButton
) -> bool:
    """
    Click a season button and handle the resulting bot interaction.
    
    The button might:
    - Open a bot via URL (t.me/botname?start=xxx)
    - Trigger a callback that opens a bot
    
    Args:
        client: Pyrogram client
        message: Message containing the button
        button: Season button to click
        
    Returns:
        True if files were collected
    """
    try:
        logger.info(f"Clicking season button: '{button.text}'")
        
        if button.url:
            # URL button - usually t.me/botname?start=param
            return await handle_bot_url(client, button.url)
        elif button.callback_data:
            # Callback button - click it and see what happens
            await message.click(button.callback_data)
            await safe_sleep(Config.BUTTON_CLICK_DELAY, "after callback")
            
            # The bot might send a message with a URL button
            # Or directly start sending files
            state.waiting_for_files = True
            await wait_and_collect_files(client)
            state.waiting_for_files = False
            return True
            
    except FloodWait as e:
        await handle_flood_wait(e)
        return await click_season_button(client, message, button)
    except Exception as e:
        logger.error(f"Error clicking season button: {e}")
        return False
    
    return False


async def handle_bot_url(client: Client, url: str) -> bool:
    """
    Handle a bot URL (t.me/botname?start=param).
    
    Args:
        client: Pyrogram client
        url: Bot URL
        
    Returns:
        True if files were collected
    """
    try:
        # Parse the URL: https://t.me/BotName?start=parameter
        if "t.me/" not in url:
            return False
        
        parts = url.split("t.me/")[1]
        bot_username = parts.split("?")[0].split("/")[0]
        
        # Extract start parameter
        start_param = ""
        if "start=" in url:
            start_param = url.split("start=")[1].split("&")[0]
        
        logger.info(f"Starting bot @{bot_username} with param: {start_param}")
        
        # Send /start command to the bot
        if start_param:
            await client.send_message(f"@{bot_username}", f"/start {start_param}")
        else:
            await client.send_message(f"@{bot_username}", "/start")
        
        await safe_sleep(Config.BOT_START_DELAY, "waiting for bot response")
        
        # Wait for files from this bot
        state.waiting_for_files = True
        state.current_bot_chat_id = None  # Will be set when we receive a message
        
        await wait_and_collect_files(client, bot_username)
        
        state.waiting_for_files = False
        return True
        
    except FloodWait as e:
        await handle_flood_wait(e)
        return await handle_bot_url(client, url)
    except Exception as e:
        logger.error(f"Error handling bot URL: {e}")
        return False


async def wait_and_collect_files(
    client: Client, 
    bot_username: str = None,
    timeout: float = None
):
    """
    Wait for and collect files sent by the file bot.
    
    Args:
        client: Pyrogram client
        bot_username: Expected bot username
        timeout: Override default timeout
    """
    timeout = timeout or Config.FILE_WAIT_TIMEOUT
    logger.info(f"Waiting for files from {bot_username or 'any bot'}... (timeout: {timeout}s)")
    
    start_time = asyncio.get_event_loop().time()
    state.files_received = 0
    last_activity = start_time
    
    while True:
        current_time = asyncio.get_event_loop().time()
        
        # Check overall timeout from last activity
        if current_time - last_activity > timeout:
            logger.info(f"File collection timeout. Received {state.files_received} files.")
            break

            
        if state.stop_requested:
             logger.info("Stop requested during file collection.")
             break

        
        # Check for new messages from the bot
        if bot_username:
            try:
                async for message in client.get_chat_history(f"@{bot_username}", limit=10):
                    if message.id in collected_media:
                        # Check if message was edited since we last saw it
                        last_edit = collected_media[message.id]
                        current_edit = int(message.edit_date.timestamp()) if message.edit_date else int(message.date.timestamp())
                        
                        if current_edit <= last_edit:
                            continue # No new changes
                    
                    # Check if this is a recent message (within our session)
                    if message.date.timestamp() < start_time - 60 and not message.edit_date:  # Skip old messages unless edited
                        continue

                    
                    # Process the message
                    files_found = await handle_file_bot_message(client, message)
                    
                    if files_found:
                        last_activity = asyncio.get_event_loop().time()
                        
            except Exception as e:
                logger.debug(f"Error checking bot messages: {e}")
        
        # Small delay to prevent busy waiting
        await asyncio.sleep(1)
    
    logger.info(f"Finished collecting files: {state.files_received} total")


async def handle_file_bot_message(client: Client, message: Message) -> bool:
    """
    Handle a message from the file bot.
    
    Args:
        client: Pyrogram client
        message: Message from the file bot
        
    Returns:
        True if media was found/forwarded
    """
    current_timestamp = int(message.edit_date.timestamp()) if message.edit_date else int(message.date.timestamp())
    
    if message.id in collected_media:
        last_edit = collected_media[message.id]
        if current_timestamp <= last_edit:
             return False
    
    collected_media[message.id] = current_timestamp
    found_media = False

    
    # Check if it's a media message
    if is_media_message(message):
        media_info = get_media_info(message)
        logger.info(f"Received media: {media_info}")
        
        # Forward to destination
        success = await forward_media(
            client, message, Config.DESTINATION_CHANNEL
        )
        
        if success:
            state.files_received += 1
            logger.info(f"Forwarded ({state.files_received}): {media_info}")
            await report_status(
                f"🔄 Processing: {state.current_series}\n"
                f"Season: {state.current_season}\n"
                f"Files: {state.files_received}"
            )
            found_media = True

    
    # Check for control buttons
    if message.reply_markup:
        # Check for "Send All" button
        send_all_clicked = await click_button_by_text(
            client, message, Config.SEND_ALL_KEYWORDS
        )
        
        if send_all_clicked:
            logger.info("Clicked 'Send All' button")
            await safe_sleep(Config.BUTTON_CLICK_DELAY, "after Send All")
            return True
        
        # Check for "Next" button (for pagination)
        next_button = find_button_by_text(message, Config.NEXT_BUTTON_KEYWORDS)
        if next_button:
            logger.info("Found 'Next' button, clicking for more files...")
            await click_button(client, message, next_button)
            await safe_sleep(Config.NEXT_BUTTON_DELAY, "after Next button")
            return True
    
    return found_media


def create_handlers(client: Client):
    """
    Create and register message handlers for real-time monitoring.
    
    Args:
        client: Pyrogram client to register handlers on
    """
    
    @client.on_message(filters.private & filters.incoming)
    async def private_message_handler(client: Client, message: Message):
        """Handle private messages (from bots sending files)."""
        if not state.waiting_for_files:
            return
        
        await handle_file_bot_message(client, message)
    
    logger.info("Real-time handlers registered")


async def run_full_scan(client: Client, limit: int = 50, start_link: str = None):
    """
    Run a full scan of the index channel.
    
    Args:
        client: Pyrogram client
        limit: Number of messages to scan in index channel
        start_link: Specific message link to process
    """
    logger.info("Starting scan...")
    await process_index_channel(client, limit=limit, start_link=start_link)
    logger.info("Scan completed")
