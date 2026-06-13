import pytest
import sqlite3
from unittest.mock import Mock

from telegram_bot.bot import BookmarkBot
from shared.database import init_database

# --- Unit Tests for Helper Functions ---

@pytest.fixture
def bot_instance():
    """Fixture to get an instance of the BookmarkBot for testing its methods."""
    # We can initialize it without auth for testing synchronous methods.
    return BookmarkBot.__new__(BookmarkBot)

def test_extract_urls_simple(bot_instance):
    """Tests extracting a single, simple URL."""
    text = "Check this out: https://www.example.com"
    urls = bot_instance.extract_urls(text)
    assert urls == ["https://www.example.com"]

def test_extract_urls_multiple(bot_instance):
    """Tests extracting multiple URLs from a message."""
    text = "Here are two links: http://test.org and https://another.site/page?q=1."
    urls = bot_instance.extract_urls(text)
    assert "http://test.org" in urls
    assert "https://another.site/page?q=1" in urls

def test_extract_urls_no_protocol(bot_instance):
    """Tests that 'https://' is added to URLs without a protocol."""
    text = "A link without protocol: www.google.com"
    urls = bot_instance.extract_urls(text)
    assert urls == ["https://www.google.com"]

def test_extract_urls_with_punctuation(bot_instance):
    """Tests that trailing punctuation is correctly removed."""
    text = "Look at this link: https://site.com/path! Isn't it cool?"
    urls = bot_instance.extract_urls(text)
    assert urls == ["https://site.com/path"]

def test_extract_urls_no_urls(bot_instance):
    """Tests that an empty list is returned when no URLs are present."""
    text = "This is just a regular message with no links."
    urls = bot_instance.extract_urls(text)
    assert urls == []

def test_get_hn_comments_url(bot_instance):
    """Tests the Hacker News comments URL extraction."""
    hn_url = "https://news.ycombinator.com/item?id=12345"
    assert bot_instance.get_hn_comments_url(hn_url) == hn_url

def test_get_hn_comments_url_not_hn(bot_instance):
    """Tests that non-HN URLs return None."""
    other_url = "https://www.example.com"
    assert bot_instance.get_hn_comments_url(other_url) is None


# --- Integration Tests for Database Interaction ---

@pytest.fixture
def db_for_bot(mocker):
    """
    Fixture to set up an in-memory database for bot tests.
    It mocks get_db_path to ensure all DB operations use the in-memory DB.
    """
    db_uri = 'file:bot_test_db?mode=memory&cache=shared' # Use a unique name to avoid conflicts
    conn = sqlite3.connect(db_uri, uri=True, detect_types=sqlite3.PARSE_DECLTYPES)
    
    # Mock the get_db_path function to return our in-memory URI
    mocker.patch('telegram_bot.bot.get_db_path', return_value=db_uri)

    # Initialize schema and create a web user to associate bookmarks with
    init_database(conn)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                   (1, 'webuser', 'somehash'))
    conn.commit()

    yield conn

    conn.close()

def test_save_bookmark_integration(bot_instance, db_for_bot):
    """
    Tests that the save_bookmark method correctly saves a bookmark to the database.
    """
    # 1. Prepare mock data
    mock_message = Mock()
    mock_message.from_user.id = 12345
    mock_message.id = 54321

    metadata = {
        "title": "Integration Test Bookmark",
        "description": "A test description.",
        "image_url": "https://test.com/image.png",
        "domain": "test.com"
    }
    url_to_save = "https://test.com/article"

    # 2. Call the method to be tested
    success = bot_instance.save_bookmark(url_to_save, metadata, mock_message)

    # 3. Assert the results
    assert success is True

    # 4. Verify the data was actually written to the in-memory database
    cursor = db_for_bot.cursor()
    cursor.execute("SELECT * FROM bookmarks WHERE url = ?", (url_to_save,))
    saved_data = cursor.fetchone()

    assert saved_data is not None
    # Columns: id, user_id, url, title, description, image_url, domain, tags, saved_at, telegram_user_id, telegram_message_id, ...
    assert saved_data[1] == 1  # Associated with web_user_id 1
    assert saved_data[2] == url_to_save
    assert saved_data[3] == "Integration Test Bookmark"
    assert saved_data[9] == 12345 # telegram_user_id
    assert saved_data[10] == 54321 # telegram_message_id
