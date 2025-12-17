
import sys
import os
import subprocess
import time
import requests
import signal

# Add Root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_verification():
    print("============================================================")
    print("       HEARTBEAT & PROBE VERIFICATION (Mistake #5)       ")
    print("============================================================")
    
    # 0. Clean DB env var (ensure usage of standard or new distinct one)
    # We use a distinct DB to avoid locking
    import uuid
    run_id = str(uuid.uuid4())[:8]
    unique_db = f"event_bus_hb_{run_id}.db"
    os.environ["EVENT_BUS_DB"] = unique_db
    print(f"[0] Using unique Event DB: {unique_db}")
    
    # 1. Start Monitor
    print("[1] Starting Monitor Service...")
    monitor_out = open("monitor_hb.log", "w")
    monitor_proc = subprocess.Popen([sys.executable, "-u", "monitoring/monitor.py"],
                                    stdout=monitor_out,
                                    stderr=subprocess.STDOUT,
                                    env=os.environ.copy())
    
    time.sleep(5)
    
    # 2. Start Worker (Signal Engine)
    print("[2] Starting Signal Engine (Worker)...")
    worker_proc = subprocess.Popen([sys.executable, "-u", "workers/signal_engine.py"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=os.environ.copy())
                                   
    print("    Waiting 15s for heartbeats...")
    time.sleep(15)
    
    # 3. Verify Prometheus Metric
    print("[3] Verifying Prometheus Metric (heartbeat_timestamp)...")
    try:
        resp = requests.get("http://localhost:8001/metrics")
        content = resp.text
        
        # Check for our metric
        if 'heartbeat_timestamp{component="signal_engine"}' in content:
            print("    [PASS] Metric 'heartbeat_timestamp' found for signal_engine.")
            
            # Extract value
            import re
            match = re.search(r'heartbeat_timestamp{component="signal_engine"} (\d+\.\d+)', content)
            if match:
                val = float(match.group(1))
                print(f"    Value: {val} (Now: {time.time()})")
            else:
                print("    [WARN] Metric found but value not parseable?")
        else:
            print("    [FAIL] Metric 'heartbeat_timestamp' NOT found!")
            print(f"DEBUG PROMETHEUS:\n{content}")
            worker_proc.terminate()
            monitor_proc.terminate()
            sys.exit(1)
            
    except Exception as e:
        print(f"    [FAIL] Could not scrape Prometheus: {e}")
        worker_proc.terminate()
        monitor_proc.terminate()
        sys.exit(1)

    # 4. Synthetic Removal Test
    print("[4] Testing Synthetic Removal (Heartbeat Alert)...")
    print("    Terminating Signal Engine...")
    worker_proc.terminate()
    try:
        worker_proc.wait(timeout=5)
    except:
        worker_proc.kill()
        
    print("    Waiting 40s for Monitor to detect missing heartbeat (Threshold: 30s)...")
    time.sleep(40)
    
    # 5. Check Monitor Logs for Pager Alert
    print("[5] checking Monitor Logs for Alert...")
    monitor_proc.terminate()
    monitor_out.close()
    
    with open("monitor_hb.log", "r") as f:
        logs = f.read()
        
    if "PAGER_ALERT [critical]: Heartbeat Missing! signal_engine" in logs:
        print("    [PASS] PagerDuty Alert Triggered correctly.")
        print("SUCCESS: Heartbeat & Probes Verified.")
    else:
        print("    [FAIL] PagerDuty Alert NOT found in logs!")
        print("    Tail of logs:")
        print(logs[-2000:])
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
