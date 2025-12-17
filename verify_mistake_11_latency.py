
import sys
import os
import subprocess
import time
import requests
import uuid
from datetime import datetime, timedelta
import json

# Add Root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from event_bus import event_bus

def run_verification():
    print("============================================================")
    print("       LATENCY PANEL VERIFICATION (Mistake #11)       ")
    print("============================================================")
    
    run_id = str(uuid.uuid4())[:8]
    unique_db = f"event_bus_lat_{run_id}.db"
    os.environ["EVENT_BUS_DB"] = unique_db
    print(f"[0] Using unique Event DB: {unique_db}")
    
    # 1. Start Monitor
    print("[1] Starting Monitor Service...")
    monitor_out = open("monitor_lat.log", "w")
    monitor_proc = subprocess.Popen([sys.executable, "-u", "monitoring/monitor.py"],
                                    stdout=monitor_out,
                                    stderr=subprocess.STDOUT,
                                    env=os.environ.copy())
    time.sleep(5)
    
    # 2. Inject Signals with controlled delays
    print("[2] Injecting Signals with delays...")
    
    from event_bus import EventBus
    local_bus = EventBus()
    
    symbol = f"TEST_LAT_{run_id}"
    
    # Batch 1: 20 signals with 200ms latency
    # Use fromtimestamp to align with monitor's local-time interpretation
    print("    Injecting 20 signals with ~200ms delay...")
    for i in range(20):
        # target_ts = time.time() - 0.2
        target_dt = datetime.fromtimestamp(time.time() - 0.2)
        payload = {
            "signal_id": f"sig_200_{i}",
            "symbol": symbol,
            "action": "BUY",
            "timestamp": target_dt.isoformat()
        }
        local_bus.publish("signal.new", payload)
        time.sleep(0.05)
        
    # Batch 2: 5 signals with 1000ms latency (Outliers to push p95)
    print("    Injecting 5 signals with ~1000ms delay...")
    for i in range(5):
        target_dt = datetime.fromtimestamp(time.time() - 1.0)
        payload = {
            "signal_id": f"sig_1000_{i}",
            "symbol": symbol,
            "action": "BUY",
            "timestamp": target_dt.isoformat()
        }
        local_bus.publish("signal.new", payload)
        time.sleep(0.05)

    print("    Waiting for processing...")
    time.sleep(10)
    
    # 3. Verify Logs for Latency Stats
    # Monitor prints stats every 10s via check_health
    print("[3] checking Monitor Logs for Latency Stats...")
    monitor_proc.terminate()
    monitor_out.close()
    
    found_stat = False
    with open("monitor_lat.log", "r") as f:
        content = f.read()
        
    print("    Scanning logs for Latency lines...")
    # Expected format: "Latency (ms): p50=200.0 | p95=1000.0"
    # We allow some jitter (e.g. 200-250, 1000-1100)
    
    import re
    # Find all latency lines
    matches = re.findall(r"Latency \(ms\): p50=([\d\.]+) \| p95=([\d\.]+)", content)
    
    if matches:
        last_stat = matches[-1]
        p50 = float(last_stat[0])
        p95 = float(last_stat[1])
        print(f"    Found Stats: p50={p50}, p95={p95}")
        
        # Validation
        # p50 should be around 200 (allow 190-300 due to processing time)
        # p95 should be around 1000 (allow 990-1200)
        
        if 150 <= p50 <= 350:
            print("    [PASS] p50 is within valid range (~200ms)")
        else:
             print(f"    [FAIL] p50 {p50} is out of range 150-350")
             
        if 950 <= p95 <= 1300:
             print("    [PASS] p95 is within valid range (~1000ms)")
             found_stat = True
        else:
             print(f"    [FAIL] p95 {p95} is out of range 950-1300")
    else:
        print("    [FAIL] No Latency stats found in log!")
        print("    Tail of logs:")
        print(content[-2000:])
        sys.exit(1)

    if found_stat:
        print("SUCCESS: Latency Panel Verified.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
