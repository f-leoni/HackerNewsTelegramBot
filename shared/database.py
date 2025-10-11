"""
Modulo per la gestione centralizzata del database SQLite.
Contiene la logica per l'inizializzazione e la migrazione dello schema.
"""
import os
import sqlite3
import logging

__version__ = "1.0"
logger = logging.getLogger(__name__)


def get_db_path():
    """Restituisce il percorso assoluto del file di database."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "bookmarks.db")


def init_database():
    """
    Inizializza il database, crea la tabella se non esiste ed esegue le migrazioni.
    Questa è l'unica fonte di verità per lo schema del DB.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            description TEXT,
            image_url TEXT,
            domain TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            telegram_user_id INTEGER,
            telegram_message_id INTEGER,
            comments_url TEXT,
            is_read INTEGER DEFAULT 0
        )
    """)

    # Logica di migrazione
    try:
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = [col[1] for col in cursor.fetchall()]
        if "telegram_user_id" not in columns: cursor.execute("ALTER TABLE bookmarks ADD COLUMN telegram_user_id INTEGER")
        if "comments_url" not in columns: cursor.execute("ALTER TABLE bookmarks ADD COLUMN comments_url TEXT")
        if "is_read" not in columns: cursor.execute("ALTER TABLE bookmarks ADD COLUMN is_read INTEGER DEFAULT 0")
    except Exception as e:
        logger.warning("Could not perform database migration: %s", e)

    conn.commit()
    logger.info("Database inizializzato: %s", db_path)
    return conn