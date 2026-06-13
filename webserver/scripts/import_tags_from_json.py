#!/usr/bin/env python3
"""
Script to import tags from a JSON file into the bookmarks database.
Usage:
  python scripts/import_tags_from_json.py --file bookmarks_tags.json
  python scripts/import_tags_from_json.py --file bookmarks_tags.json --dry-run
"""
import argparse
import sqlite3
import json
from pathlib import Path
import sys

# Ensure shared package is importable
SCRIPT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(SCRIPT_DIR))

from shared.database import get_db_path, init_database


def main():
    parser = argparse.ArgumentParser(description="Import tags from JSON file to bookmarks")
    parser.add_argument('--file', required=True, help='JSON file containing tags')
    parser.add_argument('--dry-run', action='store_true', help='Do not write changes to the DB')
    args = parser.parse_args()

    # Check if file exists
    if not Path(args.file).exists():
        print(f"Error: File '{args.file}' not found")
        sys.exit(1)

    # Load the JSON file
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("Error: JSON file must contain an array of objects with 'id' and 'tags'")
        sys.exit(1)

    # Connect to database
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    init_database(conn)
    cursor = conn.cursor()

    updated = 0
    skipped = 0
    errors = 0

    for item in data:
        if not isinstance(item, dict) or 'id' not in item or 'tags' not in item:
            print(f"Warning: Skipping malformed entry: {item}")
            skipped += 1
            continue

        bid = item['id']
        tags = item['tags']

        if not isinstance(tags, list):
            print(f"Warning: Tags for ID {bid} is not a list, skipping")
            skipped += 1
            continue

        try:
            tags_json = json.dumps(tags, ensure_ascii=False)
            if not args.dry_run:
                cursor.execute("UPDATE bookmarks SET tags = ? WHERE id = ?", (tags_json, bid))
            print(f"ID {bid}: {tags}")
            updated += 1
        except Exception as e:
            print(f"Error updating ID {bid}: {e}")
            errors += 1

    if not args.dry_run:
        conn.commit()
        print(f"\n[OK] Updated {updated} bookmarks in DB")
    else:
        print(f"\n[DRY-RUN] Would update {updated} bookmarks")

    if skipped > 0:
        print(f"[SKIP] Skipped {skipped} entries")
    if errors > 0:
        print(f"[ERROR] Errors: {errors}")

    conn.close()


if __name__ == '__main__':
    main()
