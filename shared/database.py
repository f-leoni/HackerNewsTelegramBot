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

# Bumped whenever the physical schema changes in a way that needs migration.
SCHEMA_VERSION = 2

BOOKMARKS_COLUMNS = (
    "id",
    "user_id",
    "url",
    "title",
    "description",
    "image_url",
    "domain",
    "tags",
    "saved_at",
    "telegram_user_id",
    "telegram_message_id",
    "comments_url",
    "is_read",
    "rating",
)


def _bookmarks_table_ddl(table_name="bookmarks"):
    """Returns the bookmarks DDL for the given table name."""
    return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
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
            rating INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, url)
        )
    """

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


def connect_db(db_path=None, timeout=5.0, check_same_thread=True):
    """
    Opens a SQLite connection with the pragmas required by a multi-process setup.

    - busy_timeout: waits instead of failing immediately with "database is locked"
    - journal_mode=WAL: lets the bot and the webserver read/write concurrently
    - foreign_keys=ON: makes ON DELETE CASCADE actually work
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(
        path,
        timeout=timeout,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=check_same_thread,
        uri=str(path).startswith("file:"),
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.Error as exc:
        logger.warning("Could not enable WAL journal mode: %s", exc)
    return conn


def _has_unique_user_url_index(cursor):
    """Returns True when bookmarks has a UNIQUE index on (user_id, url)."""
    cursor.execute("PRAGMA index_list(bookmarks)")
    for row in cursor.fetchall():
        if not row[2]:
            continue
        index_name = row[1]
        cursor.execute(f"PRAGMA index_info('{index_name}')")
        columns = [info[2] for info in cursor.fetchall()]
        if columns == ["user_id", "url"]:
            return True
    return False


def _rebuild_bookmarks_with_tenant_constraints(cursor):
    """
    Rebuilds the bookmarks table when it was created by an older version.

    SQLite cannot add UNIQUE or FOREIGN KEY constraints with ALTER TABLE, so
    databases upgraded from the single-user schema lack both. Duplicate
    (user_id, url) rows are collapsed keeping the most recent one.
    """
    columns = ", ".join(BOOKMARKS_COLUMNS)
    cursor.execute(f"SELECT {columns} FROM bookmarks ORDER BY id DESC")
    rows = cursor.fetchall()

    cursor.execute("DROP TABLE IF EXISTS bookmarks_migrated")
    cursor.execute(_bookmarks_table_ddl("bookmarks_migrated"))
    placeholders = ", ".join(["?"] * len(BOOKMARKS_COLUMNS))
    insert_sql = f"INSERT OR IGNORE INTO bookmarks_migrated ({columns}) VALUES ({placeholders})"

    inserted = 0
    for row in rows:
        cursor.execute(insert_sql, tuple(row))
        inserted += cursor.rowcount

    cursor.execute("DROP TABLE bookmarks")
    cursor.execute("ALTER TABLE bookmarks_migrated RENAME TO bookmarks")
    dropped = len(rows) - inserted
    logger.info(
        "Rebuilt bookmarks table with tenant constraints: %s rows kept, %s duplicate rows dropped",
        inserted,
        dropped,
    )


def init_database(conn=None):
    """
    Initializes the database, creates the table if it doesn't exist, and runs migrations.
    This is the single source of truth for the DB schema.
    If a connection object is passed, it uses it; otherwise, it creates a new one.
    """
    # If no connection is passed, create a new one. The caller is responsible for closing it.
    if conn is None:
        conn = connect_db(check_same_thread=False)
    cursor = conn.cursor()

    # Create the users table first: bookmarks references it.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user'))
        )
    """)

    cursor.execute(_bookmarks_table_ddl())

    # Create the sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Create the telegram links table (1:1 between web user and Telegram user)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telegram_user_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            telegram_user_id INTEGER NOT NULL UNIQUE,
            linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Create one-time token table used for Telegram account linking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telegram_link_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP,
            used_telegram_user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Migration logic
    try:
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = [col[1] for col in cursor.fetchall()]
        if "telegram_user_id" not in columns:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN telegram_user_id INTEGER")
        if "comments_url" not in columns:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN comments_url TEXT")
        if "tags" not in columns:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN tags TEXT")
        if "is_read" not in columns:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN is_read INTEGER DEFAULT 0")
        if "rating" not in columns:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN rating INTEGER DEFAULT 0")
        if "user_id" not in columns:
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN user_id INTEGER")

        # Older databases were created without UNIQUE(user_id, url) and without
        # the users FK, because ALTER TABLE cannot add constraints.
        if not _has_unique_user_url_index(cursor):
            _rebuild_bookmarks_with_tenant_constraints(cursor)

        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        if "role" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")

        cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'telegram_user_links'")
        if cursor.fetchone() is None:
            cursor.execute("""
                CREATE TABLE telegram_user_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    telegram_user_id INTEGER NOT NULL UNIQUE,
                    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

        cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'telegram_link_tokens'")
        if cursor.fetchone() is None:
            cursor.execute("""
                CREATE TABLE telegram_link_tokens (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_at TIMESTAMP,
                    used_telegram_user_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telegram_link_tokens_user_id ON telegram_link_tokens(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telegram_link_tokens_expires_at ON telegram_link_tokens(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telegram_user_links_telegram_user_id ON telegram_user_links(telegram_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user_id ON bookmarks(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")

        if not _has_unique_user_url_index(cursor):
            logger.error(
                "bookmarks still lacks UNIQUE(user_id, url) after migration. "
                "A concurrent process may hold a lock; restart the service to retry."
            )

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        if admin_count == 0:
            # Bootstrap: promote the oldest user to admin when no admin exists.
            cursor.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1")
            first_user = cursor.fetchone()
            if first_user:
                cursor.execute("UPDATE users SET role = 'admin' WHERE id = ?", (first_user[0],))
    except Exception as e:
        logger.warning("Could not perform database migration: %s", e)

    try:
        cursor.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")
    except sqlite3.Error as e:
        logger.warning("Could not set schema version: %s", e)

    conn.commit()
    return conn