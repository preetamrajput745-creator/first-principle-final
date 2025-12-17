import sys
import os
from sqlalchemy import text

# Add workers to path
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import engine, Base
from workers.common.models import ConfigAuditLog, User, Automation, Signal, Order, Backtest, SlippageProfile, VaultAccessLog, CircuitBreakerState, CircuitBreakerEvent

def migrate_db():
    print("Migrating Database...")
    
    # 1. Base Create All (Handles new tables like VaultAccessLog, Backtest, CircuitBreakerState/Event)
    Base.metadata.create_all(bind=engine)
    
    # ... existing column migrations logic ...
    # (Leaving it since they might have run already, but duplicate runs are safe due to try/catch)
    
    # 2. Check/Add 'second_approver' to ConfigAuditLog (Mistake 5/8)
    try:
         with engine.connect() as conn:
            conn.execute(text("SELECT second_approver FROM config_audit_logs LIMIT 1"))
    except Exception:
        print("Migrating: Adding 'second_approver' to config_audit_logs...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE config_audit_logs ADD COLUMN second_approver VARCHAR"))
            conn.commit()
            print("Added 'second_approver'.")

    # 3. Mistake #11: Add l2_snapshot_path
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT l2_snapshot_path FROM signals LIMIT 1"))
    except Exception:
        print("Adding 'l2_snapshot_path'...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE signals ADD COLUMN l2_snapshot_path TEXT"))
            conn.commit()
            print("Added 'l2_snapshot_path'.")

    # 4. Mistake #12: Add regime columns
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT regime_volatility FROM signals LIMIT 1"))
    except Exception:
        print("Adding regime columns...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE signals ADD COLUMN regime_volatility TEXT DEFAULT 'normal'"))
            conn.execute(text("ALTER TABLE signals ADD COLUMN regime_session TEXT DEFAULT 'mid'"))
            conn.commit()
            print("Added regime columns.")

    print("Migration complete.")

if __name__ == "__main__":
    migrate_db()
