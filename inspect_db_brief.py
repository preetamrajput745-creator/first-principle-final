import sqlite3
import pandas as pd
import datetime

try:
    conn = sqlite3.connect("sql_app.db")
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    
    if ('signals',) in tables:
        print("\n--- Signals (Last 5) ---")
        cursor.execute("SELECT * FROM signals ORDER BY timestamp_utc DESC LIMIT 5")
        cols = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        if rows:
            print(pd.DataFrame(rows, columns=cols))
        else:
            print("No rows in signals.")

    if ('signal_snapshots',) in tables:
        print("\n--- Signal Snapshots (Count) ---")
        cursor.execute("SELECT count(*) FROM signal_snapshots")
        print(cursor.fetchone()[0])

except Exception as e:
    print(e)
finally:
    if 'conn' in locals():
        conn.close()
