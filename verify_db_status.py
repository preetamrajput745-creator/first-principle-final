import sys
from workers.common.database import SessionLocal, engine
from sqlalchemy import text

def check_db():
    print("Checking Database Integrity...")
    db = SessionLocal()
    try:
        # Check connection
        db.execute(text("SELECT 1"))
        print("[OK] Database Connection")
        
        # Check Tables
        tables = ["automations", "signals", "orders", "config_audit_logs", "backtests"]
        for t in tables:
            try:
                count = db.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                print(f"[OK] Table '{t}': Exists (Rows: {count})")
            except Exception as e:
                print(f"[FAIL] Table '{t}': MISSING or ERROR ({e})")
                sys.exit(1)
                
    except Exception as e:
        print(f"[FAIL] Database Critical Error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    check_db()
