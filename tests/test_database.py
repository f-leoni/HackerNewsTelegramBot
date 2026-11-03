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
    assert 'telegram_user_links' in tables
    assert 'telegram_link_tokens' in tables
    

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
    expected_bookmark_columns = {'id', 'user_id', 'url', 'title', 'description', 'image_url', 'domain', 'saved_at', 'telegram_user_id', 'telegram_message_id', 'comments_url', 'is_read', 'rating'}
    assert expected_bookmark_columns.issubset(bookmark_columns)


def _legacy_bookmarks_connection():
    """Builds an in-memory DB shaped like the pre-constraint multi-user schema.

    This is the state left behind by `ALTER TABLE ... ADD COLUMN user_id` plus the
    backfill script: two users, duplicates allowed, no UNIQUE(user_id, url), no FK.
    """
    conn = sqlite3.connect("file:memdb_legacy?mode=memory&cache=shared", uri=True, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT NOT NULL,
            title TEXT,
            description TEXT,
            image_url TEXT,
            domain TEXT,
            tags TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            telegram_user_id INTEGER,
            telegram_message_id INTEGER,
            comments_url TEXT,
            is_read INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT INTO users (username, password_hash) VALUES ('legacy', 'hash')")
    # Duplicate (user_id, url) pairs that the rebuild must collapse.
    cursor.execute("INSERT INTO bookmarks (user_id, url) VALUES (1, 'https://legacy.example/dup')")
    cursor.execute("INSERT INTO bookmarks (user_id, url) VALUES (1, 'https://legacy.example/dup')")
    cursor.execute("INSERT INTO bookmarks (user_id, url) VALUES (1, 'https://legacy.example/other')")
    conn.commit()
    return conn


def test_legacy_schema_gets_tenant_constraints():
    """An upgraded DB must end up with UNIQUE(user_id, url) and collapsed duplicates."""
    conn = _legacy_bookmarks_connection()
    try:
        init_database(conn)
        cursor = conn.cursor()

        cursor.execute("PRAGMA index_list(bookmarks)")
        unique_indexes = [
            row[1] for row in cursor.fetchall() if row[2]
        ]
        assert unique_indexes, "bookmarks should have a UNIQUE index after migration"

        cursor.execute("SELECT COUNT(*) FROM bookmarks")
        assert cursor.fetchone()[0] == 2

        # The constraint is now enforced.
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO bookmarks (user_id, url) VALUES (1, 'https://legacy.example/dup')")
        conn.rollback()
    finally:
        conn.close()


def test_init_database_is_idempotent_on_migrated_schema():
    """Running init_database twice must not rebuild or duplicate anything."""
    conn = _legacy_bookmarks_connection()
    try:
        init_database(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bookmarks")
        first_count = cursor.fetchone()[0]

        init_database(conn)
        cursor.execute("SELECT COUNT(*) FROM bookmarks")
        assert cursor.fetchone()[0] == first_count

        cursor.execute("PRAGMA user_version")
        assert cursor.fetchone()[0] == 2
    finally:
        conn.close()