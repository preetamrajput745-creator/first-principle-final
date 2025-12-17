"""
Test: Clock Drift Detection (Mistake #3 Requirement)
Simulates ticks with artificial latency to verify drift tracking.
"""

import sys
import os
import time

workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.time_normalizer import TimeNormalizer

def test_drift_detection():
    print("Testing Clock Drift Detection...")
    print("=" * 60)
    
    # Case 1: Normal Tick (Low Latency)
    print("Case 1: Normal Tick (<1ms latency)")
    source_time = TimeNormalizer.get_source_clock()
    tick_normal = {
        "symbol": "TEST",
        "source_clock": source_time
    }
    normalized_normal = TimeNormalizer.normalize_tick(tick_normal)
    print(f"  Drift: {normalized_normal['clock_drift_ms']}ms")
    
    if normalized_normal['clock_drift_ms'] < 10:
        print("  Status: OK (Low Drift)")
    else:
        print("  Status: FAIL (Unexpected High Drift)")
        
    print("-" * 30)
    
    # Case 2: High Latency Tick (Simulated Network Delay)
    print("Case 2: High Latency Tick (150ms delay)")
    source_time_delayed = TimeNormalizer.get_source_clock()
    
    # Sleep 150ms to simulate network/processing lag
    time.sleep(0.15)
    
    tick_delayed = {
        "symbol": "TEST",
        "source_clock": source_time_delayed
    }
    
    # This should trigger the "WARNING: High Clock Drift" print
    normalized_delayed = TimeNormalizer.normalize_tick(tick_delayed)
    print(f"  Drift: {normalized_delayed['clock_drift_ms']}ms")
    
    if normalized_delayed['clock_drift_ms'] > 100:
        print("  Status: OK (High Drift Detected & Logged)")
    else:
        print("  Status: FAIL (Drift Not Detected)")
        
    print("=" * 60)

if __name__ == "__main__":
    test_drift_detection()
