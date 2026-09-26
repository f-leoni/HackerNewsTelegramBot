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
    <link rel="stylesheet" href="/static/export-styles.css">
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


def get_user_management_page(self, translations=None):
    """Generates the HTML page for web-based user management."""
    if translations is None:
        translations = {}

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{translations.get('users_page_title', 'User Management')}</title>
    <link rel="icon" href="/static/img/favicon.svg" type="image/svg+xml">
    <link rel="alternate icon" href="/favicon.ico" type="image/x-icon">
    <link rel="apple-touch-icon" href="/static/img/favicon.svg">
    <link rel="stylesheet" href="/static/style.css">
    <style nonce="{self.nonce}">
        .users-actions {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}

        .users-card {{
            background: #fff;
            border: 1px solid #e6e8ef;
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        }}

        .users-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
        }}

        .users-grid .full {{
            grid-column: 1 / -1;
        }}

        .users-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            background: #fff;
            border-radius: 10px;
            overflow: hidden;
        }}

        .users-table th,
        .users-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #edf0f5;
            text-align: left;
        }}

        .users-table th {{
            background: #f7f9fc;
            font-weight: 700;
        }}

        .users-table tr:last-child td {{
            border-bottom: none;
        }}

        .inline-actions {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .inline-actions .btn {{
            padding: 6px 10px;
            font-size: 12px;
        }}

        .btn-danger {{
            background: #c62828;
        }}

        .btn-danger:hover {{
            background: #9a1f1f;
        }}

        .status-msg {{
            margin-top: 12px;
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 14px;
            display: none;
        }}

        .status-msg.ok {{
            display: block;
            background: #e8f7ee;
            color: #136c3c;
        }}

        .status-msg.err {{
            display: block;
            background: #fdecea;
            color: #8d1d17;
        }}

        .mono {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 12px;
        }}

        @media (max-width: 820px) {{
            .users-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{translations.get('users_header', 'User Management')}</h1>

        <div class="users-actions">
            <a href="/" class="btn">{translations.get('back_to_bookmarks', 'Back to Bookmarks')}</a>
            <a href="/logout" class="btn btn-secondary">{translations.get('logout', 'Logout')}</a>
        </div>

        <div class="users-card">
            <h3>{translations.get('create_user', 'Create New User')}</h3>
            <form id="createUserForm" class="users-grid">
                <div>
                    <label for="newUsername">{translations.get('username', 'Username')}</label>
                    <input id="newUsername" type="text" required minlength="3" maxlength="64">
                </div>
                <div>
                    <label for="newPassword">{translations.get('password', 'Password')}</label>
                    <input id="newPassword" type="password" required minlength="6">
                </div>
                <div>
                    <label for="newRole">{translations.get('role', 'Role')}</label>
                    <select id="newRole">
                        <option value="user">{translations.get('role_user', 'User')}</option>
                        <option value="admin">{translations.get('role_admin', 'Admin')}</option>
                    </select>
                </div>
                <div class="full">
                    <button type="submit" class="btn btn-primary">{translations.get('create_user', 'Create New User')}</button>
                </div>
            </form>
            <div id="statusMsg" class="status-msg"></div>
        </div>

        <div class="users-card" style="margin-top: 16px;">
            <h3>{translations.get('existing_users', 'Existing Users')}</h3>
            <table class="users-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>{translations.get('username', 'Username')}</th>
                        <th>{translations.get('role', 'Role')}</th>
                        <th>{translations.get('telegram_user_id_label', 'Telegram ID')}</th>
                        <th>{translations.get('actions', 'Actions')}</th>
                    </tr>
                </thead>
                <tbody id="usersTableBody"></tbody>
            </table>
        </div>
    </div>

    <script nonce="{self.nonce}">
        const labels = {{
            edit: {json.dumps(translations.get('edit', 'Edit'))},
            remove: {json.dumps(translations.get('delete', 'Delete'))},
            changePassword: {json.dumps(translations.get('change_password', 'Change Password'))},
            changeRole: {json.dumps(translations.get('change_role', 'Change Role'))},
            confirmDelete: {json.dumps(translations.get('confirm_delete_user', 'Delete this user and all related data?'))},
            promptUsername: {json.dumps(translations.get('prompt_new_username', 'New username'))},
            promptPassword: {json.dumps(translations.get('prompt_new_password', 'New password (min 6 chars)'))},
            promptRole: {json.dumps(translations.get('prompt_new_role', 'New role: admin or user'))},
            cannotDeleteSelf: {json.dumps(translations.get('cannot_delete_current_user', 'You cannot delete your current user.'))},
            loadError: {json.dumps(translations.get('users_load_error', 'Unable to load users.'))},
            roleUser: {json.dumps(translations.get('role_user', 'User'))},
            roleAdmin: {json.dumps(translations.get('role_admin', 'Admin'))},
            generateToken: {json.dumps(translations.get('generate_telegram_token', 'Generate Token'))},
            unlinkTelegram: {json.dumps(translations.get('unlink_telegram', 'Unlink Telegram'))},
            promptTokenTtl: {json.dumps(translations.get('prompt_token_ttl', 'Token validity in minutes'))},
            tokenCreated: {json.dumps(translations.get('token_created', 'Token generated'))},
            tokenUsageHint: {json.dumps(translations.get('token_usage_hint', 'Use in Telegram with: /link <token>'))}
        }};

        const statusMsg = document.getElementById('statusMsg');
        const usersTableBody = document.getElementById('usersTableBody');

        function showStatus(message, isError = false) {{
            statusMsg.className = `status-msg ${{isError ? 'err' : 'ok'}}`;
            statusMsg.textContent = message;
        }}

        function clearStatus() {{
            statusMsg.className = 'status-msg';
            statusMsg.textContent = '';
        }}

        async function fetchUsers() {{
            try {{
                const res = await fetch('/api/users');
                if (!res.ok) throw new Error(labels.loadError);
                const users = await res.json();
                usersTableBody.innerHTML = users.map((u) => `
                    <tr>
                        <td>${{u.id}}</td>
                        <td>${{u.username}}</td>
                        <td>${{u.role === 'admin' ? labels.roleAdmin : labels.roleUser}}</td>
                        <td class="mono">${{u.telegram_user_id ?? '-'}}</td>
                        <td>
                            <div class="inline-actions">
                                <button class="btn btn-secondary" data-action="rename" data-id="${{u.id}}" data-username="${{u.username}}">${{labels.edit}}</button>
                                <button class="btn" data-action="password" data-id="${{u.id}}">${{labels.changePassword}}</button>
                                <button class="btn" data-action="role" data-id="${{u.id}}" data-role="${{u.role || 'user'}}">${{labels.changeRole}}</button>
                                <button class="btn" data-action="token" data-id="${{u.id}}">${{labels.generateToken}}</button>
                                <button class="btn" data-action="unlink_tg" data-id="${{u.id}}">${{labels.unlinkTelegram}}</button>
                                <button class="btn btn-danger" data-action="delete" data-id="${{u.id}}">${{labels.remove}}</button>
                            </div>
                        </td>
                    </tr>
                `).join('');
            }} catch (err) {{
                showStatus(err.message || labels.loadError, true);
            }}
        }}

        document.getElementById('createUserForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            clearStatus();

            const username = document.getElementById('newUsername').value.trim();
            const password = document.getElementById('newPassword').value;
            const role = document.getElementById('newRole').value;

            const res = await fetch('/api/users', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ username, password, role }})
            }});

            const payload = await res.json().catch(() => ({{}}));
            if (!res.ok) {{
                showStatus(payload.error || 'Error', true);
                return;
            }}

            showStatus(payload.status || 'User created');
            e.target.reset();
            await fetchUsers();
        }});

        usersTableBody.addEventListener('click', async (e) => {{
            const btn = e.target.closest('button[data-action]');
            if (!btn) return;
            clearStatus();

            const action = btn.dataset.action;
            const userId = btn.dataset.id;

            if (action === 'rename') {{
                const currentUsername = btn.dataset.username || '';
                const newUsername = window.prompt(labels.promptUsername, currentUsername);
                if (newUsername === null) return;

                const res = await fetch(`/api/users/${{userId}}`, {{
                    method: 'PUT',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ username: newUsername.trim() }})
                }});
                const payload = await res.json().catch(() => ({{}}));
                if (!res.ok) {{
                    showStatus(payload.error || 'Error', true);
                    return;
                }}
                showStatus(payload.status || 'User updated');
                await fetchUsers();
                return;
            }}

            if (action === 'password') {{
                const password = window.prompt(labels.promptPassword, '');
                if (password === null) return;

                const res = await fetch(`/api/users/${{userId}}`, {{
                    method: 'PUT',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ password }})
                }});
                const payload = await res.json().catch(() => ({{}}));
                if (!res.ok) {{
                    showStatus(payload.error || 'Error', true);
                    return;
                }}
                showStatus(payload.status || 'Password updated');
                return;
            }}

            if (action === 'role') {{
                const currentRole = (btn.dataset.role || 'user').toLowerCase();
                const roleInput = window.prompt(labels.promptRole, currentRole);
                if (roleInput === null) return;

                const normalizedRole = roleInput.trim().toLowerCase();
                if (!['admin', 'user'].includes(normalizedRole)) {{
                    showStatus(labels.promptRole, true);
                    return;
                }}

                const res = await fetch(`/api/users/${{userId}}`, {{
                    method: 'PUT',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ role: normalizedRole }})
                }});
                const payload = await res.json().catch(() => ({{}}));
                if (!res.ok) {{
                    showStatus(payload.error || 'Error', true);
                    return;
                }}
                showStatus(payload.status || 'Role updated');
                await fetchUsers();
                return;
            }}

            if (action === 'token') {{
                const ttlRaw = window.prompt(labels.promptTokenTtl, '60');
                if (ttlRaw === null) return;
                const ttl = Number.parseInt(ttlRaw, 10);
                const ttlMinutes = Number.isFinite(ttl) ? ttl : 60;

                const res = await fetch('/api/telegram-link-token', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: Number(userId), ttl_minutes: ttlMinutes }})
                }});
                const payload = await res.json().catch(() => ({{}}));
                if (!res.ok) {{
                    showStatus(payload.error || 'Error', true);
                    return;
                }}
                showStatus(`${{labels.tokenCreated}}: ${{payload.token}}. ${{labels.tokenUsageHint}}`, false);
                return;
            }}

            if (action === 'unlink_tg') {{
                const res = await fetch(`/api/telegram-links/${{userId}}`, {{ method: 'DELETE' }});
                const payload = await res.json().catch(() => ({{}}));
                if (!res.ok) {{
                    showStatus(payload.error || 'Error', true);
                    return;
                }}
                showStatus(payload.status || 'Telegram link removed');
                await fetchUsers();
                return;
            }}

            if (action === 'delete') {{
                if (!window.confirm(labels.confirmDelete)) return;
                const res = await fetch(`/api/users/${{userId}}`, {{ method: 'DELETE' }});
                const payload = await res.json().catch(() => ({{}}));
                if (!res.ok) {{
                    showStatus(payload.error || labels.cannotDeleteSelf, true);
                    return;
                }}
                showStatus(payload.status || 'User deleted');
                await fetchUsers();
            }}
        }});

        fetchUsers();
    </script>
