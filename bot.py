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

class BookmarkBot:
    def __init__(self):
        # Carica variabili ambiente
        from dotenv import load_dotenv
        load_dotenv()
        
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        
        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID e API_HASH devono essere impostati nel file .env")
        
        # Inizializza client Telegram
        self.app = Client("bookmark_bot", api_id=self.api_id, api_hash=self.api_hash)
        
        # Inizializza database
        self.init_database()
        
        # Registra handlers
        self.setup_handlers()
    
    def init_database(self):
        """Inizializza il database SQLite"""
        self.conn = sqlite3.connect('bookmarks.db', check_same_thread=False)
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                description TEXT,
                image_url TEXT,
                domain TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_message_id INTEGER
            )
        ''')
        self.conn.commit()
        logger.info("Database inizializzato")
    
    def extract_urls(self, text):
        """Estrae URL dal testo del messaggio"""
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        return url_pattern.findall(text)
    
    def get_article_metadata(self, url):
        """Estrae metadati dall'articolo"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Estrai titolo
            title = None
            for selector in ['meta[property="og:title"]', 'meta[name="twitter:title"]', 'title']:
                element = soup.select_one(selector)
                if element:
                    title = element.get('content') if element.name == 'meta' else element.get_text()
                    break
            
            # Estrai descrizione
            description = None
            for selector in ['meta[property="og:description"]', 'meta[name="twitter:description"]', 'meta[name="description"]']:
                element = soup.select_one(selector)
                if element:
                    description = element.get('content')
                    break
            
            # Estrai immagine
            image_url = None
            for selector in ['meta[property="og:image"]', 'meta[name="twitter:image"]']:
                element = soup.select_one(selector)
                if element:
                    image_url = element.get('content')
                    break
            
            # Ottieni dominio
            domain = urlparse(url).netloc
            
            return {
                'title': title or 'Titolo non trovato',
                'description': description or '',
                'image_url': image_url or '',
                'domain': domain
            }
            
        except Exception as e:
            logger.error(f"Errore nell'estrazione metadati per {url}: {e}")
            return {
                'title': f"Errore: {urlparse(url).netloc}",
                'description': str(e),
                'image_url': '',
                'domain': urlparse(url).netloc
            }
    
    def save_bookmark(self, url, metadata, message_id):
        """Salva il bookmark nel database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO bookmarks 
                (url, title, description, image_url, domain, telegram_message_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                url,
                metadata['title'],
                metadata['description'],
                metadata['image_url'],
                metadata['domain'],
                message_id
            ))
            self.conn.commit()
            logger.info(f"Bookmark salvato: {metadata['title']}")
            return True
        except Exception as e:
            logger.error(f"Errore nel salvare bookmark: {e}")
            return False
    
    def setup_handlers(self):
        """Setup degli event handlers"""
        
        @self.app.on_message(filters.me & filters.saved_messages)
        async def handle_saved_message(client, message):
            """Handler per messaggi nei salvati"""
            logger.info("Nuovo messaggio nei salvati ricevuto")
            
            # Cerca URL nel messaggio
            urls = []
            if message.text:
                urls.extend(self.extract_urls(message.text))
            
            # Cerca URL nelle entità del messaggio
            if message.entities:
                for entity in message.entities:
                    if entity.type == "url":
                        url = message.text[entity.offset:entity.offset + entity.length]
                        urls.append(url)
                    elif entity.type == "text_link":
                        urls.append(entity.url)
            
            # Processa ogni URL trovato
            if urls:
                for url in urls:
                    logger.info(f"Processando URL: {url}")
                    
                    # Estrai metadati
                    metadata = self.get_article_metadata(url)
                    
                    # Salva bookmark
                    success = self.save_bookmark(url, metadata, message.id)
                    
                    if success:
                        # Invia conferma (opzionale)
                        await message.reply(
                            f"📖 **Bookmark salvato!**\n"
                            f"📰 {metadata['title']}\n"
                            f"🔗 {metadata['domain']}"
                        )
            else:
                logger.info("Nessun URL trovato nel messaggio")
    
    def export_bookmarks_html(self, filename="bookmarks.html"):
        """Esporta i bookmark in formato HTML"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM bookmarks ORDER BY saved_at DESC')
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
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Bookmarks esportati in {filename}")
        return filename
    
    def run(self):
        """Avvia il bot"""
        logger.info("Avvio del bot...")
        self.app.run()

if __name__ == "__main__":
    bot = BookmarkBot()
    
    # Esporta bookmark esistenti (opzionale)
    # bot.export_bookmarks_html()
    
    # Avvia il bot
    bot.run()