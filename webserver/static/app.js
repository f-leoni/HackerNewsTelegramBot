// --- STATE ---
let isLoading = false;
let allLoaded = false;
let currentOffset = 0;
const limit = 20;
let visibleCount = 0;
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

// --- FILTERS & SEARCH ---
function triggerSearch() {
    document.getElementById('bookmarksGrid').innerHTML = '';
    document.getElementById('bookmarksCompact').innerHTML = '';
    visibleCount = 0;
    currentOffset = 0;
    allLoaded = false;
    isLoading = false;
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.textContent = window.TRANSLATIONS.loading;
    loadingIndicator.classList.add('hidden');
    
    loadMoreBookmarks();
}

function updateVisibleCount() {
    document.getElementById('visibleCount').textContent = visibleCount;
}

// --- DATA LOADING ---
async function loadMoreBookmarks() {
    if (isLoading || allLoaded) return;
    isLoading = true;
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.classList.remove('hidden');

    const searchTerm = document.getElementById('searchBox').value;
    // Get sortOrder from the globally exposed Alpine.js component state
    const sortOrder = window.viewControlsState?.sortOrder || 'desc';
    const hideRead = window.viewControlsState?.hideRead ?? true;
    const activeSpecialFilter = window.viewControlsState?.activeSpecialFilter || null;
    let apiUrl = `/api/bookmarks?offset=${currentOffset}&limit=${limit}&hide_read=${hideRead}&sort=${sortOrder}`;
    if (activeSpecialFilter) apiUrl += `&filter=${activeSpecialFilter}`;
    if (searchTerm) apiUrl += `&search=${encodeURIComponent(searchTerm)}`;

    try {
        const response = await fetch(apiUrl); // eslint-disable-line no-undef
        
        if (response.status === 401) {
            window.location.href = '/login'; // Sessione scaduta, reindirizza al login
            return;
        }

        const newBookmarks = await response.json();

        if (newBookmarks.length === 0) {
            allLoaded = true;
            loadingIndicator.textContent = visibleCount === 0 ? window.TRANSLATIONS.no_bookmarks_found : window.TRANSLATIONS.all_bookmarks_loaded;
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
        console.error("Error loading bookmarks:", error);
        loadingIndicator.textContent = window.TRANSLATIONS.error_loading;
    } finally {
        isLoading = false;
        if (allLoaded) {
            loadingIndicator.classList.remove('hidden');
        } else {
            loadingIndicator.classList.add('hidden');
        }
    }
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', function() {
    // Set initial state from data passed by the server
    currentOffset = window.APP_CONFIG.initialCount;
    visibleCount = window.APP_CONFIG.initialCount;

    updateVisibleCount();

    // Event Listeners

    const searchBox = document.getElementById('searchBox');
    const clearSearchBtn = document.getElementById('clearSearchBtn');

    searchBox.addEventListener('input', function(e) {
        // Mostra/nascondi il pulsante di cancellazione
        clearSearchBtn.classList.toggle('hidden', !e.target.value);

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            triggerSearch();
        }, 300); // Debounce
    });

    clearSearchBtn.addEventListener('click', () => {
        searchBox.value = '';
        clearSearchBtn.classList.add('hidden');
        triggerSearch();
    });

    window.addEventListener('scroll', () => {
        // Infinite scroll
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 300) {
            loadMoreBookmarks();
        }
    });

    // Event Delegation for dynamic buttons
    document.body.addEventListener('click', function(event) {
        const button = event.target.closest('.icon-btn');
        if (!button) return;

        // The edit button now dispatches a custom event handled by Alpine.js
        if (button.classList.contains('edit')) {
            const bookmarkData = JSON.parse(button.dataset.bookmark);
            window.dispatchEvent(new CustomEvent('open-edit-modal', { detail: bookmarkData }));
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

// --- API ACTIONS ---
async function bookmarkDelete(id) {
    if (!confirm(window.TRANSLATIONS.confirm_delete)) return;
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
            showToast("Bookmark deleted successfully.");
        } else {
             showToast("Error during deletion", true);
        }
    } catch (e) {
        showToast("Connection error", true);
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
                    readButton.title = isRead ? window.TRANSLATIONS.tooltip_mark_as_unread : window.TRANSLATIONS.tooltip_mark_as_read;
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
            showToast("Error during update", true);
        }
    } catch (e) {
        showToast("Connection error", true);
    }
}

