"""
Verification: Mistake #11 - L2 Snapshots
Ensures every signal has a compressed orderbook snapshot available for debugging.
"""

import sys
import os
import uuid
import uuid
from datetime import datetime

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from common.database import get_db
from common.models import Signal, Automation
from ingestion.l2_recorder import L2Recorder

def verify_l2_snapshots():
    print("TEST: L2 Snapshot Integrity (Mistake #11)")
    print("=" * 60)
    
    recorder = L2Recorder()
    automation_id = uuid.uuid4()
    
    # Create dummy automation for FK
    with next(get_db()) as db:
        auto = Automation(id=automation_id, name="L2 Tester", slug=f"l2-test-{str(uuid.uuid4())[:6]}")
        db.add(auto)
        db.commit()

    generated_ids = []
    
    print("1. Generating 10 Signals with Compressed L2 Snapshots...")
    with next(get_db()) as db:
        for i in range(10):
            # Simulate Strategy Logic
            mid_price = 100.0 + i
            l2_data = recorder.generate_simulated_l2(mid_price)
            
            sig_id = uuid.uuid4()
            
            # STORE SNAPSHOT (Critical Step)
            path = recorder.store_snapshot(l2_data, str(sig_id))
            
            # Create Signal
            sig = Signal(
                id=sig_id,
                automation_id=automation_id,
                symbol="L2_TEST_SYM",
                timestamp=datetime.utcnow(),
                score=0.9,
                payload={"action": "BUY"},
                l1_snapshot=l2_data, # Legacy field (can keep small version)
                l2_snapshot_path=path, # NEW field,
                clock_drift_ms=0.5 # Simulated Drift
            )
            db.add(sig)
            generated_ids.append((sig_id, path))
            print(f"   Signal {i+1}: Stored snapshot at {os.path.basename(path)}")
        db.commit()
        
    print("\n2. Verifying Loadability & Decompression...")
    failures = 0
    with next(get_db()) as db:
        for sig_id, original_path in generated_ids:
            # Reload from DB to ensure path was saved
            sig = db.query(Signal).filter(Signal.id == sig_id).first()
            
            if not sig.l2_snapshot_path:
                print(f"   FAILURE: Signal {sig_id} missing path in DB!")
                failures += 1
                continue
                
            try:
                # Attempt to load
                data = recorder.load_snapshot(sig.l2_snapshot_path)
                
                # Check contents
                bids = data.get("bids", [])
                asks = data.get("asks", [])
                
                if len(bids) > 0 and len(asks) > 0:
                    # Success
                    pass
                else:
                    print(f"   FAILURE: Signal {sig_id} snapshot empty!")
                    failures += 1
            except Exception as e:
                print(f"   FAILURE: Could not load snapshot for {sig_id}: {e}")
                failures += 1

    if failures == 0:
        print("\nSUCCESS: All 10 signals have valid, loadable L2 snapshots.")
        print("VERIFICATION COMPLETE.")
    else:
        print(f"\nFAILURE: {failures}/10 snapshots failed verification.")
        sys.exit(1)

if __name__ == "__main__":
    verify_l2_snapshots()
