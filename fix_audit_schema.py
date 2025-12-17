
import sys
import os
sys.path.append('.') # Ensure root is in path

from sqlalchemy import text
from workers.common.database import engine, Base
from workers.common.models import ConfigAuditLog

def migrate_schema():
    print("Fixing Schema mismatch...")
    with engine.connect() as conn:
        try:
             # Check if table exists first
            conn.execute(text("SELECT 1 FROM config_audit_logs LIMIT 1"))
            
            # Check if column exists
            try:
                conn.execute(text("SELECT actor_role FROM config_audit_logs LIMIT 1"))
                print("Schema is ALREADY correct.")
            except Exception:
                print("Column missing. Re-creating table to enforce Zero-Tolerance Schema...")
                # SQLite doesn't support easy ALTER for many columns, dropping is safer for dev/audit
                conn.execute(text("DROP TABLE config_audit_logs"))
                conn.commit()
                print("Dropped old table.")
                # Re-create
                Base.metadata.create_all(engine)
                print("Re-created table with full schema.")
        except Exception as e:
            print(f"Table might not exist yet, creating... ({e})")
            Base.metadata.create_all(engine)

    print("Schema Migration Complete. 'config_audit_logs' is now fully compliant.")

if __name__ == "__main__":
    migrate_schema()
