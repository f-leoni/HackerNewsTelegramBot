#!/usr/bin/env python3
"""
HTTPS server to serve bookmarks from an SQLite database - Enhanced Version
"""
import os
import sqlite3
import ssl
import json
import csv
import re
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs
import socket
import sys
from contextlib import contextmanager
import argparse
import secrets
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash

# Add the project root to the path to import the shared library
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from shared.utils import extract_domain, get_article_metadata
from shared.database import get_db_path
from htmldata import get_html
from htmldata import get_login_page
__version__ = "2.0.0"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration

# Default
DB_PATH = get_db_path()
DEFAULT_PAGE_SIZE = 20 # Default number of bookmarks per page for infinite scrolling
PORT = 8443

@contextmanager
def db_connection():
    """Context manager to handle database connections safely."""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()

SUPPORTED_LANGUAGES = ['en', 'it']
DEFAULT_LANGUAGE = 'en'

def load_translations(lang_code):
    """Loads the translation dictionary from a JSON file."""
    # Sanitize lang_code to prevent directory traversal
    lang_code = re.sub(r'[^a-zA-Z_-]', '', lang_code).split('-')[0].lower()
    if lang_code not in SUPPORTED_LANGUAGES:
        lang_code = DEFAULT_LANGUAGE

    filepath = os.path.join(SCRIPT_DIR, 'locales', f'{lang_code}.json')
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback to default language if the file is missing or corrupt
        return load_translations(DEFAULT_LANGUAGE)

