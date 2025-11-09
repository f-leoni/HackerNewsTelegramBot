import pytest
from unittest.mock import Mock

# Import functions from htmldata.py
from webserver.htmldata import (
    get_login_page,
    render_bookmark_card,
    render_bookmark_compact_item,
    render_bookmarks,
    render_bookmarks_compact,
    get_html
)

# --- Fixtures ---

@pytest.fixture
def sample_bookmark():
    """A sample bookmark tuple for testing."""
    # Corresponds to: id, url, title, description, image_url, domain, saved_at, _, _, comments_url, is_read
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
        0  # Not read
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