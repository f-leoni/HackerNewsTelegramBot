import os
import re
import sqlite3
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from datetime import datetime
from urllib.parse import urlparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Import dinamico per compatibilità ---
from dotenv import load_dotenv
from pyrogram.enums import ChatType, MessageEntityType

# Cerca StringSession in percorsi comuni per supportare diverse versioni di Pyrogram
StringSession = None
for path in ('pyrogram.storage.storage', 'pyrogram.sessions.string_session', 'pyrogram.sessions', 'pyrogram.storage'):
    try:
        StringSession = getattr(__import__(path, fromlist=['StringSession']), 'StringSession')
        break
    except (ImportError, AttributeError):
        continue


class BookmarkBot:
    def __init__(self):
        # Carica variabili ambiente

        load_dotenv()
        try:
            here_env = os.path.join(os.path.dirname(__file__), ".env")
            if os.path.exists(here_env):
                load_dotenv(here_env, override=False)
        except Exception:
            pass

        self.api_id = os.getenv("API_ID")
        self.api_hash = os.getenv("API_HASH")
        # Credenziali opzionali: BOT_TOKEN per account bot, o SESSION_STRING per evitare login interattivo
        self.bot_token = os.getenv("BOT_TOKEN")
        self.session_string = os.getenv("SESSION_STRING")

        # Log di debug: mostra quali variabili d'ambiente per l'autenticazione sono presenti
        logger.info(
            "Auth env presence: BOT_TOKEN=%s, SESSION_STRING=%s, API_ID=%s, API_HASH=%s",
            "yes" if self.bot_token else "no",
            "yes" if self.session_string else "no",
            "yes" if self.api_id else "no",
            "yes" if self.api_hash else "no",
        )

        # Inizializza il client Pyrogram in una delle tre modalità:
        # 1) BOT_TOKEN: avvia come account bot. Nota: i bot non hanno accesso ai "Messaggi Salvati".
        # 2) SESSION_STRING: usa una sessione pre-generata (non richiede login interattivo).
        # 3) Fallback: sessione utente standard, che potrebbe richiedere il login al primo avvio.
        if self.bot_token:
            # Modalità Bot: usa un nome di sessione dedicato. Pyrogram gestirà la creazione
            # e il riutilizzo del file .session corrispondente.
            logger.info("Auth mode: BOT_TOKEN (bot account)")

            self.app = Client("bookmark_bot_bot", api_id=self.api_id, api_hash=self.api_hash, bot_token=self.bot_token)
        elif self.session_string:
            # Modalità StringSession: evita il login interattivo.
            # Richiede che API_ID e API_HASH siano comunque presenti.
            if not self.api_id or not self.api_hash:
                raise ValueError(
                    "SESSION_STRING requires API_ID and API_HASH to be set in .env"
                )
            if not StringSession:
                raise ImportError("Could not import StringSession. Please upgrade Pyrogram: pip install -U pyrogram")
            logger.info("Auth mode: SESSION_STRING (user session)")
            self.app = Client(
                name="bookmark_bot_string_session",
                session_string=self.session_string,
                api_id=self.api_id,
                api_hash=self.api_hash,
            )
        else:
            if not self.api_id or not self.api_hash:
                raise ValueError(
                    "API_ID e API_HASH devono essere impostati nel file .env (or set SESSION_STRING or BOT_TOKEN)"
                )
            # Modalità interattiva: il client potrebbe chiedere il numero di telefono al primo avvio.
            logger.info(
                "Auth mode: INTERACTIVE user session (will prompt for phone on first run)"
            )
            self.app = Client(
                "bookmark_bot", api_id=self.api_id, api_hash=self.api_hash
            )

        # Definisce il percorso del database relativo alla posizione dello script
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.script_dir, "bookmarks.db")

        # Inizializza database
        self.init_database()

        # Registra handlers
        self.setup_handlers()

    def init_database(self):
        """Inizializza il database SQLite"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                description TEXT,
                image_url TEXT,
                domain TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_user_id INTEGER,
                telegram_message_id INTEGER,
                comments_url TEXT,
                is_read INTEGER DEFAULT 0
            )
        """)

        # Logica di migrazione: aggiunge colonne mancanti a un DB esistente
        try:
            cursor.execute("PRAGMA table_info(bookmarks)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if "telegram_user_id" not in columns:
                cursor.execute("ALTER TABLE bookmarks ADD COLUMN telegram_user_id INTEGER")
            if "comments_url" not in columns:
                cursor.execute("ALTER TABLE bookmarks ADD COLUMN comments_url TEXT")
            if "is_read" not in columns:
                cursor.execute("ALTER TABLE bookmarks ADD COLUMN is_read INTEGER DEFAULT 0")

        except Exception as e:
            logger.warning("Could not perform database migration: %s", e)

        self.conn.commit()
        logger.info("Database inizializzato: %s", self.db_path)

    def extract_urls(self, text):
        """Estrae URL dal testo del messaggio"""
        url_pattern = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )
        return url_pattern.findall(text)

    def get_hn_comments_url(self, url):
        """Se l'URL è di Hacker News, restituisce il link ai commenti."""
        parsed_url = urlparse(url)
        if parsed_url.netloc == "news.ycombinator.com":
            query_params = dict(p.split('=') for p in parsed_url.query.split('&') if '=' in p)
            item_id = query_params.get('id')
            if item_id:
                return f"https://news.ycombinator.com/item?id={item_id}"
        return None

    def get_article_metadata(self, url):
        """Estrae metadati dall'articolo"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Estrai titolo
            title = None
            for selector in [
                'meta[property="og:title"]',
                'meta[name="twitter:title"]',
                "title",
            ]:
                element = soup.select_one(selector)
                if element:
                    title = (
                        element.get("content")
                        if element.name == "meta"
                        else element.get_text()
                    )
                    break

            # Estrai descrizione
            description = None
            for selector in [
                'meta[property="og:description"]',
                'meta[name="twitter:description"]',
                'meta[name="description"]',
            ]:
                element = soup.select_one(selector)
                if element:
                    description = element.get("content")
                    break

            # Estrai immagine
            image_url = None
            for selector in ['meta[property="og:image"]', 'meta[name="twitter:image"]']:
                element = soup.select_one(selector)
                if element:
                    image_url = element.get("content")
                    break

            # Ottieni dominio
            domain = urlparse(url).netloc

            return {
                "title": title or "Titolo non trovato",
                "description": description or "",
                "image_url": image_url or "",
                "domain": domain,
            }

        except Exception as e:
            logger.error(f"Errore nell'estrazione metadati per {url}: {e}")
            return {
                "title": f"Errore: {urlparse(url).netloc}",
                "description": str(e),
                "image_url": "",
                "domain": urlparse(url).netloc,
            }

    def save_bookmark(self, url, metadata, message, comments_url_override=None):
        """Salva il bookmark nel database"""
        try:
            cursor = self.conn.cursor()
            from_user_id = getattr(message.from_user, "id", None)
            comments_url = comments_url_override if comments_url_override is not None else self.get_hn_comments_url(url)

            cursor.execute(
                """
                INSERT OR REPLACE INTO bookmarks 
                (url, title, description, image_url, domain, telegram_user_id, telegram_message_id, comments_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
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
            self.conn.commit()
            logger.info(f"Bookmark salvato: {metadata['title']}")
            return True
        except Exception as e:
            logger.error(f"Errore nel salvare bookmark: {e}")
            return False

    def setup_handlers(self):
        """Setup degli event handlers"""

        @self.app.on_message(filters.private)
        async def handle_saved_message(client, message):
            """Handler per messaggi nei salvati
            
            Questo gestore viene registrato all'interno di un metodo di istanza per avere accesso a `self`.
            Analizza i messaggi in arrivo ed estrae URL da testo, didascalie, anteprime (web_page)
            e dalle "entità" del messaggio, per supportare anche i messaggi inoltrati.
            """

            # Log di debug: riassume le informazioni del messaggio in arrivo per facilitare la diagnosi.
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

            # Memorizza l'ID dell'utente/bot alla prima chiamata (necessario per la modalità utente)
            if not hasattr(self, "_my_user_id") or self._my_user_id is None:
                me = await client.get_me()
                self._my_user_id = me.id
                logger.info("Running as user: %s (ID: %s)", getattr(me, 'username', 'N/A'), me.id)

            # Se eseguito come bot, processa solo i messaggi ricevuti in chat privata.
            if self.bot_token:
                logger.info("-> Controllo modalità BOT")
                if not message.chat or message.chat.type != ChatType.PRIVATE:
                    # Ignora messaggi da gruppi o canali per default
                    logger.info("Bot mode: ignoring non-private chat (type: %s)", message.chat.type)
                    return
                logger.info("-> OK: Chat privata. Procedo con l'analisi del messaggio.")
                await self.process_message_for_urls(message)
            else:
                logger.info("-> Controllo modalità USER (sessione utente)")
                # La verifica per i "Messaggi Salvati" è stata rimossa.
                # Ora il bot processerà i messaggi da qualsiasi chat privata.
                logger.info("-> OK: Procedo con l'analisi del messaggio in chat privata.")
                await self.process_message_for_urls(message)

    async def process_message_for_urls(self, message):
        """Extracts and processes URLs from a given message."""
        logger.info("--> Entrato in process_message_for_urls")

        # Cerca URL nel messaggio (supporta testo, didascalie e web_page)
        urls = []

        # If message contains an embedded web page, include its url
        if getattr(message, "web_page", None) and getattr(
            message.web_page, "url", None
        ):
            logger.info("--> Trovato URL in web_page (anteprima link)")
            urls.append(message.web_page.url)

        # Cerca URL nelle entità del messaggio (text or caption)
        entities_source = None
        if getattr(message, "entities", None):
            entities_source = message.text or ""
        elif getattr(message, "caption_entities", None):
            entities_source = message.caption or ""

        if entities_source:
            logger.info("--> Analizzo 'entità' del messaggio per URL...")
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

        # Processa ogni URL trovato (rimuovendo duplicati)
        if urls:
            unique_urls = sorted(list(set(urls)))
            logger.info("Trovati %d URL unici: %s", len(unique_urls), unique_urls)
            
            # Logica per accoppiare link articolo e commenti HN
            hn_url = None
            article_url = None
            
            if len(unique_urls) == 2:
                url1, url2 = unique_urls
                is_url1_hn = "news.ycombinator.com" in urlparse(url1).netloc
                is_url2_hn = "news.ycombinator.com" in urlparse(url2).netloc
                
                if is_url1_hn and not is_url2_hn:
                    hn_url, article_url = url1, url2
                elif not is_url1_hn and is_url2_hn:
                    hn_url, article_url = url2, url1

            if article_url and hn_url:
                # Caso speciale: un solo bookmark per la coppia articolo + commenti HN
                logger.info(f"---> Rilevato pattern Hacker News: Articolo={article_url}, Commenti={hn_url}")
                metadata = self.get_article_metadata(article_url)
                logger.info(f"---> Salvando bookmark singolo nel DB...")
                success = self.save_bookmark(article_url, metadata, message, comments_url_override=hn_url)
                if success:
                    await message.reply(f"📖 **Bookmark HN salvato!**\n📰 {metadata['title']}\n🔗 {metadata['domain']}")
                return # Abbiamo finito, usciamo dalla funzione

            # Logica precedente per tutti gli altri casi (link singoli o multipli non HN)
            saved_count = 0
            saved_metadata = []
            for url in unique_urls:
                logger.info(f"---> Processando URL: {url}")
                metadata = self.get_article_metadata(url)
                logger.info(f"---> Salvando bookmark nel DB...")
                success = self.save_bookmark(url, metadata, message)
                if success:
                    saved_count += 1
                    saved_metadata.append(metadata)
            
            if saved_count > 0:
                logger.info(f"---> Salvati {saved_count} bookmark con successo. Invio risposta.")
                if saved_count == 1:
                    meta = saved_metadata[0]
                    reply_text = f"📖 **Bookmark salvato!**\n📰 {meta['title']}\n🔗 {meta['domain']}"
                else:
                    reply_text = f"📖 **Salvati {saved_count} bookmarks!**"
                await message.reply(reply_text)
        else:
            logger.info("--> Nessun URL trovato nel messaggio. Fine elaborazione.")

    def export_bookmarks_html(self, filename="bookmarks.html"):
        """Esporta i bookmark in formato HTML"""
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

        logger.info(f"Bookmarks esportati in {filename}")
        return filename

    def run(self):
        """Avvia il bot"""
        logger.info("Avvio del bot...")
        try:
            self.app.run()
        except AttributeError as e:
            # Fornisce un messaggio di errore più chiaro per una comune errata configurazione dell'autenticazione
            logger.error("Pyrogram AttributeError during start: %s", e)
            logger.error(
                "This usually means the client attempted a new authorization but API_ID/API_HASH were not available."
            )
            logger.error(
                "If you intended to run as a bot, set BOT_TOKEN in .env. If you use a user session string, set SESSION_STRING and also API_ID/API_HASH."
            )
            raise


if __name__ == "__main__":
    bot = BookmarkBot()

    # Esporta bookmark esistenti (opzionale)
    # bot.export_bookmarks_html()

    # Avvia il bot
    bot.run()
