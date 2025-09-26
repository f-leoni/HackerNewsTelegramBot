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

1. Install dependencies (examples):

    ```powershell
    python -m pip install -r telegram_bot/requirements.txt
    python -m pip install pyrogram python-dotenv beautifulsoup4 requests
    ```

2. Create a `.env` file in the project root (or set environment variables) with your Telegram API credentials:

    ```ini
    API_ID=your_api_id
    API_HASH=your_api_hash
    ```

3. Run the bot (it uses a Pyrogram session named `bookmark_bot`):

    ```powershell
    python telegram_bot/bot.py
    ```

Usage

- Save or forward a message containing a URL to your Saved Messages (the account that runs this script). The bot will detect the URL, scrape metadata and save it to `bookmarks.db`. It replies to the message with a confirmation when a bookmark is saved.

Notes and troubleshooting

- The bot expects `API_ID` and `API_HASH` to be set. If missing, the script raises a ValueError.
- The provided `telegram_bot/requirements.txt` includes some dependencies; you may need to install `pyrogram`, `python-dotenv`, `requests` and `beautifulsoup4` if not already present.
- The SQLite database file (`bookmarks.db`) is created in the working directory.

If you want, I can also update `telegram_bot/requirements.txt` to include all runtime dependencies (pyrogram, python-dotenv, requests, beautifulsoup4) and add a short troubleshooting section. Tell me if you'd like that.

