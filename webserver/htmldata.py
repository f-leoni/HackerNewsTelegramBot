def get_html(self, bookmarks):
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

        /* Pulsante per mostrare form */
        .add-toggle {{
            text-align: center;
            margin-bottom: 20px;
        }}

        .btn-toggle {{
            background: #28a745;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: background-color 0.3s;
        }}

        .btn-toggle:hover {{
            background: #218838;
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

        .btn-toggle.active {{
            background: #dc3545;
        }}

        .btn-toggle.active:hover {{
            background: #c82333;
        }}

        /* Form nascosto di default */
        .add-form {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border: 2px dashed #dee2e6;
            display: none;
            animation: slideDown 0.3s ease-out;
        }}

        .add-form.show {{
            display: block;
        }}

        @keyframes slideDown {{
            from {{
                opacity: 0;
                transform: translateY(-10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .form-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }}

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
            min-width: 147px;
            white-space: nowrap;
            flex-shrink: 0;
            box-sizing: border-box;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            /* Force a stable button size: fixed flex basis prevents unexpected shrinking */
            flex: 0 0 147px;
            width: auto !important;
        }}

        /* Strong override to ensure buttons are not collapsed by other rules */
        .view-controls .view-btn {{
            width: 147px !important;
            max-width: 147px !important;
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
        <h1>📚 I Miei Bookmark</h1>

        <!-- Toggle per mostrare form -->
        <div class="add-toggle">
            <button class="btn-toggle" onclick="toggleForm()">➕ Aggiungi Bookmark</button>
        </div>

        <!-- Form nascosto -->
        <div class="add-form" id="addForm">
            <h3>Aggiungi Nuovo Bookmark</h3>
            <form id="bookmarkForm">
                <div class="form-group">
                    <label>URL: *</label>
                    <input type="url" id="url" name="url" required placeholder="https://esempio.com">
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Titolo:</label>
                        <input type="text" id="title" name="title" placeholder="Titolo del sito">
                    </div>
                    <div class="form-group">
                        <label>URL Immagine:</label>
                        <input type="url" id="image_url" name="image_url" placeholder="https://esempio.com/image.jpg">
                    </div>
                </div>

                <div class="form-group">
                    <label>Descrizione:</label>
                    <textarea id="description" name="description" placeholder="Descrizione opzionale"></textarea>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>URL HackerNews:</label>
                        <input type="url" id="comments_url" name="comments_url" placeholder="https://news.ycombinator.com/item?id=...">
                    </div>
                    <div class="form-group">
                        <label>Telegram User ID:</label>
                        <input type="number" id="telegram_user_id" name="telegram_user_id" placeholder="123456789">
                    </div>
                </div>

                <button type="submit" class="btn">Aggiungi Bookmark</button>
            </form>
        </div>

        <input type="text" class="search-box" id="searchBox" placeholder="🔍 Cerca nei bookmark...">

        <!-- Controlli vista -->
        <div class="view-controls">
            <button type="button" class="view-btn active" data-view="cards">📋 Vista Cards</button>
            <button type="button" class="view-btn" data-view="compact">📄 Vista Compatta</button>
            <span id="viewStatus" style="margin-left:12px; font-weight:600; color:#333">cards</span>
        </div>

        <div class="special-filters">
            <button class="filter-btn filter-telegram" onclick="filterSpecial('telegram')">📱 Solo Telegram</button>
            <button class="filter-btn filter-hn" onclick="filterSpecial('hn')">🗞️ Con HackerNews</button>
            <button class="filter-btn" onclick="filterSpecial('recent')">🕐 Ultimi 7 giorni</button>
        </div>

        <div class="filter-bar" id="filterBar">
            <!-- I filtri verranno popolati dinamicamente -->
        </div>

        <div class="stats">
            <strong>{len(bookmarks)} bookmark totali</strong>
        </div>

        <!-- Vista normale (cards) -->
        <div class="bookmarks-grid" id="bookmarksGrid">
            {self.render_bookmarks(bookmarks)}
        </div>

        <!-- Vista compatta -->
        <div class="bookmarks-compact" id="bookmarksCompact">
            {self.render_bookmarks_compact(bookmarks)}
        </div>
    </div>

    <script>
        // Toggle form
        function toggleForm() {{
            const form = document.getElementById('addForm');
            const button = document.querySelector('.btn-toggle');

            if (form.classList.contains('show')) {{
                form.classList.remove('show');
                button.textContent = '➕ Aggiungi Bookmark';
                button.classList.remove('active');
            }} else {{
                form.classList.add('show');
                button.textContent = '❌ Nascondi Form';
                button.classList.add('active');
            }}
        }}

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
        }}

        // Expose switchView on window for inline handlers
        // Ensure switchView is available globally
        (function() {{
            try {{
                window.switchView = switchView;
            }} catch (e) {{
                // ignore
            }}
        }})();
            // Attach listeners to view buttons (use data-view attribute)
            document.querySelectorAll('.view-btn[data-view]').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    const v = btn.getAttribute('data-view');
                    if (v) switchView(v);
                }});
            }});

            // Fallback: delegation listener for clicks (robust if buttons are dynamically replaced)
            document.addEventListener('click', function(e) {{
                const btn = e.target.closest && e.target.closest('.view-btn[data-view]');
                if (btn) {{
                    const v = btn.getAttribute('data-view');
                    if (v) switchView(v);
                }}
            }});

        // Ricerca in tempo reale
        document.getElementById('searchBox').addEventListener('input', function(e) {{
            const searchTerm = e.target.value.toLowerCase();

            // Cerca nelle cards
            const cards = document.querySelectorAll('.bookmark-card');
            cards.forEach(card => {{
                const title = (card.querySelector('.bookmark-title')?.textContent || '').toLowerCase();
                const url = (card.querySelector('.bookmark-url')?.textContent || '').toLowerCase();
                const description = (card.querySelector('.bookmark-description')?.textContent || '').toLowerCase();
                const domain = (card.querySelector('.bookmark-domain')?.textContent || '').toLowerCase();

                if (title.includes(searchTerm) || url.includes(searchTerm) || 
                    description.includes(searchTerm) || domain.includes(searchTerm)) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            // Cerca nella vista compatta
            const compactItems = document.querySelectorAll('.compact-item');
            compactItems.forEach(item => {{
                const title = (item.querySelector('.compact-title')?.textContent || '').toLowerCase();
                const url = (item.querySelector('.compact-url')?.textContent || '').toLowerCase();
                const domain = (item.querySelector('.compact-domain')?.textContent || '').toLowerCase();

                if (title.includes(searchTerm) || url.includes(searchTerm) || domain.includes(searchTerm)) {{
                    item.style.display = 'grid';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }});

        // Form submission
        document.getElementById('bookmarkForm').addEventListener('submit', async function(e) {{
            e.preventDefault();

            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);

            // Rimuovi campi vuoti
            Object.keys(data).forEach(key => {{
                if (data[key] === '') {{
                    delete data[key];
                }}
            }});

            try {{
                const response = await fetch('/api/bookmarks', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
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

        // Domain filters removed per user request (cleanup)

        function filterSpecial(type) {{
            // Reset altri filtri
            const domainButtons = document.querySelectorAll('.filter-bar .filter-btn');
            const specialButtons = document.querySelectorAll('.special-filters .filter-btn');

            domainButtons.forEach(btn => btn.classList.remove('active'));
            specialButtons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            const now = new Date();
            const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

            // Filtra cards
            const cards = document.querySelectorAll('.bookmark-card');
            cards.forEach(card => {{
                let show = false;

                if (type === 'telegram') {{
                    show = card.querySelector('.telegram-badge') !== null;
                }} else if (type === 'hn') {{
                    show = card.querySelector('.hn-link') !== null;
                }} else if (type === 'recent') {{
                    const dateText = card.querySelector('.bookmark-date')?.textContent;
                    if (dateText) {{
                        const cardDate = new Date(dateText);
                        show = cardDate >= weekAgo;
                    }}
                }}

                card.style.display = show ? 'block' : 'none';
            }});

            // Filtra vista compatta
            const compactItems = document.querySelectorAll('.compact-item');
            compactItems.forEach(item => {{
                let show = false;

                if (type === 'telegram') {{
                    show = item.querySelector('.telegram-badge') !== null;
                }} else if (type === 'hn') {{
                    show = item.querySelector('.hn-link') !== null;
                }} else if (type === 'recent') {{
                    const dateText = item.querySelector('.compact-date')?.textContent;
                    if (dateText) {{
                        const itemDate = new Date(dateText);
                        show = itemDate >= weekAgo;
                    }}
                }}

                item.style.display = show ? 'grid' : 'none';
            }});
        }}

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
            try {{
                const res = await fetch('/api/bookmarks/' + id + '/read', {{ method: 'PUT' }});
                if (res.ok) location.reload(); else alert("Errore durante l'operazione");
            }} catch (e) {{
                alert("Errore di connessione");
            }}
        }}
    </script>
</body>
</html>"""