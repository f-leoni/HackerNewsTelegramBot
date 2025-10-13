# migrate_bookmarks.py
import sqlite3
import os
import sys

# Aggiungi la root del progetto al path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from shared.database import init_database

def migrate_existing_bookmarks():
    """Assegna tutti i bookmark senza utente al primo utente trovato nel DB."""
    print("Inizializzazione e migrazione dello schema del database...")
    # Chiama init_database() per assicurarsi che lo schema sia aggiornato
    conn = init_database()
    cursor = conn.cursor()
    try:
        # Trova il primo utente
        cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        first_user = cursor.fetchone()

        if not first_user:
            print("❌ Nessun utente trovato nel database. Esegui prima 'add_user.py'.")
            return

        first_user_id = first_user[0]
        print(f"Trovato primo utente con ID: {first_user_id}")

        # Aggiorna tutti i bookmark che non hanno un user_id
        cursor.execute("UPDATE bookmarks SET user_id = ? WHERE user_id IS NULL", (first_user_id,))
        
        updated_rows = cursor.rowcount
        conn.commit()

        if updated_rows > 0:
            print(f"✅ Migrazione completata: {updated_rows} bookmark sono stati assegnati all'utente {first_user_id}.")
        else:
            print("ℹ️ Nessun bookmark da migrare.")

    except Exception as e:
        print(f"ERRORE durante la migrazione: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_existing_bookmarks()
