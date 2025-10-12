// --- STATE ---
let isLoading = false;
let allLoaded = false;
let currentOffset = 0;
const limit = 20;
let currentView = 'cards';
let hideRead = true;
let visibleCount = 0;
let activeSpecialFilter = null;
let searchTimeout;

function escape_html(text) {
    if (text === null || text === undefined) {
        return "";
    }
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, '&quot;');
}

function showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'error' : ''}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Force reflow to trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => toast.remove());
    }, 3000);
}

// --- VIEW SWITCHING ---
function setView(view) {
    const cardsView = document.getElementById('bookmarksGrid');
    const compactView = document.getElementById('bookmarksCompact');
    const viewToggleBtn = document.getElementById('viewToggleBtn');

    if (view === 'cards') {
        cardsView.style.display = 'grid';
        compactView.classList.remove('show');
        viewToggleBtn.innerHTML = '📄 Vista Compatta';
    } else {
        cardsView.style.display = 'none';
        compactView.classList.add('show');
        viewToggleBtn.innerHTML = '📋 Vista Cards';
    }
    currentView = view;
    updateVisibleCount();
}

function toggleView() {
    const newView = currentView === 'cards' ? 'compact' : 'cards';
    setView(newView);
}

// --- FILTERS & SEARCH ---
function triggerSearch() {
    document.getElementById('bookmarksGrid').innerHTML = '';
    document.getElementById('bookmarksCompact').innerHTML = '';
    visibleCount = 0;
    currentOffset = 0;
    allLoaded = false;
    isLoading = false;
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.textContent = 'Caricamento...';
    loadingIndicator.style.display = 'none';
    
    loadMoreBookmarks();
}

function filterSpecial(type, event) {
    const clickedButton = event.target;
    if (clickedButton.classList.contains('active')) {
        activeSpecialFilter = null;
        clickedButton.classList.remove('active');
    } else {
        document.querySelectorAll('.special-filters .filter-btn').forEach(btn => btn.classList.remove('active'));
        clickedButton.classList.add('active');
        activeSpecialFilter = type;
    }
    triggerSearch();
}

function toggleHideRead() {
    hideRead = !hideRead;
    localStorage.setItem('hideRead', hideRead);
    updateHideReadButton();
    triggerSearch();
}

function updateHideReadButton() {
    const btn = document.getElementById('hideReadBtn');
    btn.classList.toggle('active', hideRead);
    btn.textContent = hideRead ? '🙉 Mostra Letti' : '🙈 Nascondi Letti';
}

function updateVisibleCount() {
    document.getElementById('visibleCount').textContent = visibleCount;
}

// --- DATA LOADING ---
async function loadMoreBookmarks() {
    if (isLoading || allLoaded) return;
    isLoading = true;
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'block';

    const searchTerm = document.getElementById('searchBox').value;
    let apiUrl = `/api/bookmarks?offset=${currentOffset}&limit=${limit}&hide_read=${hideRead}`;
    if (activeSpecialFilter) apiUrl += `&filter=${activeSpecialFilter}`;
    if (searchTerm) apiUrl += `&search=${encodeURIComponent(searchTerm)}`;

    try {
        const response = await fetch(apiUrl);
        const newBookmarks = await response.json();

        if (newBookmarks.length === 0) {
            allLoaded = true;
            loadingIndicator.textContent = visibleCount === 0 ? 'Nessun bookmark trovato.' : 'Tutti i bookmark sono stati caricati.';
            if (currentOffset === 0) document.getElementById('visibleCount').textContent = 0;
            return;
        }

        const cardsContainer = document.getElementById('bookmarksGrid');
        const compactContainer = document.getElementById('bookmarksCompact');

        newBookmarks.forEach(bookmark => {
            cardsContainer.insertAdjacentHTML('beforeend', renderBookmarkCard(bookmark));
            compactContainer.insertAdjacentHTML('beforeend', renderBookmarkCompactItem(bookmark));
        });

        currentOffset += newBookmarks.length;
        visibleCount += newBookmarks.length;
        updateVisibleCount();

    } catch (error) {
        console.error("Errore nel caricamento dei bookmark:", error);
        loadingIndicator.textContent = 'Errore nel caricamento.';
    } finally {
        isLoading = false;
        if (allLoaded) {
            loadingIndicator.style.display = 'block';
        } else {
            loadingIndicator.style.display = 'none';
        }
    }
}

