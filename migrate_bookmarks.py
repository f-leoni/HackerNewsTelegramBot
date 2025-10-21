# migrate_bookmarks.py
import sqlite3
import os
import sys

# Add the project root to the path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from shared.database import init_database

def migrate_existing_bookmarks():
    """Assigns all bookmarks without a user to the first user found in the DB."""
    print("Initializing and migrating the database schema...")
    # Call init_database() to ensure the schema is up-to-date
    conn = init_database()
    cursor = conn.cursor()
    try:
        # Find the first user
        cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        first_user = cursor.fetchone()

        if not first_user:
            print("❌ No user found in the database. Run 'add_user.py' first.")
            return

        first_user_id = first_user[0]
        print(f"Found first user with ID: {first_user_id}")

        # Update all bookmarks that do not have a user_id
        cursor.execute("UPDATE bookmarks SET user_id = ? WHERE user_id IS NULL", (first_user_id,))
        
        updated_rows = cursor.rowcount
        conn.commit()

        if updated_rows > 0:
            print(f"✅ Migration completed: {updated_rows} bookmarks have been assigned to user {first_user_id}.")
        else:
            print("ℹ️ No bookmarks to migrate.")

    except Exception as e:
        print(f"ERROR during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_existing_bookmarks()
