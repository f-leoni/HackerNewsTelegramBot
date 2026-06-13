#!/usr/bin/env python3
import sys
sys.path.append(r'd:\Progetti\HackerNewsTelegramBot')
from shared.database import get_db_path, init_database
import sqlite3

path = get_db_path()
conn = sqlite3.connect(path)
init_database(conn)
cur = conn.cursor()

# Check some of the newly added tags
rows = cur.execute('SELECT id, tags FROM bookmarks WHERE id IN (844, 850, 856, 864) ORDER BY id').fetchall()
print('Newly imported bookmarks:')
for r in rows:
    print(f'  ID {r[0]}: {r[1]}')

total = cur.execute('SELECT COUNT(*) FROM bookmarks WHERE tags IS NOT NULL AND tags != ""').fetchone()[0]
print(f'\nTotal bookmarks with tags: {total}')

conn.close()
