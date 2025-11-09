import pytest
import sqlite3
import os
from datetime import datetime

# Import the functions to be tested
from shared.database import get_db_path, init_database, adapt_datetime_iso, convert_timestamp


def test_get_db_path_returns_correct_structure():
    """
    Tests that get_db_path returns a path ending with the expected structure.
    """
    path = get_db_path()
    # We use os.path.join to make the test OS-agnostic
    expected_end = os.path.join("shared", "db", "bookmarks.db")
    assert path.endswith(expected_end)


def test_datetime_adapters():
    """
    Tests the custom datetime adapters for SQLite.
    """
    now = datetime.now()
    
    # Test adapter
    iso_string = adapt_datetime_iso(now)
    assert isinstance(iso_string, str)
    
    # Test converter
    # The converter expects bytes, so we encode the string
    converted_datetime = convert_timestamp(iso_string.encode('utf-8'))
    assert isinstance(converted_datetime, datetime)
    
    # Check if the converted datetime is almost identical (ignoring microseconds precision loss)
    assert abs((now - converted_datetime).total_seconds()) < 0.001


@pytest.fixture
def mock_db_path(mocker):
    """
    Pytest fixture that mocks get_db_path to use an in-memory SQLite database.
    This isolates database tests from the file system.
    """
    # Use a shared in-memory database that persists across connections in the same test
    db_uri = 'file:memdb_test_db?mode=memory&cache=shared'
    conn = sqlite3.connect(db_uri, uri=True, detect_types=sqlite3.PARSE_DECLTYPES)
    yield conn # Yield the connection object
    conn.close() # Teardown: close the connection after tests


def test_init_database_creates_tables(mock_db_path):
    """
    Tests that init_database creates all the necessary tables.
    """
    # Pass the connection from the fixture to init_database
    conn = init_database(mock_db_path)
    cursor = conn.cursor() # This will now work as conn is open

    # Query sqlite_master to check for table existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    assert 'users' in tables
    assert 'sessions' in tables
    assert 'bookmarks' in tables
    

def test_init_database_creates_all_columns(mock_db_path):
    """
    Tests that init_database creates all expected columns in the tables,
    implicitly testing the migration logic as well.
    """
    # Pass the connection from the fixture to init_database
    conn = init_database(mock_db_path)
    cursor = conn.cursor()

    # Check columns for the 'bookmarks' table
    cursor.execute("PRAGMA table_info(bookmarks)")
    bookmark_columns = {row[1] for row in cursor.fetchall()}
    expected_bookmark_columns = {'id', 'user_id', 'url', 'title', 'description', 'image_url', 'domain', 'saved_at', 'telegram_user_id', 'telegram_message_id', 'comments_url', 'is_read'}
    assert expected_bookmark_columns.issubset(bookmark_columns)