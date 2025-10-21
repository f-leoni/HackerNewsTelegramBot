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
    # Il percorso della cartella che contiene questo script (es. /app/shared)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Il database deve trovarsi nella sottocartella 'db'
    db_dir = os.path.join(script_dir, "db")
    os.makedirs(db_dir, exist_ok=True) # Assicura che la cartella esista
    return os.path.join(db_dir, "bookmarks.db")


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

    # Crea la tabella degli utenti
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # Crea la tabella delle sessioni
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Logica di migrazione
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
    logger.info("Database inizializzato: %s", db_path)
    return conn