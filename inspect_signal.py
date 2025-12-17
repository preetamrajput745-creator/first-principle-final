
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add workers path
sys.path.append(os.path.join(os.getcwd(), 'workers'))

from common.models import Signal
from common.database import get_db

def inspect_latest_signal():
    print("INSPECTING LATEST SIGNAL...")
    with next(get_db()) as db:
        sig = db.query(Signal).order_by(Signal.created_at.desc()).first()
        if sig:
            print(f"ID: {sig.id}")
            print(f"Symbol: {sig.symbol}")
            print(f"L2 Path: {sig.l2_snapshot_path}")
            print(f"L1 Snapshot (Sample): {str(sig.l1_snapshot)[:50]}...")
        else:
            print("No signals found.")

if __name__ == "__main__":
    inspect_latest_signal()
