"""
Modulo per la generazione dell'HTML della pagina web.
"""

def get_login_page(error=None):
    """Genera l'HTML per la pagina di login."""
    error_html = f'<div class="login-error">{error}</div>' if error else ''
    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Zitzu's Bookmarks</title>
    <link rel="stylesheet" href="/static/style.css">
    <style>
        body {{ display: flex; align-items: center; justify-content: center; }}
        .login-container {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }}
        .login-container h1 {{ margin-top: 0; }}
        .login-error {{ background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin-bottom: 15px; text-align: center; }}
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Login</h1>
        {error_html}
        <form action="/login" method="post">
            <div class="form-group"><label for="username">Username</label><input type="text" id="username" name="username" required></div>
            <div class="form-group"><label for="password">Password</label><input type="password" id="password" name="password" required></div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Accedi</button>
        </form>
    </div>
</body>
</html>
"""

def get_html(self, bookmarks, version="N/A", total_count=0, search_query=None):
    # Funzione di escape per l'HTML per evitare problemi con le virgolette nei dati
    def escape_html(text):
        if text is None:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')

    search_value = escape_html(search_query)

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zitzu's HackerNews Bot</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>📚 Zitzu's Bookmarks Bot</h1>
        
        <div class="search-container">
            <input type="text" class="search-box" id="searchBox" placeholder="🔍 Cerca nei bookmark..." value="{search_value}">
            <button type="button" id="clearSearchBtn" class="clear-search-btn" title="Cancella ricerca">&times;</button>
        </div>

        <!-- Controlli vista -->
        <div class="view-controls">
            <button type="button" class="view-btn add-bookmark-btn" onclick="openAddModal()">
                ➕ Aggiungi Bookmark
            </button>
            <button type="button" class="view-btn" id="viewToggleBtn" title="Cambia vista">📄 Vista Compatta</button>
            <button type="button" class="view-btn" id="themeToggleBtn" title="Cambia tema">🌙</button>
            <span><small>v{version}</small></span>
        </div>

        <!-- Filtri speciali -->
        <div class="special-filters">
            <button class="filter-btn" onclick="filterSpecial('recent', event)">🕐 Ultimi 7 giorni</button>
            <button class="filter-btn" id="hideReadBtn" onclick="toggleHideRead()">🙈 Nascondi Letti</button>
            <a href="/logout" class="filter-btn">🚪 Logout</a>
        </div>

        <div class="filter-bar" id="filterBar">
            <!-- I filtri verranno popolati dinamicamente -->
        </div>

        <div class="stats">
            <strong id="visibleCount">{len(bookmarks)}</strong> di <strong id="totalCount">{total_count}</strong> bookmark totali
        </div>

        <!-- Vista normale (cards) -->
        <div class="bookmarks-grid" id="bookmarksGrid">
            {self.render_bookmarks(bookmarks)}
        </div>

        <!-- Vista compatta -->
        <div class="bookmarks-compact" id="bookmarksCompact">
            {self.render_bookmarks_compact(bookmarks)}
        </div>

        <div id="loadingIndicator">Caricamento...</div>

        <footer>
            <p>Zitzu's Bookmarks Bot - v{version}</p>
        </footer>

        <!-- Modale per la modifica -->
        <div id="editModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 id="modalTitle">Modifica Bookmark</h3>
                    <span class="close-btn" onclick="closeEditModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <form id="editBookmarkForm">
                        <input type="hidden" id="edit-id" name="id">
                        <div class="form-group form-group-with-button">
                            <label for="edit-url">URL: *</label>
                            <div class="input-with-button">
                                <input type="url" id="edit-url" name="url" required>
                                <button type="button" class="btn btn-icon" id="scrapeBtn" title="Estrai metadati dall'URL">✨</button>
                            </div>
                        </div>
                        <div class="form-group" style="grid-column: 1 / -1;">
                            <label for="edit-title">Titolo:</label>
                            <input type="text" id="edit-title" name="title">
                        </div>
                        <div class="form-group">
                            <label for="edit-image_url">URL Immagine:</label>
                            <input type="url" id="edit-image_url" name="image_url">
                        </div>
                        <div class="form-group">
                            <label for="edit-description">Descrizione:</label>
                            <textarea id="edit-description" name="description" rows="3"></textarea>
                        </div>
                        <div class="form-group" style="grid-column: 1 / -1;">
                            <label for="edit-comments_url">URL HackerNews:</label>
                            <input type="url" id="edit-comments_url" name="comments_url">
                        </div>
                        <div class="form-group">
                            <label for="edit-telegram_user_id">Telegram User ID:</label>
                            <input type="number" id="edit-telegram_user_id" name="telegram_user_id">
                        </div>
                        <div class="form-group form-group-checkbox">
                            <label><input type="checkbox" id="edit-is_read" name="is_read"> Già letto</label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="submit" form="editBookmarkForm" class="btn btn-primary">Salva Modifiche</button>
                    <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Annulla</button>
                </div>
            </div>
        </div>
    </div>

    <button type="button" id="backToTopBtn" title="Torna su">↑</button>

    <script>
        // Pass initial data from server to JavaScript
        window.APP_CONFIG = {{
            'initialCount': {len(bookmarks)},
            'totalCount': {total_count}
        }};
    </script>
    <script src="/static/app.js" defer></script>
</body>
</html>"""