</body>
</html>
"""

# --- Icon Definitions ---
ICON_OPEN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>'
ICON_EDIT = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>'
ICON_DELETE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>'
ICON_READ = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
ICON_UNREAD = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle></svg>'
ICON_HN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>'
ICON_STAR_FILLED = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>'
ICON_STAR_EMPTY = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>'

def render_star_rating(bookmark_id, rating, translations):
    """Renders a 5-star inline rating control for a bookmark."""
    rating = rating or 0
    stars = []
    for value in range(1, 6):
        filled = value <= rating
        title = translations.get('tooltip_set_rating', 'Rate {n} stars').format(n=value)
        icon = ICON_STAR_FILLED if filled else ICON_STAR_EMPTY
        stars.append(f'<span class="star{" filled" if filled else ""}" data-value="{value}" title="{title}">{icon}</span>')
    return f'<div class="star-rating" data-id="{bookmark_id}" data-rating="{rating}">{"".join(stars)}</div>'

def render_bookmark_card(bookmark, translations):
    """Renders a single bookmark as an HTML card."""
    (id, url, title, description, image_url, domain, saved_at, telegram_user_id, telegram_message_id, comments_url, tags, is_read, rating) = bookmark
    
    def escape_html(text):
        if text is None: return ""  # noqa: E701
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')

    # Handle tags safely - they might be JSON string, empty, or invalid
    try:
        if isinstance(tags, str) and tags.strip():
            parsed_tags = json.loads(tags)
        elif isinstance(tags, (list, dict)):
            parsed_tags = tags
        else:
            parsed_tags = []
    except (json.JSONDecodeError, AttributeError):
        parsed_tags = []
    
    bookmark_data_json = json.dumps({
        'id': id, 'url': url, 'title': title, 'description': description,
        'image_url': image_url, 'comments_url': comments_url, 'is_read': is_read, 'tags': parsed_tags, 'rating': rating
    }, ensure_ascii=False)
    bookmark_json_html = bookmark_data_json.replace("\\", "\\\\").replace("'", "&#39;").replace('"', '&quot;')

    class_attr = f"bookmark-card {'read' if is_read else ''}".strip()
    read_button_title = translations.get("tooltip_mark_as_unread", "Mark as unread") if is_read else translations.get("tooltip_mark_as_read", "Mark as read")
    read_button_icon = ICON_READ if is_read else ICON_UNREAD

    return f"""
    <div id="bookmark-card-{id}" class="{class_attr}" data-id="{id}" data-is-read="{1 if is_read else 0}" data-bookmark-json="{bookmark_json_html}" hx-swap-oob="outerHTML">
        <div class="bookmark-main">
            <div class="bookmark-visuals">
                <div class="image-placeholder{'' if image_url else ' has-error'}">
                    {f'<img src="{escape_html(image_url)}" alt="Preview" class="bookmark-image">' if image_url else ''}
                </div>
                <div class="bookmark-actions">
                    <a href="{escape_html(url)}" target="_blank" class="icon-btn" title="{translations.get('tooltip_open_link', 'Open link')}">{ICON_OPEN}</a>                    
                    <button class="icon-btn read" data-id="{id}" title="{read_button_title}">{read_button_icon}</button>
                    <button 
                        class="icon-btn edit"
                        title="{translations.get('tooltip_edit', 'Edit')}"
                        data-bookmark-json="{bookmark_json_html}"
                        @click="$dispatch('open-edit-modal', $event.currentTarget.dataset.bookmarkJson)"
                    >{ICON_EDIT}</button>
                    <button class="icon-btn delete" data-id="{id}" title="{translations.get('tooltip_delete', 'Delete')}">{ICON_DELETE}</button>
                </div>
            </div>
            <div class="bookmark-details">
                <h3 class="bookmark-title"><a href="{escape_html(url)}" target="_blank">{escape_html(title)}</a></h3>
            </div>
        </div>
        <p class="bookmark-description">{escape_html(description)}</p>
        <div class="bookmark-tags">
            {''.join(f'<span class="tag">{escape_html(t)}</span>' for t in parsed_tags)}
        </div>
        {render_star_rating(id, rating, translations)}
        <div class="bookmark-footer">
            <div class="bookmark-footer-meta">
                <span class="bookmark-date">{saved_at.split(' ')[0]}</span>
                <span class="bookmark-id">ID {id}</span>
            </div>
            {f'<a href="{escape_html(comments_url)}" target="_blank" class="hn-link" title="{translations.get("tooltip_hn_comments", "View HN comments")}">{ICON_HN} HN Comments</a>' if comments_url else ''}
        </div>
    </div>
    """

def render_bookmark_compact_item(bookmark, translations):
    """Renders a single bookmark as a compact list item."""
    (id, url, title, _, image_url, domain, saved_at, telegram_user_id, telegram_message_id, comments_url, tags, is_read, rating) = bookmark

    def escape_html(text):
        if text is None: return ""  # noqa: E701
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')

    # include tags in compact item JSON
    try:
        if isinstance(tags, str) and tags.strip():
            compact_tags = json.loads(tags)
        elif isinstance(tags, (list, dict)):
            compact_tags = tags
        else:
            compact_tags = []
    except (json.JSONDecodeError, AttributeError):
        compact_tags = []
    bookmark_data_json = json.dumps({
        'id': id, 'url': url, 'title': title, 'description': _, 'image_url': image_url, 'comments_url': comments_url, 'is_read': is_read, 'tags': compact_tags, 'rating': rating
    }, ensure_ascii=False)
    bookmark_json_html = bookmark_data_json.replace("\\", "\\\\").replace("'", "&#39;").replace('"', '&quot;')

    class_attr = f"compact-item {'read' if is_read else ''}".strip()
    read_button_title = translations.get("tooltip_mark_as_unread", "Mark as unread") if is_read else translations.get("tooltip_mark_as_read", "Mark as read")
    read_button_icon = ICON_READ if is_read else ICON_UNREAD

    return f"""
    <div class="{class_attr}" data-id="{id}" data-is-read="{1 if is_read else 0}" id="bookmark-compact-{id}" data-bookmark-json="{bookmark_json_html}" hx-swap-oob="outerHTML">
        <div class="image-placeholder{'' if image_url else ' has-error'}">
            {f'<img src="{escape_html(image_url)}" alt="" class="compact-image">' if image_url else ''}
        </div>
        <div class="compact-content">
            <a href="{escape_html(url)}" target="_blank" class="compact-title" title="{escape_html(title)}">{escape_html(title)}</a>
            <span class="compact-domain">{escape_html(domain)}</span>
            <span class="compact-id">ID {id}</span>
            <div class="compact-tags">{''.join(f'<span class="tag">{escape_html(t)}</span>' for t in compact_tags)}</div>
            {render_star_rating(id, rating, translations)}
        </div>
        <div class="compact-date">{saved_at.split(' ')[0]}</div>
        <div class="compact-badges">
            {f'<a href="{escape_html(comments_url)}" target="_blank" class="hn-link" title="{translations.get("tooltip_hn_comments", "View HN comments")}">{ICON_HN}</a>' if comments_url else ''}
        </div>
        <div class="bookmark-actions">
            <button class="icon-btn read" data-id="{id}" title="{read_button_title}">{read_button_icon}</button>
            <button 
                class="icon-btn edit"
                title="{translations.get('tooltip_edit', 'Edit')}"
                data-bookmark-json="{bookmark_json_html}"
                @click="$dispatch('open-edit-modal', $event.currentTarget.dataset.bookmarkJson)"
            >{ICON_EDIT}</button>
            <button class="icon-btn delete" data-id="{id}" title="{translations.get('tooltip_delete', 'Delete')}">{ICON_DELETE}</button>
        </div>
    </div>
    """

def render_bookmarks(bookmarks, translations):
    """Renders a list of bookmarks into HTML cards."""
    if not bookmarks:
        return f"<p>{translations.get('no_bookmarks_found', 'No bookmarks found.')}</p>"
    return "".join(render_bookmark_card(b, translations) for b in bookmarks)

def render_bookmarks_compact(bookmarks, translations):
    """Renders a list of bookmarks into a compact HTML list."""
    if not bookmarks:
        return f"<p>{translations.get('no_bookmarks_found', 'No bookmarks found.')}</p>"
    return "".join(render_bookmark_compact_item(b, translations) for b in bookmarks)


def render_bookmark_card_export(bookmark, translations):
    """Renders a single bookmark as an HTML card for export (no action buttons)."""
    # Handle both tuple and dict formats
    if isinstance(bookmark, tuple):
        (id, url, title, description, image_url, domain, saved_at, telegram_user_id, telegram_message_id, comments_url, tags, is_read) = bookmark
    else:  # dict format
        id = bookmark['id']
        url = bookmark['url']
        title = bookmark['title']
        description = bookmark['description']
        image_url = bookmark['image_url']
        domain = bookmark['domain']
        saved_at = bookmark['saved_at']
        telegram_user_id = bookmark['telegram_user_id']
        telegram_message_id = bookmark['telegram_message_id']
        comments_url = bookmark['comments_url']
        tags = bookmark['tags']
        is_read = bookmark['is_read']
    
    def escape_html(text):
        if text is None: return ""  # noqa: E701
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')

    # Handle tags safely - they might be JSON string, empty, or invalid
    try:
        if isinstance(tags, str) and tags.strip():
            parsed_tags = json.loads(tags)
        elif isinstance(tags, (list, dict)):
            parsed_tags = tags
        else:
            parsed_tags = []
    except (json.JSONDecodeError, AttributeError):
        parsed_tags = []

    class_attr = f"bookmark-card {'read' if is_read else ''}".strip()
    read_button_title = translations.get("tooltip_mark_as_unread", "Mark as unread") if is_read else translations.get("tooltip_mark_as_read", "Mark as read")
    read_button_icon = ICON_READ if is_read else ICON_UNREAD

    return f"""
    <div id="bookmark-card-{id}" class="{class_attr}" data-id="{id}" data-is-read="{1 if is_read else 0}">
        <div class="bookmark-main">
            <div class="bookmark-visuals">
                <div class="image-placeholder{'' if image_url else ' has-error'}">
                    {f'<img src="{escape_html(image_url)}" alt="Preview" class="bookmark-image">' if image_url else ''}
                </div>
                <div class="bookmark-actions">
                    <a href="{escape_html(url)}" target="_blank" class="icon-btn" title="{translations.get('tooltip_open_link', 'Open link')}">{ICON_OPEN}</a>                    
                </div>
            </div>
            <div class="bookmark-details">
                <h3 class="bookmark-title"><a href="{escape_html(url)}" target="_blank">{escape_html(title)}</a></h3>
            </div>
        </div>
        <p class="bookmark-description">{escape_html(description)}</p>
        <div class="bookmark-tags">
            {''.join(f'<span class="tag">{escape_html(t)}</span>' for t in parsed_tags)}
        </div>
        <div class="bookmark-footer">
            <div class="bookmark-footer-meta">
                <span class="bookmark-date">{saved_at.split(' ')[0]}</span>
                <span class="bookmark-id">ID {id}</span>
            </div>
            {f'<a href="{escape_html(comments_url)}" target="_blank" class="hn-link" title="{translations.get("tooltip_hn_comments", "View HN comments")}">{ICON_HN} HN Comments</a>' if comments_url else ''}
        </div>
    </div>
    """


def render_bookmarks_export(bookmarks, translations):
    """Renders a list of bookmarks into HTML cards for export (no action buttons)."""
    if not bookmarks:
        return f"<p>{translations.get('no_bookmarks_found', 'No bookmarks found.')}</p>"
    return "".join(render_bookmark_card_export(b, translations) for b in bookmarks)


def build_export_html_document(html_content, total_count, generated_at):
    """Builds a complete HTML document for bookmark export."""
    generated_at_text = generated_at.strftime('%Y-%m-%d %H:%M:%S')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bookmarks Export</title>
    <link rel="stylesheet" href="/static/export-page.css">
</head>
<body>
    <div class="container">
        <h1>📚 Bookmarks Export</h1>
        <p class="export-info">Exported on {generated_at_text} | Total: {total_count} bookmarks</p>
        <div class="bookmarks-container">
            {html_content}
        </div>
    </div>
</body>
</html>"""

