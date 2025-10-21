"""
Script to add a new user to the database for webserver login.
"""
import os
import sys
import getpass
import sqlite3

# Add the project root to the path to import shared modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from shared.database import get_db_path, init_database

def add_user():
    """Adds a user to the database interactively."""
    try:
        from werkzeug.security import generate_password_hash
    except ImportError:
        print("ERROR: The 'werkzeug' library is not installed.")
        print("Run: pip install werkzeug")
        sys.exit(1)

    print("--- Creating a new user for the webserver ---")
    username = input("Enter username: ").strip()
    password = getpass.getpass("Enter password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if not username or not password:
        print("❌ Username and password cannot be empty.")
        return

    if password != password_confirm:
        print("❌ Passwords do not match.")
        return

    password_hash = generate_password_hash(password)
    db_path = get_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        print(f"✅ User '{username}' created successfully!")
    except sqlite3.IntegrityError:
        print(f"❌ Error: User '{username}' already exists.")
    finally:
        conn.close()

if __name__ == '__main__':
    init_database() # Ensure the table exists
    add_user()