# add_user.py
import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

# Aggiungi la root del progetto al path per importare la libreria condivisa
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from shared.database import init_database

def add_user(username, password):
    """Aggiunge un nuovo utente o aggiorna la password di un utente esistente."""
    # Chiama init_database() per assicurarsi che lo schema sia aggiornato
    conn = init_database()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        # Prova a inserire un nuovo utente
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        print(f"✅ Utente '{username}' aggiunto con successo!")
    except sqlite3.IntegrityError:
        # Se l'utente esiste già, aggiorna la sua password
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
        print(f"🔑 Password per l'utente '{username}' aggiornata con successo!")
    finally:
        conn.commit()
        conn.close()

if __name__ == '__main__':
    print("--- Gestione Utenti ---")
    uname = input("Inserisci il nome utente: ")
    pword = input("Inserisci la nuova password: ")
    if uname and pword:
        add_user(uname, pword)
    else:
        print("❌ Nome utente e password non possono essere vuoti.")
