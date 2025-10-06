"""
Modulo per la generazione dell'HTML della pagina web.
"""
#__version__ = "1.2"
def get_html(self, bookmarks, version="N/A", total_count=0):
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zitzu's HackerNews Bot</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 30px;
        }}

        h1 {{
            color: #333;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2.5em;
        }}

        .icon-btn {{
            background: transparent;
            border: none;
            font-size: 16px;
            cursor: pointer;
            padding: 6px;
            border-radius: 6px;
            transition: background-color 0.15s;
        }}

        .icon-btn:hover {{
            background: rgba(0,0,0,0.06);
        }}

        .icon-btn.delete {{ color: #c82333; }}
        .icon-btn.read {{ color: #28a745; }}

        .form-group {{
            margin-bottom: 15px;
        }}

        .form-group.full-width {{
            grid-column: 1 / -1;
        }}

        .form-group label {{
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
            font-size: 14px;
        }}

        .form-group input, .form-group textarea {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}

        .form-group textarea {{
            height: 60px;
            resize: vertical;
        }}

        .btn {{
            background: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }}

        .btn:hover {{
            background: #0056b3;
        }}

        /* Controlli vista */
        .view-controls {{
            display: flex;
            gap: 10px;
            justify-content: center;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}

        .add-bookmark-btn {{
            background: #28a745;
            color: white;
        }}

        .view-btn > img, .view-btn > svg, .view-btn::before {{
            font-size: 18px;
            line-height: 1;
            vertical-align: middle;
        }}

        .view-btn {{
            padding: 8px 12px;
            border: 2px solid #007bff;
            background: white;
            color: #007bff;
            border-radius: 8px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.15s ease;
            cursor: pointer;
            line-height: 1;
            min-height: 36px;
            min-width: 170px;
            white-space: nowrap;
            flex-shrink: 0;
            box-sizing: border-box;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }}

        .filter-btn, .btn-toggle {{
            flex-shrink: 0;
        }}

        .view-btn.active {{
            background: #007bff;
            color: white;
        }}

        .view-btn:hover {{
            background: #007bff;
            color: white;
        }}

        /* Vista normale (cards) */
        .bookmarks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}

        .bookmark-card {{
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .bookmark-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}

        .bookmark-header {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
        }}

        .bookmark-actions {{
            margin-left: auto;
            display: flex;
            gap: 8px;
            align-items: center;
        }}

        /* Azioni posizionate sopra il titolo (per cards) */
        .bookmark-actions-top {{
            display: flex;
            gap: 8px;
            align-items: center;
            margin-bottom: 8px;
            width: 100%;
            justify-content: flex-end;
        }}

        /* Compact view: actions above title */
        .compact-actions-top {{
            display: flex;
            gap: 6px;
            align-items: center;
            margin-bottom: 6px;
            flex-wrap: wrap;
            width: 100%;
            justify-content: flex-end;
        }}

        .bookmark-image {{
            width: 50px;
            height: 50px;
            border-radius: 8px;
            object-fit: cover;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
        }}

        .bookmark-info {{
            flex: 1;
            min-width: 0;
        }}

        /* Stack info vertically so action row can be right-aligned */
        .bookmark-info {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }}

        .bookmark-title {{
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 4px;
            color: #333;
            line-height: 1.3;
        }}

        .bookmark-domain {{
            color: #6c757d;
            font-size: 0.85em;
            font-weight: 500;
        }}

        /* Domain tags removed at user's request: hide them globally */
        .bookmark-domain, .compact-domain {{
            display: none !important;
        }}

        .bookmark-url {{
            color: #007bff;
            text-decoration: none;
            font-size: 0.9em;
            margin: 8px 0;
            display: block;
            word-break: break-all;
            line-height: 1.3;
        }}

        .bookmark-url:hover {{
            text-decoration: underline;
        }}

        .bookmark-description {{
            color: #666;
            font-size: 0.9em;
            line-height: 1.4;
            margin-bottom: 12px;
        }}

        .bookmark-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 12px;
            border-top: 1px solid #f0f0f0;
            font-size: 0.8em;
            color: #999;
        }}

        .bookmark-date {{
            font-weight: 500;
        }}

        /* Vista compatta */
        .bookmarks-compact {{
            display: none;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
        }}

        .bookmarks-compact.show {{
            display: block;
        }}

        .compact-item {{
            display: grid;
            grid-template-columns: 32px 1fr auto auto auto;
            gap: 12px;
            padding: 12px 16px;
            border-bottom: 1px solid #f0f0f0;
            align-items: center;
            transition: background-color 0.2s;
        }}

        .compact-item:hover {{
            background: #f8f9fa;
        }}

        .compact-item:last-child {{
            border-bottom: none;
        }}

        .compact-image {{
            width: 32px;
            height: 32px;
            border-radius: 6px;
            object-fit: cover;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }}

        .compact-content {{
            min-width: 0;
        }}

        .compact-title {{
            font-weight: 600;
            color: #333;
            margin-bottom: 2px;
            font-size: 16px;
            line-height: 1.2;
        }}

        .compact-url {{
            color: #007bff;
            text-decoration: none;
            font-size: 13px;
            word-break: break-all;
        }}

        .compact-url:hover {{
            text-decoration: underline;
        }}

        .compact-domain {{
            color: #6c757d;
            font-size: 12px;
            margin-top: 2px;
        }}

        .compact-date {{
            color: #999;
            font-size: 12px;
            text-align: right;
            white-space: nowrap;
        }}

        .compact-badges {{
            display: flex;
            gap: 4px;
        }}

        .telegram-badge {{
            background: #0088cc;
            color: white;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 500;
        }}

        .hn-link {{
            color: #ff6600;
            text-decoration: none;
            font-size: 12px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 2px;
        }}

        .hn-link:hover {{
            text-decoration: underline;
        }}

        /* Badge per vista normale */
        .bookmark-footer .telegram-badge {{
            padding: 3px 8px;
            font-size: 0.7em;
        }}

        .bookmark-footer .hn-link {{
            font-size: 0.8em;
            gap: 4px;
        }}

        .search-box {{
            width: 100%;
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 25px;
            margin-bottom: 20px;
            font-size: 16px;
        }}

        .search-box:focus {{
            outline: none;
            border-color: #007bff;
        }}

        .stats {{
            text-align: center;
            margin-bottom: 20px;
            color: #666;
        }}

        .filter-bar {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            padding: 6px 12px;
            border: 1px solid #dee2e6;
            background: white;
            border-radius: 20px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }}

        .filter-btn:hover {{
            background: #f8f9fa;
        }}

        .filter-btn.active {{
            background: #007bff;
            color: white;
            border-color: #007bff;
        }}

        .special-filters {{
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }}

        .filter-telegram {{
            background: #0088cc;
            color: white;
        }}

        .filter-hn {{
            background: #ff6600;
            color: white;
        }}

        footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            color: #999;
            font-size: 0.9em;
        }}

        #loadingIndicator {{
            text-align: center;
            padding: 20px;
            font-weight: 500;
            color: #666;
            display: none;
        }}


        @media (max-width: 768px) {{
            .bookmarks-grid {{
                grid-template-columns: 1fr;
            }}

            .form-row {{
                grid-template-columns: 1fr;
            }}

            .compact-item {{
                grid-template-columns: 32px 1fr;
                gap: 8px;
            }}

            .compact-date, .compact-badges {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Zitzu's Bookmarks Bot  - v{version}</h1>

        <input type="text" class="search-box" id="searchBox" placeholder="🔍 Cerca nei bookmark...">

        <!-- Controlli vista -->
        <div class="view-controls">
            <button type="button" class="view-btn add-bookmark-btn" onclick="openAddModal()">
                ➕ Aggiungi Bookmark
            </button>
            <button type="button" class="view-btn active" data-view="cards">📋 Vista Cards</button>
            <button type="button" class="view-btn" data-view="compact">📄 Vista Compatta</button>
            <span id="viewStatus" style="margin-left:12px; font-weight:600; color:#333">cards</span>
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
        // Switch vista
        function switchView(view) {{
            const cardsView = document.getElementById('bookmarksGrid');
            const compactView = document.getElementById('bookmarksCompact');
            const buttons = document.querySelectorAll('.view-btn');

            buttons.forEach(btn => btn.classList.remove('active'));

            // Find button matching view
            const activeBtn = document.querySelector(`.view-btn[data-view="${{view}}"]`);
            if (activeBtn) activeBtn.classList.add('active');

            if (view === 'cards') {{
                cardsView.style.display = 'grid';
                compactView.classList.remove('show');
            }} else {{
                cardsView.style.display = 'none';
                compactView.classList.add('show');
            }}

            const status = document.getElementById('viewStatus');
            if (status) status.textContent = view;

            // Riapplica tutti i filtri alla nuova vista
            applyAllFilters();
        }}

        // Imposta lo stato iniziale e aggiunge gli event listener al caricamento della pagina
        document.addEventListener('DOMContentLoaded', function() {{
            // Ripristina lo stato del filtro 'hideRead' dal localStorage
            const savedHideRead = localStorage.getItem('hideRead');
            hideRead = savedHideRead !== null ? JSON.parse(savedHideRead) : true;

            updateHideReadButton();
            applyAllFilters();

            // Aggiunge i listener per i pulsanti di cambio vista
            document.querySelectorAll('.view-btn[data-view]').forEach(btn => {{
                btn.addEventListener('click', () => {{
                    switchView(btn.dataset.view);
                }});
            }});
        }});

        function updateVisibleCount() {{
            const activeView = document.querySelector('.view-btn.active').dataset.view;
            const selector = activeView === 'cards' ? '.bookmark-card' : '.compact-item';
            const visibleItems = document.querySelectorAll(selector);
            let count = 0;
            visibleItems.forEach(item => {{
                if (window.getComputedStyle(item).display !== 'none') {{
                    count++;
                }}
            }});
            const countElement = document.getElementById('visibleCount');
            if (countElement) countElement.textContent = count;
        }}

        // Ricerca in tempo reale
        document.getElementById('searchBox').addEventListener('input', function(e) {{
            applyAllFilters();
        }});

        // Logica per nascondere i letti (default: true)
        let hideRead = true;
        function toggleHideRead() {{
            hideRead = !hideRead;
            localStorage.setItem('hideRead', hideRead); // Salva lo stato
            updateHideReadButton();

            // Svuota i contenitori e ricarica i dati dal server con il nuovo stato di hideRead
            document.getElementById('bookmarksGrid').innerHTML = '';
            document.getElementById('bookmarksCompact').innerHTML = '';
            currentOffset = 0;
            allLoaded = false;
            isLoading = false;
            
            loadMoreBookmarks();
        }}

        function updateHideReadButton() {{
            const btn = document.getElementById('hideReadBtn');
            btn.classList.toggle('active', hideRead);
            btn.textContent = hideRead ? '🙉 Mostra Letti' : '🙈 Nascondi Letti';
        }}

        function applyAllFilters() {{
            // Questa funzione ora gestisce solo la ricerca e il cambio di vista,
            // perché il filtro "hideRead" è gestito dal server.
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            const activeView = document.querySelector('.view-btn.active').dataset.view;

            document.querySelectorAll('.bookmark-card, .compact-item').forEach(item => {{
                const isCardViewItem = item.classList.contains('bookmark-card');
                const isCompactViewItem = item.classList.contains('compact-item');
                let isVisible = true;

                const searchText = item.dataset.searchText || '';
                if (!searchText.includes(searchTerm)) {{
                    isVisible = false;
                }}

                // Applica la visibilità in base alla vista attiva
                if (activeView === 'cards' && isCardViewItem) item.style.display = isVisible ? 'block' : 'none';
                else if (activeView === 'compact' && isCompactViewItem) item.style.display = isVisible ? 'grid' : 'none';
                else item.style.display = 'none';
            }});
            updateVisibleCount();

            // Dopo aver filtrato, controlla se è necessario caricare altri bookmark
            // perché la pagina potrebbe non essere più scrollabile.
            if (document.body.scrollHeight <= window.innerHeight && !isLoading && !allLoaded) {{
                loadMoreBookmarks();
            }}
        }}

        // Applica il filtro quando si cambia vista

        // Domain filters removed per user request (cleanup)

        let activeSpecialFilter = null;

        function filterSpecial(type, event) {{
            const clickedButton = event.target;
            const specialButtons = document.querySelectorAll('.special-filters .filter-btn');

            // Se il filtro cliccato è già attivo, lo disattiviamo
            if (clickedButton.classList.contains('active')) {{
                activeSpecialFilter = null;
                clickedButton.classList.remove('active');
            }} else {{
                // Altrimenti, disattiviamo gli altri e attiviamo quello cliccato
                specialButtons.forEach(btn => btn.classList.remove('active'));
                clickedButton.classList.add('active');
                activeSpecialFilter = type;
            }}

            // Svuota i contenitori dei bookmark
            document.getElementById('bookmarksGrid').innerHTML = '';
            document.getElementById('bookmarksCompact').innerHTML = '';

            // Resetta lo stato dell'infinite scroll
            currentOffset = 0;
            allLoaded = false;
            isLoading = false;
            const loadingIndicator = document.getElementById('loadingIndicator');
            loadingIndicator.textContent = 'Caricamento...';
            loadingIndicator.style.display = 'none';

            // Carica i primi risultati filtrati
            loadMoreBookmarks();
        }}

        // Logica per il modale di modifica
        const editModal = document.getElementById('editModal');
        const editForm = document.getElementById('editBookmarkForm');

        function openAddModal() {{
            editForm.reset();
            document.getElementById('modalTitle').textContent = 'Aggiungi Nuovo Bookmark';
            document.getElementById('edit-id').value = ''; // Assicura che l'ID sia vuoto
            editModal.style.display = 'block';
        }}

        function openEditModal(bookmark) {{
            document.getElementById('edit-id').value = bookmark.id;
            document.getElementById('edit-url').value = bookmark.url || '';
            document.getElementById('edit-title').value = bookmark.title || '';
            document.getElementById('edit-image_url').value = bookmark.image_url || '';
            document.getElementById('edit-description').value = bookmark.description || '';
            document.getElementById('edit-comments_url').value = bookmark.comments_url || '';
            document.getElementById('edit-telegram_user_id').value = bookmark.telegram_user_id || '';
            document.getElementById('edit-is_read').checked = bookmark.is_read == 1;
            document.getElementById('modalTitle').textContent = 'Modifica Bookmark';
            editModal.style.display = 'block';
        }}

        function closeEditModal() {{
            editModal.style.display = 'none';
        }}

        window.onclick = function(event) {{
            if (event.target == editModal) {{
                closeEditModal();
            }}
        }}

        editForm.addEventListener('submit', async function(e) {{
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            const id = data.id;

            const isAdding = !id;
            const method = isAdding ? 'POST' : 'PUT';
            const url = isAdding ? '/api/bookmarks' : '/api/bookmarks/' + id;

            // Gestisci checkbox
            data.is_read = document.getElementById('edit-is_read').checked ? 1 : 0;

            // Rimuovi campi vuoti e l'ID dal corpo della richiesta
            Object.keys(data).forEach(key => {{
                if (data[key] === '') {{
                    delete data[key];
                }}
            }});
            // L'ID non deve mai essere nel body
            delete data.id;
            // In modalità aggiunta, non inviare il campo is_read se non è spuntato
            if (isAdding && !data.is_read) {{
                delete data.is_read;
            }}

            try {{
                const response = await fetch(url, {{
                    method: method,
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }});

                if (response.ok) {{
                    location.reload();
                }} else {{
                    const error = await response.json();
                    alert("Errore: " + (error.error || 'Errore sconosciuto'));
                }}
            }} catch (error) {{
                alert("Errore di connessione");
            }}
        }});


        // API actions: delete and mark read
        async function bookmarkDelete(id) {{
            if (!confirm('Sei sicuro di voler eliminare questo bookmark?')) return;
            try {{
                const res = await fetch('/api/bookmarks/' + id, {{ method: 'DELETE' }});
                if (res.ok) location.reload(); else alert("Errore durante la cancellazione");
            }} catch (e) {{
                alert("Errore di connessione");
            }}
        }}

        async function bookmarkMarkRead(id) {{
            const item = document.querySelector(`.bookmark-card[data-id='${{id}}']`) || document.querySelector(`.compact-item[data-id='${{id}}']`);
            const isCurrentlyRead = item ? item.dataset.isRead === '1' : false;
            const newReadState = !isCurrentlyRead;

            try {{
                const response = await fetch('/api/bookmarks/' + id + '/read', {{ 
                    method: 'PUT',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ is_read: newReadState }})
                }});
                if (response.ok) {{
                    // Aggiornamento dinamico senza ricaricare la pagina
                    const updatedBookmarkData = await response.json();
                    const newReadStatus = updatedBookmarkData.is_read;

                    // Trova entrambi gli elementi (card e compact)
                    const cardItem = document.querySelector(`.bookmark-card[data-id='${{id}}']`);
                    const compactItem = document.querySelector(`.compact-item[data-id='${{id}}']`);

                    [cardItem, compactItem].forEach(el => {{
                        if (!el) return;

                        // Aggiorna l'attributo data-is-read
                        el.dataset.isRead = newReadStatus;

                        // Aggiorna l'icona e il titolo del pulsante
                        const readButton = el.querySelector('.icon-btn.read');
                        if (readButton) {{
                            const isRead = newReadStatus == 1;
                            readButton.title = isRead ? "Segna come non letto" : "Segna come letto";
                            readButton.innerHTML = isRead
                                ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>`
                                : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
                        }}

                        // Se stiamo nascondendo i letti, fai sparire l'elemento appena marcato
                        if (hideRead && newReadStatus == 1) {{
                            el.style.display = 'none';
                        }}
                    }});
                    updateVisibleCount();
                }} else {{
                    alert("Errore durante l'operazione");
                }}
            }} catch (e) {{
                alert("Errore di connessione");
            }}
        }}

        // Stili per il modale
        const modalStyle = `
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                overflow: auto;
                background-color: rgba(0,0,0,0.5);
            }}
            .modal-content {{
                background-color: #fefefe;
                margin: 5% auto;
                padding: 20px;
                border: 1px solid #888;
                width: 80%;
                max-width: 700px;
                border-radius: 8px;
                position: relative;
                animation: slideDown 0.3s ease-out;
            }}
            .modal-content .form-row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }}
            .modal-content .form-group input, .modal-content .form-group textarea {{
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }}
            .close-btn {{
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }}
            .close-btn:hover, .close-btn:focus {{
                color: black;
            }}
        `;
        const styleSheet = document.createElement("style");
        styleSheet.type = "text/css";
        styleSheet.innerText = modalStyle;
        document.head.appendChild(styleSheet);

        // --- Funzioni di Rendering Client-Side ---
        function renderBookmarkCard(bookmark) {{
            const imageHtml = bookmark.image_url
                ? `<img src="${{bookmark.image_url}}" alt="Preview" class="bookmark-image" onerror="this.style.display='none'">`
                : '<div class="bookmark-image" style="display: flex; align-items: center; justify-content: center; background: #f8f9fa; color: #6c757d;">🔗</div>';
            const telegramBadge = bookmark.telegram_user_id ? '<span class="telegram-badge">📱 Telegram</span>' : '';
            const hnLink = bookmark.comments_url ? `<a href="${{bookmark.comments_url}}" target="_blank" class="hn-link">🗞️ HN</a>` : '';
            const bookmarkJson = JSON.stringify(bookmark).replace(/"/g, '&quot;');
            const searchText = `${{bookmark.url || ''}} ${{bookmark.title || ''}} ${{bookmark.description || ''}} ${{bookmark.domain || ''}}`.toLowerCase();

            const isRead = bookmark.is_read == 1;
            const readButtonTitle = isRead ? "Segna come non letto" : "Segna come letto";
            const readButtonIcon = isRead 
                ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>` // Icona "già letto" (doppio check)
                : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`; // Icona "da leggere"

            return `
            <div class="bookmark-card" data-id="${{bookmark.id}}" data-is-read="${{bookmark.is_read}}" data-search-text="${{searchText}}">
                <div class="bookmark-header">
                    ${{imageHtml}}
                    <div class="bookmark-info">
                        <div class="bookmark-actions-top">
                            ${{telegramBadge}}
                            ${{hnLink}}
                            <button class="icon-btn read" title="${{readButtonTitle}}" onclick="bookmarkMarkRead(${{bookmark.id}})">${{readButtonIcon}}</button>
                            <button class="icon-btn edit" title="Modifica" onclick='openEditModal(${{bookmarkJson}})'><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                            <button class="icon-btn delete" title="Elimina" onclick="bookmarkDelete(${{bookmark.id}})"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 6h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 6v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                        </div>
                        <div class="bookmark-title">${{bookmark.title || 'Senza titolo'}}</div>
                    </div>
                </div>
                <a href="${{bookmark.url}}" target="_blank" class="bookmark-url">${{bookmark.url}}</a>
                <div class="bookmark-description">${{bookmark.description || 'Nessuna descrizione'}}</div>
                <div class="bookmark-footer">
                    <span class="bookmark-date">${{bookmark.saved_at}}</span>
                </div>
            </div>`;
        }}

        function renderBookmarkCompactItem(bookmark) {{
            const imageHtml = bookmark.image_url
                ? `<img src="${{bookmark.image_url}}" alt="Preview" class="compact-image" onerror="this.innerHTML='🔗'">`
                : '<div class="compact-image">🔗</div>';
            let badgesHtml = '';
            if (bookmark.telegram_user_id) badgesHtml += '<span class="telegram-badge">TG</span>';
            if (bookmark.comments_url) badgesHtml += `<a href="${{bookmark.comments_url}}" target="_blank" class="hn-link">HN</a>`;
            if (badgesHtml) badgesHtml = `<div class="compact-badges">${{badgesHtml}}</div>`;
            const shortDate = (bookmark.saved_at || '').split(' ')[0];
            const bookmarkJson = JSON.stringify(bookmark).replace(/"/g, '&quot;');
            const searchText = `${{bookmark.url || ''}} ${{bookmark.title || ''}} ${{bookmark.description || ''}} ${{bookmark.domain || ''}}`.toLowerCase();

            const isRead = bookmark.is_read == 1;
            const readButtonTitle = isRead ? "Segna come non letto" : "Segna come letto";
            const readButtonIcon = isRead 
                ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>` // Icona "già letto" (doppio check)
                : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`; // Icona "da leggere"

            return `
            <div class="compact-item" data-id="${{bookmark.id}}" data-is-read="${{bookmark.is_read}}" data-search-text="${{searchText}}">
                ${{imageHtml}}
                <div class="compact-content">
                    <div class="compact-actions-top">
                        ${{badgesHtml}}
                        <button class="icon-btn read" title="${{readButtonTitle}}" onclick="bookmarkMarkRead(${{bookmark.id}})">${{readButtonIcon}}</button>
                        <button class="icon-btn edit" title="Modifica" onclick='openEditModal(${{bookmarkJson}})'><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                        <button class="icon-btn delete" title="Elimina" onclick="bookmarkDelete(${{bookmark.id}})"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 6h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 6v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                    </div>
                    <div class="compact-title">${{bookmark.title || 'Senza titolo'}}</div>
                    <a href="${{bookmark.url}}" target="_blank" class="compact-url">${{bookmark.url}}</a>
                </div>
                <div class="compact-date">${{shortDate}}</div>
            </div>`;
        }}

        // --- Infinite Scroll ---
        let isLoading = false;
        let allLoaded = false;
        let currentOffset = {len(bookmarks)};
        const limit = 20;

        window.addEventListener('scroll', () => {{
            if (isLoading || allLoaded) return;

            // Avvia il caricamento quando l'utente è a 300px dal fondo
            if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 300) {{
                loadMoreBookmarks();
            }}
        }});

        // Controlla se è necessario caricare più bookmark dopo un filtro
        const observer = new MutationObserver(() => {{
            if (document.body.scrollHeight <= window.innerHeight && !isLoading && !allLoaded) {{
                loadMoreBookmarks();
            }}
        }});

        async function loadMoreBookmarks() {{
            isLoading = true;
            const loadingIndicator = document.getElementById('loadingIndicator');
            loadingIndicator.style.display = 'block';

            try {{
                let apiUrl = `/api/bookmarks?offset=${{currentOffset}}&limit=${{limit}}&hide_read=${{hideRead}}`;
                if (activeSpecialFilter) apiUrl += `&filter=${{activeSpecialFilter}}`;
                const response = await fetch(apiUrl);
                const newBookmarks = await response.json();

                if (newBookmarks.length === 0) {{
                    allLoaded = true;
                    loadingIndicator.textContent = 'Tutti i bookmark sono stati caricati.';
                    return;
                }}

                const cardsContainer = document.getElementById('bookmarksGrid');
                const compactContainer = document.getElementById('bookmarksCompact');

                newBookmarks.forEach(bookmark => {{
                    // Crea e appende la nuova card e l'item compatto
                    cardsContainer.insertAdjacentHTML('beforeend', renderBookmarkCard(bookmark));
                    compactContainer.insertAdjacentHTML('beforeend', renderBookmarkCompactItem(bookmark));
                }});

                currentOffset += newBookmarks.length;
                applyAllFilters(); // Riapplica i filtri per i nuovi elementi

            }} catch (error) {{
                console.error("Errore nel caricamento dei bookmark:", error);
                loadingIndicator.textContent = 'Errore nel caricamento.';
            }} finally {{
                isLoading = false;
                if (!allLoaded) loadingIndicator.style.display = 'none';
            }}
        }}

        // Avvia l'observer per monitorare le modifiche al DOM
        observer.observe(document.getElementById('bookmarksGrid'), {{ childList: true, subtree: true }});
        observer.observe(document.getElementById('bookmarksCompact'), {{ childList: true, subtree: true }});

    </script>
</body>
</html>"""
