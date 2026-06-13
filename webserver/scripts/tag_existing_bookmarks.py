#!/usr/bin/env python3
"""
Batch script to generate tags for existing bookmarks using the local extractor.
Usage:
  python scripts/tag_existing_bookmarks.py --dry-run --limit 50
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
from shared.utils import generate_tags


def main():
    parser = argparse.ArgumentParser(description="Generate tags for existing bookmarks")
    parser.add_argument('--dry-run', action='store_true', help='Do not write changes to the DB')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of bookmarks processed (0 = all)')
    parser.add_argument('--min-empty', action='store_true', help='Only process bookmarks with empty or null tags')
    args = parser.parse_args()

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    # Ensure the bookmarks schema is up to date before reading rows.
    init_database(conn)
    cursor = conn.cursor()

    query = "SELECT id, title, description, tags FROM bookmarks"
    rows = cursor.execute(query).fetchall()

    to_process = []
    for r in rows:
        bid, title, desc, tags = r
        if args.min_empty:
            if tags and str(tags).strip():
                continue
        to_process.append((bid, title or '', desc or '', tags))

    if args.limit and args.limit > 0:
        to_process = to_process[:args.limit]

    print(f"Processing {len(to_process)} bookmarks (dry-run={args.dry_run})")

    for bid, title, desc, existing_tags in to_process:
        combined = f"{title}\n{desc}"
        tags = generate_tags(combined, n=3)
        print(f"{bid}: {tags}")
        if not args.dry_run:
            tags_json = json.dumps(tags, ensure_ascii=False)
            cursor.execute("UPDATE bookmarks SET tags = ? WHERE id = ?", (tags_json, bid))

    if not args.dry_run:
        conn.commit()
        print("Changes committed to DB.")
    else:
        print("Dry-run complete. No changes were written.")

    conn.close()

if __name__ == '__main__':
    main()
