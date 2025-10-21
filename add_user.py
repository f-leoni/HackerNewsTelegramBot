"""
Script per aggiungere un nuovo utente al database per il login al webserver.
"""
import os
import sys
import getpass
import sqlite3

# Aggiungi la root del progetto al path per importare i moduli condivisi
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from shared.database import get_db_path, init_database

def add_user():
    """Aggiunge un utente al database in modo interattivo."""
    try:
        from werkzeug.security import generate_password_hash
    except ImportError:
        print("ERRORE: La libreria 'werkzeug' non è installata.")
        print("Esegui: pip install werkzeug")
        sys.exit(1)

    print("--- Creazione nuovo utente per il webserver ---")
    username = input("Inserisci il nome utente: ").strip()
    password = getpass.getpass("Inserisci la password: ")
    password_confirm = getpass.getpass("Conferma la password: ")

    if not username or not password:
        print("❌ Nome utente e password non possono essere vuoti.")
        return

    if password != password_confirm:
        print("❌ Le password non coincidono.")
        return

    password_hash = generate_password_hash(password)
    db_path = get_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        print(f"✅ Utente '{username}' creato con successo!")
    except sqlite3.IntegrityError:
        print(f"❌ Errore: L'utente '{username}' esiste già.")
    finally:
        conn.close()

if __name__ == '__main__':
    init_database() # Assicura che la tabella esista
    add_user()