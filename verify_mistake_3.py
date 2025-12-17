import sys
import os
import time
from datetime import datetime, timedelta, timezone

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infra.time_normalizer import clock

def test_time_normalizer():
    print("=== TESTING MISTAKE 3: CLOCK NORMALIZATION ===")
    
    # 1. Test UTC Generation
    print("\n[1] Testing UTC Generation...")
    now = clock.get_current_utc()
    print(f"   -> Current UTC: {now}")
    assert now.tzinfo == timezone.utc
    print("   -> Timezone correct [OK]")
    
    # 2. Test Normalization (ISO Strings)
    print("\n[2] Testing Parsing...")
    iso_str = "2023-10-27T10:00:00.000Z"
    normalized = clock.normalize_timestamp(iso_str)
    print(f"   -> Parsed '{iso_str}' to {normalized}")
    assert normalized.year == 2023
    assert normalized.tzinfo == timezone.utc
    print("   -> Parsing correct [OK]")
    
    # 3. Test Drift Detection
    print("\n[3] Testing Drift Detection...")
    remote_ts_ms = (time.time() * 1000) - 1000 # 1 second in PAST
    drift = clock.check_drift(remote_ts_ms)
    print(f"   -> Remote (1s ago) Drift: {drift:.2f}ms")
    assert drift < -900 # Should be around -1000
    
    remote_future_ms = (time.time() * 1000) + 5000 # 5s in FUTURE
    drift_future = clock.check_drift(remote_future_ms)
    print(f"   -> Remote (5s ahead) Drift: {drift_future:.2f}ms")
    assert drift_future > 4900
    
    print("   -> Drift calculation correct [OK]")
    
    print("\n=== CLOCK SERVICE VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_time_normalizer()
