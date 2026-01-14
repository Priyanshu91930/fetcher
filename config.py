"""
Configuration module for the Telegram Userbot.
Loads settings from environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the userbot."""
    
    # Telegram API credentials (get from https://my.telegram.org)
    API_ID = int(os.getenv("API_ID", "37663759"))
    API_HASH = os.getenv("API_HASH", "8c279fdd3f2a8a1a441afca3766b855b")
    
    # User session string (generate using session_generator.py)
    SESSION_STRING = os.getenv("SESSION_STRING", "BQI-tA8Ail8rL_YzIckLsCRMfg8GdYsjSwkjT8X46ZZsBphX6azvFKskJja2a27bZaIfNk6SRcViMrOSjEnXNsCVKjLZwfXMSe-xZ4qu-W5HzKfM-NmjHYDVjdhDDeirLk8zkDjqnCi8Tvr_wQS6TGTBTbsHKF3b9QYDo3n8fuXhFn62neXqy6lkYdoIJVnPkIPIYqGC6x4AUjsIX7uhAr5bNXGzKGl7ZYT2kRae0zpnkRMZgjkbQXrzwyCc-ShFLKN3C0kvnicfG_W3hi8t2lCXt9pP2X7cVBcQSH2GFBClas_DYyd4hzhwiI_GW0KI5zAmF8jcCJMv5Dh5DXJM1y_fvWYPLQAAAAFqWGVsAA")
    
    # INDEX channel - the main channel with series list
    # This is @SeriesBayX0 - contains clickable series links
    INDEX_CHANNEL = os.getenv("INDEX_CHANNEL", "@SeriesBayX0")
    
    # Destination channel to forward files to
    # Example: "@my_channel" or -1001234567890
    _dest_channel = os.getenv("DESTINATION_CHANNEL", "-1003321519174")
    try:
        DESTINATION_CHANNEL = int(_dest_channel)
    except ValueError:
        DESTINATION_CHANNEL = _dest_channel
    
    # Bot username that sends the files (the third-party bot)
    # Example: "@file_bot"
    FILE_BOT_USERNAME = os.getenv("FILE_BOT_USERNAME", "")

    # Control Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8523574826:AAFEo1U0lgRpT6cmU7x9-Qk1oSaNtCkYcYk")

    # Admin User IDs (comma separated)
    # If empty, anyone can control the bot (NOT RECOMMENDED)
    _admin_ids = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = [int(x.strip()) for x in _admin_ids.split(",") if x.strip().isdigit()]

    
    # Delay settings (in seconds) to avoid rate limits
    BUTTON_CLICK_DELAY = float(os.getenv("BUTTON_CLICK_DELAY", "2.0"))
    SEASON_BUTTON_DELAY = float(os.getenv("SEASON_BUTTON_DELAY", "3.0"))
    FILE_COLLECTION_DELAY = float(os.getenv("FILE_COLLECTION_DELAY", "1.5"))
    FORWARD_DELAY = float(os.getenv("FORWARD_DELAY", "1.0"))
    NEXT_BUTTON_DELAY = float(os.getenv("NEXT_BUTTON_DELAY", "2.0"))
    JOIN_CHANNEL_DELAY = float(os.getenv("JOIN_CHANNEL_DELAY", "2.0"))
    BOT_START_DELAY = float(os.getenv("BOT_START_DELAY", "3.0"))
    
    # Maximum wait time for file bot response (in seconds)
    FILE_WAIT_TIMEOUT = float(os.getenv("FILE_WAIT_TIMEOUT", "60.0"))
    
    # How many series to process per run (0 = unlimited)
    MAX_SERIES_TO_PROCESS = int(os.getenv("MAX_SERIES_TO_PROCESS", "0"))
    
    # Keywords to identify buttons
    DOWNLOAD_BUTTON_KEYWORDS = ["download", "⬇️", "get", "links"]
    SEASON_BUTTON_KEYWORDS = ["season", "s0", "s1", "s2", "720p", "1080p", "x265", "x264"]
    SEND_ALL_KEYWORDS = ["send all", "send_all", "all files", "get all", "batch"]
    NEXT_BUTTON_KEYWORDS = ["next", "→", ">>", "more", "▶", "➡"]
    START_KEYWORDS = ["start", "begin", "go"]
    
    # File types to forward
    ALLOWED_MEDIA_TYPES = ["video", "document", "audio"]
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """Validate that all required configuration is set."""
        errors = []
        
        if not cls.API_ID or cls.API_ID == 0:
            errors.append("API_ID is required")
        if not cls.API_HASH:
            errors.append("API_HASH is required")
        if not cls.SESSION_STRING:
            errors.append("SESSION_STRING is required")
        if not cls.INDEX_CHANNEL:
            errors.append("INDEX_CHANNEL is required")
        if not cls.DESTINATION_CHANNEL:
            errors.append("DESTINATION_CHANNEL is required")
            
        return len(errors) == 0, errors
