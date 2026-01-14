# Telegram Userbot - File Fetcher & Forwarder

A Telegram userbot that automates downloading files from bots via inline buttons and forwards them to your channel.

## 🎯 What It Does

This bot automates the following workflow:

```
┌─────────────────────────────────────────────────────────────┐
│  1. INDEX CHANNEL (@SeriesBayX0)                            │
│     Contains list of series with clickable links            │
│     ▶ A.N.T. Farm                                          │
│     ▶ A.P. Bio                                             │
│     ▶ #1 Happy Family USA                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ Click series link
┌─────────────────────────────────────────────────────────────┐
│  2. SERIES CHANNEL (#1 HAPPY FAMILY USA SEASON 1)           │
│     Contains download info and season buttons               │
│     ┌─────────────────────────────────────────────────┐    │
│     │ #1 Happy Family USA [2025] Index                │    │
│     │ [Download Links ⬇️]                             │    │
│     │ [SEASON 1 (720p x265)]                          │    │
│     └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ Click season button
┌─────────────────────────────────────────────────────────────┐
│  3. FILE BOT (Animated Shows 5.9)                           │
│     Sends episode files                                     │
│     ┌─────────────────────────────────────────────────┐    │
│     │ 📹 Episode01.mkv                                │    │
│     │ 📹 Episode02.mkv                                │    │
│     │ [Send All] [Next ▶]                             │    │
│     └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ Forward files
┌─────────────────────────────────────────────────────────────┐
│  4. YOUR DESTINATION CHANNEL                                │
│     All files forwarded here automatically!                 │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

- 🔐 **User Session Authentication** - Uses Pyrogram session string (not bot token)
- 📋 **Index Channel Scanning** - Automatically finds series from the index
- 🔗 **Auto Channel Joining** - Joins series channels automatically
- 🖱️ **Smart Button Clicking** - Handles "Download Links", season buttons, "Send All", "Next"
- 📁 **File Detection** - Collects video/document files from bots
- 📤 **Auto Forwarding** - Forwards all media to your channel
- ⏱️ **Rate Limit Protection** - Configurable delays and FloodWait handling

## 📁 Project Structure

```
fetcher/
├── main.py              # Entry point - starts the scan
├── config.py            # Configuration from environment
├── handlers.py          # Multi-channel flow logic
├── utils.py             # Button clicking utilities
├── session_generator.py # Generate your session string
├── requirements.txt     # Dependencies
├── .env.example         # Configuration template
└── .env                 # Your configuration (create this)
```

## 🚀 Quick Start

### 1. Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Create an application
4. Copy your `API_ID` and `API_HASH`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate Session String

```bash
python session_generator.py
```

This will:
- Ask for your API_ID and API_HASH  
- Ask for your phone number
- Send you a verification code
- Output your session string

### 4. Create Configuration

```bash
copy .env.example .env
```

Edit `.env`:

```env
API_ID=12345678
API_HASH=your_api_hash_here
SESSION_STRING=your_long_session_string_here

# Index channel with series list
INDEX_CHANNEL=@SeriesBayX0

# Your destination channel
DESTINATION_CHANNEL=-1003321519174

# How many series to process (0 = unlimited)
MAX_SERIES_TO_PROCESS=5
```

### 5. Run the Bot

```bash
python main.py
```

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `API_ID` | Telegram API ID | Required |
| `API_HASH` | Telegram API Hash | Required |
| `SESSION_STRING` | Pyrogram session string | Required |
| `INDEX_CHANNEL` | Index channel with series list | `@SeriesBayX0` |
| `DESTINATION_CHANNEL` | Your channel to forward to | Required |
| `MAX_SERIES_TO_PROCESS` | Series limit per run (0=unlimited) | `5` |
| `BUTTON_CLICK_DELAY` | Delay after clicks (sec) | `2.0` |
| `SEASON_BUTTON_DELAY` | Delay between seasons (sec) | `3.0` |
| `JOIN_CHANNEL_DELAY` | Delay after joining (sec) | `2.0` |
| `BOT_START_DELAY` | Delay after starting bot (sec) | `3.0` |
| `FILE_WAIT_TIMEOUT` | Max wait for files (sec) | `60.0` |

## 🛠️ Key Functions

### `handlers.py`

| Function | Description |
|----------|-------------|
| `process_index_channel()` | Scans index for series links |
| `process_series_channel()` | Handles a single series channel |
| `click_season_button()` | Clicks season and starts bot |
| `handle_bot_url()` | Handles bot deep links |
| `wait_and_collect_files()` | Waits for and forwards files |

### `utils.py`

| Function | Description |
|----------|-------------|
| `click_button_by_text()` | Find and click button by keywords |
| `get_all_season_buttons()` | Detect season buttons |
| `forward_media()` | Forward media to destination |
| `handle_flood_wait()` | Handle Telegram rate limits |

## 🔒 Safety Features

- **Configurable delays** prevent rate limiting
- **FloodWait handling** with automatic retry
- **Duplicate detection** avoids reprocessing
- **Logging** to console and `userbot.log`

## ⚠️ Important Notes

1. **This is a USERBOT** - Uses your personal Telegram account
2. **Keep SESSION_STRING secret** - Anyone with it can access your account
3. **Don't set delays too low** - Respect Telegram's rate limits
4. **Use responsibly** - Comply with Telegram ToS

## 🐛 Troubleshooting

### "SESSION_STRING is required"
Run `python session_generator.py` to generate one.

### FloodWait errors
Increase delay values in `.env`.

### "Could not access series channel"
- Make sure your account can view the channel
- The bot will auto-join if possible

### No season buttons found
- Check if the page layout changed
- Look at the logs for details

### Files not forwarding
- Ensure you're an admin in the destination channel
- Check if the bot actually sent files

## 📝 License

MIT
