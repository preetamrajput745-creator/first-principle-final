"""
Verification: Mistake #3 - Clock Metrics
Ensures drift is being recorded in the database (metrics).
"""

import sys
import os
import time

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from common.database import get_db
from common.models import Signal

def verify_clock_metrics():
    print("TEST: Clock Norm & Drift Metrics (Mistake #3)")
    print("=" * 60)
    
    with next(get_db()) as db:
        # Check last 10 signals
        signals = db.query(Signal).order_by(Signal.timestamp.desc()).limit(10).all()
        
        if not signals:
            print("   WARNING: No signals found. Run the system to generate data first.")
            return

        pass_count = 0
        for s in signals:
            drift = s.clock_drift_ms
            # We expect drift to be float number. 
            # In simulation, it might be 0.0 if very fast, but let's check it exists.
            
            print(f"   Signal {str(s.id)[:8]} | Timestamp: {s.timestamp} | Drift: {drift} ms")
            
            if drift is not None:
                pass_count += 1
                
        if pass_count == 10:
             print("\nSUCCESS: All recent signals have recorded Clock Drift metrics.")
        else:
             print(f"\nFAILURE: Only {pass_count}/10 signals have drift metrics.")
             sys.exit(1)
             
    print("VERIFICATION COMPLETE.")

if __name__ == "__main__":
    verify_clock_metrics()