// --- THEME SWITCHING (DARK MODE) ---
function applyTheme(theme) {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (theme === 'dark') {
        document.documentElement.classList.add('dark-mode');
        if (themeToggleBtn) themeToggleBtn.textContent = '☀️ Light Mode';
    } else {
        document.documentElement.classList.remove('dark-mode');
        if (themeToggleBtn) themeToggleBtn.textContent = '🌙 Dark Mode';
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.classList.contains('dark-mode') ? 'dark' : 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', newTheme);
    applyTheme(newTheme);
}

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(savedTheme || (systemPrefersDark ? 'dark' : 'light'));
}
// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', function() {
    // Set initial state from data passed by the server
    currentOffset = window.APP_CONFIG.initialCount;
    visibleCount = window.APP_CONFIG.initialCount;

    // Restore state from localStorage
    const savedHideRead = localStorage.getItem('hideRead');
    hideRead = savedHideRead !== null ? JSON.parse(savedHideRead) : true;
    updateHideReadButton();

    // Initialize theme
    initializeTheme();

    // Initial view setup
    setView('cards');
    updateVisibleCount();

    // Event Listeners
    document.getElementById('viewToggleBtn').addEventListener('click', toggleView);
    document.getElementById('themeToggleBtn').addEventListener('click', toggleTheme);


    document.getElementById('searchBox').addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            triggerSearch();
        }, 300); // Debounce
    });

    window.addEventListener('scroll', () => {
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 300) {
            loadMoreBookmarks();
        }
    });

    // Event Delegation for dynamic buttons
    document.body.addEventListener('click', function(event) {
        const button = event.target.closest('.icon-btn');
        if (!button) return;

        if (button.classList.contains('edit')) {
            // L'attributo data-bookmark contiene già un oggetto JSON valido
            const bookmarkData = JSON.parse(button.dataset.bookmark);
            openEditModal(bookmarkData);
        }
        else if (button.classList.contains('delete')) {
            const bookmarkId = button.dataset.id;
            bookmarkDelete(bookmarkId);
        }
        else if (button.classList.contains('read')) {
            const bookmarkId = button.dataset.id;
            bookmarkMarkRead(bookmarkId);
        }
    });
    
    // Load more if the initial content is not scrollable
    if (document.body.scrollHeight <= window.innerHeight) {
        loadMoreBookmarks();
    }
});


// --- MODAL LOGIC ---
const editModal = document.getElementById('editModal');
const editForm = document.getElementById('editBookmarkForm');

function openAddModal() {
    editForm.reset();
    document.getElementById('modalTitle').textContent = 'Aggiungi Nuovo Bookmark';
    document.getElementById('edit-id').value = '';
    editModal.style.display = 'block';
}

function openEditModal(bookmark) {
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
}

function closeEditModal() {
    editModal.style.display = 'none';
}

window.onclick = function(event) {
    if (event.target == editModal) {
        closeEditModal();
    }
}

editForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);
    const id = data.id;

    const isAdding = !id;
    const method = isAdding ? 'POST' : 'PUT';
    const url = isAdding ? '/api/bookmarks' : '/api/bookmarks/' + id;

    data.is_read = document.getElementById('edit-is_read').checked ? 1 : 0;

    Object.keys(data).forEach(key => {
        if (data[key] === '') delete data[key];
    });
    delete data.id;
    if (isAdding && !data.is_read) delete data.is_read;

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok && !isAdding) {
            const updatedBookmark = await response.json();
            
            // Trova e sostituisci la card e l'item compatto esistenti
            const oldCard = document.querySelector(`.bookmark-card[data-id='${id}']`);
            if (oldCard) {
                oldCard.outerHTML = renderBookmarkCard(updatedBookmark);
            }
            const oldCompactItem = document.querySelector(`.compact-item[data-id='${id}']`);
            if (oldCompactItem) {
                oldCompactItem.outerHTML = renderBookmarkCompactItem(updatedBookmark);
            }
            closeEditModal();
            showToast("Bookmark aggiornato con successo!");
        } else if (response.ok && isAdding) {
            // Se l'aggiunta ha successo, aggiorna il contatore e ricarica
            const totalCountEl = document.getElementById('totalCount');
            if (totalCountEl) {
                totalCountEl.textContent = parseInt(totalCountEl.textContent, 10) + 1;
            }
            closeEditModal();
            triggerSearch(); // Ricarica la lista per mostrare il nuovo bookmark
            showToast("Bookmark aggiunto con successo!");
        } else {
            const error = await response.json();
            showToast("Errore: " + (error.error || 'Errore sconosciuto'), true);
        }
    } catch (error) {
        showToast("Errore di connessione", true);
    }
});

