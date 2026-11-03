"""
Main module of the Telegram bot for saving bookmarks.
"""
import os
import sys
import re
import json
import time
import asyncio
import sqlite3
import threading
from pyrogram import Client, filters
from datetime import datetime
from urllib.parse import urlparse

# Ensure project root is importable when launched as a script (e.g. under systemd)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import init_database, get_db_path, connect_db
from shared.utils import get_article_metadata, generate_tags_llm
import logging

# Setup logging
__version__ = "1.0"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Guard rails so a single message cannot monopolize the bot.
MAX_URLS_PER_MESSAGE = 10
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_MESSAGES = 20

UNLINKED_MESSAGE = "Account non collegato. Usa /register e poi /link <token>."

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

        # Pyrogram writes <name>.session in the current working directory unless an
        # absolute path is given. In Docker that directory is ephemeral, so keep the
        # session in the mounted volume when it is available.
        session_dir = os.getenv("SESSION_DIR")
        if not session_dir:
            volume_dir = os.path.join(os.path.dirname(SCRIPT_DIR), "session")
            session_dir = volume_dir if os.path.isdir(volume_dir) else os.path.join(SCRIPT_DIR, ".sessions")
        os.makedirs(session_dir, exist_ok=True)
        self.session_name = os.path.join(session_dir, "bookmark_bot_session")
        logger.info("Pyrogram session path: %s", self.session_name)

        # Initialize the Pyrogram client. For Docker, only non-interactive modes are supported.
        if self.bot_token:
            # Bot Mode: use a BOT_TOKEN. Does not require API_ID/HASH except for specific functions.
            logger.info("Auth mode: BOT_TOKEN (bot account)")
            self.app = Client(
                name=self.session_name, # Session name for the bot
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
                name=self.session_name, # A consistent session name
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

        # Per-user rate limiting state (guarded by a lock because handlers may
        # run concurrently on the event loop).
        self._rate_windows = {}
        self._rate_lock = threading.Lock()

        # Register handlers
        self.setup_handlers()

    def _consume_rate_limit(self, telegram_user_id):
        """Sliding-window rate limit: True when the user may send another message."""
        if telegram_user_id is None:
            return True
        now = time.monotonic()
        with self._rate_lock:
            timestamps = [
                ts for ts in self._rate_windows.get(telegram_user_id, [])
                if now - ts < RATE_LIMIT_WINDOW_SECONDS
            ]
            if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
                self._rate_windows[telegram_user_id] = timestamps
                return False
            timestamps.append(now)
            self._rate_windows[telegram_user_id] = timestamps
        return True

    def _get_linked_web_user_id(self, telegram_user_id):
        """Synchronously resolves the web user linked to a Telegram user."""
        if telegram_user_id is None:
            return None
        conn = None
        try:
            conn = connect_db()
            return self._resolve_web_user_id(conn.cursor(), telegram_user_id)
        except sqlite3.Error as e:
            logger.error("Error resolving web user for telegram id %s: %s", telegram_user_id, e)
            return None
        finally:
            if conn:
                conn.close()

    def _parse_db_datetime(self, raw_value):
        """Parses datetime values returned by SQLite into a datetime object."""
        if raw_value is None:
            return None
        if isinstance(raw_value, datetime):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return datetime.fromisoformat(raw_value.replace(' ', 'T'))
            except ValueError:
                return None
        return None

    def _resolve_web_user_id(self, cursor, telegram_user_id):
        """Returns the mapped web user id for a Telegram user id."""
        cursor.execute(
            "SELECT user_id FROM telegram_user_links WHERE telegram_user_id = ?",
            (telegram_user_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def _consume_link_token(self, cursor, token, telegram_user_id):
        """Consumes a one-time token and creates/updates Telegram-to-web mapping."""
        cursor.execute(
            "SELECT token, user_id, expires_at, used_at FROM telegram_link_tokens WHERE token = ?",
            (token,)
        )
        token_row = cursor.fetchone()
        if not token_row:
            return False, "Token non valido."

        _, user_id, expires_at, used_at = token_row
        if used_at is not None:
            return False, "Token gia utilizzato."

        expires_dt = self._parse_db_datetime(expires_at)
        if not expires_dt or expires_dt <= datetime.now():
            return False, "Token scaduto. Chiedi un nuovo token all'admin."

        # Enforce 1:1 mapping by replacing previous links on both sides.
        cursor.execute("DELETE FROM telegram_user_links WHERE telegram_user_id = ?", (telegram_user_id,))
        cursor.execute("DELETE FROM telegram_user_links WHERE user_id = ?", (user_id,))
        cursor.execute(
            "INSERT INTO telegram_user_links (user_id, telegram_user_id) VALUES (?, ?)",
            (user_id, telegram_user_id)
        )
        cursor.execute(
            "UPDATE telegram_link_tokens SET used_at = ?, used_telegram_user_id = ? WHERE token = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), telegram_user_id, token)
        )

        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        username = user_row[0] if user_row else f"ID {user_id}"
        return True, f"Collegamento completato. Account web associato: {username}."

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
        Saves a URL as a bookmark for the web user linked to the Telegram sender.

        Existing bookmarks with the same URL keep their read flag and rating:
        only the scraped metadata is refreshed.

        Returns:
            tuple[bool, str]: (True, "") on success, otherwise (False, reason)
            where reason is "unlinked", "locked" or "generic".
        """
        db_path = get_db_path()
        conn = None
        try:
            conn = connect_db(db_path)
            cursor = conn.cursor()
            from_user_id = getattr(message.from_user, "id", None)

            # Authorize before doing any network or LLM work.
            web_user_id = self._resolve_web_user_id(cursor, from_user_id)
            if not web_user_id:
                logger.error("Telegram user %s is not linked to a web user. Cannot save bookmark.", from_user_id)
                return False, "unlinked"

            comments_url = comments_url_override if comments_url_override is not None else self.get_hn_comments_url(url)
            tags = generate_tags_llm(
                metadata.get("title", ""),
                metadata.get("description", ""),
                metadata.get("domain", ""),
            )
            metadata["tags"] = tags

            cursor.execute(
                """
                INSERT INTO bookmarks 
                (user_id, url, title, description, image_url, domain, tags, telegram_user_id, telegram_message_id, comments_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, url) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    image_url = excluded.image_url,
                    domain = excluded.domain,
                    tags = excluded.tags,
                    telegram_user_id = excluded.telegram_user_id,
                    telegram_message_id = excluded.telegram_message_id,
                    comments_url = excluded.comments_url
            """,
                (
                    web_user_id,
                    url,
                    metadata["title"],
                    metadata["description"],
                    metadata["image_url"],
                    metadata["domain"],
                    json.dumps(tags, ensure_ascii=False),
                    from_user_id,
                    message.id,
                    comments_url,
                ),
            )
            conn.commit()
            logger.info(f"Bookmark saved for user {web_user_id}: {metadata['title']}")
            return True, ""
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() or "busy" in str(e).lower():
                logger.error("Database locked while saving bookmark: %s", e)
                return False, "locked"
            logger.error(f"Error saving bookmark: {e}")
            return False, "generic"
        except Exception as e:
            logger.error(f"Error saving bookmark: {e}")
            return False, "generic"
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

        @self.app.on_message(filters.private & ~filters.command(["start", "count", "help", "register", "link", "whoami", "unlink"]))
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
                conn = connect_db(db_path)
                cursor = conn.cursor()

                telegram_user_id = getattr(getattr(message, 'from_user', None), 'id', None)
                if telegram_user_id is None:
                    await message.reply("Impossibile leggere il tuo Telegram ID.")
                    return

                web_user_id = self._resolve_web_user_id(cursor, telegram_user_id)
                if web_user_id is None:
                    await message.reply("Il tuo account Telegram non e collegato. Usa /register e poi /link <token>.")
                    return

                cursor.execute("SELECT COUNT(*) FROM bookmarks WHERE user_id = ?", (web_user_id,))
                count = cursor.fetchone()[0]
                
                await message.reply(f"You have saved a total of **{count}** bookmarks.")
                
            except Exception as e:
                logger.error(f"Error handling /count command: {e}")
                await message.reply("Si è verificato un errore nel contare i bookmark.")

        @self.app.on_message(filters.command("register") & filters.private)
        async def handle_register_command(client, message):
            """Shows instructions to link current Telegram account with a web user."""
            telegram_user_id = getattr(getattr(message, 'from_user', None), 'id', None)
            text = (
                "Per collegare il tuo account Telegram al webserver:\n"
                "1) Chiedi a un admin di generare un token di collegamento.\n"
                "2) Invia qui: /link <token>\n\n"
                f"Il tuo Telegram ID: {telegram_user_id}"
            )
            await message.reply(text)

        @self.app.on_message(filters.command("link") & filters.private)
        async def handle_link_command(client, message):
            """Links current Telegram account using a one-time token."""
            telegram_user_id = getattr(getattr(message, 'from_user', None), 'id', None)
            text = (message.text or '').strip()
            parts = text.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                await message.reply("Uso corretto: /link <token>")
                return

            token = parts[1].strip()

            if not self._consume_rate_limit(telegram_user_id):
                await message.reply("Troppi tentativi di collegamento. Attendi qualche minuto e riprova.")
                return

            db_path = get_db_path()
            conn = None
            try:
                conn = connect_db(db_path)
                cursor = conn.cursor()
                ok, response_message = self._consume_link_token(cursor, token, telegram_user_id)
                if ok:
                    conn.commit()
                    await message.reply(response_message)
                else:
                    await message.reply(response_message)
            except Exception as e:
                logger.error("Error linking telegram account: %s", e)
                await message.reply("Errore durante il collegamento account.")
            finally:
                if conn:
                    conn.close()

        @self.app.on_message(filters.command("whoami") & filters.private)
        async def handle_whoami_command(client, message):
            """Shows current Telegram-to-web mapping information."""
            telegram_user_id = getattr(getattr(message, 'from_user', None), 'id', None)
            db_path = get_db_path()
            conn = None
            try:
                conn = connect_db(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT u.username, u.role
                    FROM telegram_user_links tul
                    JOIN users u ON u.id = tul.user_id
                    WHERE tul.telegram_user_id = ?
                    """,
                    (telegram_user_id,)
                )
                row = cursor.fetchone()
                if not row:
                    await message.reply("Nessun collegamento attivo. Usa /register e poi /link <token>.")
                    return
                await message.reply(f"Collegato a: {row[0]} (ruolo: {row[1]})")
            except Exception as e:
                logger.error("Error in /whoami: %s", e)
                await message.reply("Errore durante la lettura del collegamento.")
            finally:
                if conn:
                    conn.close()

        @self.app.on_message(filters.command("unlink") & filters.private)
        async def handle_unlink_command(client, message):
            """Removes current Telegram-to-web mapping."""
            telegram_user_id = getattr(getattr(message, 'from_user', None), 'id', None)
            db_path = get_db_path()
            conn = None
            try:
                conn = connect_db(db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM telegram_user_links WHERE telegram_user_id = ?", (telegram_user_id,))
                if cursor.rowcount > 0:
                    conn.commit()
                    await message.reply("Collegamento rimosso con successo.")
                else:
                    await message.reply("Nessun collegamento da rimuovere.")
            except Exception as e:
                logger.error("Error unlinking telegram account: %s", e)
                await message.reply("Errore durante la rimozione del collegamento.")
            finally:
                if conn:
                    conn.close()

        @self.app.on_message(filters.command("start") & filters.private)
        async def handle_start_command(client, message):
            """Handles /start with a short onboarding message and link status."""
            telegram_user_id = getattr(getattr(message, 'from_user', None), 'id', None)
            web_user_id = await asyncio.to_thread(self._get_linked_web_user_id, telegram_user_id)
            if web_user_id is None:
                await message.reply(
                    "👋 Benvenuto!\n\n"
                    "Per usare il bot devi collegare il tuo account Telegram a un utente web:\n"
                    "1) Chiedi a un admin un token di collegamento.\n"
                    "2) Invia qui: /link <token>\n\n"
                    f"Il tuo Telegram ID: {telegram_user_id}"
                )
                return
            await message.reply(
                "👋 Benvenuto! Il tuo account è già collegato.\n"
                "Inviami un link e lo salverò tra i tuoi bookmark.\n"
                "Usa /help per l'elenco dei comandi."
            )

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
                "- `/register`: Shows instructions to link your Telegram account.\n"
                "- `/link <token>`: Links your Telegram account to your web user.\n"
                "- `/whoami`: Shows your current account mapping.\n"
                "- `/unlink`: Removes your current account mapping.\n"
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

        from_user_id = getattr(getattr(message, "from_user", None), "id", None)

        # Authorize before any scraping/tagging work: unlinked users must not be
        # able to use the bot as a scraping proxy.
        web_user_id = await asyncio.to_thread(self._get_linked_web_user_id, from_user_id)
        if web_user_id is None:
            logger.info("Telegram user %s is not linked; skipping processing.", from_user_id)
            await message.reply(UNLINKED_MESSAGE)
            return

        if not self._consume_rate_limit(from_user_id):
            await message.reply("Stai inviando troppi link. Attendi qualche minuto e riprova.")
            return

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
            if len(unique_urls) > MAX_URLS_PER_MESSAGE:
                logger.info("Message contains %d URLs; limiting to %d", len(unique_urls), MAX_URLS_PER_MESSAGE)
                await message.reply(
                    f"Ho ricevuto {len(unique_urls)} link, salvo solo i primi {MAX_URLS_PER_MESSAGE}."
                )
                unique_urls = unique_urls[:MAX_URLS_PER_MESSAGE]

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
                article_metadata = await asyncio.to_thread(get_article_metadata, article_url)
                hn_metadata = await asyncio.to_thread(get_article_metadata, hn_url)

                # Merge the information: description from HN, the rest from the article
                metadata = article_metadata
                if hn_metadata.get("description"):
                    metadata["description"] = hn_metadata["description"]

                logger.info(f"---> Saving single bookmark to DB...")
                success, reason = await asyncio.to_thread(
                    self.save_bookmark, article_url, metadata, message, hn_url
                )
                # If saving is successful, send the reply and exit
                # to avoid processing the links individually.
                if success:
                    tags_line = f"\n🏷️ {', '.join(metadata.get('tags', []))}" if metadata.get('tags') else ""
                    await message.reply(
                        f"📖 **HN Bookmark saved!**\n📰 {metadata['title']}\n🔗 {metadata['domain']}{tags_line}"
                    )
                    return # We are done, exit the function
                if reason == "unlinked":
                    await message.reply(UNLINKED_MESSAGE)
                    return

            # Previous logic for all other cases (single or multiple non-HN links)
            saved_count = 0
            saved_metadata = []
            last_reason = ""
            for url in unique_urls:
                logger.info(f"---> Processing URL: {url}")
                metadata = await asyncio.to_thread(get_article_metadata, url)
                logger.info(f"---> Saving bookmark to DB...")
                success, reason = await asyncio.to_thread(self.save_bookmark, url, metadata, message)
                last_reason = reason
                if success:
                    saved_count += 1
                    saved_metadata.append(metadata)
            
            if saved_count > 0:
                logger.info(f"---> Successfully saved {saved_count} bookmarks. Sending reply.")
                if saved_count == 1:
                    meta = saved_metadata[0]
                    tags_line = f"\n🏷️ {', '.join(meta.get('tags', []))}" if meta.get('tags') else ""
                    reply_text = f"📖 **Bookmark saved!**\n📰 {meta['title']}\n🔗 {meta['domain']}{tags_line}"
                else:
                    tags_summary = []
                    for meta in saved_metadata:
                        if meta.get('tags'):
                            tags_summary.append(f"- {meta.get('domain', 'link')}: {', '.join(meta['tags'])}")
                    tags_block = "\n🏷️ Tags:\n" + "\n".join(tags_summary) if tags_summary else ""
                    reply_text = f"📖 **Saved {saved_count} bookmarks!**{tags_block}"
                await message.reply(reply_text)
            elif last_reason == "unlinked":
                await message.reply(UNLINKED_MESSAGE)
            elif last_reason == "locked":
                await message.reply("Database occupato, riprova tra qualche secondo. Nessun bookmark è stato salvato.")
            else:
                await message.reply("Non sono riuscito a salvare i bookmark. Riprova tra poco.")
        else:
            logger.info("--> No URL found in the message. End of processing.")

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
    try:
        bot = BookmarkBot()

        # Start the bot
        bot.run()
    except Exception:
        logger.exception("Fatal startup error in Telegram bot")
        raise
