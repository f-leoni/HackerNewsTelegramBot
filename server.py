#!/usr/bin/env python3
"""
Server HTTPS per servire bookmark da database SQLite - Versione Enhanced
Con form nascosto e vista compatta
"""
import os
import sqlite3
import ssl
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import socket
import subprocess
import sys
# datetime non usato direttamente
from htmldata import get_html

# Configurazione

# Percorso Let's Encrypt
LE_CERT_DIR = '/etc/letsencrypt/live/oc.zitzu.it'
LE_FULLCHAIN = os.path.join(LE_CERT_DIR, 'fullchain.pem')
LE_PRIVKEY = os.path.join(LE_CERT_DIR, 'privkey.pem')

# Default
DB_PATH = 'bookmarks.db'
CERT_FILE = 'server.pem'
KEY_FILE = 'server.key'
PORT = 8443

# Se trovi certificati Let's Encrypt, usali:
if os.path.exists(LE_FULLCHAIN) and os.path.exists(LE_PRIVKEY):
    print(f"Usando certificati Let's Encrypt da: {LE_CERT_DIR}")
    CERT_FILE = LE_FULLCHAIN
    KEY_FILE = LE_PRIVKEY
else:
    print("Let's Encrypt certs non trovati, userò i certificati locali (o li autogenererò).")
print("SERVER MODULE LOADED: server.py")

class BookmarkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """
        Gestisce le richieste GET.

        Route supportate:
          - /                 -> pagina principale (HTML generato da get_html)
          - /api/bookmarks     -> API JSON che ritorna la lista dei bookmark
          - /favicon.ico       -> risponde 404

        Effetto: analizza self.path, chiama il metodo di servizio corrispondente
        e invia la risposta HTTP con codice e header appropriati.
        In caso di percorso sconosciuto risponde 404.
        """
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            self.serve_homepage()
        elif parsed_path.path == '/api/bookmarks':
            self.serve_bookmarks_api()
        elif parsed_path.path == '/favicon.ico':
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """
        Gestisce le richieste POST.

        Attualmente supporta solo la route:
          - POST /api/bookmarks  : aggiunge un nuovo bookmark leggendo JSON dal body

        Se il percorso non è riconosciuto risponde con 404.
        """
        if self.path == '/api/bookmarks':
            self.add_bookmark()
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        """
        Gestisce le richieste PUT per aggiornare risorse esistenti.

        Supporta:
          - PUT /api/bookmarks/<id>        -> aggiorna i campi del bookmark (chiama update_bookmark)
          - PUT /api/bookmarks/<id>/read   -> imposta il flag "is_read" (chiama mark_read)

        Il metodo effettua il parsing della path per estrarre l'id. Se l'id non
        è un intero risponde 400. Se la route non è riconosciuta risponde 404.
        """
        print(f"DEBUG: do_PUT {self.path}")
        parsed = urlparse(self.path)
        parts = parsed.path.strip('/').split('/')

        # Supporta: /api/bookmarks/<id>  (update)
        # e /api/bookmarks/<id>/read (set read flag)
        if len(parts) >= 3 and parts[0] == 'api' and parts[1] == 'bookmarks':
            try:
                bookmark_id = int(parts[2])
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return

            if len(parts) == 4 and parts[3] == 'read':
                self.mark_read(bookmark_id)
            else:
                self.update_bookmark(bookmark_id)
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        """
        Gestisce le richieste DELETE.

        Route supportata:
          - DELETE /api/bookmarks/<id>  -> cancella il bookmark con l'id specificato

        Effettua parsing dell'id dalla path; se non è valido risponde 400.
        In caso di successo chiama delete_bookmark che manda la risposta JSON.
        """
        print(f"DEBUG: do_DELETE {self.path}")
        parsed = urlparse(self.path)
        parts = parsed.path.strip('/').split('/')

        # Supporta: /api/bookmarks/<id>
        if len(parts) == 3 and parts[0] == 'api' and parts[1] == 'bookmarks':
            try:
                bookmark_id = int(parts[2])
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return

            self.delete_bookmark(bookmark_id)
        else:
            self.send_response(404)
            self.end_headers()

    def serve_homepage(self):
        """
        Costruisce e invia la pagina HTML principale.

        Azioni:
          - recupera i bookmark tramite get_bookmarks()
          - genera l'HTML con get_html(self, bookmarks)
          - invia la risposta HTTP 200 con Content-Type text/html

        Nota: il template HTML è generato da `htmldata.get_html` e può
        contenere JS che utilizza le API server-side per operazioni CRUD.
        """
        bookmarks = self.get_bookmarks()

        html = get_html(self, bookmarks)

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def extract_domain(self, url):
        """
        Estrae il dominio (host) da un URL.

        Input: string `url`.
        Output: dominio in minuscolo senza il prefisso 'www.' quando presente.
        In caso di errore ritorna stringa vuota.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Rimuovi www. se presente
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ''

    def render_bookmarks(self, bookmarks):
        """
        Renderizza i bookmark come HTML nella vista "card" (dettagliata).

        Input: `bookmarks` è una lista di tuple con la forma:
            (id, url, title, description, image_url, domain, saved_at, telegram_user_id, telegram_message_id, comments_url, is_read?)

        Output: stringa HTML che rappresenta una sequenza di card. Se la lista
        è vuota ritorna un blocco HTML che indica che non ci sono bookmark.

        Nota sugli errori: il metodo è progettato per non sollevare eccezioni
        durante il rendering; eventuali problemi con dati mancanti vengono
        gestiti con valori di fallback (es. 'Senza titolo').
        """
        if not bookmarks:
            return '<div style="text-align: center; color: #666; padding: 40px;">Nessun bookmark trovato. Aggiungine uno!</div>'

        html_cards = []
        for bookmark in bookmarks:
            # bookmark = (id, url, title, description, image_url, domain, saved_at, telegram_user_id, telegram_message_id, comments_url)

            image_html = ''
            if bookmark[4]:  # image_url
                image_html = f'<img src="{bookmark[4]}" alt="Preview" class="bookmark-image" onerror="this.style.display=\'none\'">'
            else:
                image_html = '<div class="bookmark-image" style="display: flex; align-items: center; justify-content: center; background: #f8f9fa; color: #6c757d;">🔗</div>'

            telegram_badge = ''
            if bookmark[7]:  # telegram_user_id
                telegram_badge = '<span class="telegram-badge">📱 Telegram</span>'

            hn_link = ''
            if bookmark[9]:  # comments_url (HackerNews)
                hn_link = f'<a href="{bookmark[9]}" target="_blank" class="hn-link">🗞️ HN</a>'

            html_cards.append(f"""
            <div class="bookmark-card">
                <div class="bookmark-header">
                    {image_html}
                    <div class="bookmark-info">
                        <div class="bookmark-actions-top">
                            {telegram_badge}
                            {hn_link}
                            <button class="icon-btn read" title="Segna come letto" onclick="bookmarkMarkRead({bookmark[0]})">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                            </button>
                            <button class="icon-btn delete" title="Elimina" onclick="bookmarkDelete({bookmark[0]})">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 6h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 6v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                            </button>
                        </div>
                        <div class="bookmark-title">{bookmark[2] or 'Senza titolo'}</div>
                    </div>
                </div>

                <a href="{bookmark[1]}" target="_blank" class="bookmark-url">{bookmark[1]}</a>

                <div class="bookmark-description">{bookmark[3] or 'Nessuna descrizione'}</div>

                <div class="bookmark-footer">
                    <span class="bookmark-date">{bookmark[6]}</span>
                </div>
            </div>
            """)

        return ''.join(html_cards)

    def render_bookmarks_compact(self, bookmarks):
        """
        Renderizza i bookmark nella vista compatta (lista densa).

        Input e output simili a `render_bookmarks`, ma il markup è più
        compatto (meno dettagli per ogni elemento). Se la lista è vuota
        ritorna un messaggio HTML informativo.
        """
        if not bookmarks:
            return '<div style="text-align: center; color: #666; padding: 40px;">Nessun bookmark trovato. Aggiungine uno!</div>'

        html_items = []
        for bookmark in bookmarks:
            # bookmark = (id, url, title, description, image_url, domain, saved_at, telegram_user_id, telegram_message_id, comments_url)

            image_html = ''
            if bookmark[4]:  # image_url
                image_html = f'<img src="{bookmark[4]}" alt="Preview" class="compact-image" onerror="this.innerHTML=\'🔗\'">'
            else:
                image_html = '<div class="compact-image">🔗</div>'

            badges_html = ''
            badges = []
            if bookmark[7]:  # telegram_user_id
                badges.append('<span class="telegram-badge">TG</span>')
            if bookmark[9]:  # comments_url (HackerNews)
                badges.append(f'<a href="{bookmark[9]}" target="_blank" class="hn-link">HN</a>')

            if badges:
                badges_html = '<div class="compact-badges">' + ''.join(badges) + '</div>'

            # Formatta la data più compatta
            date_parts = bookmark[6].split(' ')
            short_date = date_parts[0] if len(date_parts) > 0 else bookmark[6]

            html_items.append(f"""
            <div class="compact-item">
                {image_html}
                <div class="compact-content">
                    <div class="compact-actions-top">
                        {badges_html}
                        <button class="icon-btn read" title="Segna come letto" onclick="bookmarkMarkRead({bookmark[0]})">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        </button>
                        <button class="icon-btn delete" title="Elimina" onclick="bookmarkDelete({bookmark[0]})">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 6h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 6v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        </button>
                    </div>
                    <div class="compact-title">{bookmark[2] or 'Senza titolo'}</div>
                    <a href="{bookmark[1]}" target="_blank" class="compact-url">{bookmark[1]}</a>
                </div>
                <div class="compact-date">{short_date}</div>
            </div>
            """)

        return ''.join(html_items)

    def serve_bookmarks_api(self):
        """
        API che restituisce la lista dei bookmark in formato JSON.

        Azioni:
          - recupera i bookmark con get_bookmarks()
          - costruisce una lista di dizionari serializzabile in JSON
          - invia la risposta HTTP 200 con Content-Type application/json

        Ogni elemento JSON contiene le chiavi: id, url, title, description,
        image_url, domain, saved_at, telegram_user_id, telegram_message_id,
        comments_url, is_read.
        """
        bookmarks = self.get_bookmarks()

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        bookmark_list = []
        for bookmark in bookmarks:
            bookmark_list.append({
                'id': bookmark[0],
                'url': bookmark[1],
                'title': bookmark[2],
                'description': bookmark[3],
                'image_url': bookmark[4],
                'domain': bookmark[5],
                'saved_at': bookmark[6],
                'telegram_user_id': bookmark[7],
                'telegram_message_id': bookmark[8],
                'comments_url': bookmark[9],
                'is_read': bookmark[10] if len(bookmark) > 10 else 0
            })

        self.wfile.write(json.dumps(bookmark_list, ensure_ascii=False).encode('utf-8'))

    def delete_bookmark(self, bookmark_id):
        """
        Cancella un bookmark dal database dato il suo `bookmark_id`.

        Risponde con JSON:
          - 200 {"status": "deleted"} in caso di successo
          - 500 {"error": "..."} in caso di errore

        Apre una connessione SQLite, esegue DELETE e chiude la connessione.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "deleted"}')

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))

    def update_bookmark(self, bookmark_id):
        """
        Aggiorna i campi di un bookmark esistente.

        Comportamento:
          - legge JSON dal body della richiesta (Content-Length)
          - considera solo i campi consentiti: url, title, description,
            image_url, comments_url, telegram_user_id, telegram_message_id
          - se è fornito `url` aggiorna anche il campo `domain` tramite extract_domain
          - esegue UPDATE su SQLite e risponde 200 su successo

        Errori gestiti:
          - 400 se il body è vuoto o non contiene campi consentiti
          - 409 se si verifica un vincolo di unicità (URL già presente)
          - 500 per errori generici
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(400)
                self.end_headers()
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            fields = {}
            allowed = ['url', 'title', 'description', 'image_url', 'comments_url', 'telegram_user_id', 'telegram_message_id']
            for k in allowed:
                if k in data:
                    fields[k] = data[k]

            if not fields:
                self.send_response(400)
                self.end_headers()
                return

            # If url changed, update domain automatically
            if 'url' in fields:
                fields['domain'] = self.extract_domain(fields['url'])

            set_clause = ', '.join([f"{k} = ?" for k in fields.keys()])
            params = list(fields.values())
            params.append(bookmark_id)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(f"UPDATE bookmarks SET {set_clause} WHERE id = ?", params)
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "updated"}')

        except sqlite3.IntegrityError:
            self.send_response(409)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "URL gia\' esistente"}')
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))

    def mark_read(self, bookmark_id):
        """
        Imposta il flag `is_read` per un bookmark.

        Comportamento:
          - legge opzionalmente JSON dal body con chiave 'is_read' (true/false)
          - se non è fornito, imposta is_read = 1 (letto)
          - aggiorna il record nel DB e risponde con JSON contenente
            lo stato risultante: {"status": "ok", "is_read": <0|1>}

        In caso di errore risponde 500 con il messaggio di errore.
        """
        try:
            # leggi body se presente
            content_length = int(self.headers.get('Content-Length', 0))
            is_read = 1
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                if 'is_read' in data:
                    is_read = 1 if data.get('is_read') else 0

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE bookmarks SET is_read = ? WHERE id = ?", (is_read, bookmark_id))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'is_read': is_read}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))

    def add_bookmark(self):
        """
        Aggiunge un nuovo bookmark nel database leggendo JSON dal body.

        Campi attesi nel JSON: url (obbligatorio), title, description,
        image_url, telegram_user_id, telegram_message_id, comments_url.

        Comportamento:
          - valida la presenza dell'url
          - estrae il dominio automaticamente e lo salva
          - verifica vincolo di unicità sull'URL -> risponde 409 se già esistente
          - inserisce il record e risponde 201 in caso di successo

        Errori gestiti: 400 (request bad), 409 (URL duplicato), 500 (altro)
        """
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            url = data.get('url', '').strip()
            if not url:
                raise ValueError("URL è obbligatorio")

            # Estrai dominio automaticamente
            domain = self.extract_domain(url)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Verifica se URL già existe (UNIQUE constraint)
            cursor.execute("SELECT id FROM bookmarks WHERE url = ?", (url,))
            if cursor.fetchone():
                conn.close()
                self.send_response(409)  # Conflict
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "URL gia\' esistente"}')
                return

            cursor.execute("""
                INSERT INTO bookmarks (url, title, description, image_url, domain, telegram_user_id, telegram_message_id, comments_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                url,
                data.get('title'),
                data.get('description'),
                data.get('image_url'),
                domain,
                data.get('telegram_user_id') if data.get('telegram_user_id') else None,
                data.get('telegram_message_id') if data.get('telegram_message_id') else None,
                data.get('comments_url')
            ))

            conn.commit()
            conn.close()

            self.send_response(201)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')

        except ValueError as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))
        except sqlite3.IntegrityError:
            self.send_response(409)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "URL gia\' esistente"}')
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))

    def get_bookmarks(self):
        """
        Recupera i bookmark dal database e restituisce una lista di tuple.

        Output: lista di tuple con colonne:
          (id, url, title, description, image_url, domain, saved_at,
           telegram_user_id, telegram_message_id, comments_url, is_read)

        In caso di errore con il DB stampa il messaggio di errore e ritorna lista vuota.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
          SELECT id, url, title, description, image_url, domain, 
              datetime(saved_at, 'localtime') as saved_at,
              telegram_user_id, telegram_message_id, comments_url,
              COALESCE(is_read, 0) as is_read
                FROM bookmarks 
                ORDER BY saved_at DESC
            """)

            bookmarks = cursor.fetchall()
            conn.close()

            return bookmarks

        except sqlite3.Error as e:
            print(f"Errore database: {e}")
            return []

