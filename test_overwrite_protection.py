"""
Test: Verify Overwrite Protection (Mistake #2 Requirement)
This script attempts to overwrite raw data and should append instead.
"""

import sys
import os

workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.raw_data_store import RawDataStore
from datetime import datetime

def test_overwrite_protection():
    print("Testing Overwrite Protection...")
    print("=" * 60)
    
    store = RawDataStore()
    
    # Write tick 1
    tick1 = {
        "symbol": "TEST",
        "bid": 100.0,
        "ask": 100.5,
        "timestamp": datetime.utcnow().isoformat()
    }
    store.append_tick(tick1)
    print("Tick 1 written")
    
    # Attempt to "overwrite" by writing again
    tick2 = {
        "symbol": "TEST",
        "bid": 200.0,  # Different data
        "ask": 200.5,
        "timestamp": datetime.utcnow().isoformat()
    }
    store.append_tick(tick2)
    print("Tick 2 written (should APPEND, not overwrite)")
    
    # Read all ticks
    ticks = store.read_ticks("TEST")
    print(f"\nTotal ticks for TEST: {len(ticks)}")
    
    if len(ticks) >= 2:
        print("SUCCESS: Data was APPENDED (immutable storage working)")
        print(f"  Count: {len(ticks)}")
        print(f"  Last Tick bid: {ticks[-1]['bid']}")
    else:
        print("FAILURE: Data was overwritten (Count < 2)!")
    
    print("=" * 60)

if __name__ == "__main__":
    test_overwrite_protection()
