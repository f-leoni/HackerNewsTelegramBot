"""
Main module of the Telegram bot for saving bookmarks.
"""
import os
import sys
import re
import sqlite3
from pyrogram import Client, filters
from datetime import datetime
from urllib.parse import urlparse

# Add the project root to the path to import the shared library
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from shared.database import init_database, get_db_path
from shared.utils import get_article_metadata
import logging

# Setup logging
__version__ = "1.0"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Dynamic import for compatibility ---
from dotenv import load_dotenv
from pyrogram.enums import ChatType, MessageEntityType

# Search for StringSession in common paths to support different Pyrogram versions
StringSession = None
for path in ('pyrogram.storage.storage', 'pyrogram.sessions.string_session', 'pyrogram.sessions', 'pyrogram.storage'):
    try:
        StringSession = getattr(__import__(path, fromlist=['StringSession']), 'StringSession')
        break
    except (ImportError, AttributeError):
        continue


class BookmarkBot:
    """
    A Telegram bot that saves bookmarks from messages containing URLs.
    
    This bot monitors messages (in Saved Messages when running as user, or in private 
    chat when running as bot) and extracts URLs to save them as bookmarks with metadata.
    
    Attributes:
        app (Client): The Pyrogram client instance used to interact with Telegram.
        _me_id (int): Cached user ID of the running client (set after first lookup).
    """

    def __init__(self):
        # Load environment variables

        load_dotenv()
        try:
            here_env = os.path.join(os.path.dirname(__file__), ".env")
            if os.path.exists(here_env):
                load_dotenv(here_env, override=False)
        except Exception:
            pass

        self.api_id = os.getenv("API_ID")
        self.api_hash = os.getenv("API_HASH")
        # Optional credentials: BOT_TOKEN for bot account, or SESSION_STRING to avoid interactive login
        self.bot_token = os.getenv("BOT_TOKEN")
        self.session_string = os.getenv("SESSION_STRING")

        # Debug log: show which authentication environment variables are present
        logger.info(
            "Auth env presence: BOT_TOKEN=%s, SESSION_STRING=%s, API_ID=%s, API_HASH=%s",
            "yes" if self.bot_token else "no",
            "yes" if self.session_string else "no",
            "yes" if self.api_id else "no",
            "yes" if self.api_hash else "no",
        )

        # Initialize the Pyrogram client. For Docker, only non-interactive modes are supported.
        if self.bot_token:
            # Bot Mode: use a BOT_TOKEN. Does not require API_ID/HASH except for specific functions.
            logger.info("Auth mode: BOT_TOKEN (bot account)")
            self.app = Client(
                name="bookmark_bot_session", # Session name for the bot
                api_id=self.api_id,
                api_hash=self.api_hash,
                bot_token=self.bot_token
            )
        elif self.session_string:
            # Non-interactive User Mode: use a SESSION_STRING.
            logger.info("Auth mode: SESSION_STRING (user session)")
            if not self.api_id or not self.api_hash:
                raise ValueError("SESSION_STRING requires API_ID and API_HASH to also be set in the .env file.")
            self.app = Client(
                name="bookmark_bot_session", # A consistent session name
                session_string=self.session_string,
                api_id=self.api_id,
                api_hash=self.api_hash,
            )
        else:
            # If neither mode is configured, the bot cannot start.
            raise ValueError(
                "No valid authentication mode for Docker. Set BOT_TOKEN or SESSION_STRING in the .env file."
            )

        # Initialize database
        init_database() # Ensure the DB and tables exist on startup

        # Register handlers
        self.setup_handlers()

    def extract_urls(self, text):
        """
        Extracts and normalizes URLs from text content.

        Finds URLs in text and ensures they have proper protocol (adds https:// if missing).
        Validates URL structure and filters out invalid or malformed URLs.

        Args:
            text (str): The text content to scan for URLs.

        Returns:
            list[str]: List of normalized valid URLs found in the text.
            Empty list if no valid URLs found or text is None/empty.
        """
        urls = []
        
        if not text:
            return urls
            
        # Check for URLs in text
        for word in text.split():
            # Skip words that are too short to be URLs
            if len(word) < 3:
                continue
                
            # Clean up the URL by removing trailing punctuation
            word = word.rstrip(',.!?:;\'\"')
            
            # If URL doesn't start with a protocol, add https://
            if not word.startswith(('http://', 'https://')):
                if '://' in word:  # Has some other protocol
                    continue
                # Add https:// only if word looks like a domain
                if '.' in word and not word.startswith('.'): 
                    word = 'https://' + word
                    
            try:
                # Validate URL structure
                result = urlparse(word)
                if result.netloc:
                    urls.append(word)
            except Exception as e:
                logger.debug(f"Failed to parse URL {word}: {e}")
                
        return urls

    def get_hn_comments_url(self, url):
        """
        Extracts the Hacker News comments URL from an article URL if possible.

        Attempts to find the HN comments page URL by checking URL patterns and
        querying the HN API when needed.

        Args:
            url (str): The URL to check for HN comments.

        Returns:
            str: The HN comments URL if found, None otherwise.
        """
        parsed_url = urlparse(url)
        if parsed_url.netloc == "news.ycombinator.com":
            query_params = dict(p.split('=') for p in parsed_url.query.split('&') if '=' in p)
            item_id = query_params.get('id')
            if item_id:
                return f"https://news.ycombinator.com/item?id={item_id}"
        return None

    def save_bookmark(self, url, metadata, message, comments_url_override=None):
        """
        Saves a URL as a bookmark in the database with metadata.

        Stores the URL, metadata (title, description etc.), message info and optional
        comments URL in the bookmarks database. Associates the bookmark with the first
        web user found in the database.

        Args:
            url (str): The URL to bookmark.
            metadata (dict): Metadata for the URL (title, description etc.).
            message (Message): The Telegram message containing the URL.
            comments_url_override (str, optional): Override the auto-detected comments URL.

        Returns:
            bool: True if bookmark was saved successfully, False otherwise.
        """
        db_path = get_db_path()
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            from_user_id = getattr(message.from_user, "id", None)
            comments_url = comments_url_override if comments_url_override is not None else self.get_hn_comments_url(url)

            # Retrieve the ID of the first webserver user to associate the bookmark
            cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
            web_user = cursor.fetchone()
            web_user_id = web_user[0] if web_user else None

            if not web_user_id:
                logger.error("No web user found in the database. Cannot associate bookmark.")
                return False

            cursor.execute(
                """
                INSERT OR REPLACE INTO bookmarks 
                (user_id, url, title, description, image_url, domain, telegram_user_id, telegram_message_id, comments_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    web_user_id,
                    url,
                    metadata["title"],
                    metadata["description"],
                    metadata["image_url"],
                    metadata["domain"],
                    from_user_id,
                    message.id,
                    comments_url,
                ),
            )
            conn.commit()
            logger.info(f"Bookmark saved: {metadata['title']}")
            return True
        except Exception as e:
            logger.error(f"Error saving bookmark: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def setup_handlers(self):
        """
        Configures message handlers for the bot.

        Sets up handlers to process messages:
        - For user sessions: monitors Saved Messages
        - For bot mode: processes messages in private chats
        
        The handlers extract URLs from messages and save them as bookmarks.
        """

        @self.app.on_message(filters.private & ~filters.command(["count", "help"]))
        async def handle_private_message(client, message):
            """Handler for messages in saved messages
            
            This handler is registered within an instance method to have access to `self`.
            It analyzes incoming messages and extracts URLs from text, captions, previews (web_page),
            and from the message "entities", to also support forwarded messages.
            """

            # Debug log: summarizes incoming message information for easier diagnosis.
            try:
                logger.info(
                    "Incoming message: chat_id=%s from_id=%s forward_from=%s text_len=%s caption_len=%s web_page=%s ents=%s cap_ents=%s",
                    getattr(message.chat, "id", None),
                    getattr(getattr(message, "from_user", None), "id", None),
                    repr(getattr(message, "forward_from", None)),
                    len(message.text or ""),
                    len(getattr(message, "caption", "") or ""),
                    bool(getattr(message, "web_page", None)),
                    bool(getattr(message, "entities", None)),
                    bool(getattr(message, "caption_entities", None)),
                )
            except Exception:
                logger.info("Incoming message received (could not serialize fields)")

            # Store the user/bot ID on the first call (necessary for user mode)
            if not hasattr(self, "_my_user_id") or self._my_user_id is None:
                me = await client.get_me()
                self._my_user_id = me.id
                logger.info("Running as user: %s (ID: %s)", getattr(me, 'username', 'N/A'), me.id)

            # If running as a bot, only process messages received in a private chat.
            if self.bot_token:
                logger.info("-> Checking BOT mode")
                if not message.chat or message.chat.type != ChatType.PRIVATE:
                    # Ignore messages from groups or channels by default
                    logger.info("Bot mode: ignoring non-private chat (type: %s)", message.chat.type)
                    return
                logger.info("-> OK: Private chat. Proceeding with message analysis.")
                await self.process_message_for_urls(message)
            else:
                logger.info("-> Checking USER mode (user session)")
                # The check for "Saved Messages" has been removed.
                # The bot will now process messages from any private chat.
                logger.info("-> OK: Proceeding with message analysis in private chat.")
                await self.process_message_for_urls(message)

        @self.app.on_message(filters.command("count") & filters.private)
        async def handle_count_command(client, message):
            """Handles the /count command to return the total number of bookmarks."""
            db_path = get_db_path()
            conn = None
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Find the web user to count bookmarks for.
                # This logic matches how bookmarks are saved.
                cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
                web_user = cursor.fetchone()

                if not web_user:
                    await message.reply("No web user configured. Cannot count bookmarks.")
                    return

                web_user_id = web_user[0]

                cursor.execute("SELECT COUNT(*) FROM bookmarks WHERE user_id = ?", (web_user_id,))
                count = cursor.fetchone()[0]
                
                await message.reply(f"You have saved a total of **{count}** bookmarks.")
                
            except Exception as e:
                logger.error(f"Error handling /count command: {e}")
                await message.reply("Si è verificato un errore nel contare i bookmark.")

        @self.app.on_message(filters.command("help") & filters.private)
        async def handle_help_command(client, message):
            """Handles the /help command to show usage instructions."""
            help_text = (
                "**Welcome to your Bookmark Bot!**\n\n"
                "Here's how you can use me:\n\n"
                "🔗 **Saving a link**\n"
                "Just send a message containing one or more links. "
                "I will automatically save them as bookmarks.\n\n"
                "🗞️ **HackerNews Links**\n"
                "If you send a link to an article and a link to the HackerNews comments "
                "in the same message, I will link them into a single bookmark.\n\n"
                "🤖 **Available commands**\n"
                "- `/count`: Shows the total number of bookmarks you have saved.\n"
                "- `/help`: Shows this help message.\n\n"
                "Your bookmarks are visible in the web interface."
            )
            try:
                await message.reply(help_text, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Error handling /help command: {e}")

    async def process_message_for_urls(self, message):
        """
        Processes a message to extract and save URLs as bookmarks.

        Extracts URLs from message text/caption/entities, gets metadata for each URL,
        and saves them as bookmarks. Also attempts to find HN comments URLs when 
        relevant.

        Args:
            message (Message): The Telegram message to process.

        Returns:
            None
        """
        logger.info("--> Entered process_message_for_urls")

        # Search for URLs in the message (supports text, captions, and web_page)
        urls = []

        # Search for URLs in the message entities (text or caption)
        entities_source = None
        if getattr(message, "entities", None):
            entities_source = message.text or ""
        elif getattr(message, "caption_entities", None):
            entities_source = message.caption or ""

        if entities_source:
            logger.info("--> Analyzing message 'entities' for URLs...")
            ents = (
                message.entities
                if getattr(message, "entities", None)
                else message.caption_entities
            )
            for entity in ents:
                if entity.type == MessageEntityType.URL:
                    src = entities_source
                    url = src[entity.offset : entity.offset + entity.length]
                    urls.append(url)
                elif entity.type == MessageEntityType.TEXT_LINK:
                    urls.append(entity.url)

        # If we didn't find URLs in the entities, try to get it from the web preview.
        # This avoids duplicates when a link is in both the text and the preview.
        if not urls and getattr(message, "web_page", None) and getattr(
            message.web_page, "url", None
        ):
            logger.info("--> No URL in entities, using the one from web_page (link preview)")
            urls.append(message.web_page.url)

        # Process each found URL (removing duplicates)
        if urls:
            unique_urls = sorted(list(set(urls)))
            logger.info("Found %d unique URLs: %s", len(unique_urls), unique_urls)
            
            # Logic to pair article links and HN comments
            hn_url = None
            article_url = None
            other_urls = []
            
            for url in unique_urls:
                if "news.ycombinator.com" in urlparse(url).netloc:
                    hn_url = url
                else:
                    other_urls.append(url)
            
            # If we find exactly one HN link and one other link, we treat them as a pair.
            if hn_url and len(other_urls) == 1:
                article_url = other_urls[0]

            if article_url and hn_url:
                # Special case: a single bookmark for the article + HN comments pair
                logger.info(f"---> Hacker News pattern detected: Article={article_url}, Comments={hn_url}")
                # Extract metadata from the article and the HN page using the shared function
                article_metadata = get_article_metadata(article_url)
                hn_metadata = get_article_metadata(hn_url)

                # Merge the information: description from HN, the rest from the article
                metadata = article_metadata
                if hn_metadata.get("description"):
                    metadata["description"] = hn_metadata["description"]

                logger.info(f"---> Saving single bookmark to DB...")
                success = self.save_bookmark(article_url, metadata, message, comments_url_override=hn_url)
                # If saving is successful, send the reply and exit
                # to avoid processing the links individually.
                if success:
                    await message.reply(f"📖 **HN Bookmark saved!**\n📰 {metadata['title']}\n🔗 {metadata['domain']}")
                    return # We are done, exit the function

            # Previous logic for all other cases (single or multiple non-HN links)
            saved_count = 0
            saved_metadata = []
            for url in unique_urls:
                logger.info(f"---> Processing URL: {url}")
                metadata = get_article_metadata(url)
                logger.info(f"---> Saving bookmark to DB...")
                success = self.save_bookmark(url, metadata, message)
                if success:
                    saved_count += 1
                    saved_metadata.append(metadata)
            
            if saved_count > 0:
                logger.info(f"---> Successfully saved {saved_count} bookmarks. Sending reply.")
                if saved_count == 1:
                    meta = saved_metadata[0]
                    reply_text = f"📖 **Bookmark saved!**\n📰 {meta['title']}\n🔗 {meta['domain']}"
                else:
                    reply_text = f"📖 **Saved {saved_count} bookmarks!**"
                await message.reply(reply_text)
        else:
            logger.info("--> No URL found in the message. End of processing.")

    def export_bookmarks_html(self, filename="bookmarks.html"):
        """Exports bookmarks to HTML format"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bookmarks ORDER BY saved_at DESC")
        bookmarks = cursor.fetchall()

        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>My Telegram Bookmarks</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .bookmark { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }
        .title { font-weight: bold; font-size: 18px; margin-bottom: 5px; }
        .description { color: #666; margin-bottom: 10px; }
        .meta { font-size: 12px; color: #999; }
        .url { word-break: break-all; }
    </style>
</head>
<body>
    <h1>📖 My Telegram Bookmarks</h1>
"""

        for bookmark in bookmarks:
            html_content += f"""
    <div class="bookmark">
        <div class="title"><a href="{bookmark[1]}" target="_blank">{bookmark[2]}</a></div>
        <div class="description">{bookmark[3]}</div>
        <div class="meta">
            <strong>Dominio:</strong> {bookmark[5]} | 
            <strong>Salvato:</strong> {bookmark[6]} |
            <strong>URL:</strong> <span class="url">{bookmark[1]}</span>
        </div>
    </div>
"""

        html_content += """
</body>
</html>
"""

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Bookmarks exported to {filename}")
        return filename

    def run(self):
        """Start the bot with error handling for time sync issues."""
        try:
            logger.info("Starting the bot...")
            self.app.run()
        except Exception as e:
            if "BadMsgNotification" in str(e):
                logger.error("Time synchronization error detected. Please run as admin:")
                logger.error("    w32tm /resync /force")
                logger.error("If that fails, run:")
                logger.error("    net start w32time")
                logger.error("    w32tm /resync /force")
            raise


if __name__ == "__main__":
    bot = BookmarkBot()

    # Export existing bookmarks (optional)
    # bot.export_bookmarks_html()

    # Start the bot
    bot.run()