// --- API ACTIONS ---
async function bookmarkDelete(id) {
    if (!confirm('Sei sicuro di voler eliminare questo bookmark?')) return;
    try {
        const res = await fetch('/api/bookmarks/' + id, { method: 'DELETE' });
        if (res.ok) {
            document.querySelector(`.bookmark-card[data-id='${id}']`)?.remove();
            document.querySelector(`.compact-item[data-id='${id}']`)?.remove();
            visibleCount--;
            updateVisibleCount();
            // Decrementa anche il contatore totale
            const totalCountEl = document.getElementById('totalCount');
            if (totalCountEl) {
                let currentTotal = parseInt(totalCountEl.textContent, 10);
                if (!isNaN(currentTotal)) totalCountEl.textContent = currentTotal - 1;
            }
            showToast("Bookmark eliminato con successo.");
        } else {
             showToast("Errore durante la cancellazione", true);
        }
    } catch (e) {
        showToast("Errore di connessione", true);
    }
}

async function bookmarkMarkRead(id) {
    const item = document.querySelector(`.bookmark-card[data-id='${id}']`) || document.querySelector(`.compact-item[data-id='${id}']`);
    const isCurrentlyRead = item ? item.dataset.isRead === '1' : false;
    const newReadState = !isCurrentlyRead;

    try {
        const response = await fetch('/api/bookmarks/' + id + '/read', { 
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_read: newReadState })
        });
        if (response.ok) {
            const updatedBookmarkData = await response.json();
            const newReadStatus = updatedBookmarkData.is_read;

            [document.querySelector(`.bookmark-card[data-id='${id}']`), document.querySelector(`.compact-item[data-id='${id}']`)].forEach(el => {
                if (!el) return;
                el.dataset.isRead = newReadStatus;
                const readButton = el.querySelector('.icon-btn.read');
                if (readButton) {
                    const isRead = newReadStatus == 1;
                    readButton.title = isRead ? "Segna come non letto" : "Segna come letto";
                    readButton.innerHTML = isRead
                        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>`
                        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
                }
                if (hideRead && newReadStatus == 1) {
                    el.style.display = 'none';
                    // Se nascondiamo un elemento, il conteggio visibile diminuisce
                    if (el.offsetParent !== null) { // Controlla se era visibile prima della modifica
                        visibleCount--;
                    }
                }
            });
            updateVisibleCount();
        } else {
            showToast("Errore durante l'aggiornamento", true);
        }
    } catch (e) {
        showToast("Errore di connessione", true);
    }
}

// --- DYNAMIC RENDERING ---
function renderBookmarkCard(bookmark) {
    const imageHtml = bookmark.image_url
        ? `<img src="${bookmark.image_url}" alt="Preview" class="bookmark-image" onerror="this.style.display='none'">`
        : '<div class="bookmark-image" style="display: flex; align-items: center; justify-content: center; background: #f8f9fa; color: #6c757d;">🔗</div>';
    const telegramBadge = bookmark.telegram_user_id ? '<span class="telegram-badge">📱 Telegram</span>' : '';
    const hnLink = bookmark.comments_url ? `<a href="${bookmark.comments_url}" target="_blank" class="hn-link">🗞️ HN</a>` : '';
    const bookmarkJson = JSON.stringify(bookmark).replace(/'/g, '&#39;').replace(/"/g, '&quot;');
    
    const isRead = bookmark.is_read == 1;
    const readButtonTitle = isRead ? "Segna come non letto" : "Segna come letto";
    const readButtonIcon = isRead 
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

    return `
    <div class="bookmark-card" data-id="${bookmark.id}" data-is-read="${bookmark.is_read}">
        <div class="bookmark-header">
            ${imageHtml}
            <div class="bookmark-info">
                <div class="bookmark-actions-top">
                    ${telegramBadge}
                    ${hnLink}
                    <button class="icon-btn read" title="${readButtonTitle}" data-id="${bookmark.id}">${readButtonIcon}</button>
                    <button class="icon-btn edit" title="Modifica" data-bookmark='${bookmarkJson}'><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                    <button class="icon-btn delete" title="Elimina" data-id="${bookmark.id}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 6h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 6v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                </div>
                <div class="bookmark-title">${escape_html(bookmark.title) || 'Senza titolo'}</div>
            </div>
        </div>
        <a href="${escape_html(bookmark.url)}" target="_blank" class="bookmark-url">${escape_html(bookmark.url)}</a>
        <div class="bookmark-description">${escape_html(bookmark.description) || 'Nessuna descrizione'}</div>
        <div class="bookmark-footer">
            <span class="bookmark-date">${bookmark.saved_at}</span>
        </div>
    </div>`;
}

function renderBookmarkCompactItem(bookmark) {
    const imageHtml = bookmark.image_url
        ? `<img src="${bookmark.image_url}" alt="Preview" class="compact-image" onerror="this.innerHTML='🔗'">`
        : '<div class="compact-image">🔗</div>';
    let badgesHtml = '';
    if (bookmark.telegram_user_id) badgesHtml += '<span class="telegram-badge">TG</span>';
    if (bookmark.comments_url) badgesHtml += `<a href="${bookmark.comments_url}" target="_blank" class="hn-link">HN</a>`;
    if (badgesHtml) badgesHtml = `<div class="compact-badges">${badgesHtml}</div>`;
    const shortDate = (bookmark.saved_at || '').split(' ')[0];
    const bookmarkJson = JSON.stringify(bookmark).replace(/'/g, '&#39;').replace(/"/g, '&quot;');

    const isRead = bookmark.is_read == 1;
    const readButtonTitle = isRead ? "Segna come non letto" : "Segna come letto";
    const readButtonIcon = isRead 
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

    return `
    <div class="compact-item" data-id="${bookmark.id}" data-is-read="${bookmark.is_read}">
        ${imageHtml}
        <div class="compact-content">
            <div class="compact-actions-top">
                ${badgesHtml}
                <button class="icon-btn read" title="${readButtonTitle}" data-id="${bookmark.id}">${readButtonIcon}</button>
                <button class="icon-btn edit" title="Modifica" data-bookmark='${bookmarkJson}'><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                <button class="icon-btn delete" title="Elimina" data-id="${bookmark.id}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M3 6h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 6v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
            </div>
            <div class="compact-title">${escape_html(bookmark.title) || 'Senza titolo'}</div>
            <a href="${escape_html(bookmark.url)}" target="_blank" class="compact-url">${escape_html(bookmark.url)}</a>
        </div>
        <div class="compact-date">${shortDate}</div>
    </div>`;
}

// --- MODAL STYLES ---
const modalStyle = `
    .modal {
        display: none;
        position: fixed;
        z-index: 1000;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        overflow: auto;
        background-color: rgba(0,0,0,0.5);
    }
    .modal-content {
        background-color: #fefefe;
        margin: 5% auto;
        padding: 20px;
        border: 1px solid #888;
        width: 80%;
        max-width: 700px;
        border-radius: 8px;
        position: relative;
        animation: slideDown 0.3s ease-out;
    }
    .modal-content .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
    }
    .modal-content .form-group input, .modal-content .form-group textarea {
        width: 100%;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 14px;
    }
    .close-btn {
        color: #aaa;
        float: right;
        font-size: 28px;
        font-weight: bold;
        cursor: pointer;
    }
    .close-btn:hover, .close-btn:focus {
        color: black;
    }
`;
const styleSheet = document.createElement("style");
styleSheet.type = "text/css";
styleSheet.innerText = modalStyle;
document.head.appendChild(styleSheet);