def get_html(self, bookmarks, version="N/A", total_count=0, translations={}, search_query=None, has_more=False, can_manage_users=False):
    # HTML escape function to avoid issues with quotes in data
    def escape_html(text):
        if text is None:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')

    search_value = escape_html(search_query)
    self.DEFAULT_PAGE_SIZE = 20 # Ensure this is consistent with server.py

    # Helper function to render the load more trigger
    def _render_load_more_trigger(current_visible_count, total_count_for_filters, translations, has_more_items):
        if has_more_items:
            next_offset = current_visible_count
            return f"""
            <div id="loadMoreTrigger" hx-get="/ui/bookmarks/scroll"
                 hx-trigger="revealed"
                 hx-swap="outerHTML"
                 hx-indicator="#loadingIndicator"
                 :hx-vals="getHtmxVals({next_offset})"
                 class="load-more-trigger">
                {translations.get('loading', 'Loading more bookmarks...')}
            </div>
            """
        else:
            return f"""
            <div id="loadMoreTrigger" class="load-more-trigger no-more-items">
                {translations.get('all_bookmarks_loaded', 'All bookmarks have been loaded.')}
            </div>
            """
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
    <link rel="stylesheet" href="/static/export-styles.css">
    <script src="https://cdn.jsdelivr.net/npm/@alpinejs/csp@3.x.x/dist/cdn.min.js" nonce="{self.nonce}" defer></script>
    <meta name="htmx-config" content='{{"defaultSwapTransition": false}}'>
    <script src="https://unpkg.com/htmx.org@1.9.10" integrity="sha384-D1Kt99CQMDuVetoL1lrYwg5t+9QdHe7NLX/SoJYkXDFfX37iInKRy5xLSi8nO7UC" crossorigin="anonymous" nonce="{self.nonce}"></script>
    <script nonce="{self.nonce}">
        // Define Alpine.js components. This script runs after Alpine.js is loaded.
        document.addEventListener('alpine:init', () => {{
            // Register a global magic property to unescape HTML entities.
            // The callback receives the component's root element, which we don't need here.
            Alpine.magic('unescapeHtml', () => (html) => {{
                const doc = new DOMParser().parseFromString(html, 'text/html');
                return doc.documentElement.textContent;
            }});

            Alpine.data('viewControls', () => ({{
                theme: 'light',
                view: 'cards',
                sortOrder: 'desc',
                hideRead: true,
                activeSpecialFilter: null,
                searchQuery: '{search_value}',
                getHtmxVals: function(offset = 0) {{
                    return JSON.stringify({{
                        'sort_order': this.sortOrder,
                        'hide_read': this.hideRead,
                        'filter_type': this.activeSpecialFilter,
                        'search_query': this.searchQuery,
                        'limit': {self.DEFAULT_PAGE_SIZE},
                        'offset': offset
                    }});
                }},
                init: function() {{
                    const savedTheme = localStorage.getItem('theme');
                    const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                    this.theme = savedTheme || (systemPrefersDark ? 'dark' : 'light');

                    const savedHideRead = localStorage.getItem('hideRead');
                    this.hideRead = savedHideRead !== null ? JSON.parse(savedHideRead) : true;

                    const savedSortOrder = localStorage.getItem('sortOrder');
                    this.sortOrder = savedSortOrder || 'desc';

                    const savedView = localStorage.getItem('view');
                    this.view = savedView || 'cards'; // Default to cards if not saved

                    // Apply theme to html tag initially
                    document.documentElement.classList.toggle('dark-mode', this.theme === 'dark');

                    // Watch for changes in searchQuery and trigger an htmx request.
                    // This is the CSP-compliant way to link Alpine state to htmx triggers.
                    this.$watch('searchQuery', (value) => {{
                        window.htmx.trigger('#searchBox', 'search');
                    }});
                }},
                toggleTheme: function() {{
                    this.theme = (this.theme === 'dark' ? 'light' : 'dark');
                    localStorage.setItem('theme', this.theme);
                    // Apply theme to html tag on change
                    document.documentElement.classList.toggle('dark-mode', this.theme === 'dark');
                }},
                toggleView: function() {{
                    this.view = (this.view === 'cards' ? 'compact' : 'cards');
                    // Persist view state
                    localStorage.setItem('view', this.view);
                    // No htmx request needed here, Alpine.js handles the class toggling
                }},
                toggleSort: function() {{
                    this.sortOrder = (this.sortOrder === 'desc' ? 'asc' : 'desc');
                    localStorage.setItem('sortOrder', this.sortOrder);
                    window.htmx.trigger('#searchBox', 'search');
                }},
                toggleHideRead: function() {{
                    this.hideRead = !this.hideRead;
                    localStorage.setItem('hideRead', this.hideRead);
                    window.htmx.trigger('#searchBox', 'search');
                }},
                toggleSpecialFilter: function(filter) {{
                    this.activeSpecialFilter = this.activeSpecialFilter === filter ? null : filter;
                    window.htmx.trigger('#searchBox', 'search');
                }},
                changeLanguage: function(event) {{
                    window.location.href = '/?lang=' + event.target.value;
                }}
            }}));

            Alpine.data('modalManager', () => ({{
                isOpen: false,
                isEditing: false,
                isLoading: false,
                bookmark: {{}},
                
                init: function() {{
                    // CSP-compliant way to handle htmx events.
                    // We listen for events on the form element itself.
                    this.$refs.form.addEventListener('htmx:afterRequest', (event) => {{
                        this.handleSuccess(event);
                    }});
                    this.$refs.form.addEventListener('htmx:error', (event) => {{
                        this.handleError(event);
                    }});
                }},

                openAdd: function() {{
                    this.isEditing = false;
                    this.bookmark = {{ id: '', url: '', title: '', description: '', image_url: '', comments_url: '', telegram_user_id: '', tags: '', is_read: false }};
                    this.isOpen = true;
                }},

                openEdit: function(bookmarkDataString) {{
                    this.isEditing = true;
                    const bookmarkData = JSON.parse(bookmarkDataString);
                    // Normalize tags to a comma-separated string for editing
                    let tagsStr = '';
                    if (bookmarkData.tags) {{
                        try {{
                            if (Array.isArray(bookmarkData.tags)) tagsStr = bookmarkData.tags.join(', ');
                            else if (typeof bookmarkData.tags === 'string' && bookmarkData.tags) tagsStr = bookmarkData.tags;
                        }} catch (e) {{ tagsStr = '' }}
                    }}
                    this.bookmark = {{ ...bookmarkData, tags: tagsStr, is_read: bookmarkData.is_read == 1 }};
                    this.isOpen = true;
                }},

                close: function() {{
                    this.isOpen = false;
                }},

                updateField: function(field, value) {{
                    this.bookmark[field] = value;
                }},

                submit: function() {{
                    // Use the standard fetch API for full control over the request.
                    const method = this.isEditing ? 'PUT' : 'POST';
                    const url = this.isEditing ? `/api/bookmarks/${{this.bookmark.id}}` : '/api/bookmarks';
                    
                    this.isLoading = true;
                    fetch(url, {{
                        method: method,
                        headers: {{ 'Content-Type': 'application/json', 'HX-Request': 'true' }},
                        body: JSON.stringify(this.bookmark)
                    }})
                    .then(response => {{
                        if (!response.ok) {{
                            return response.text().then(text => {{ throw new Error(text || 'Server error') }});
                        }}
                        return response.text();
                    }})
                    .then(html => {{
                        // The htmx functions for programmatic swapping (swap, settle, oobSwap) are not public API.
                        // The most robust solution is to manually parse the response and apply the OOB swaps.
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = html;
                        
                        // Find all elements in the response marked for OOB swap
                        const oobElements = tempDiv.querySelectorAll('[hx-swap-oob]');
                        oobElements.forEach(oobEl => {{
                            const target = document.getElementById(oobEl.id);
                            if (target) target.replaceWith(oobEl);
                        }});

                        this.handleSuccess({{ detail: {{ successful: true }} }});
                    }})
                    .catch(error => this.handleError({{ detail: {{ xhr: {{ responseText: error.message }} }} }}))
                    .finally(() => this.isLoading = false);
                }},

                handleSuccess: function(event) {{
                    // This is called by htmx's hx-on::after-request
                    if (!event.detail.successful) return; // Only proceed on success
                    this.close();
                    showToast(this.isEditing 
                        ? (window.TRANSLATIONS.toast_bookmark_updated_success || "Bookmark updated successfully!")
                        : (window.TRANSLATIONS.toast_bookmark_added_success || "Bookmark added successfully!")
                    );
                    // If adding, we might need to refresh the list to see the new item.
                    // A simple way is to re-trigger the search.
                    if (!this.isEditing) {{
                        htmx.trigger('#searchBox', 'search');
                    }}
                }},

                handleError: function(event) {{
                    // This is called by the htmx:error event listener.
                    // We make it robust by checking for the existence of properties.
                    let errorMsg = "Unknown server error";
                    if (event.detail && event.detail.xhr && event.detail.xhr.responseText) {{
                        errorMsg = event.detail.xhr.responseText;
                        try {{
                            const errorJson = JSON.parse(errorMsg);
                            if (errorJson.error === "URL already exists for another bookmark.") {{
                                errorMsg = window.TRANSLATIONS.toast_error_url_exists || errorJson.error;
                            }}
                        }} catch (e) {{
                            // Not a JSON error, use the raw text
                        }}
                    }}
                    showToast(`${{window.TRANSLATIONS.toast_error_prefix || 'Error: '}}${{errorMsg}}`, true);
                }},

                scrape: async function() {{
                    if (!this.bookmark.url) {{
                        showToast(window.TRANSLATIONS.toast_url_required_for_scrape || "Please enter a URL before scraping.", true);
                        return;
                    }}
                    // Add 'https://' if the protocol is missing
                    if (!this.bookmark.url.startsWith('http://') && !this.bookmark.url.startsWith('https://')) {{
                        this.bookmark.url = 'https://' + this.bookmark.url;
                        showToast(window.TRANSLATIONS.toast_protocol_added || "Protocol https:// automatically added.", false);
                    }}

                    this.isLoading = true;
                    try {{
                        const response = await fetch('/api/scrape', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ url: this.bookmark.url }}) }});
                        if (!response.ok) throw new Error('Scraping failed');
                        const metadata = await response.json();
                        this.bookmark.title = metadata.title || this.bookmark.title;
                        this.bookmark.description = metadata.description || this.bookmark.description;
                        this.bookmark.image_url = metadata.image_url || this.bookmark.image_url;
                        if (Array.isArray(metadata.tags) && metadata.tags.length > 0) {{
                            this.bookmark.tags = metadata.tags.join(', ');
                        }}
                        showToast(window.TRANSLATIONS.toast_metadata_scraped_success || "Metadata scraped successfully!", false);
                    }} catch (error) {{
                        showToast(window.TRANSLATIONS.toast_error_scraping_metadata || "Error during metadata scraping.", true);
                    }} finally {{
                        this.isLoading = false;
                    }}
                }}
            }}));

            Alpine.data('backToTop', () => ({{
                show: false,
                init: function() {{
                    window.addEventListener('scroll', () => this.show = window.scrollY > 300);
                }},
                goTop: function() {{
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                }}
            }}));
        }});
    </script>
