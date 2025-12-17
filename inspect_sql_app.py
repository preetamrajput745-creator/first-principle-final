import sqlite3
import os

db_path = 'sql_app.db'
if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    # Check if orders/fills exist
    for t in tables:
        if 'orders' in t[0] or 'fills' in t[0]:
            print(f"--- Schema for {t[0]} ---")
            cursor.execute(f"PRAGMA table_info({t[0]})")
            print(cursor.fetchall())
            cursor.execute(f"SELECT count(*) FROM {t[0]}")
            print(f"Count: {cursor.fetchone()[0]}")
    
    conn.close()
