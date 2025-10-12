#!/usr/bin/env python3
"""
Server HTTPS per servire bookmark da database SQLite - Versione Enhanced
"""
import os
import sqlite3
import ssl
import json
import re
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket
import sys
from contextlib import contextmanager

# Aggiungi la root del progetto al path per importare la libreria condivisa
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from shared.utils import extract_domain
from htmldata import get_html

__version__ = "1.4.1"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurazione

# Default
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'telegram_bot', 'bookmarks.db')
PORT = 8443

@contextmanager
def db_connection():
    """Context manager per gestire le connessioni al database in modo sicuro."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()

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
        path = urlparse(self.path).path

        if path == '/':
            self.serve_homepage()
        elif path == '/api/bookmarks':
            query_components = parse_qs(urlparse(self.path).query)
            limit = int(query_components.get("limit", [20])[0]) # noqa
            offset = int(query_components.get("offset", [0])[0]) # noqa
            filter_type = query_components.get("filter", [None])[0] # noqa
            search_query = query_components.get("search", [None])[0]
            hide_read = query_components.get("hide_read", ['false'])[0].lower() == 'true'
            self.serve_bookmarks_api(limit=limit, offset=offset, filter_type=filter_type, hide_read=hide_read, search_query=search_query)
        elif path.startswith('/static/'):
            self.serve_static_file()
        else:
            self._send_error_response(404, "Not Found")

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
            self._send_error_response(404, "Not Found")

    def do_PUT(self):
        """
        Gestisce le richieste PUT per aggiornare risorse esistenti.

        Supporta:
          - PUT /api/bookmarks/<id>        -> aggiorna i campi del bookmark (chiama update_bookmark)
          - PUT /api/bookmarks/<id>/read   -> imposta il flag "is_read" (chiama mark_read)

        Il metodo effettua il parsing della path per estrarre l'id. Se l'id non
        è un intero risponde 400. Se la route non è riconosciuta risponde 404.
        """
        logger.info(f"PUT request for: {self.path}")
        parts = urlparse(self.path).path.strip('/').split('/')

        # Supporta: /api/bookmarks/<id>  (update)
        # e /api/bookmarks/<id>/read (set read flag)
        if len(parts) >= 3 and parts[0] == 'api' and parts[1] == 'bookmarks':
            try:
                bookmark_id = int(parts[2])
            except ValueError:
                self._send_error_response(400, "Invalid bookmark ID")
                return

            if len(parts) == 4 and parts[3] == 'read':
                self.mark_read(bookmark_id)
            else:
                self.update_bookmark(bookmark_id)
        else:
            self._send_error_response(404, "Not Found")

    def do_DELETE(self):
        """
        Gestisce le richieste DELETE.

        Route supportata:
          - DELETE /api/bookmarks/<id>  -> cancella il bookmark con l'id specificato

        Effettua parsing dell'id dalla path; se non è valido risponde 400.
        In caso di successo chiama delete_bookmark che manda la risposta JSON.
        """
        logger.info(f"DELETE request for: {self.path}")
        parts = urlparse(self.path).path.strip('/').split('/')

        # Supporta: /api/bookmarks/<id>
        if len(parts) == 3 and parts[0] == 'api' and parts[1] == 'bookmarks':
            try:
                bookmark_id = int(parts[2])
            except ValueError:
                self._send_error_response(400, "Invalid bookmark ID")
                return

            self.delete_bookmark(bookmark_id)
        else:
            self._send_error_response(404, "Not Found")

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
        # Carica solo la prima "pagina" di bookmark non filtrati per il rendering iniziale
        # Per default, nasconde i letti, ma questo può essere sovrascritto dal JS lato client
        hide_read_default = True

        bookmarks = self.get_bookmarks(limit=20, offset=0, filter_type=None, hide_read=hide_read_default)

        # Il conteggio totale si riferisce sempre a tutti i bookmark nel DB
        total_count = self.get_total_bookmark_count(filter_type=None, hide_read=False)
        html = get_html(self, bookmarks, __version__, total_count)

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _send_json_response(self, status_code, data):
        """Helper per inviare risposte JSON."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_error_response(self, status_code, message):
        """Helper per inviare risposte di errore in formato JSON."""
        error_data = {'error': message}
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(error_data, ensure_ascii=False).encode('utf-8'))

    def serve_static_file(self):
        """Serve un file statico dalla cartella 'static'."""
        try:
            # Costruisci un percorso sicuro per il file
            # es. /static/app.js -> webserver/static/app.js
            static_path = os.path.join(SCRIPT_DIR, self.path.lstrip('/'))

            # Verifica che il percorso risolto sia effettivamente dentro la cartella 'static'
            # per prevenire attacchi di directory traversal.
            if not os.path.abspath(static_path).startswith(os.path.join(SCRIPT_DIR, 'static')):
                self._send_error_response(403, "Forbidden")
                return

            if os.path.exists(static_path) and os.path.isfile(static_path):
                content_type = 'application/javascript' if static_path.endswith('.js') else 'text/css'
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                with open(static_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self._send_error_response(404, "Static file not found")

        except Exception as e:
            logger.error(f"Error serving static file {self.path}: {e}")
            self._send_error_response(500, "Internal Server Error")

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

            # Sanitize for JS: remove newlines from title and description
            bookmark_list = list(bookmark)
            if bookmark_list[2]: bookmark_list[2] = re.sub(r'[\r\n\u2028\u2029]', ' ', str(bookmark_list[2]))
            if bookmark_list[3]: bookmark_list[3] = re.sub(r'[\r\n\u2028\u2029]', ' ', str(bookmark_list[3]))
            bookmark_safe = tuple(bookmark_list)

            # Crea una stringa di ricerca che contiene tutti i dati testuali
            search_text = f"{bookmark_safe[1] or ''} {bookmark_safe[2] or ''} {bookmark_safe[3] or ''} {bookmark_safe[5] or ''}".lower()
            search_text = re.sub(r'[\r\n\u2028\u2029]', ' ', search_text)

            # Converte la tupla del bookmark in un dizionario JSON per il pulsante di modifica
            bookmark_json = json.dumps(dict(zip(['id', 'url', 'title', 'description', 'image_url', 'domain', 'saved_at', 'telegram_user_id', 'telegram_message_id', 'comments_url', 'is_read'], bookmark_safe)), ensure_ascii=False)
            bookmark_json_html = bookmark_json.replace("'", "&#39;").replace('"', '&quot;')

            # Logica per l'icona e il titolo del pulsante "leggi"
            is_read = bookmark[10] == 1
            read_button_title = "Segna come non letto" if is_read else "Segna come letto"
            read_button_icon = (
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>'
                if is_read
                else '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            )

            html_cards.append(f"""
            <div class="bookmark-card" data-id="{bookmark_safe[0]}" data-is-read="{bookmark_safe[10]}" data-search-text="{search_text}">
                <div class="bookmark-header">
                    {image_html}
                    <div class="bookmark-info">
                        <div class="bookmark-actions-top">
                            {telegram_badge}
                            {hn_link}
                            <button class="icon-btn read" title="{read_button_title}" data-id="{bookmark_safe[0]}">{read_button_icon}</button>
                            <button class="icon-btn edit" title="Modifica" data-bookmark='{bookmark_json_html}'>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                            </button>
                            <button class="icon-btn delete" title="Elimina" data-id="{bookmark_safe[0]}">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 6h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 6v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                            </button>
                        </div>
                        <div class="bookmark-title">{bookmark_safe[2] or 'Senza titolo'}</div>
                    </div>
                </div>

                <a href="{bookmark_safe[1]}" target="_blank" class="bookmark-url">{bookmark_safe[1]}</a>

                <div class="bookmark-description">{bookmark_safe[3] or 'Nessuna descrizione'}</div>

                <div class="bookmark-footer">
                    <span class="bookmark-date">{bookmark_safe[6]}</span>
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

            # Sanitize for JS: remove newlines from title and description
            bookmark_list = list(bookmark)
            if bookmark_list[2]: bookmark_list[2] = re.sub(r'[\r\n\u2028\u2029]', ' ', str(bookmark_list[2]))
            if bookmark_list[3]: bookmark_list[3] = re.sub(r'[\r\n\u2028\u2029]', ' ', str(bookmark_list[3]))
            bookmark_safe = tuple(bookmark_list)

            # Converte la tupla del bookmark in un dizionario JSON per il pulsante di modifica
            bookmark_json = json.dumps(dict(zip(['id', 'url', 'title', 'description', 'image_url', 'domain', 'saved_at', 'telegram_user_id', 'telegram_message_id', 'comments_url', 'is_read'], bookmark_safe)), ensure_ascii=False)
            bookmark_json_html = bookmark_json.replace("'", "&#39;").replace('"', '&quot;')

            # Logica per l'icona e il titolo del pulsante "leggi"
            is_read = bookmark[10] == 1
            read_button_title = "Segna come non letto" if is_read else "Segna come letto"
            read_button_icon = (
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>'
                if is_read
                else '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            )

            html_items.append(f"""
            <div class="compact-item" data-id="{bookmark_safe[0]}" data-is-read="{bookmark_safe[10]}">
                {image_html}
                <div class="compact-content">
                    <div class="compact-actions-top">
                        {badges_html}
                        <button class="icon-btn read" title="{read_button_title}" data-id="{bookmark_safe[0]}">{read_button_icon}</button>
                        <button class="icon-btn edit" title="Modifica" data-bookmark='{bookmark_json_html}'>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        </button>
                        <button class="icon-btn delete" title="Elimina" data-id="{bookmark_safe[0]}">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 6h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 6v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        </button>
                    </div>
                    <div class="compact-title">{bookmark_safe[2] or 'Senza titolo'}</div>
                    <a href="{bookmark_safe[1]}" target="_blank" class="compact-url">{bookmark_safe[1]}</a>
                </div>
                <div class="compact-date">{short_date}</div>
            </div>
            """)

        return ''.join(html_items)

    def serve_bookmarks_api(self, limit=20, offset=0, filter_type=None, hide_read=False, search_query=None):
        """
        API che restituisce la lista dei bookmark in formato JSON.

        Azioni:
          - recupera i bookmark con get_bookmarks(), applicando filtri e ricerca
          - costruisce una lista di dizionari serializzabile in JSON
          - invia la risposta HTTP 200 con Content-Type application/json

        Ogni elemento JSON contiene le chiavi: id, url, title, description,
        image_url, domain, saved_at, telegram_user_id, telegram_message_id,
        comments_url, is_read.
        """
        bookmarks = self.get_bookmarks(limit=limit, offset=offset, filter_type=filter_type, hide_read=hide_read, search_query=search_query)

        bookmark_list = [] # noqa
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

        self._send_json_response(200, bookmark_list)

    def delete_bookmark(self, bookmark_id):
        """
        Cancella un bookmark dal database dato il suo `bookmark_id`.

        Risponde con JSON:
          - 200 {"status": "deleted"} in caso di successo
          - 500 {"error": "..."} in caso di errore

        Apre una connessione SQLite, esegue DELETE e chiude la connessione.
        """
        try:
            with db_connection() as cursor:
                cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            self._send_json_response(200, {"status": "deleted"})
        except sqlite3.Error as e:
            self._send_error_response(500, str(e))

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
                self._send_error_response(400, "Request body is empty")
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            fields = {} # noqa
            allowed = ['url', 'title', 'description', 'image_url', 'comments_url', 'telegram_user_id', 'telegram_message_id', 'is_read']
            for k in allowed:
                if k in data:
                    fields[k] = data[k]

            if not fields:
                self._send_error_response(400, "No valid fields to update")
                return

            # If url changed, update domain automatically
            if 'url' in fields:
                fields['domain'] = extract_domain(fields['url'])

            set_clause = ', '.join([f"{k} = ?" for k in fields.keys()])
            params = list(fields.values())
            params.append(bookmark_id)

            with db_connection() as cursor:
                cursor.execute(f"UPDATE bookmarks SET {set_clause} WHERE id = ?", params)

                # Dopo l'aggiornamento, recupera il bookmark aggiornato per restituirlo
                cursor.execute("""
                    SELECT id, url, title, description, image_url, domain,
                        datetime(saved_at, 'localtime') as saved_at,
                        telegram_user_id, telegram_message_id, comments_url,
                        COALESCE(is_read, 0) as is_read
                    FROM bookmarks WHERE id = ?
                """, (bookmark_id,))
                updated_bookmark_tuple = cursor.fetchone()

            if not updated_bookmark_tuple:
                self._send_error_response(404, "Bookmark not found after update")
                return

            updated_bookmark = dict(zip(['id', 'url', 'title', 'description', 'image_url', 'domain', 'saved_at', 'telegram_user_id', 'telegram_message_id', 'comments_url', 'is_read'], updated_bookmark_tuple))
            self._send_json_response(200, updated_bookmark)
        except sqlite3.IntegrityError:
            self._send_error_response(409, "URL already exists")
        except Exception as e:
            logger.error(f"Error updating bookmark {bookmark_id}: {e}")
            self._send_error_response(500, "An internal error occurred")

    def mark_read(self, bookmark_id):
        """
        Imposta il flag `is_read` per un bookmark.

        Comportamento:
          - legge opzionalmente JSON dal body con chiave 'is_read' (true/false)
          - se non è fornito, imposta is_read = 1 (letto)
          - aggiorna il record nel DB e risponde con JSON contenente lo stato risultante: {"status": "ok", "is_read": <0|1>}

        In caso di errore risponde 500 con il messaggio di errore.
        """
        try:
            # Legge il body della richiesta per determinare lo stato desiderato.
            # Se il body è assente, l'azione di default è marcare come letto (is_read=1).
            content_length = int(self.headers.get('Content-Length', 0))
            is_read = 1
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                if 'is_read' in data:
                    is_read = 1 if data.get('is_read') else 0

            with db_connection() as cursor:
                cursor.execute("UPDATE bookmarks SET is_read = ? WHERE id = ?", (int(is_read), bookmark_id))
            self._send_json_response(200, {'status': 'ok', 'is_read': is_read})

        except sqlite3.Error as e:
            self._send_error_response(500, str(e))

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
            domain = extract_domain(url)

            with db_connection() as cursor:
                # Verifica se URL già existe (UNIQUE constraint)
                cursor.execute("SELECT id FROM bookmarks WHERE url = ?", (url,))
                if cursor.fetchone():
                    self._send_error_response(409, "URL already exists")
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

            self._send_json_response(201, {"status": "created"})

        except ValueError as e:
            self._send_error_response(400, str(e))
        except sqlite3.IntegrityError:
            self._send_error_response(409, "URL already exists")
        except Exception as e:
            logger.error(f"Error adding bookmark: {e}")
            self._send_error_response(500, "An internal error occurred")

    def get_total_bookmark_count(self, filter_type=None, hide_read=False):
        """Recupera il numero totale di bookmark dal database."""
        try:
            with db_connection() as cursor:
                query, params = self._build_query_parts(filter_type, hide_read)
                cursor.execute(f"SELECT COUNT(*) FROM bookmarks WHERE {query}", params)
                count = cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error(f"Database error during count: {e}")
            return 0

    def _build_query_parts(self, filter_type=None, hide_read=False, search_query=None):
        """
        Costruisce le clausole WHERE e i parametri per le query dei bookmark.
        Args:
            filter_type (str, optional): Filtro per 'telegram', 'hn', 'recent'.
            hide_read (bool, optional): Se True, esclude i bookmark letti.
            search_query (str, optional): Termine di ricerca testuale.

        Returns:
            tuple: Una stringa con le clausole WHERE e una lista di parametri.
        """
        where_clauses = ["1=1"]
        params = []

        if filter_type == 'telegram':
            where_clauses.append("telegram_user_id IS NOT NULL AND (comments_url IS NULL OR comments_url = '')")
        elif filter_type == 'hn':
            where_clauses.append("comments_url IS NOT NULL AND comments_url != ''")
        elif filter_type == 'recent':
            where_clauses.append("saved_at >= datetime('now', '-7 days')")

        if hide_read:
            where_clauses.append("is_read = 0")

        if search_query:
            where_clauses.append("(title LIKE ? OR description LIKE ? OR url LIKE ? OR domain LIKE ?)")
            params.extend([f'%{search_query}%'] * 4)

        return " AND ".join(where_clauses), params

    def get_bookmarks(self, limit=20, offset=0, filter_type=None, hide_read=False, search_query=None):
        """
        Recupera i bookmark dal database, applicando filtri e ricerca opzionali.
        """
        try:
            with db_connection() as cursor:
                where_clause, params = self._build_query_parts(filter_type, hide_read, search_query)

                cursor.execute("""
                    SELECT id, url, title, description, image_url, domain,
                        datetime(saved_at, 'localtime') as saved_at,
                        telegram_user_id, telegram_message_id, comments_url,
                        COALESCE(is_read, 0) as is_read
                    FROM bookmarks
                    WHERE {where_clause}
                    ORDER BY saved_at DESC
                    LIMIT ? OFFSET ?
                """.format(where_clause=where_clause), params + [limit, offset])

                bookmarks = cursor.fetchall()
            return bookmarks

        except sqlite3.Error as e:
            logger.error(f"Database error fetching bookmarks: {e}")
            return []

def create_self_signed_cert(cert_file_path, key_file_path):
    """
    Crea un certificato self-signed (se non esiste) usando OpenSSL.

    Produce due file: KEY_FILE (chiave privata) e CERT_FILE (certificato).
    Se OpenSSL non è disponibile o il comando fallisce l'esecuzione termina.
    """
    # Questa funzione richiede 'openssl' nel PATH
    import subprocess
    if os.path.exists(cert_file_path) and os.path.exists(key_file_path):
        logger.info(f"Certificati esistenti trovati: {cert_file_path}, {key_file_path}")
        return

    logger.info("Creazione certificato self-signed con chiave RSA 2048-bit...")

    try:
        # Prima genera la chiave privata RSA 2048-bit
        subprocess.run([
            'openssl', 'genrsa',
            '-out', key_file_path,
            '2048'
        ], check=True, capture_output=True)

        # Poi genera il certificato
        subprocess.run([
            'openssl', 'req', '-new', '-x509',
            '-key', key_file_path,
            '-out', cert_file_path,
            '-days', '365',
            '-subj', '/C=IT/ST=Italy/L=Rome/O=LocalServer/CN=localhost'
        ], check=True, capture_output=True)
        logger.info("✅ Certificato creato con successo!")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Errore nella creazione del certificato: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("❌ OpenSSL non trovato nel PATH del sistema")
        sys.exit(1)

def main():
    """
    Entry-point principale che avvia il server HTTPS.

    Azioni principali:
      - inizializza il DB (init_database)
      - configura HTTPServer e TLS
      - avvia il loop serve_forever

    Gestisce KeyboardInterrupt per chiudere ordinatamente il server.
    """
    # --- Logica Certificati ---
    cert_file = os.path.join(SCRIPT_DIR, 'server.pem')
    key_file = os.path.join(SCRIPT_DIR, 'server.key')

    le_domain = os.getenv('LE_DOMAIN', None)
    logger.info(f"LE_DOMAIN letto come '{le_domain}'")

    if le_domain:
        #le_cert_dir = f'/etc/letsencrypt/live/{le_domain}'
        le_cert_dir = '..'
        le_fullchain = os.path.join(le_cert_dir, 'fullchain.pem')
        le_privkey = os.path.join(le_cert_dir, 'privkey.pem')

        if os.path.exists(le_fullchain) and os.path.exists(le_privkey):
            logger.info(f"Trovati certificati Let's Encrypt: {le_cert_dir}")
            cert_file = le_fullchain
            key_file = le_privkey
        else:
            logger.warning(f"LE_DOMAIN impostato ma certificati non trovati o non leggibili in {le_cert_dir}")
            logger.warning("Verifica i permessi o il percorso. Procedo con certificati locali.")
    else:
        logger.info("LE_DOMAIN non impostato. Uso certificati locali.")

    # Crea certificato se necessario
    if not (os.path.exists(cert_file) and os.path.exists(key_file)):
        print("Certificati non trovati. Provo a generarli...")
        create_self_signed_cert(cert_file, key_file)


    # Configura il server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, BookmarkHandler)

    # Configura SSL
    try:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert_file, key_file)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    except ssl.SSLError as e:
        logger.error(f"❌ Errore SSL: {e}")
        return

    # Ottieni l'IP locale
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "IP_NON_DISPONIBILE"

    logger.info(f"""
🚀 Server HTTPS avviato!

📍 Accedi da:
   • https://oc.zitzu.it:{PORT}
   • https://127.0.0.1:{PORT}
   • https://{local_ip}:{PORT}

📁 Database: {os.path.abspath(DB_PATH)}
🔒 Certificato: {os.path.abspath(cert_file)}

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
        logger.info("\n🛑 Server fermato correttamente")
        httpd.shutdown()

if __name__ == '__main__':
    # Aggiungi la root del progetto al path per importare la libreria condivisa
    sys.path.append(os.path.dirname(SCRIPT_DIR))
    try:
        # Importa direttamente la funzione di inizializzazione del DB
        from shared.database import init_database
        logger.info("Inizializzazione database...")
        init_database()
        
        # Avvia il server
        main()

    except ImportError:
        logger.error("ERRORE: Impossibile importare la logica del database. Assicurati che la struttura del progetto sia corretta.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"ERRORE inatteso durante l'avvio: {e}")
        sys.exit(1)
