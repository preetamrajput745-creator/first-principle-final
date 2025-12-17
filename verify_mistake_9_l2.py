
import sys
import os
import subprocess
import time
import requests
import signal
import uuid
from datetime import datetime
import json

# Add Root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from event_bus import event_bus

def run_verification():
    print("============================================================")
    print("       L2 SNAPSHOT COMPLETENESS VERIFICATION (Mistake #9)       ")
    print("============================================================")
    
    run_id = str(uuid.uuid4())[:8]
    unique_db = f"event_bus_l2_{run_id}.db"
    os.environ["EVENT_BUS_DB"] = unique_db
    print(f"[0] Using unique Event DB: {unique_db}")
    
    # 1. Start Monitor
    print("[1] Starting Monitor Service...")
    monitor_out = open("monitor_l2.log", "w")
    monitor_proc = subprocess.Popen([sys.executable, "-u", "monitoring/monitor.py"],
                                    stdout=monitor_out,
                                    stderr=subprocess.STDOUT,
                                    env=os.environ.copy())
    
    time.sleep(5)
    
    # 2. Inject Mixed Signals
    print("[2] Injecting Signals (5 Valid, 5 Missing L2)...")
    
    # Create a dummy file for valid check
    dummy_snapshot = f"dummy_snapshot_{run_id}.json"
    with open(dummy_snapshot, "w") as f:
        f.write("{}")
    dummy_path = os.path.abspath(dummy_snapshot)
    
    symbol = f"TEST_L2_{run_id}"
    
    # Re-init event bus with new DB env logic is handled by restart or using sqlite3 directly?
    # verify_signal_panel.py re-initialized event_bus. 
    # But here we import event_bus at top. If 'event_bus' module initializes on import, it might use default DB.
    # We should re-instantiate EventBus if we want it to use the new env.
    # OR we just rely on the fact that if we inject via the SAME db, it works.
    # Since I cannot easily reload the module here without tricks, I will manually create an EventBus instance pointing to unique_db.
    from event_bus import EventBus
    # We need to workaround the method signature that might not accept db_path if it reads env var.
    # event_bus.py reads env var on init.
    # So we can just instantiate a new one.
    local_bus = EventBus()
    
    for i in range(10):
        # Alternate Valid / Invalid
        has_snapshot = (i % 2 == 0) # 0, 2, 4, 6, 8 -> Valid. 1, 3, 5, 7, 9 -> Invalid.
        
        payload = {
            "signal_id": f"sig_{i}",
            "automation_id": "auto_1",
            "symbol": symbol,
            "action": "BUY",
            "quantity": 100,
            "price": 100.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if has_snapshot:
            payload["l2_snapshot_path"] = dummy_path
        else:
            # Missing path key or None
            if i == 1: payload["l2_snapshot_path"] = None 
            else: pass # Key missing
            
        local_bus.publish("signal.new", payload)
        time.sleep(0.1)
        
    print("    Signals injected. Waiting for processing...")
    time.sleep(10)
    
    # 3. Check Monitor Logs for Alert
    print("[3] checking Monitor Logs for Alert...")
    monitor_proc.terminate()
    monitor_out.close()
    
    with open("monitor_l2.log", "r") as f:
        logs = f.read()
        
    # We expect 50% missing ratio.
    expected_msg = f"EMAIL_ALERT [critical]: High L2 Missing Ratio for {symbol}: 50.00% (>1%)"
    
    if expected_msg in logs:
        print(f"    [PASS] Email Alert Triggered correctly: {expected_msg}")
        print("SUCCESS: L2 Snapshot Completeness Verified.")
    else:
        print("    [FAIL] Email Alert NOT found in logs!")
        print(f"    Expected: {expected_msg}")
        print("    Tail of logs:")
        print(logs[-2000:])
        
        # Cleanup
        if os.path.exists(dummy_snapshot): os.remove(dummy_snapshot)
        sys.exit(1)

    # Cleanup
    if os.path.exists(dummy_snapshot): os.remove(dummy_snapshot)

if __name__ == "__main__":
    run_verification()
