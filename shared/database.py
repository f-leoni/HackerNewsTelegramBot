"""
Module for centralized SQLite database management.
Contains the logic for schema initialization and migration.
"""
import os
import sqlite3
import logging
from datetime import datetime

__version__ = "1.0"
logger = logging.getLogger(__name__)

# --- Datetime Adapters for SQLite ---
# As of Python 3.12, the default datetime adapters are deprecated.
# We register explicit adapters to ensure future compatibility.

def adapt_datetime_iso(val):
    """Adapter to convert datetime object to ISO 8601 string."""
    return val.isoformat()

def convert_timestamp(val):
    """Converter to parse ISO 8601 string back to datetime object."""
    return datetime.fromisoformat(val.decode())

sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("timestamp", convert_timestamp)

def get_db_path():
    """Returns the absolute path of the database file."""
    # The path of the folder containing this script (e.g., /app/shared)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # The database must be in the 'db' subfolder
    db_dir = os.path.join(script_dir, "db")
    os.makedirs(db_dir, exist_ok=True) # Ensure the folder exists
    return os.path.join(db_dir, "bookmarks.db")


def init_database(conn=None):
    """
    Initializes the database, creates the table if it doesn't exist, and runs migrations.
    This is the single source of truth for the DB schema.
    If a connection object is passed, it uses it; otherwise, it creates a new one.
    """
    # If no connection is passed, create a new one. The caller is responsible for closing it.
    if conn is None:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT NOT NULL,
            title TEXT,
            description TEXT,
            image_url TEXT,
            domain TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            telegram_user_id INTEGER,
            telegram_message_id INTEGER,
            comments_url TEXT,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, url)
        )
    """)

    # Create the users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # Create the sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Migration logic
    try:
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = [col[1] for col in cursor.fetchall()]
        if "telegram_user_id" not in columns: cursor.execute("ALTER TABLE bookmarks ADD COLUMN telegram_user_id INTEGER")
        if "comments_url" not in columns: cursor.execute("ALTER TABLE bookmarks ADD COLUMN comments_url TEXT")
        if "is_read" not in columns: cursor.execute("ALTER TABLE bookmarks ADD COLUMN is_read INTEGER DEFAULT 0")
        if "user_id" not in columns: cursor.execute("ALTER TABLE bookmarks ADD COLUMN user_id INTEGER")
    except Exception as e:
        logger.warning("Could not perform database migration: %s", e)

    conn.commit()
    return conn