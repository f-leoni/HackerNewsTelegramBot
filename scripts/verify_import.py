#!/usr/bin/env python3
import os, sys, sqlite3, json
sys.path.append(r'd:\Progetti\HackerNewsTelegramBot')
from shared.database import get_db_path, init_database

path = get_db_path()
conn = sqlite3.connect(path)
init_database(conn)
cur = conn.cursor()

rows = cur.execute('SELECT id, tags FROM bookmarks WHERE tags IS NOT NULL AND tags != "" LIMIT 5').fetchall()
print('Sample of updated bookmarks:')
for r in rows:
    print(f'  ID {r[0]}: {r[1]}')

total = cur.execute('SELECT COUNT(*) FROM bookmarks WHERE tags IS NOT NULL AND tags != ""').fetchone()[0]
print(f'\nTotal bookmarks with tags: {total}')

conn.close()