def init_database():
    """
    Inizializza il database SQLite.

    Azioni:
      - crea la tabella `bookmarks` se non esiste
      - inserisce alcuni esempi se la tabella è vuota
      - assicura la presenza della colonna `is_read` (migrazione per DB esistenti)

    Questo metodo viene chiamato all'avvio del server per preparare il DB.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Crea la tabella bookmark con la nuova struttura
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

    # Inserisci alcuni bookmark di esempio se la tabella è vuota
    cursor.execute("SELECT COUNT(*) FROM bookmarks")
    if cursor.fetchone()[0] == 0:
        sample_bookmarks = [
            {
                'url': 'https://github.com',
                'title': 'GitHub',
                'description': 'Piattaforma per hosting di repository Git',
                'image_url': 'https://github.com/fluidicon.png',
                'domain': 'github.com',
                'comments_url': None,
                'telegram_user_id': None,
                'telegram_message_id': None
            },
            {
                'url': 'https://stackoverflow.com',
                'title': 'Stack Overflow',
                'description': 'Community di Q&A per programmatori',
                'image_url': 'https://cdn.sstatic.net/Sites/stackoverflow/Img/apple-touch-icon.png',
                'domain': 'stackoverflow.com',
                'comments_url': 'https://news.ycombinator.com/item?id=1',
                'telegram_user_id': 123456789,
                'telegram_message_id': 42
            },
            {
                'url': 'https://python.org',
                'title': 'Python.org',
                'description': 'Sito ufficiale del linguaggio Python',
                'image_url': 'https://www.python.org/static/favicon.ico',
                'domain': 'python.org',
                'comments_url': 'https://news.ycombinator.com/item?id=2',
                'telegram_user_id': None,
                'telegram_message_id': None
            }
        ]

        for bookmark in sample_bookmarks:
            cursor.execute("""
                INSERT INTO bookmarks (url, title, description, image_url, domain, comments_url, telegram_user_id, telegram_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bookmark['url'], bookmark['title'], bookmark['description'], 
                bookmark['image_url'], bookmark['domain'], bookmark['comments_url'],
                bookmark['telegram_user_id'], bookmark['telegram_message_id']
            ))

    # Assicura che la colonna is_read esista (migrazione semplice per DB esistenti)
    try:
        cursor.execute("PRAGMA table_info(bookmarks)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'is_read' not in cols:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN is_read INTEGER DEFAULT 0")
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("Database inizializzato con struttura HackerNews: {}".format(DB_PATH))

