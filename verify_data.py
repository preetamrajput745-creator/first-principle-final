import sys
import os
import json

# Add workers to path
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db
from common.models import Signal

def verify():
    print("TRIPLE CHECK: Verifying Database Integrity...")
    
    with next(get_db()) as db:
        # Get latest 5 signals
        signals = db.query(Signal).order_by(Signal.timestamp.desc()).limit(5).all()
        
        if not signals:
            print("No signals found in database!")
            return

        print(f"Found {len(signals)} recent signals.")
        
        for s in signals:
            print(f"\nSignal ID: {s.id}")
            print(f"Symbol: {s.symbol} | Type: {s.payload.get('type')} | Price: {s.payload.get('price')}")
            
            # Check 1: Slippage Logic
            if s.estimated_slippage is not None and s.execution_price is not None:
                print(f"Estimated Slippage: {s.estimated_slippage}")
                print(f"Execution Price: {s.execution_price}")
                
                # Logic Check
                expected_price = s.payload.get('price') + s.estimated_slippage if s.payload.get('type') == 'BUY' else s.payload.get('price') - s.estimated_slippage
                diff = abs(expected_price - s.execution_price)
                if diff < 0.01:
                    print("Slippage Calculation Verified (Math is correct)")
                else:
                    print(f"Slippage Math Mismatch! Expected {expected_price}, Got {s.execution_price}")
            else:
                print("Missing slippage/execution data!")
                
            # Check 3: L1 Snapshot & Drift
            if s.l1_snapshot:
                print(f"L1 Snapshot Present (Source Clock: {s.l1_snapshot.get('source_clock')})")
                
                # Verify Drift
                if s.clock_drift_ms is not None:
                     print(f"Clock Drift: {s.clock_drift_ms:.3f}ms")
                     if s.clock_drift_ms < 100:
                         print("Drift Status: OK (Stable)")
                     else:
                         print("Drift Status: WARNING (High Latency)")
                else:
                     print("Missing clock_drift_ms!")
                     
                print(f"   Bid: {s.l1_snapshot.get('bid')} | Ask: {s.l1_snapshot.get('ask')} | Vol: {s.l1_snapshot.get('volume')}")
            else:
                print("Missing L1 Snapshot!")

if __name__ == "__main__":
    verify()