// --- DYNAMIC RENDERING ---
function renderBookmarkCard(bookmark) {
    const imageHtml = bookmark.image_url
        ? `<img src="${bookmark.image_url}" alt="Preview" class="bookmark-image">`
        : '<div class="bookmark-image image-placeholder">🔗</div>';
    const hnLink = bookmark.comments_url ? `<a href="${bookmark.comments_url}" target="_blank" class="hn-link" title="${window.TRANSLATIONS.tooltip_hn_comments}">🗞️ HN</a>` : '';
    const bookmarkJson = JSON.stringify(bookmark).replace(/'/g, '&#39;').replace(/"/g, '&quot;');
    
    const isRead = bookmark.is_read == 1;
    const readButtonTitle = isRead ? window.TRANSLATIONS.tooltip_mark_as_unread : window.TRANSLATIONS.tooltip_mark_as_read;
    const readButtonIcon = isRead 
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

    return `
    <div class="bookmark-card" data-id="${bookmark.id}" data-is-read="${bookmark.is_read}">
        <div class="bookmark-header">
            ${imageHtml}
            <div class="bookmark-info">
                <div class="bookmark-actions-top">
                    ${hnLink}
                    <button class="icon-btn read" title="${readButtonTitle}" data-id="${bookmark.id}">${readButtonIcon}</button>
                    <button class="icon-btn edit" title="${window.TRANSLATIONS.tooltip_edit}" data-bookmark='${bookmarkJson}'><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                    <button class="icon-btn delete" title="${window.TRANSLATIONS.tooltip_delete}" data-id="${bookmark.id}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg></button>
                </div>
                <div class="bookmark-title">${escape_html(bookmark.title) || 'Untitled'}</div>
            </div>
        </div>
        <a href="${escape_html(bookmark.url)}" target="_blank" class="bookmark-url" title="${window.TRANSLATIONS.tooltip_open_link}">${escape_html(bookmark.url)}</a>
        <div class="bookmark-description">${escape_html(bookmark.description) || 'No description'}</div>
        <div class="bookmark-footer">
            <span class="bookmark-date">${bookmark.saved_at}</span>
        </div>
    </div>`;
}

function renderBookmarkCompactItem(bookmark) {
    const imageHtml = bookmark.image_url
        ? `<img src="${bookmark.image_url}" alt="Preview" class="compact-image">`
        : '<div class="compact-image">🔗</div>';
    let badgesHtml = '';
    if (bookmark.comments_url) badgesHtml += `<a href="${bookmark.comments_url}" target="_blank" class="hn-link" title="${window.TRANSLATIONS.tooltip_hn_comments}">HN</a>`;
    if (badgesHtml) badgesHtml = `<div class="compact-badges">${badgesHtml}</div>`;
    const shortDate = (bookmark.saved_at || '').split(' ')[0];
    const bookmarkJson = JSON.stringify(bookmark).replace(/'/g, '&#39;').replace(/"/g, '&quot;');

    const isRead = bookmark.is_read == 1;
    const readButtonTitle = isRead ? window.TRANSLATIONS.tooltip_mark_as_unread : window.TRANSLATIONS.tooltip_mark_as_read;
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
                <button class="icon-btn edit" title="${window.TRANSLATIONS.tooltip_edit}" data-bookmark='${bookmarkJson}'><svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                <button class="icon-btn delete" title="${window.TRANSLATIONS.tooltip_delete}" data-id="${bookmark.id}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg></button>
            </div>
            <div class="compact-title">${escape_html(bookmark.title) || 'Untitled'}</div>
            <a href="${escape_html(bookmark.url)}" target="_blank" class="compact-url" title="${window.TRANSLATIONS.tooltip_open_link}">${escape_html(bookmark.url)}</a>
        </div>
        <div class="compact-date">${shortDate}</div>
    </div>`;
}