class BookmarkHandler(BaseHTTPRequestHandler):
    # Override server_version to prevent revealing Python version
    server_version = "Web Server"

    def version_string(self):
        """Overrides the 'Server' header to not reveal the software version."""
        # This method is also called, so we return the same generic string.
        return self.server_version

    def get_current_user(self):
        """Verifies the session cookie and returns the user ID if valid."""
        cookies = SimpleCookie(self.headers.get('Cookie'))
        session_id = cookies.get('session_id')

        if not session_id:
            return None

        with db_connection() as cursor:
            cursor.execute(
                "SELECT user_id FROM sessions WHERE session_id = ? AND expires_at > ?",
                (session_id.value, datetime.now())
            )
            result = cursor.fetchone()

        return result[0] if result else None

    def get_user_language(self):
        """Determines the user's preferred language."""
        # 1. Check for a language query parameter (e.g., /?lang=it)
        query_components = parse_qs(urlparse(self.path).query)
        lang_param = query_components.get('lang', [None])[0]
        if lang_param in SUPPORTED_LANGUAGES:
            return lang_param

        # 2. Check for a language cookie
        cookies = SimpleCookie(self.headers.get('Cookie'))
        lang_cookie = cookies.get('lang')
        if lang_cookie and lang_cookie.value in SUPPORTED_LANGUAGES:
            return lang_cookie.value

        # 3. Check the Accept-Language header
        accept_language = self.headers.get('Accept-Language', '')
        for lang in accept_language.split(','):
            code = lang.split(';')[0].strip().lower().split('-')[0]
            if code in SUPPORTED_LANGUAGES:
                return code

        return DEFAULT_LANGUAGE

    def _send_security_headers(self):
        """Adds common security headers to all responses."""
        # Generate a nonce if it doesn't exist for this request.
        # This makes the method safe to be called multiple times.
        if not hasattr(self, 'nonce'):
            self.nonce = secrets.token_hex(16)

        # CSP: include script-src-elem and style-src-elem / style-src-attr to cover
        # dynamically created <script>/<style> elements and inline style attributes.
        # La gestione degli indicatori di htmx è stata spostata su CSS per evitare 'unsafe-inline'.
        csp = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{self.nonce}' https://cdn.jsdelivr.net https://unpkg.com; "
            f"script-src-elem 'self' 'nonce-{self.nonce}' https://cdn.jsdelivr.net https://unpkg.com; "
            f"style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
            f"img-src 'self' data: https:; "
            f"connect-src 'self'; "
            f"form-action 'self';"
        )
        self.send_header('Content-Security-Policy', csp)

    def _redirect(self, path):
        """Sends a 302 redirect response."""
        self.send_response(302)
        self._send_security_headers()
        self.send_header('Location', path)
        self.end_headers()

    def _send_html_response(self, status_code, html_content):
        """Helper to send HTML responses."""
        self.send_response(status_code)
        self._send_security_headers()
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def do_AUTHHEAD(self):
        """Dummy method to handle non-standard authentication requests."""
        self.send_response(401)
        self._send_security_headers()
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_OPTIONS(self):
        """Handles OPTIONS pre-flight requests for CORS."""
        self.send_response(204) # No Content
        self.send_header('Access-Control-Allow-Origin', '*') # Or be more restrictive
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_HEAD(self):
        """Handles HEAD requests by delegating to do_GET and discarding the body."""
        # This is a simple way to handle HEAD. It runs do_GET but the framework
        # prevents the body from being sent.
        self.do_GET()

    def do_GET(self):
        """
        Handles GET requests.

        Supported routes:
          - /                 -> main page (HTML generated by get_html)
          - /api/bookmarks     -> JSON API that returns the list of bookmarks
          - /favicon.ico       -> responds 404

        Effect: analyzes self.path, calls the corresponding service method
        and sends the HTTP response with the appropriate code and headers.
        Responds 404 for unknown paths.
        """
        path = urlparse(self.path).path

        if path == '/login':
            self.serve_login_page()
            return
        elif path == '/logout':
            self.handle_logout()
            return

        # Allow access to static files without authentication
        if path.startswith('/static/'):
            self.serve_static_file()
            return

        # Protect all other routes
        user_id = self.get_current_user()
        if not user_id:
            self._redirect('/login')
            return

        if path == '/':
            self.serve_homepage()
        elif path == '/api/bookmarks':
            query_components = parse_qs(urlparse(self.path).query)
            limit = int(query_components.get("limit", [DEFAULT_PAGE_SIZE])[0])
            offset = int(query_components.get("offset", [0])[0])
            filter_type = query_components.get("filter_type", [None])[0]
            search_query = query_components.get("search_query", [None])[0]
            hide_read = query_components.get("hide_read", ['false'])[0].lower() == 'true'
            sort_order = query_components.get("sort_order", ['desc'])[0].lower()
            self.serve_bookmarks_api(limit=limit, offset=offset, filter_type=filter_type, hide_read=hide_read, search_query=search_query, sort_order=sort_order)
        elif path == '/api/export/csv':
            self.serve_export_csv()
        elif path == '/ui/bookmarks':
            query_components = parse_qs(urlparse(self.path).query)
            search_query = query_components.get("search", [None])[0]
            hide_read = query_components.get("hide_read", ['false'])[0].lower() == 'true'
            sort_order = query_components.get("sort", ['desc'])[0].lower()
            filter_type = query_components.get("filter_type", [None])[0]
            limit = int(query_components.get("limit", [DEFAULT_PAGE_SIZE])[0])
            offset = int(query_components.get("offset", [0])[0])
            self.serve_bookmarks_ui(search_query=search_query, hide_read=hide_read, sort_order=sort_order, filter_type=filter_type, limit=limit, offset=offset)
        elif path == '/ui/bookmarks/scroll':  # New endpoint for infinite scrolling
            query_components = parse_qs(urlparse(self.path).query)
            # Ensure correct types from query string
            limit = int(query_components.get('limit', [DEFAULT_PAGE_SIZE])[0])
            offset = int(query_components.get('offset', [0])[0])
            hide_read = str(query_components.get('hide_read', 'false')).lower() == 'true'
            search_query = query_components.get('search_query', [None])[0]
            sort_order = query_components.get('sort_order', ['desc'])[0]
            filter_type = query_components.get('filter_type', [None])[0]
            self.serve_bookmarks_scroll_ui(search_query=search_query, hide_read=hide_read, sort_order=sort_order, filter_type=filter_type, limit=limit, offset=offset)
        elif path == '/favicon.ico':
            self.path = '/static/img/favicon.svg' # Reindirizza la richiesta standard alla nostra SVG
            self.serve_static_file()
        else:
            self._send_error_response(404, "Not Found")

    def do_POST(self):
        """
        Handles POST requests.

        Currently only supports the route:
          - POST /api/bookmarks  : adds a new bookmark by reading JSON from the body

        Responds with 404 if the path is not recognized.
        """
        path = urlparse(self.path).path

        if path == '/login':
            self.handle_login()
            return

        # Protect all other routes
        user_id = self.get_current_user()
        if not user_id and path != '/login':
            self._send_error_response(401, "Authentication required")
            return

        if path == '/api/bookmarks':
            self.add_bookmark()
        elif path == '/api/scrape':
            self.scrape_metadata()
        else:
            self._send_error_response(404, "Not Found")

    def do_PUT(self):
        """
        Handles PUT requests to update existing resources.

        Supports:
          - PUT /api/bookmarks/<id>        -> updates bookmark fields (calls update_bookmark)
          - PUT /api/bookmarks/<id>/read   -> sets the "is_read" flag (calls mark_read)

        The method parses the path to extract the id. If the id is not
        an integer, it responds with 400. If the route is not recognized, it responds with 404.
        """
        logger.info(f"PUT request for: {self.path}")

        user_id = self.get_current_user()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return

        parts = urlparse(self.path).path.strip('/').split('/')

        # Supports: /api/bookmarks/<id>  (update)
        # and /api/bookmarks/<id>/read (set read flag)
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
        Handles DELETE requests.

        Supported route:
          - DELETE /api/bookmarks/<id>  -> deletes the bookmark with the specified id

        Parses the id from the path; if it's invalid, it responds with 400.
        On success, it calls delete_bookmark which sends the JSON response.
        """
        logger.info(f"DELETE request for: {self.path}")

        user_id = self.get_current_user()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return

        parts = urlparse(self.path).path.strip('/').split('/')

        # Supports: /api/bookmarks/<id>
        if len(parts) == 3 and parts[0] == 'api' and parts[1] == 'bookmarks':
            try:
                bookmark_id = int(parts[2])
            except ValueError:
                self._send_error_response(400, "Invalid bookmark ID")
                return

            self.delete_bookmark(bookmark_id)
        else:
            self._send_error_response(404, "Not Found")

    def serve_login_page(self):
        """Serves the HTML login page."""
        if not hasattr(self, 'nonce'):
            self.nonce = secrets.token_hex(16)
        self._send_html_response(200, get_login_page(self))

    def handle_login(self):
        """Handles a login attempt from a POST request."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            credentials = parse_qs(post_data.decode('utf-8'))

            username = credentials.get('username', [''])[0]
            password = credentials.get('password', [''])[0]

            with db_connection() as cursor:
                cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()

            if user and check_password_hash(user[1], password):
                session_id = secrets.token_hex(16)
                expires_at = datetime.now() + timedelta(days=30)

                with db_connection() as cursor:
                    cursor.execute(
                        "INSERT INTO sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)",
                        (session_id, user[0], expires_at)
                    )

                self.send_response(302)
                self.send_header('Location', '/')
                cookie = SimpleCookie()
                cookie['session_id'] = session_id
                cookie['session_id']['path'] = '/'
                cookie['session_id']['expires'] = expires_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
                self.send_header('Set-Cookie', cookie.output(header='').lstrip())
                self.end_headers()
            else:
                self._send_html_response(401, get_login_page(self, error="Invalid credentials."))

        except Exception as e:
            logger.error(f"Error during login: {e}")
            self._send_html_response(500, get_login_page(self, error="Internal server error."))

    def handle_logout(self):
        """Handles logout by deleting the session cookie."""
        cookies = SimpleCookie(self.headers.get('Cookie'))
        session_id = cookies.get('session_id')

        if session_id:
            with db_connection() as cursor:
                cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id.value,))

        self.send_response(302)
        self.send_header('Location', '/login')
        self.send_header('Set-Cookie', 'session_id=; Path=/; Max-Age=0') # Delete the cookie
        self.end_headers()

    def serve_homepage(self):
        """Builds and sends the main HTML page.

        Actions:
          - retrieves bookmarks via get_bookmarks()
          - generates HTML with get_html(self, bookmarks)
          - sends HTTP 200 response with Content-Type text/html

        Note: the HTML template is generated by `htmldata.get_html` and can
        contain JS that uses the server-side APIs for CRUD operations.
        """
        # Load only the first "page" of unfiltered bookmarks for initial rendering
        # By default, it hides read items, but this can be overridden by client-side JS
        hide_read_default = True

        # Determine language and load translations
        lang_code = self.get_user_language()
        translations = load_translations(lang_code)

        # Generate the nonce *before* rendering the HTML template that needs it.
        if not hasattr(self, 'nonce'):
            self.nonce = secrets.token_hex(16)

        # For initial load, fetch DEFAULT_PAGE_SIZE + 1 to check for more items
        bookmarks_raw = self.get_bookmarks(self.get_current_user(), limit=DEFAULT_PAGE_SIZE + 1, offset=0, filter_type=None, hide_read=hide_read_default)
        has_more = len(bookmarks_raw) > DEFAULT_PAGE_SIZE
        bookmarks_to_render = bookmarks_raw[:DEFAULT_PAGE_SIZE]

        # The total count always refers to all bookmarks in the DB
        total_count_for_filters = self.get_total_bookmark_count(filter_type=None, hide_read=hide_read_default) # Initial filter
        
        html = get_html(self, bookmarks_to_render, __version__, total_count_for_filters, translations, has_more=has_more)

        # Send headers in the correct order
        self.send_response(200)
        self._send_security_headers()
        self.send_header('Content-type', 'text/html; charset=utf-8')

        # Set a cookie to remember the user's language choice
        cookie = SimpleCookie()
        cookie['lang'] = lang_code
        self.send_header('Set-Cookie', cookie.output(header='').lstrip())

        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _send_json_response(self, status_code, data):
        """Helper to send JSON responses."""
        self.send_response(status_code)
        self._send_security_headers()
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_error_response(self, status_code, message):
        """Helper to send error responses in JSON format."""
        error_data = {'error': message}
        self.send_response(status_code)
        self._send_security_headers()
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(error_data, ensure_ascii=False).encode('utf-8'))

    def serve_static_file(self):
        """Serves a static file from the 'static' folder."""
        try:
            static_path = os.path.join(SCRIPT_DIR, self.path.lstrip('/'))

            # Verify that the resolved path is actually inside the 'static' folder
            # to prevent directory traversal attacks.
            if not os.path.abspath(static_path).startswith(os.path.join(SCRIPT_DIR, 'static')):
                self._send_error_response(403, "Forbidden")
                return

            if os.path.exists(static_path) and os.path.isfile(static_path):
                if static_path.endswith('.js'):
                    content_type = 'application/javascript'
                elif static_path.endswith('.css'):
                    content_type = 'text/css'
                elif static_path.endswith('.svg'):
                    content_type = 'image/svg+xml'
                else:
                    content_type = 'application/octet-stream' # Fallback generico
                self.send_response(200)
                self._send_security_headers()
                self.send_header('Content-type', content_type)
                self.end_headers()
                with open(static_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self._send_error_response(404, "Static file not found")

        except (ConnectionAbortedError, BrokenPipeError):
            # This happens if the client closes the connection while we are sending data.
            # It's a common network event, not a server error.
            logger.info(f"Client aborted connection for {self.path}. Request terminated.")

        except Exception as e:
            logger.error(f"Error serving static file {self.path}: {e}")
            self._send_error_response(500, "Internal Server Error")

    def serve_bookmarks_api(self, limit=20, offset=0, filter_type=None, hide_read=False, search_query=None, sort_order='desc'):
        """
        API that returns the list of bookmarks in JSON format.

        Actions:
          - retrieves bookmarks with get_bookmarks(), applying filters and search
          - builds a list of dictionaries serializable to JSON
          - sends HTTP 200 response with Content-Type application/json

        Each JSON element contains the keys: id, url, title, description,
        image_url, domain, saved_at, telegram_user_id, telegram_message_id,
        comments_url, is_read.
        """
        bookmarks = self.get_bookmarks(self.get_current_user(), limit=limit, offset=offset, filter_type=filter_type, hide_read=hide_read, search_query=search_query, sort_order=sort_order)

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

    def serve_bookmarks_ui(self, search_query=None, hide_read=False, sort_order='desc', filter_type=None, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        API that returns bookmarks rendered as HTML fragments for htmx.
        This endpoint is used for initial loads (search, sort, filter) and returns full divs.
        """
        # Fetch one more than the limit to check if there are more items
        bookmarks_raw = self.get_bookmarks(self.get_current_user(), limit=limit + 1, offset=offset, search_query=search_query, hide_read=hide_read, sort_order=sort_order, filter_type=filter_type)
        
        has_more = len(bookmarks_raw) > limit
        bookmarks_to_render = bookmarks_raw[:limit]
        
        lang_code = self.get_user_language()
        translations = load_translations(lang_code)

        # Render the actual bookmarks
        rendered_cards = render_bookmarks(bookmarks_to_render, translations)
        rendered_compact = render_bookmarks_compact(bookmarks_to_render, translations)

        # Calculate total count for the current filters
        total_count_for_filters = self.get_total_bookmark_count(self.get_current_user(), filter_type=filter_type, hide_read=hide_read, search_query=search_query)
        
        # Build the "load more" trigger if there are more items
        load_more_trigger = ""
        if has_more:
            next_offset = offset + len(bookmarks_to_render)
            load_more_trigger = f"""
            <div id="loadMoreTrigger" hx-get="/ui/bookmarks/scroll"
                 hx-trigger="revealed"
                 hx-swap="outerHTML"
                 hx-indicator="#loadingIndicator"
                 :hx-vals="JSON.stringify({{'offset': {next_offset}, 'limit': {limit}, 'sort_order': sort_order, 'search_query': search_query, 'hide_read': hide_read, 'filter_type': filter_type}})"
                 class="load-more-trigger">
                {translations.get('loading', 'Loading more bookmarks...')}
            </div>
            """
        else:
            load_more_trigger = f"""
            <div id="loadMoreTrigger" class="load-more-trigger no-more-items">
                {translations.get('all_bookmarks_loaded', 'All bookmarks have been loaded.')}
            </div>
            """

        html_response = f"""
        <div id="bookmarksGrid" class="bookmarks-grid" hx-swap-oob="innerHTML">{rendered_cards}</div>
        <div id="bookmarksCompact" class="bookmarks-compact" hx-swap-oob="innerHTML">{rendered_compact}</div>
        <div id="loadMoreContainer" hx-swap-oob="innerHTML">{load_more_trigger}</div>
        <div id="visibleCount" hx-swap-oob="innerHTML">{len(bookmarks_to_render)}</div>
        <div id="totalCount" hx-swap-oob="innerHTML">{total_count_for_filters}</div>
        """
        self._send_html_response(200, html_response)

    def serve_bookmarks_scroll_ui(self, search_query=None, hide_read=False, sort_order='desc', filter_type=None, limit=DEFAULT_PAGE_SIZE, offset=0):
        """
        API that returns additional bookmarks for infinite scrolling.
        Returns only the new items and the next "load more" trigger.
        """
        # Ensure types are correct, as they come from a query string
        limit = int(limit) if limit is not None else DEFAULT_PAGE_SIZE
        offset = int(offset) if offset is not None else 0
        hide_read = str(hide_read).lower() == 'true'
        bookmarks_raw = self.get_bookmarks(self.get_current_user(), limit=limit + 1, offset=offset, search_query=search_query, hide_read=hide_read, sort_order=sort_order, filter_type=filter_type)
        
        has_more = len(bookmarks_raw) > limit
        bookmarks_to_render = bookmarks_raw[:limit]
        
        lang_code = self.get_user_language()
        translations = load_translations(lang_code)

        # Render the actual bookmarks
        rendered_cards = render_bookmarks(bookmarks_to_render, translations)
        rendered_compact = render_bookmarks_compact(bookmarks_to_render, translations)

        # Build the "load more" trigger for the next page
        load_more_trigger = ""
        current_total = offset + len(bookmarks_to_render)
        if has_more:
            next_offset = offset + len(bookmarks_to_render)
            load_more_trigger = f"""
            <div id="loadMoreTrigger" hx-get="/ui/bookmarks/scroll"
                 hx-trigger="revealed"
                 hx-swap="outerHTML"
                 hx-indicator="#loadingIndicator"
                 :hx-vals="JSON.stringify({{'offset': {next_offset}, 'limit': {limit}, 'sort_order': '{sort_order}', 'search_query': '{search_query or ''}', 'hide_read': {str(hide_read).lower()}, 'filter_type': '{filter_type or ''}'}})"
                 class="load-more-trigger">
                {translations.get('loading', 'Loading more bookmarks...')}
            </div>
            """
        else:
            load_more_trigger = f"""
            <div id="loadMoreTrigger" class="load-more-trigger no-more-items">
                {translations.get('all_bookmarks_loaded', 'All bookmarks have been loaded.')}
            </div>
            """

        # We return the new bookmarks to append, and the updated loadMoreTrigger
        # The visibleCount also needs to be updated.
        html_response = f"""
        <div id="bookmarksGrid" hx-swap-oob="beforeend">{rendered_cards}</div>
        <div id="bookmarksCompact" hx-swap-oob="beforeend">{rendered_compact}</div>
        <div id="loadMoreContainer" hx-swap-oob="innerHTML">{load_more_trigger}</div>
        <span id="visibleCount" hx-swap-oob="innerHTML">{current_total}</span>
        """
        self._send_html_response(200, html_response)

    def serve_export_csv(self):
        """
        Exports all bookmarks for the current user to a CSV file.
        """
        user_id = self.get_current_user()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return

        try:
            # Fetch all bookmarks without pagination
            bookmarks = self.get_bookmarks(user_id, limit=-1)

            # Send headers for file download
            from io import StringIO
            # Use StringIO with newline='' as recommended by Python's csv module documentation
            # This correctly handles multiline fields.
            output = StringIO(newline='')
            writer = csv.writer(output, quoting=csv.QUOTE_ALL)

            # Write header
            header = ['id', 'url', 'title', 'description', 'image_url', 'domain', 'saved_at', 'telegram_user_id', 'telegram_message_id', 'comments_url', 'is_read']
            writer.writerow(header)

            # Write data rows, manually sanitizing fields to prevent issues.
            def sanitize_field(field):
                if field is None:
                    return ""
                # Replace quotes with double quotes and remove newlines to ensure single-line rows.
                return str(field).replace('"', '""').replace('\n', ' ').replace('\r', ' ')

            for row in bookmarks:
                sanitized_row = [sanitize_field(field) for field in row]
                writer.writerow(sanitized_row)

            csv_data = output.getvalue().encode('utf-8')
            
            self.send_response(200)
            self._send_security_headers()
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', 'attachment; filename="bookmarks.csv"')
            self.send_header('Content-Length', str(len(csv_data)))
            self.end_headers()
            self.wfile.write(csv_data)
        except Exception as e:
            logger.error(f"Error exporting CSV for user {user_id}: {e}")
            # Cannot send error response if headers are already sent

    def delete_bookmark(self, bookmark_id):
        """
        Deletes a bookmark from the database given its `bookmark_id`.

        Responds with JSON:
          - 200 {"status": "deleted"} in caso di successo
          - 500 {"error": "..."} in caso di errore

        Opens an SQLite connection, executes DELETE, and closes the connection.
        """
        try:
            with db_connection() as cursor:
                cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            self._send_json_response(200, {"status": "deleted"})
        except sqlite3.Error as e:
            self._send_error_response(500, str(e))

    def update_bookmark(self, bookmark_id):
        """
        Updates the fields of an existing bookmark.

        Behavior:
          - reads JSON from the request body (Content-Length)
          - only considers allowed fields: url, title, description,
            image_url, comments_url, telegram_user_id, telegram_message_id
          - if `url` is provided, it also updates the `domain` field via extract_domain
          - executes UPDATE on SQLite and responds with 200 on success

        Handled errors:
          - 400 if the body is empty or contains no allowed fields
          - 409 if a uniqueness constraint is violated (URL already exists)
          - 500 for generic errors
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
                cursor.execute(f"UPDATE bookmarks SET {set_clause} WHERE id = ? AND user_id = ?", params + [self.get_current_user()])

                # After the update, retrieve the updated bookmark to return it
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
        Sets the `is_read` flag for a bookmark.

        Behavior:
          - optionally reads JSON from the body with the key 'is_read' (true/false)
          - if not provided, sets is_read = 1 (read)
          - updates the record in the DB and responds with JSON containing the resulting state: {"status": "ok", "is_read": <0|1>}

        Responds with 500 with the error message in case of an error.
        """
        try:
            # Reads the request body to determine the desired state.
            # If the body is absent, the default action is to mark as read (is_read=1).
            content_length = int(self.headers.get('Content-Length', 0))
            is_read = 1
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                if 'is_read' in data:
                    is_read = 1 if data.get('is_read') else 0

            with db_connection() as cursor:
                cursor.execute("UPDATE bookmarks SET is_read = ? WHERE id = ? AND user_id = ?", (int(is_read), bookmark_id, self.get_current_user()))
            self._send_json_response(200, {'status': 'ok', 'is_read': is_read})

        except sqlite3.Error as e:
            self._send_error_response(500, str(e))

    def add_bookmark(self):
        """
        Adds a new bookmark to the database by reading JSON from the body.

        Expected fields in JSON: url (required), title, description,
        image_url, telegram_user_id, telegram_message_id, comments_url.

        Behavior:
          - validates the presence of the url
          - automatically extracts and saves the domain
          - checks for uniqueness constraint on the URL -> responds 409 if it already exists
          - inserts the record and responds with 201 on success

        Handled errors: 400 (bad request), 409 (duplicate URL), 500 (other)
        """
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            url = data.get('url', '').strip()
            if not url:
                raise ValueError("URL is required")

            user_id = self.get_current_user()
            # Extract domain automatically
            domain = extract_domain(url)

            with db_connection() as cursor:
                # Check if URL already exists for this user
                cursor.execute("SELECT id FROM bookmarks WHERE url = ? AND user_id = ?", (url, user_id))
                if cursor.fetchone():
                    self._send_error_response(409, "URL already exists")
                    return

                cursor.execute("""
                    INSERT INTO bookmarks (user_id, url, title, description, image_url, domain, telegram_user_id, telegram_message_id, comments_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    url,
                    data.get('title'),
                    data.get('description'),
                    data.get('image_url'),
                    domain,
                    data.get('telegram_user_id') if data.get('telegram_user_id') else None,
                    data.get('telegram_message_id') if data.get('telegram_message_id') else None,
                    data.get('comments_url')
                ))

                new_bookmark_id = cursor.lastrowid
                cursor.execute("""
                    SELECT id, url, title, description, image_url, domain,
                        datetime(saved_at, 'localtime') as saved_at,
                        telegram_user_id, telegram_message_id, comments_url,
                        COALESCE(is_read, 0) as is_read
                    FROM bookmarks WHERE id = ?
                """, (new_bookmark_id,))
                new_bookmark_tuple = cursor.fetchone()

            if not new_bookmark_tuple:
                self._send_error_response(500, "Failed to retrieve newly created bookmark")
                return

            new_bookmark = dict(zip(['id', 'url', 'title', 'description', 'image_url', 'domain', 'saved_at', 'telegram_user_id', 'telegram_message_id', 'comments_url', 'is_read'], new_bookmark_tuple))
            self._send_json_response(201, new_bookmark)

        except ValueError as e:
            self._send_error_response(400, str(e))
        except sqlite3.IntegrityError:
            self._send_error_response(409, "URL already exists")
        except Exception as e:
            logger.error(f"Error adding bookmark: {e}")
            self._send_error_response(500, "An internal error occurred")

    def scrape_metadata(self):
        """
        Scrapes metadata from a URL provided in the request body.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response(400, "Request body is empty")
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            url = data.get('url')

            if not url:
                self._send_error_response(400, "URL is required")
                return

            metadata = get_article_metadata(url)
            self._send_json_response(200, metadata)

        except Exception as e:
            logger.error(f"Error scraping metadata for URL {data.get('url', '')}: {e}")
            self._send_error_response(500, "Failed to scrape metadata")

    def get_total_bookmark_count(self, user_id, filter_type=None, hide_read=False, search_query=None):
        """Retrieves the total number of bookmarks from the database."""
        try:
            with db_connection() as cursor: # Pass search_query to _build_query_parts
                query, params = self._build_query_parts(user_id, filter_type, hide_read, search_query)
                cursor.execute(f"SELECT COUNT(*) FROM bookmarks WHERE {query}", params)
                count = cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error(f"Database error during count: {e}")
            return 0

    def _build_query_parts(self, user_id, filter_type=None, hide_read=False, search_query=None):
        """
        Builds the WHERE clauses and parameters for bookmark queries.
        Args:
            user_id (int): The ID of the current user.
            filter_type (str, optional): Filter for 'telegram', 'hn', 'recent'.
            hide_read (bool, optional): If True, excludes read bookmarks.
            search_query (str, optional): Text search term.

        Returns:
            tuple: A string with the WHERE clauses and a list of parameters.
        """
        where_clauses = ["user_id = ?"]
        params = [user_id]

        if filter_type == 'recent':
            where_clauses.append("saved_at >= datetime('now', '-7 days')")

        if hide_read:
            where_clauses.append("is_read = 0")

        if search_query:
            where_clauses.append("(title LIKE ? OR description LIKE ? OR url LIKE ? OR domain LIKE ?)")
            params.extend([f'%{search_query}%'] * 4)

        return " AND ".join(where_clauses), params

    def get_bookmarks(self, user_id, limit=20, offset=0, filter_type=None, hide_read=False, search_query=None, sort_order='desc'):
        """
        Retrieves bookmarks from the database, applying optional filters and search.
        """
        try:
            with db_connection() as cursor:
                # Validate sort_order to prevent SQL injection
                if sort_order not in ['asc', 'desc']:
                    sort_order = 'desc' # Default to desc if invalid value is provided
                order = sort_order.upper()
                where_clause, params = self._build_query_parts(user_id, filter_type, hide_read, search_query)

                limit_clause = "LIMIT ? OFFSET ?" if limit != -1 else ""
                query_params = params + [limit, offset] if limit != -1 else params

                query = """
                    SELECT id, url, title, description, image_url, domain,
                        datetime(saved_at, 'localtime') as saved_at,
                        telegram_user_id, telegram_message_id, comments_url,
                        COALESCE(is_read, 0) as is_read
                    FROM bookmarks
                    WHERE {where_clause}
                    ORDER BY saved_at {order}
                    {limit_clause}
                """.format(where_clause=where_clause, order=order, limit_clause=limit_clause)
                cursor.execute(query, query_params)

                bookmarks = cursor.fetchall()
            return bookmarks

        except sqlite3.Error as e:
            logger.error(f"Database error fetching bookmarks: {e}")
            return []

def create_self_signed_cert(cert_file_path, key_file_path):
    """
    Creates a self-signed certificate (if it doesn't exist) using OpenSSL.

    Produces two files: KEY_FILE (private key) and CERT_FILE (certificate).
    If OpenSSL is not available or the command fails, execution terminates.
    """
    # This function requires 'openssl' in the system's PATH
    import subprocess
    if os.path.exists(cert_file_path) and os.path.exists(key_file_path):
        logger.info(f"Existing certificates found: {cert_file_path}, {key_file_path}")
        return

    logger.info("Creazione certificato self-signed con chiave RSA 2048-bit...")

    try:
        # First, generate the 2048-bit RSA private key
        subprocess.run([
            'openssl', 'genrsa',
            '-out', key_file_path,
            '2048'
        ], check=True, capture_output=True)

        # Then, generate the certificate
        subprocess.run([
            'openssl', 'req', '-new', '-x509',
            '-key', key_file_path,
            '-out', cert_file_path,
            '-days', '365',
            '-subj', '/C=IT/ST=Italy/L=Rome/O=LocalServer/CN=localhost'
        ], check=True, capture_output=True)
        logger.info("✅ Certificate created successfully!")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error creating certificate: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("❌ OpenSSL not found in the system's PATH")
        sys.exit(1)

def main():
    """
    Main entry-point that starts the web server.

    Main actions:
      - initializes the DB (init_database)
      - configures HTTPServer (HTTP by default, HTTPS with --https flag)
      - starts the serve_forever loop

    Handles KeyboardInterrupt to shut down the server gracefully.
    """
    parser = argparse.ArgumentParser(description="HackerNews Bookmarks Web Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--https', action='store_true', help='Enable HTTPS mode (default is HTTP on port 80)')
    parser.add_argument('--port', type=int, help='Specify the port for the server to listen on')
    args = parser.parse_args()

    # Initialize the database only after parsing args, so --help doesn't trigger it.
    logger.info("Initializing database...")
    init_database()

    # Get the local IP
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "IP_NOT_AVAILABLE"

    # Determine port based on arguments
    if args.port:
        port = args.port
    else:
        if args.https:
            port = 443  # Default HTTPS port
        else:
            port = 80   # Default HTTP port


    if args.https:
        # --- HTTPS Mode ---
        protocol = "https"
        le_domain = os.getenv('LE_DOMAIN', None)
        logger.info(f"LE_DOMAIN letto come '{le_domain}'")

        if le_domain:
            le_cert_dir = f'/etc/letsencrypt/live/{le_domain}'
            le_fullchain = os.path.join(le_cert_dir, 'fullchain.pem')
            le_privkey = os.path.join(le_cert_dir, 'privkey.pem')

            if os.path.exists(le_fullchain) and os.path.exists(le_privkey):
                logger.info(f"Found Let's Encrypt certificates: {le_cert_dir}")
                cert_file = le_fullchain
                key_file = le_privkey
            else:
                logger.warning(f"LE_DOMAIN is set but certificates were not found in {le_cert_dir}. Falling back to self-signed certs.")
                le_domain = None

        if not le_domain:
            logger.info("Using local self-signed certificates.")
            cert_dir = os.path.join(SCRIPT_DIR, 'certs')
            os.makedirs(cert_dir, exist_ok=True)
            cert_file = os.path.join(cert_dir, 'server.pem')
            key_file = os.path.join(cert_dir, 'server.key')
            if not (os.path.exists(cert_file) and os.path.exists(key_file)):
                create_self_signed_cert(cert_file, key_file)

        server_address = ('', port)
        httpd = HTTPServer(server_address, BookmarkHandler)

        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(cert_file, key_file)
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            logger.info(f"🔒 Certificate: {os.path.abspath(cert_file)}")
        except ssl.SSLError as e:
            logger.error(f"❌ Errore SSL: {e}")
            return
    else:
        # --- HTTP Mode (Default) ---
        protocol = "http"
        server_address = ('', port)
        httpd = HTTPServer(server_address, BookmarkHandler)

    access_url = f"{protocol}://localhost:{port}"

    logger.info(f"""
🚀 Server started in {protocol.upper()} mode!

📍 Access from:
   • {access_url}
   • {protocol}://{local_ip}:{port}

📁 Database: {os.path.abspath(DB_PATH)}

✨ NEW FEATURES:
   • ➕ Hidden form (show on request)
   • 📋 Cards View (detailed)
   • 📄 Compact View (dense list)
   • 🔍 Search and filters for both views
   • 📱 Telegram Integration
   • 🗞️ HackerNews Links

Press Ctrl+C to stop the server.
    """)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n🛑 Server stopped gracefully")
        httpd.shutdown()

if __name__ == '__main__':
    # Add the project root to the path to import the shared library
    sys.path.append(os.path.dirname(SCRIPT_DIR))
    try:
        from shared.database import init_database # Import remains here
        # Start the server
        main()

    except ImportError:
        logger.error("ERROR: Could not import database logic. Make sure the project structure is correct.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected ERROR during startup: {e}")
        sys.exit(1)