def create_self_signed_cert():
    """
    Crea un certificato self-signed (se non esiste) usando OpenSSL.

    Produce due file: KEY_FILE (chiave privata) e CERT_FILE (certificato).
    Se OpenSSL non è disponibile o il comando fallisce l'esecuzione termina.
    """
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        print(f"Certificati esistenti trovati: {CERT_FILE}, {KEY_FILE}")
        return

    print("Creazione certificato self-signed con chiave RSA 2048-bit...")

    try:
        # Prima genera la chiave privata RSA 2048-bit
        subprocess.run([
            'openssl', 'genrsa',
            '-out', KEY_FILE,
            '2048'
        ], check=True, capture_output=True)

        # Poi genera il certificato
        subprocess.run([
            'openssl', 'req', '-new', '-x509',
            '-key', KEY_FILE,
            '-out', CERT_FILE,
            '-days', '365',
            '-subj', '/C=IT/ST=Italy/L=Rome/O=LocalServer/CN=localhost'
        ], check=True, capture_output=True)
        print("✅ Certificato creato con successo!")

    except subprocess.CalledProcessError as e:
        print(f"❌ Errore nella creazione del certificato: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ OpenSSL non trovato nel PATH del sistema")
        sys.exit(1)


def main():
    """
    Entry-point principale che avvia il server HTTPS.

    Azioni principali:
      - inizializza il DB (init_database)
      - crea certificato se necessario (create_self_signed_cert)
      - configura HTTPServer e TLS
      - avvia il loop serve_forever

    Gestisce KeyboardInterrupt per chiudere ordinatamente il server.
    """
    # Inizializza database
    init_database()

    # Crea certificato se necessario
    create_self_signed_cert()

    # Configura il server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, BookmarkHandler)

    # Configura SSL
    try:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(CERT_FILE, KEY_FILE)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    except ssl.SSLError as e:
        print(f"❌ Errore SSL: {e}")
        return

    # Ottieni l'IP locale
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "IP_NON_DISPONIBILE"

    print(f"""
🚀 Server HTTPS avviato!

📍 Accedi da:
   • https://localhost:{PORT}
   • https://127.0.0.1:{PORT}
   • https://{local_ip}:{PORT}

📁 Database: {os.path.abspath(DB_PATH)}
🔒 Certificato: {os.path.abspath(CERT_FILE)}

✨ NUOVE FUNZIONALITÀ:
   • ➕ Form nascosto (mostra su richiesta)
   • 📋 Vista Cards (dettagliata)
   • 📄 Vista Compatta (lista densa)
   • 🔍 Ricerca e filtri per entrambe le viste
   • 📱 Integrazione Telegram
   • 🗞️ Link HackerNews

Premi Ctrl+C per fermare il server.
    """)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server fermato correttamente")
        httpd.shutdown()

if __name__ == '__main__':
    main()
