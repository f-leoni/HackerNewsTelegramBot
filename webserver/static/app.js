/**
 * app.js - Client-side logic for the Bookmarks web interface.
 * This file handles interactions that are not managed by htmx or Alpine.js,
 * such as individual bookmark actions (delete, mark as read) and toast notifications.
 */

/**
 * Displays a toast notification at the bottom of the screen.
 * @param {string} message - The message to display.
 * @param {boolean} isError - If true, the toast will have an error style.
 */
function showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'error' : ''}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Trigger the animation
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    // Hide and remove the toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => toast.remove());
    }, 3000);
}

/**
 * Renders a single bookmark into the detailed card view HTML structure.
 * This function is still used by the Alpine.js modal to update the UI after an edit/add.
 * @param {object} bookmark - The bookmark object.
 * @returns {string} - The HTML string for the bookmark card.
 */
function renderBookmarkCard(bookmark) {
    // These must match the icons in htmldata.py
    const ICON_OPEN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>';
    const ICON_EDIT = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>';
    const ICON_DELETE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>';
    const ICON_READ = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
    const ICON_UNREAD = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle></svg>';
    const ICON_HN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';

    const translations = window.TRANSLATIONS || {};
    const isRead = bookmark.is_read == 1;
    const readButtonTitle = isRead ? (translations.tooltip_mark_as_unread || "Mark as unread") : (translations.tooltip_mark_as_read || "Mark as read");
    const readButtonIcon = isRead ? ICON_READ : ICON_UNREAD;
    const bookmarkJson = JSON.stringify(bookmark).replace(/'/g, "&#39;").replace(/"/g, '&quot;');

    return `
    <div class="bookmark-card ${isRead ? 'read' : ''}" data-id="${bookmark.id}" data-is-read="${isRead ? 1 : 0}">
        <div class="bookmark-content">
            <h3 class="bookmark-title"><a href="${bookmark.url}" target="_blank">${bookmark.title || 'Untitled'}</a></h3>
            <span class="bookmark-domain">${bookmark.domain}</span>
            
            <div class="bookmark-actions">
                <a href="${bookmark.url}" target="_blank" class="icon-btn" title="${translations.tooltip_open_link || 'Open link'}">${ICON_OPEN}</a>
                <button class="icon-btn read" data-id="${bookmark.id}" title="${readButtonTitle}">${readButtonIcon}</button>
                <button class="icon-btn edit" title="${translations.tooltip_edit || 'Edit'}" @click="$dispatch('open-edit-modal', JSON.parse(this.dataset.bookmark))" data-bookmark='${bookmarkJson}'>${ICON_EDIT}</button>
                <button class="icon-btn delete" data-id="${bookmark.id}" title="${translations.tooltip_delete || 'Delete'}">${ICON_DELETE}</button>
            </div>

            <p class="bookmark-description">${bookmark.description || ''}</p>
        </div>
        <div class="bookmark-footer">
            <img src="${bookmark.image_url}" alt="Preview" class="bookmark-image-footer">
            <span class="bookmark-date">${bookmark.saved_at}</span>
            ${bookmark.comments_url ? `<a href="${bookmark.comments_url}" target="_blank" class="hn-link" title="${translations.tooltip_hn_comments || 'View HN comments'}">${ICON_HN} HN Comments</a>` : ''}
        </div>
    </div>`;
}

/**
 * Renders a single bookmark into the compact list view HTML structure.
 * This function is still used by the Alpine.js modal to update the UI after an edit/add.
 * @param {object} bookmark - The bookmark object.
 * @returns {string} - The HTML string for the compact list item.
 */
function renderBookmarkCompactItem(bookmark) {
    // These must match the icons in htmldata.py
    const ICON_EDIT = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>';
    const ICON_DELETE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>';
    const ICON_READ = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
    const ICON_UNREAD = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle></svg>';
    const ICON_HN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';

    const translations = window.TRANSLATIONS || {};
    const shortDate = bookmark.saved_at.split(' ')[0];
    const isRead = bookmark.is_read == 1;
    const readButtonTitle = isRead ? (translations.tooltip_mark_as_unread || "Mark as unread") : (translations.tooltip_mark_as_read || "Mark as read");
    const readButtonIcon = isRead ? ICON_READ : ICON_UNREAD;
    const bookmarkJson = JSON.stringify(bookmark).replace(/'/g, "&#39;").replace(/"/g, '&quot;');

    return `
    <div class="compact-item ${isRead ? 'read' : ''}" data-id="${bookmark.id}" data-is-read="${isRead ? 1 : 0}">
        <img src="${bookmark.image_url}" alt="" class="compact-image">
        <div class="image-placeholder" style="display:none;">🔗</div>
        <div class="compact-content">
            <a href="${bookmark.url}" target="_blank" class="compact-title" title="${bookmark.title}">${bookmark.title || 'Untitled'}</a>
            <span class="compact-domain">${bookmark.domain}</span>
        </div>
        <div class="compact-date">${shortDate}</div>
        <div class="compact-badges">
            ${bookmark.comments_url ? `<a href="${bookmark.comments_url}" target="_blank" class="hn-link" title="${translations.tooltip_hn_comments || 'View HN comments'}">${ICON_HN}</a>` : ''}
        </div>
        <div class="bookmark-actions">
            <button class="icon-btn read" data-id="${bookmark.id}" title="${readButtonTitle}">${readButtonIcon}</button>
            <button class="icon-btn edit" title="${translations.tooltip_edit || 'Edit'}" @click="$dispatch('open-edit-modal', JSON.parse(this.dataset.bookmark))" data-bookmark='${bookmarkJson}'>${ICON_EDIT}</button>
            <button class="icon-btn delete" data-id="${bookmark.id}" title="${translations.tooltip_delete || 'Delete'}">${ICON_DELETE}</button>
        </div>
    </div>`;
}

// --- Global Event Listeners ---

/**
 * Handles broken images gracefully by hiding them and showing a placeholder if available.
 * This is CSP-compliant as it avoids inline 'onerror' attributes.
 */
document.addEventListener('error', function(event) {
    const target = event.target;
    // Check if the target is an image and is inside an image-placeholder
    if (target.tagName.toLowerCase() === 'img' && target.parentElement.classList.contains('image-placeholder')) {
        target.style.display = 'none';
        // Add the 'has-error' class to the parent placeholder to show the fallback icon via CSS
        target.parentElement.classList.add('has-error');
    }
}, true); // Use capture phase to catch the error early.

// Event delegation for bookmark actions (delete, mark as read, edit)
document.addEventListener('click', function(event) {
    const target = event.target.closest('.icon-btn');
    if (!target) return;

    const translations = window.TRANSLATIONS || {};

    if (target.classList.contains('delete')) {
        const bookmarkId = target.dataset.id;
        if (bookmarkId && confirm(translations.confirm_delete || "Are you sure you want to delete this bookmark?")) {
            fetch(`/api/bookmarks/${bookmarkId}`, { method: 'DELETE' })
                .then(response => {
                    if (!response.ok) throw new Error('Failed to delete');
                    document.querySelectorAll(`[data-id='${bookmarkId}']`).forEach(el => el.remove());
                    showToast(translations.toast_bookmark_deleted || "Bookmark deleted!");
                })
                .catch(error => showToast(error.message, true));
        }
    }

    if (target.classList.contains('read')) {
        const bookmarkId = target.dataset.id;
        const card = target.closest('[data-id]');
        const isCurrentlyRead = card.dataset.isRead == '1';
        fetch(`/api/bookmarks/${bookmarkId}/read`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_read: !isCurrentlyRead })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // Instead of reloading, just update the UI directly
                document.querySelectorAll(`[data-id='${bookmarkId}']`).forEach(el => {
                    el.dataset.isRead = data.is_read;
                    // Optionally, re-render the button to update its icon and title
                    const readButton = el.querySelector('.icon-btn.read');
                    if (readButton) {
                        const ICON_READ = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
                        const ICON_UNREAD = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle></svg>';
                        readButton.title = data.is_read ? (translations.tooltip_mark_as_unread || "Mark as unread") : (translations.tooltip_mark_as_read || "Mark as read");
                        readButton.innerHTML = data.is_read ? ICON_READ : ICON_UNREAD;
                    }
                });
                showToast(data.is_read ? (translations.toast_marked_as_read || "Marked as read") : (translations.toast_marked_as_unread || "Marked as unread"));
            }
        })
        .catch(error => showToast(error.message, true));
    }
});