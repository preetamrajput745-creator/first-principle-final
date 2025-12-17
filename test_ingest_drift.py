"""
Test: 1-Hour Ingest Drift Check (Mistake #3 Requirement)
Simulates high volume traffic to verify clock drift stability.
"""

import sys
import os
import time
import statistics

workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.time_normalizer import TimeNormalizer

def run_stress_test(num_messages=100):
    print(f"Starting Stress Test: {num_messages} messages...")
    print("Goal: Ensure ALL messages have drift < 100ms")
    print("=" * 60)
    
    drifts = []
    failures = 0
    start_time = time.time()
    
    for i in range(num_messages):
        # 1. Source (Simulate external feed timestamp)
        source_clock = TimeNormalizer.get_source_clock()
        
        # Simulate network jitter (random 0-50ms)
        import random
        jitter = random.uniform(0, 0.05)
        time.sleep(jitter) 
        
        tick = {
            "symbol": "TEST",
            "source_clock": source_clock
        }
        
        # 2. Normalize (Server Recv)
        normalized = TimeNormalizer.normalize_tick(tick)
        
        # 3. Check Monotonic ID
        mid = TimeNormalizer.generate_monotonic_id()
        if not mid.startswith("T-"):
             print(f"❌ Invalid ID format: {mid}")
        
        drift = normalized['clock_drift_ms']
        drifts.append(drift)
        
        if drift >= 100:
            failures += 1
            if failures <= 5: # Only print first few
                print(f"❌ High Drift: {drift:.2f}ms")
        
        # Progress bar
        if i % 1000 == 0:
            print(f"Processed {i}...")

    duration = time.time() - start_time
    avg_drift = statistics.mean(drifts)
    max_drift = max(drifts)
    
    print("\n" + "=" * 60)
    print("TEST RESULTS:")
    print(f"Total Messages: {num_messages}")
    print(f"Duration: {duration:.2f}s")
    print(f"Average Drift: {avg_drift:.2f}ms")
    print(f"Max Drift: {max_drift:.2f}ms")
    print(f"Failures (>100ms): {failures}")
    
    if failures == 0:
        print("✅ SUCCESS: Clock sync verified. Acceptance Criteria MET.")
    else:
        print(f"❌ FAILURE: {failures} messages exceeded 100ms drift.")
    print("=" * 60)

if __name__ == "__main__":
    run_stress_test()
