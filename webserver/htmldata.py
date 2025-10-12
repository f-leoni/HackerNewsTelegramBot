"""
Modulo per la generazione dell'HTML della pagina web.
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
        <h1>📚 Zitzu's Bookmarks Bot  - v{version}</h1>

        <input type="text" class="search-box" id="searchBox" placeholder="🔍 Cerca nei bookmark..." value="{search_value}">

        <!-- Controlli vista -->
        <div class="view-controls">
            <button type="button" class="view-btn add-bookmark-btn" onclick="openAddModal()">
                ➕ Aggiungi Bookmark
            </button>
            <button type="button" class="view-btn" id="viewToggleBtn" title="Cambia vista">📄 Vista Compatta</button>
            <button type="button" class="view-btn" id="themeToggleBtn" title="Cambia tema">🌙 Dark Mode</button>
        </div>

        <!-- Filtri speciali -->
        <div class="special-filters">
            <button class="filter-btn filter-telegram" onclick="filterSpecial('telegram', event)">📱 Solo Telegram</button>
            <button class="filter-btn filter-hn" onclick="filterSpecial('hn', event)">🗞️ Con HackerNews</button>
            <button class="filter-btn" onclick="filterSpecial('recent', event)">🕐 Ultimi 7 giorni</button>
            <button class="filter-btn" id="hideReadBtn" onclick="toggleHideRead()">🙈 Nascondi Letti</button>
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
                <span class="close-btn" onclick="closeEditModal()">&times;</span>
                <h3 id="modalTitle">Modifica Bookmark</h3>
                <form id="editBookmarkForm">
                    <input type="hidden" id="edit-id" name="id">
                    <div class="form-group">
                        <label>URL: *</label>
                        <input type="url" id="edit-url" name="url" required>
                    </div>
                    <div class="form-row">
                        <div class="form-group" style="grid-column: 1 / -1;">
                            <label>Titolo:</label>
                            <input type="text" id="edit-title" name="title">
                        </div>
                        <div class="form-group">
                            <label>URL Immagine:</label>
                            <input type="url" id="edit-image_url" name="image_url">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Descrizione:</label>
                        <textarea id="edit-description" name="description"></textarea>
                    </div>
                    <div class="form-row">
                        <div class="form-group" style="grid-column: 1 / -1;">
                            <label>URL HackerNews:</label>
                            <input type="url" id="edit-comments_url" name="comments_url">
                        </div>
                        <div class="form-group">
                            <label>Telegram User ID:</label>
                            <input type="number" id="edit-telegram_user_id" name="telegram_user_id">
                        </div>
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="edit-is_read" name="is_read"> Già letto</label>
                    </div>
                    <button type="submit" class="btn">Salva Modifiche</button>
                </form>
            </div>
        </div>
    </div>

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