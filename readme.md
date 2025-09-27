# Telegram Bot

## Send a Hacker News link to the bot to save it into the bookmarks DB

## English description

This repository contains a small Telegram client (a bot-like userbot) that saves web links shared in your Saved Messages into a local SQLite bookmarks database. When you send or forward a Hacker News link (or any other URL) to your Saved Messages, the bot extracts the URL, fetches the page to collect metadata (title, description, image, domain) and stores it in `bookmarks.db`.

Key features

- Watches your Saved Messages for URLs (uses a user session via Pyrogram).
- Extracts page metadata using requests + BeautifulSoup.
- Stores bookmarks in an SQLite database (`bookmarks.db`).
- Can export bookmarks as a simple HTML file via the `export_bookmarks_html` helper.

Quick setup

1) Install dependencies (examples):

```powershell
python -m pip install -r telegram_bot/requirements-full.txt
```

2) Create a `.env` file in the project root (or set environment variables) with your Telegram API credentials. You can copy the included example:

```powershell
copy .env.example .env
```

Then edit `.env` and fill your credentials:

```ini
API_ID=your_api_id
API_HASH=your_api_hash
```

3) Run the bot (it uses a Pyrogram session named `bookmark_bot`). You can run directly or use the provided PowerShell helper:

Direct:

```powershell
python telegram_bot/bot.py
```

With helper (creates a venv, installs deps and runs):

```powershell
.\run_bot.ps1
```

Usage

- Save or forward a message containing a URL to your Saved Messages (the account that runs this script). The bot will detect the URL, scrape metadata and save it to `bookmarks.db`. It replies to the message with a confirmation when a bookmark is saved.

Notes and troubleshooting

- The bot expects `API_ID` and `API_HASH` to be set. If missing, the script raises a ValueError.
- The provided `telegram_bot/requirements.txt` includes some dependencies; you may need to install `pyrogram`, `python-dotenv`, `requests` and `beautifulsoup4` if not already present.
- The SQLite database file (`bookmarks.db`) is created in the working directory.

Interactive session creation (auth) issues

- If you see the client prompt "Enter phone number or bot token" when starting and then an error like:
	"'BadMsgNotification' object has no attribute 'type'", this often means the auth flow was interrupted by the debugger or your system time is out-of-sync.
- To generate a user session safely, run the included helper from a normal PowerShell terminal:

```powershell
python telegram_bot/generate_session.py
```

This script will load API_ID/API_HASH from `.env` and start an interactive login that creates a local `.session` file. If the helper reports the BadMsgNotification error, follow its printed suggestions (sync clock, run outside debugger, update Pyrogram/tgcrypto).
