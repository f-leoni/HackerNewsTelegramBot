# migrate_bookmarks.py
import sqlite3
import os
import sys

# Add the project root to the path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from shared.database import init_database

def migrate_existing_bookmarks():
    """Assigns legacy bookmarks (user_id NULL) to the first user found in the DB.

    Returns:
        int: process exit code (0 on success, 1 on error).
    """
    print("Initializing and migrating the database schema...")
    # Call init_database() to ensure the schema is up-to-date
    conn = init_database()
    cursor = conn.cursor()
    try:
        # Find the first user
        cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        first_user = cursor.fetchone()

        if not first_user:
            # Expected on a fresh install: the schema exists but no user has been
            # created yet. Not an error, so exit 0 to keep startup idempotent.
            print("ℹ️ No user found in the database yet. Run 'add_user.py' and then re-run this script.")
            return 0

        first_user_id = first_user[0]
        print(f"Found first user with ID: {first_user_id}")

        # Resolve per-row so a URL that already exists for the owner does not
        # abort the whole migration with an IntegrityError.
        cursor.execute("SELECT id, url FROM bookmarks WHERE user_id IS NULL ORDER BY id")
        orphans = cursor.fetchall()

        updated_rows = 0
        skipped_rows = 0
        for bookmark_id, url in orphans:
            cursor.execute(
                "SELECT 1 FROM bookmarks WHERE user_id = ? AND url = ? AND id <> ?",
                (first_user_id, url, bookmark_id),
            )
            if cursor.fetchone():
                # Leave the orphan untouched: it is not visible to any user and
                # deleting bookmarks automatically would be destructive.
                skipped_rows += 1
                continue
            cursor.execute("UPDATE bookmarks SET user_id = ? WHERE id = ?", (bookmark_id,))
            updated_rows += cursor.rowcount

        conn.commit()

        print(f"✅ Migration completed: {updated_rows} bookmarks have been assigned to user {first_user_id}.")
        if skipped_rows:
            print(
                f"⚠️  {skipped_rows} legacy bookmarks were left unassigned because the user "
                "already owns the same URL. Review them manually if needed."
            )
        if not orphans:
            print("ℹ️ No bookmarks to migrate.")
        return 0

    except Exception as e:
        conn.rollback()
        print(f"ERROR during migration: {e}")
        return 1
    finally:
        conn.close()

if __name__ == '__main__':
    sys.exit(migrate_existing_bookmarks())
