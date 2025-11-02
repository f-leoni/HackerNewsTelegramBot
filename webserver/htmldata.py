"""
Module for generating the web page HTML.
"""
import json

def get_login_page(self, error=None):
    """Generates the HTML for the login page."""
    error_html = f'<div class="login-error">{error}</div>' if error else ''
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Zitzu's Bookmarks</title>
    <link rel="icon" href="/static/img/favicon.svg" type="image/svg+xml">
    <link rel="alternate icon" href="/favicon.ico" type="image/x-icon">
    <link rel="apple-touch-icon" href="/static/img/favicon.svg">
    <link rel="stylesheet" href="/static/style.css">
    <style nonce="{self.nonce}">
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
            <button type="submit" class="btn btn-primary w-100">Login</button>
        </form>
    </div>
</body>
</html>
"""

def get_html(self, bookmarks, version="N/A", total_count=0, translations={}, search_query=None):
    # HTML escape function to avoid issues with quotes in data
    def escape_html(text):
        if text is None:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')

    search_value = escape_html(search_query)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{translations.get('page_title', "Zitzu's Bookmarks")}</title>
    <link rel="icon" href="/static/img/favicon.svg" type="image/svg+xml">
    <link rel="alternate icon" href="/favicon.ico" type="image/x-icon">
    <link rel="apple-touch-icon" href="/static/img/favicon.svg">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>{translations.get('header', 'Bookmarks')}</h1>
        
        <div class="search-container">
            <input type="text" class="search-box" id="searchBox" placeholder="{translations.get('search_placeholder', 'Search...')}" value="{search_value}" title="{translations.get('tooltip_search', 'Search...')}">
            <button type="button" id="clearSearchBtn" class="clear-search-btn" title="{translations.get('tooltip_clear_search', 'Clear search')}">&times;</button>
        </div>

        <!-- View controls -->
        <div class="view-controls">
            <button type="button" class="view-btn add-bookmark-btn" id="addBookmarkBtn" title="{translations.get('tooltip_add_bookmark', 'Add bookmark')}">
                {translations.get('add_bookmark', 'Add Bookmark')}
            </button>
            <button type="button" class="view-btn" id="sortToggleBtn" title="{translations.get('tooltip_change_sort', 'Change sort order')}">{translations.get('sort_newest', 'Newest First')}</button>
            <button type="button" class="view-btn" id="viewToggleBtn" title="{translations.get('tooltip_change_view', 'Change view')}">{translations.get('compact_view', 'Compact View')}</button>
            <button type="button" class="view-btn" id="themeToggleBtn" title="{translations.get('tooltip_change_theme', 'Change theme')}">{translations.get('dark_mode', 'Dark Mode')}</button>
            <select id="langSelector" class="view-btn" title="{translations.get('tooltip_change_language', 'Change language')}">
                <option value="en" {'selected' if self.get_user_language() == 'en' else ''}>🇬🇧 English</option>
                <option value="it" {'selected' if self.get_user_language() == 'it' else ''}>🇮🇹 Italiano</option>
            </select>
            <span><small>v{version}</small></span>
        </div>

        <!-- Special filters -->
        <div class="special-filters">
            <button class="filter-btn" data-filter="recent" title="{translations.get('tooltip_filter_7_days', 'Filter...')}">{translations.get('filter_7_days', 'Last 7 days')}</button>
            <button class="filter-btn" id="hideReadBtn" title="{translations.get('tooltip_toggle_read', 'Toggle read...')}">{translations.get('hide_read', 'Hide Read')}</button>
            <a href="/api/export/csv" class="filter-btn" download="bookmarks.csv" target="_blank" title="{translations.get('tooltip_export_csv', 'Export...')}">{translations.get('export_csv', 'Export CSV')}</a>
            <a href="/logout" class="filter-btn" title="{translations.get('tooltip_logout', 'Logout...')}">{translations.get('logout', 'Logout')}</a>
        </div>

        <div class="filter-bar" id="filterBar">
            <!-- Filters will be populated dynamically -->
        </div>

        <div class="stats">
            <strong id="visibleCount">{len(bookmarks)}</strong> {translations.get('visible_of_total', 'of')} <strong id="totalCount">{total_count}</strong> {translations.get('total_bookmarks', 'total bookmarks')}
        </div>

        <!-- Normal view (cards) -->
        <div class="bookmarks-grid" id="bookmarksGrid">
            {self.render_bookmarks(bookmarks, translations)}
        </div>

        <!-- Compact view -->
        <div class="bookmarks-compact" id="bookmarksCompact">
            {self.render_bookmarks_compact(bookmarks, translations)}
        </div>

        <div id="loadingIndicator">{translations.get('loading', 'Loading...')}</div>

        <footer>
            <p>Zitzu's Bookmarks Bot - v{version}</p>
        </footer>

        <!-- Edit modal -->
        <div id="editModal" class="modal hidden">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 id="modalTitle">{translations.get('modal_edit_title', 'Edit Bookmark')}</h3>
                    <span class="close-btn" id="closeModalBtn" title="{translations.get('tooltip_close_modal', 'Close')}">&times;</span>
                </div>
                <div class="modal-body">
                    <form id="editBookmarkForm">
                        <input type="hidden" id="edit-id" name="id">
                        <div class="form-group form-group-with-button">
                            <label for="edit-url">URL: *</label>
                            <div class="input-with-button">
                                <input type="url" id="edit-url" name="url" required title="{translations.get('tooltip_modal_url', 'URL...')}">
                                <button type="button" class="btn btn-icon" id="scrapeBtn" title="{translations.get('tooltip_scrape', 'Scrape...')}">✨</button>
                            </div>
                        </div>
                        <div class="form-group full-width-grid-column">
                            <label for="edit-title">Title:</label>
                            <input type="text" id="edit-title" name="title" title="{translations.get('tooltip_modal_title', 'Title...')}">
                        </div>
                        <div class="form-group">
                            <label for="edit-image_url">Image URL:</label>
                            <input type="url" id="edit-image_url" name="image_url" title="{translations.get('tooltip_modal_image', 'Image URL...')}">
                        </div>
                        <div class="form-group">
                            <label for="edit-description">Description:</label>
                            <textarea id="edit-description" name="description" rows="3" title="{translations.get('tooltip_modal_description', 'Description...')}"></textarea>
                        </div>
                        <div class="form-group full-width-grid-column">
                            <label for="edit-comments_url">HackerNews URL:</label>
                            <input type="url" id="edit-comments_url" name="comments_url" title="{translations.get('tooltip_modal_hn_url', 'HN URL...')}">
                        </div>
                        <div class="form-group">
                            <label for="edit-telegram_user_id">Telegram User ID:</label>
                            <input type="number" id="edit-telegram_user_id" name="telegram_user_id" title="{translations.get('tooltip_modal_user_id', 'User ID...')}">
                        </div>
                        <div class="form-group form-group-checkbox">
                            <label><input type="checkbox" id="edit-is_read" name="is_read" title="{translations.get('tooltip_modal_is_read', 'Already read...')}"> Already read</label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="submit" form="editBookmarkForm" class="btn btn-primary" title="{translations.get('tooltip_save_changes', 'Save...')}">{translations.get('save_changes', 'Save Changes')}</button>
                    <button type="button" class="btn btn-secondary" id="cancelModalBtn" title="{translations.get('tooltip_discard_changes', 'Cancel...')}">{translations.get('cancel', 'Cancel')}</button>
                </div>
            </div>
        </div>
    </div>

    <button type="button" id="backToTopBtn" title="{translations.get('tooltip_back_to_top', 'Back to top')}">↑</button>

    <script nonce="{self.nonce}">
        // Pass initial data from server to JavaScript
        window.APP_CONFIG = {{
            'initialCount': {len(bookmarks)},
            'totalCount': {total_count}
        }};
        window.TRANSLATIONS = {json.dumps(translations)};
    </script>
    <script src="/static/app.js" defer></script>
</body>
</html>"""