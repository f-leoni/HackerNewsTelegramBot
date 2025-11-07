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
    const translations = window.TRANSLATIONS || {};
    const imageHtml = bookmark.image_url ? `<img src="${bookmark.image_url}" alt="Preview" class="bookmark-image">` : '<div class="bookmark-image image-placeholder">🔗</div>';
    const hnLink = bookmark.comments_url ? `<a href="${bookmark.comments_url}" target="_blank" class="hn-link" title="${translations.tooltip_hn_comments || 'View HackerNews comments'}">🗞️ HN</a>` : '';
    const isRead = bookmark.is_read == 1;
    const readButtonTitle = isRead ? (translations.tooltip_mark_as_unread || "Mark as unread") : (translations.tooltip_mark_as_read || "Mark as read");
    const readButtonIcon = isRead
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    
    const bookmarkJson = JSON.stringify(bookmark).replace(/'/g, "&#39;").replace(/"/g, '&quot;');

    return `
    <div class="bookmark-card" data-id="${bookmark.id}" data-is-read="${bookmark.is_read}">
        <div class="bookmark-header">
            ${imageHtml}
            <div class="bookmark-info">
                <div class="bookmark-actions-top">
                    ${hnLink}
                    <button class="icon-btn read" title="${readButtonTitle}" data-id="${bookmark.id}">${readButtonIcon}</button>
                    <button class="icon-btn edit" title="${translations.tooltip_edit || 'Edit'}" data-bookmark='${bookmarkJson}'>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </button>
                    <button class="icon-btn delete" title="${translations.tooltip_delete || 'Delete'}" data-id="${bookmark.id}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                    </button>
                </div>
                <div class="bookmark-title">${bookmark.title || 'Untitled'}</div>
            </div>
        </div>
        <a href="${bookmark.url}" target="_blank" class="bookmark-url" title="${translations.tooltip_open_link || 'Open link'}">${bookmark.url}</a>
        <div class="bookmark-description">${bookmark.description || 'No description'}</div>
        <div class="bookmark-footer">
            <span class="bookmark-date">${bookmark.saved_at}</span>
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
    const translations = window.TRANSLATIONS || {};
    const imageHtml = bookmark.image_url ? `<img src="${bookmark.image_url}" alt="Preview" class="compact-image">` : '<div class="compact-image">🔗</div>';
    const hnLink = bookmark.comments_url ? `<a href="${bookmark.comments_url}" target="_blank" class="hn-link" title="${translations.tooltip_hn_comments || 'View HackerNews comments'}">HN</a>` : '';
    const badgesHtml = hnLink ? `<div class="compact-badges">${hnLink}</div>` : '';
    const shortDate = bookmark.saved_at.split(' ')[0];
    const isRead = bookmark.is_read == 1;
    const readButtonTitle = isRead ? (translations.tooltip_mark_as_unread || "Mark as unread") : (translations.tooltip_mark_as_read || "Mark as read");
    const readButtonIcon = isRead
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

    const bookmarkJson = JSON.stringify(bookmark).replace(/'/g, "&#39;").replace(/"/g, '&quot;');

    return `
    <div class="compact-item" data-id="${bookmark.id}" data-is-read="${bookmark.is_read}">
        ${imageHtml}
        <div class="compact-content">
            <div class="compact-actions-top">
                ${badgesHtml}
                <button class="icon-btn read" title="${readButtonTitle}" data-id="${bookmark.id}">${readButtonIcon}</button>
                <button class="icon-btn edit" title="${translations.tooltip_edit || 'Edit'}" data-bookmark='${bookmarkJson}'>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <button class="icon-btn delete" title="${translations.tooltip_delete || 'Delete'}" data-id="${bookmark.id}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                </button>
            </div>
            <div class="compact-title">${bookmark.title || 'Untitled'}</div>
            <a href="${bookmark.url}" target="_blank" class="compact-url" title="${translations.tooltip_open_link || 'Open link'}">${bookmark.url}</a>
        </div>
        <div class="compact-date">${shortDate}</div>
    </div>`;
}

// --- Global Event Listeners ---

/**
 * Handles broken images gracefully by hiding them and showing a placeholder if available.
 * This is CSP-compliant as it avoids inline 'onerror' attributes.
 */
document.addEventListener('error', function(event) {
    const target = event.target;
    if (target.tagName.toLowerCase() === 'img') {
        target.style.display = 'none';
        // If there's a sibling with the 'image-placeholder' class, show it.
        if (target.nextElementSibling && target.nextElementSibling.classList.contains('image-placeholder')) {
            target.nextElementSibling.style.display = 'flex';
        }
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
                    const newReadButton = el.querySelector('.icon-btn.read');
                    if (newReadButton) {
                        newReadButton.title = data.is_read ? (translations.tooltip_mark_as_unread || "Mark as unread") : (translations.tooltip_mark_as_read || "Mark as read");
                        newReadButton.innerHTML = data.is_read
                            ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>'
                            : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
                    }
                });
                showToast(data.is_read ? (translations.toast_marked_as_read || "Marked as read") : (translations.toast_marked_as_unread || "Marked as unread"));
            }
        })
        .catch(error => showToast(error.message, true));
    }
});