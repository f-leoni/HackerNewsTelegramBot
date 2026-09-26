"""
Recovery utility for web users.
Allows password reset and optional admin role restore.
"""
import argparse
import getpass
import os
import sqlite3
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import get_db_path, init_database


def _load_password_hash_generator():
    try:
        from werkzeug.security import generate_password_hash
    except ImportError:
        print("ERROR: Missing dependency 'werkzeug'.")
        print("Install with: pip install werkzeug")
        sys.exit(1)
    return generate_password_hash


def _list_users(cursor):
    cursor.execute("SELECT id, username, role FROM users ORDER BY id ASC")
    return cursor.fetchall()


def _select_user(cursor, user_id=None, username=None):
    if user_id is not None:
        cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()

    if username:
        cursor.execute("SELECT id, username, role FROM users WHERE username = ? COLLATE NOCASE", (username,))
        return cursor.fetchone()

    users = _list_users(cursor)
    if not users:
        return None

    print("\nAvailable users:")
    for uid, uname, role in users:
        print(f"- ID={uid} username={uname} role={role}")

    raw = input("\nEnter user ID to recover: ").strip()
    try:
        selected_id = int(raw)
    except ValueError:
        return None

    cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (selected_id,))
    return cursor.fetchone()


def _read_new_password():
    password = getpass.getpass("Enter new password: ")
    confirm = getpass.getpass("Confirm new password: ")

    if not password:
        print("ERROR: Password cannot be empty.")
        return None

    if len(password) < 6:
        print("ERROR: Password must be at least 6 characters.")
        return None

    if password != confirm:
        print("ERROR: Passwords do not match.")
        return None

    return password


def main():
    parser = argparse.ArgumentParser(description="Recover a user account (password reset and admin restore).")
    parser.add_argument("--user-id", type=int, help="Target user ID")
    parser.add_argument("--username", help="Target username (case-insensitive)")
    parser.add_argument("--password-only", action="store_true", help="Reset password only")
    parser.add_argument("--promote-admin", action="store_true", help="Promote target user to admin")
    args = parser.parse_args()

    if args.user_id is not None and args.username:
        print("ERROR: Use either --user-id or --username, not both.")
        sys.exit(1)

    generate_password_hash = _load_password_hash_generator()

    init_database()
    db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        user = _select_user(cursor, args.user_id, args.username)
        if not user:
            print("ERROR: User not found.")
            sys.exit(1)

        user_id, username, role = user
        print(f"\nSelected user: ID={user_id} username={username} role={role}")

        if not args.password_only and not args.promote_admin:
            print("\nChoose operation:")
            print("1) Reset password")
            print("2) Promote to admin")
            print("3) Reset password and promote to admin")
            choice = input("Select 1, 2, or 3: ").strip()
            do_password = choice in ("1", "3")
            do_promote = choice in ("2", "3")
        else:
            do_password = True
            do_promote = bool(args.promote_admin)

        if do_password:
            new_password = _read_new_password()
            if not new_password:
                sys.exit(1)
            password_hash = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
            print("Password updated.")

        if do_promote:
            cursor.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
            print("User promoted to admin.")

        conn.commit()
        print("\nRecovery operation completed successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
