import pytest
import json
from unittest.mock import Mock
from datetime import datetime

# Import functions from htmldata.py
from webserver.htmldata import (
    get_login_page,
    render_bookmark_card,
    render_bookmark_compact_item,
    render_bookmarks,
    render_bookmarks_compact,
    get_html,
    build_export_html_document,
)

# --- Fixtures ---

@pytest.fixture
def sample_bookmark():
    """A sample bookmark tuple for testing."""
    # Corresponds to: id, url, title, description, image_url, domain, saved_at,
    #                 telegram_user_id, telegram_message_id, comments_url, tags, is_read, rating
    return (
        1,
        "https://example.com",
        "Test Title",
        "Test Description",
        "https://example.com/image.jpg",
        "example.com",
        "2023-10-27 10:00:00",
        None,
        None,
        None,
        None,  # tags
        0,  # Not read
        0  # rating
    )

@pytest.fixture
def sample_translations():
    """A sample translations dictionary."""
    return {
        "no_bookmarks_found": "No bookmarks here.",
        "tooltip_open_link": "Open link",
        "tooltip_edit": "Edit",
        "tooltip_delete": "Delete",
        "tooltip_mark_as_read": "Mark as read",
        "page_title": "Test Bookmarks",
        "header": "My Bookmarks",
    }

@pytest.fixture
def mock_handler():
    """A mock handler object that simulates the BookmarkHandler."""
    handler = Mock()
    handler.nonce = "test-nonce-123"
    handler.get_user_language.return_value = 'en'
    return handler

# --- Tests for Rendering Functions ---

def test_render_bookmark_card(sample_bookmark, sample_translations):
    """Tests that a single bookmark card is rendered correctly."""
    html = render_bookmark_card(sample_bookmark, sample_translations)
    
    assert 'class="bookmark-card"' in html
    assert 'data-id="1"' in html
    assert 'href="https://example.com"' in html
    assert ">Test Title</a>" in html
    assert ">Test Description</p>" in html
    assert 'src="https://example.com/image.jpg"' in html
    assert 'title="Mark as read"' in html

def test_render_bookmark_card_with_hn_link(sample_bookmark, sample_translations):
    """Tests that the HN comments link is rendered if present."""
    bookmark_with_hn = sample_bookmark[:9] + ("https://news.ycombinator.com/item?id=123",) + sample_bookmark[10:]
    html = render_bookmark_card(bookmark_with_hn, sample_translations)
    
    assert 'href="https://news.ycombinator.com/item?id=123"' in html
    assert 'class="hn-link"' in html

def test_render_bookmark_compact_item(sample_bookmark, sample_translations):
    """Tests that a single compact item is rendered correctly."""
    html = render_bookmark_compact_item(sample_bookmark, sample_translations)

    assert 'class="compact-item"' in html
    assert 'data-id="1"' in html
    assert 'href="https://example.com"' in html
    assert 'class="compact-title"' in html
    assert ">Test Title</a>" in html

def test_render_bookmarks_with_items(sample_bookmark, sample_translations):
    """Tests rendering a list of bookmarks."""
    bookmarks = [sample_bookmark, sample_bookmark]
    html = render_bookmarks(bookmarks, sample_translations)
    
    assert html.count('class="bookmark-card"') == 2

def test_render_bookmarks_empty(sample_translations):
    """Tests rendering an empty list of bookmarks."""
    html = render_bookmarks([], sample_translations)
    assert "No bookmarks here." in html

def test_render_bookmarks_compact_empty(sample_translations):
    """Tests rendering an empty list in compact view."""
    html = render_bookmarks_compact([], sample_translations)
    assert "No bookmarks here." in html


# --- Tests for Page Generation Functions ---

def test_get_login_page(mock_handler):
    """Tests the login page generation."""
    html = get_login_page(mock_handler)
    assert '<title>Login - Zitzu\'s Bookmarks</title>' in html
    assert 'action="/login"' in html
    assert 'name="username"' in html
    assert 'name="password"' in html
    assert 'class="login-error"' not in html # No error by default

