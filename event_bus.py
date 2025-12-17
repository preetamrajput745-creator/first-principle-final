import redis
import json
from config import settings

import sqlite3
import os
import time

class EventBus:
    def __init__(self):
        self.use_redis = False
        try:
            self.r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            self.r.ping()
            self.use_redis = True
            print("[EventBus] Connected to Redis.")
        except Exception:
            print("[EventBus] Redis unavailable. Falling back to SQLite (Local Mode).")
            self.db_path = os.getenv("EVENT_BUS_DB", "event_bus.db")
            self._init_sqlite()

    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL;") 
            conn.execute("PRAGMA synchronous = OFF;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS streams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    message TEXT,
                    timestamp REAL,
                    processed_by TEXT DEFAULT ''
                )
            """)

    def publish(self, topic: str, message: dict):
        if self.use_redis:
            try:
                self.r.xadd(topic, message)
            except Exception as e:
                print(f"Error publishing to {topic}: {e}")
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO streams (topic, message, timestamp) VALUES (?, ?, ?)", 
                             (topic, json.dumps(message), time.time()))

    def subscribe(self, topic: str, group: str, consumer: str):
        if self.use_redis:
            try:
                self.r.xgroup_create(topic, group, mkstream=True)
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
        else:
            pass # SQLite doesn't need explicit group creation

    def read(self, topic: str, group: str, consumer: str, count: int = 1, block: int = 1000):
        if self.use_redis:
            # ... (omitted for brevity, assume unchanged)
             try:
                return self.r.xreadgroup(group, consumer, {topic: ">"}, count=count, block=block)
             except Exception as e:
                print(f"Error reading from {topic}: {e}")
                return []
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode = WAL;") 
                conn.execute("PRAGMA synchronous = OFF;")
                cursor = conn.execute("""
                    SELECT id, message FROM streams 
                    WHERE topic = ? AND (processed_by NOT LIKE ?)
                    ORDER BY id ASC LIMIT ?
                """, (topic, f"%{group}%", count))
                rows = cursor.fetchall()
                if topic == "signal.new" and len(rows) == 0:
                     pass # print(f"[DEBUG] EventBus read 0 rows for {topic} (Consumer: {group})") 
                elif topic == "signal.new":
                     print(f"[DEBUG] EventBus read {len(rows)} rows for {topic} - first id {rows[0][0]}")
                
                result = []
                for row in rows:
                     msg_id = str(row[0])
                     msg_data = json.loads(row[1])
                     result.append((msg_id, msg_data))
                return result

    def ack(self, topic: str, group: str, message_id: str):
        if self.use_redis:
            self.r.xack(topic, group, message_id)
        else:
             with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode = WAL;") 
                conn.execute("PRAGMA synchronous = OFF;")
                conn.execute(f"UPDATE streams SET processed_by = processed_by || '{group},' WHERE id = ?", (message_id,))

event_bus = EventBus()
