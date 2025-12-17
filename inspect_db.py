import sqlite3
import os

db_files = [f for f in os.listdir(".") if f.startswith("app_admin_log") and f.endswith(".db")]
if db_files:
    db_file = db_files[-1]
    print(f"Inspecting {db_file}")
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print(c.fetchall())
    
    # Also inspect columns if we find a table
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    for t in tables:
        print(f"Schema for {t[0]}:")
        c.execute(f"PRAGMA table_info({t[0]})")
        print(c.fetchall())
    conn.close()
else:
    print("No DB file found.")