</head>
<body x-data>
    <div class="container" x-data="viewControls">
        <h1>{translations.get('header', 'Bookmarks')}</h1>

        <div class="search-container">
            <input type="search" class="search-box" id="searchBox" name="search"
                   placeholder="{translations.get('search_placeholder', 'Search...')}"
                   value="{search_value}"
                   title="{translations.get('tooltip_search', 'Search...')}"
                   x-model="searchQuery"
                   x-ref="searchBox"
                   hx-get="/ui/bookmarks"
                   hx-trigger="keyup changed delay:500ms, search"
                   hx-target="body" 
                   hx-swap="none"
                   :hx-vals="getHtmxVals(0)"
            >
            <button type="button" id="clearSearchBtn" class="clear-search-btn" title="{translations.get('tooltip_clear_search', 'Clear search')}" x-show="searchQuery" @click="searchQuery = '';" x-cloak>&times;</button>
        </div>

        <!-- View controls -->
        <div class="view-controls">
            <button type="button" class="view-btn add-bookmark-btn" title="{translations.get('tooltip_add_bookmark', 'Add bookmark')}" @click="$dispatch('open-add-modal')">
                {translations.get('add_bookmark', 'Add Bookmark')}
            </button>
            <button type="button" class="view-btn" id="sortToggleBtn" 
                    title="{translations.get('tooltip_change_sort', 'Change sort order')}" 
                    x-on:click="toggleSort()" 
                    x-text="sortOrder === 'asc' ? '{translations.get('sort_oldest', 'Oldest First')}' : '{translations.get('sort_newest', 'Newest First')}'"
            ></button>
            <button type="button" class="view-btn" id="viewToggleBtn" title="{translations.get('tooltip_change_view', 'Change view')}" x-on:click="toggleView()" x-text="view === 'cards' ? '{translations.get('compact_view', 'Compact View')}' : '{translations.get('card_view', 'Card View')}'"></button>
            <button type="button" class="view-btn" id="themeToggleBtn" title="{translations.get('tooltip_change_theme', 'Change theme')}" x-on:click="toggleTheme()" x-text="theme === 'dark' ? '{translations.get('light_mode', 'Light Mode')}' : '{translations.get('dark_mode', 'Dark Mode')}'"></button>
            <select id="langSelector" class="view-btn" title="{translations.get('tooltip_change_language', 'Change language')}" @change="changeLanguage($event)">
                <option value="en" {'selected' if self.get_user_language() == 'en' else ''}>🇬🇧 English</option>
                <option value="it" {'selected' if self.get_user_language() == 'it' else ''}>🇮🇹 Italiano</option>
            </select>
            <span><small>v{version}</small></span>
        </div>

        <!-- Special filters -->
        <div class="special-filters">
            <button class="filter-btn" id="hideReadBtn"
                    @click="toggleHideRead()"
                    :class="hideRead ? 'active' : ''" 
                    title="{translations.get('tooltip_toggle_read', 'Toggle read...')}"
            >{translations.get('hide_read', 'Hide Read')}</button>
            {f'<a href="/users" class="filter-btn" title="{translations.get("tooltip_manage_users", "Manage users")}">{translations.get("manage_users", "Users")}</a>' if can_manage_users else ''}
            <div class="export-dropdown">
                <button class="filter-btn export-btn" title="{translations.get('tooltip_export', 'Export bookmarks...')}">
                    📤 {translations.get('export', 'Export')}
                </button>
                <div class="export-menu">
                    <a href="/api/export/csv" download="bookmarks.csv" title="{translations.get('tooltip_export_csv', 'Export to CSV...')}">
                        {translations.get('export_csv', 'CSV')}
                    </a>
                    <a href="/api/export/json" download="bookmarks.json" title="{translations.get('tooltip_export_json', 'Export to JSON...')}">
                        {translations.get('export_json', 'JSON')}
                    </a>
                    <a href="/api/export/html" download="bookmarks.html" title="{translations.get('tooltip_export_html', 'Export to HTML...')}">
                        {translations.get('export_html', 'HTML')}
                    </a>
                </div>
            </div>
            <a href="/logout" class="filter-btn" title="{translations.get('tooltip_logout', 'Logout...')}">{translations.get('logout', 'Logout')}</a>
        </div>

        <div class="filter-bar" id="filterBar">
            <!-- Filters will be populated dynamically -->
        </div>

        <div class="stats">
            <strong id="visibleCount">{len(bookmarks)}</strong> {translations.get('visible_of_total', 'of')} <strong id="totalCount">{total_count}</strong> {translations.get('total_bookmarks', 'total bookmarks')}
        </div>

        <div id="bookmarkViewsContainer">
            <!-- Normal view (cards) -->
            <div class="bookmarks-grid" :class="view === 'cards' ? '' : 'hidden'" id="bookmarksGrid">
                {render_bookmarks(bookmarks, translations)}
            </div>

            <!-- Compact view -->
            <div class="bookmarks-compact" :class="view === 'compact' ? '' : 'hidden'" id="bookmarksCompact">
                {render_bookmarks_compact(bookmarks, translations)}
            </div>
        </div>
        
        <div id="loadMoreContainer">{_render_load_more_trigger(len(bookmarks), total_count, translations, has_more)}</div>

        <div id="loadingIndicator">{translations.get('loading', 'Loading...')}</div>

        <footer>
            <p>Zitzu's Bookmarks Bot - v{version}</p>
        </footer>

        <!-- Edit modal -->
        <div x-data="modalManager" @open-add-modal.window="openAdd" @open-edit-modal.window="openEdit($event.detail)" @keydown.escape.window="close" x-show="isOpen" x-transition:enter="transition ease-out duration-300" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100" x-transition:leave="transition ease-in duration-200" x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0" class="modal" x-cloak>
            <div class="modal-content">
                <div class="modal-header">
                    <h3 x-text="isEditing ? '{translations.get('modal_edit_title', 'Edit Bookmark')}' : '{translations.get('modal_add_title', 'Add Bookmark')}'"></h3>
                    <span class="close-btn" @click="close" title="{translations.get('tooltip_close_modal', 'Close')}">&times;</span>
                </div>
                <div class="modal-body">
                    <form 
                        x-ref="form"
                        hx-ext="json-enc"
                    >
                        <template x-if="isEditing">
                            <input type="hidden" name="id" :value="bookmark.id">
                        </template>
                        <div class="form-group full-width-grid-column form-group-with-button">
                            <label for="edit-url">URL: *</label>
                            <div class="input-with-button">
                                <input type="url" id="edit-url" name="url" required title="{translations.get('tooltip_modal_url', 'URL...')}" :value="bookmark.url" @input="updateField('url', $event.target.value)">
                                <button type="button" class="btn btn-icon" @click="scrape" :disabled="isLoading" title="{translations.get('tooltip_scrape', 'Scrape...')}">
                                    <span x-show="!isLoading">✨</span>
                                    <span x-show="isLoading">⏳</span>
                                </button>
                            </div>
                        </div>
                        <div class="form-group full-width-grid-column">
                            <label for="edit-title">{translations.get('modal_label_title', 'Title')}:</label>
                            <input type="text" id="edit-title" name="title" title="{translations.get('tooltip_modal_title', 'Title...')}" :value="bookmark.title" @input="updateField('title', $event.target.value)">
                        </div>
                        <div class="form-group full-width-grid-column">
                            <label for="edit-image_url">{translations.get('modal_label_image_url', 'Image URL')}:</label>
                            <input type="url" id="edit-image_url" name="image_url" title="{translations.get('tooltip_modal_image', 'Image URL...')}" :value="bookmark.image_url" @input="updateField('image_url', $event.target.value)">
                        </div>
                        <div class="form-group full-width-grid-column">
                            <label for="edit-description">{translations.get('modal_label_description', 'Description')}:</label>
                            <textarea id="edit-description" name="description" rows="3" title="{translations.get('tooltip_modal_description', 'Description...')}" :value="bookmark.description" @input="updateField('description', $event.target.value)"></textarea>
                        </div>
                            <div class="form-group full-width-grid-column">
                            <label for="edit-comments_url">{translations.get('modal_label_hn_url', 'HackerNews URL')}:</label>
                            <input type="url" id="edit-comments_url" name="comments_url" title="{translations.get('tooltip_modal_hn_url', 'HN URL...')}" :value="bookmark.comments_url" @input="updateField('comments_url', $event.target.value)">
                        </div>
                            <div class="form-group full-width-grid-column">
                                <label for="edit-tags">{translations.get('modal_label_tags', 'Tags (comma-separated)')}:</label>
                                <input type="text" id="edit-tags" name="tags" title="{translations.get('tooltip_modal_tags', 'Tags...')}" :value="bookmark.tags" @input="updateField('tags', $event.target.value)">
                                <small>{translations.get('modal_help_tags', 'Separate tags with commas. Delete a tag by removing it from the field.')}</small>
                            </div>
                        <div class="form-group">
                            <label for="edit-telegram_user_id">{translations.get('modal_label_user_id', 'Telegram User ID')}:</label>
                            <input type="number" id="edit-telegram_user_id" name="telegram_user_id" title="{translations.get('tooltip_modal_user_id', 'User ID...')}" :value="bookmark.telegram_user_id" @input="updateField('telegram_user_id', $event.target.valueAsNumber)">
                        </div>
                        <div class="form-group form-group-checkbox">
                            <label><input type="checkbox" id="edit-is_read" name="is_read" value="true" title="{translations.get('tooltip_modal_is_read', 'Already read...')}" :checked="bookmark.is_read" @change="updateField('is_read', $event.target.checked)"> {translations.get('modal_label_is_read', 'Already read')}</label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button 
                        type="button" 
                        class="btn btn-primary" 
                        title="{translations.get('tooltip_save_changes', 'Save...')}"
                        @click="submit"
                    >
                        {translations.get('save_changes', 'Save Changes')}
                    </button>
                    <button type="button" class="btn btn-secondary" @click="close" title="{translations.get('tooltip_discard_changes', 'Cancel...')}">{translations.get('cancel', 'Cancel')}</button>
                </div>
            </div>
        </div>
    </div>

    <button
        type="button" id="backToTopBtn" title="{translations.get('tooltip_back_to_top', 'Back to top')}"
        x-data="backToTop"
        x-show="show" x-transition @click="goTop()" x-cloak
    >↑</button>

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