# Hacker News & Link Bookmark Bot

A complete bookmarking solution that combines a **Telegram bot** for quickly saving links and a **web interface** to browse, search, and manage your collection.

## Features

### Telegram Bot
- **Link Capturing**: Automatically saves links sent to a private chat with the bot or in your "Saved Messages".
- **Metadata Fetching**: Extracts the title, description, and preview image for each link.
- **Hacker News Integration**: Intelligently pairs Hacker News comment links with their corresponding articles, saving them as a single bookmark.
- **SQLite Backend**: Stores all bookmarks in a local, portable SQLite database.

### Web Server
- **Modern Web Interface**: A web-based UI to browse, search, and manage your bookmarks.
- **Multiple Views**: Choose between a detailed "Card View" and a denser "Compact View".
- **Powerful Search & Filtering**: Instantly search all your bookmarks by text, or filter by source (Telegram, Hacker News), date, and read status.
- **Full CRUD Functionality**: Add, edit, and delete bookmarks directly from the web interface.
- **Infinite Scrolling**: Bookmarks are loaded as you scroll down the page.
- **HTTPS Support**: Runs a secure server with either Let's Encrypt or self-signed certificates.

## Architecture

The project is divided into three main components:
- `telegram_bot/`: Contains the logic for the Telegram bot that captures links.
- `webserver/`: Contains the web server and the front-end user interface.
- `shared/`: A shared library with database access logic and utility functions used by both components.

## Setup and Installation

### 1. Prerequisites
- Python 3.8+
- `pip` and `venv`

### 2. Installation

1.  **Clone the repository:**
    ```sh
    git clone <YOUR_REPOSITORY_URL>
    cd HackerNewsTelegramBot
    ```

2.  **Create and activate a virtual environment:**
    ```sh
    python -m venv venv
    # Windows
    .\venv\Scripts\Activate.ps1
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    The project has dependencies for both the bot and the server. Make sure to install both.
    ```sh
    pip install -r telegram_bot/requirements.txt
    pip install -r webserver/requirements.txt
    ```

### 3. Configuration

Create a `.env` file in the project's root directory by copying the example:

```powershell
copy .env.example .env
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
