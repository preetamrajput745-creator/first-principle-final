
import sys
import os
import time
from io import StringIO
from unittest.mock import patch

# Add workers path to sys.path
sys.path.append(os.path.join(os.getcwd(), 'workers'))

from common.time_normalizer import TimeNormalizer

def verify_drift_alert():
    print("VERIFICATION: Mistake #3 - Clock Drift Alerting")
    print("="*60)
    
    # Capture stdout to verify print alert
    captured_output = StringIO()
    sys.stdout = captured_output

    try:
        # Case 1: Normal Tick (No Drift)
        # source_clock is effectively now
        current_ns = time.time_ns()
        tick_normal = {
            "symbol": "TEST_NORMAL",
            "source_clock": current_ns
        }
        res_normal = TimeNormalizer.normalize_tick(tick_normal)
        
        # Case 2: High Drift Tick (> 100ms lag)
        # source_clock is 200ms ago (simulating lag/drift)
        drifted_ns = current_ns - (200 * 1_000_000) 
        tick_drifted = {
            "symbol": "TEST_DRIFT",
            "source_clock": drifted_ns
        }
        res_drift = TimeNormalizer.normalize_tick(tick_drifted)
        
    finally:
        # Restore stdout
        sys.stdout = sys.__stdout__
        
    output = captured_output.getvalue()
    print(output)
    
    print("-" * 30)
    print(f"Normal Tick Drift:  {res_normal.get('clock_drift_ms')} ms")
    print(f"Drifted Tick Drift: {res_drift.get('clock_drift_ms')} ms")
    print("-" * 30)
    
    # Verifications
    failed = False
    
    # 1. Verify Drift Calculation
    if res_drift.get('clock_drift_ms') < 190: # Allow some execution time noise
        print("FAILURE: Drift calculation incorrect. Expected ~200ms.")
        failed = True
    else:
        print("SUCCESS: Drift calculated correctly.")
        
    # 2. Verify Alert
    if "WARNING: High Clock Drift Detected!" in output:
        print("SUCCESS: Alert triggered for high drift.")
    else:
        print("FAILURE: Alert NOT triggered for >100ms drift.")
        failed = True
        
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    verify_drift_alert()