def test_get_login_page_with_error(mock_handler):
    """Tests the login page with an error message."""
    html = get_login_page(mock_handler, error="Invalid credentials")
    assert 'class="login-error">Invalid credentials</div>' in html

def test_get_html_main_page(mock_handler, sample_bookmark, sample_translations):
    """Tests the main HTML page structure."""
    bookmarks = [sample_bookmark]
    html = get_html(mock_handler, bookmarks, version="2.0", total_count=1, translations=sample_translations, has_more=False)

    # Check main components
    assert '<title>Test Bookmarks</title>' in html
    assert '<h1>My Bookmarks</h1>' in html
    assert 'id="searchBox"' in html
    assert 'id="bookmarksGrid"' in html
    assert 'id="bookmarksCompact"' in html
    
    # Check that the bookmark is rendered
    assert 'class="bookmark-card"' in html
    assert ">Test Title</a>" in html

    # Check nonce is used
    assert 'nonce="test-nonce-123"' in html

    # Check "load more" trigger
    assert 'id="loadMoreTrigger"' in html
    assert 'All bookmarks have been loaded.' in html # Because has_more=False

def test_get_html_has_more_bookmarks(mock_handler, sample_translations):
    """Tests that the 'load more' trigger shows a loading message when has_more is True."""
    html = get_html(mock_handler, [], version="2.0", total_count=10, translations={"loading": "Loading..."}, has_more=True)
    
    assert 'hx-trigger="revealed"' in html
    assert '>Loading...</div>' in html


def test_build_export_html_document_includes_expected_wrapper():
    generated_at = datetime(2026, 6, 28, 12, 30, 0)
    html = build_export_html_document('<div>CONTENT</div>', total_count=3, generated_at=generated_at)
    assert '<title>Bookmarks Export</title>' in html
    assert '/static/export-page.css' in html
    assert 'Total: 3 bookmarks' in html
    assert '2026-06-28 12:30:00' in html
    assert '<div>CONTENT</div>' in html


# --- JSON payload embedded in HTML attributes ---

def _extract_bookmark_json(html, bookmark_id):
    """Extracts and decodes the data-bookmark-json attribute of a rendered bookmark."""
    import html as html_module
    import json as json_module
    import re

    pattern = rf'data-bookmark-json="([^"]*)"'
    matches = re.findall(pattern, html)
    payloads = [json_module.loads(html_module.unescape(value)) for value in matches]
    for payload in payloads:
        if payload.get('id') == bookmark_id:
            return payload
    raise AssertionError(f"data-bookmark-json for id {bookmark_id} not found")


def test_card_json_survives_quotes_and_backslashes(sample_translations):
    """Titles with quotes and backslashes must not break JSON.parse on the client.

    Regression: escaping backslashes for the HTML attribute turned \" into \\",
    which terminated the JSON string early and left the Edit button dead.
    """
    bookmark = (
        7,
        'https://example.com/a',
        'The "Best" C:\\ path',
        'He said "hello" and left',
        None,
        'example.com',
        '2026-01-01 10:00:00',
        None,
        None,
        None,
        json.dumps(['tag "one"']),
        0,
        0,
    )

    payload = _extract_bookmark_json(render_bookmark_card(bookmark, sample_translations), 7)

    assert payload['title'] == 'The "Best" C:\\ path'
    assert payload['description'] == 'He said "hello" and left'
    assert payload['tags'] == ['tag "one"']


def test_compact_json_survives_quotes_and_backslashes(sample_translations):
    """Same regression check for the compact list view."""
    bookmark = (
        8,
        'https://example.com/b',
        'Quotes "here"',
        'Backslash \\ and quote "',
        None,
        'example.com',
        '2026-01-01 10:00:00',
        None,
        None,
        None,
        '[]',
        1,
        3,
    )

    payload = _extract_bookmark_json(render_bookmark_compact_item(bookmark, sample_translations), 8)

    assert payload['title'] == 'Quotes "here"'
    assert payload['description'] == 'Backslash \\ and quote "'
    assert payload['is_read'] == 1
    assert payload['rating'] == 3