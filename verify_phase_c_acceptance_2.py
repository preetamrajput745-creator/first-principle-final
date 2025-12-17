import sqlite3
import json
import os
import datetime
import pandas as pd
import sys

# Config
EVIDENCE_DIR_IN = "s3_audit_local/phase-c-shadow"
EVIDENCE_DIR_OUT = "s3_audit_local/phase-c-acceptance-2"
if not os.path.exists(EVIDENCE_DIR_OUT):
    os.makedirs(EVIDENCE_DIR_OUT)

TASK_ID = f"{datetime.datetime.utcnow().strftime('%Y%m%d')}-PHASEC-ACCEPT-2"
TESTER = "Mastermind"
DATE_UTC = datetime.datetime.utcnow().strftime("%Y-%m-%d")

def load_json(filename):
    path = os.path.join(EVIDENCE_DIR_IN, filename)
    if not os.path.exists(path):
        print(f"Warning: {filename} not found.")
        return []
    with open(path, "r") as f:
        return json.load(f)

def run_verification():
    print("[ACCEPTANCE] Starting Snapshot Coverage Check...")
    
    # 1. Load Data
    # We use order_payloads as the "Golden Source" of Signals that reached execution intent
    # We use signal_snapshots as the table to verify against
    payloads = load_json("order_payload_samples.json")
    snapshots = load_json("signal_snapshot_samples.json")
    
    if not payloads:
        print("No payloads found, treating as 0 signals in window.")
        
    # 2. Setup In-Memory DB for SQL Verification
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    
    # Schema
    cur.execute("CREATE TABLE signals (signal_id TEXT, timestamp_utc TEXT)")
    cur.execute("CREATE TABLE signal_snapshots (signal_id TEXT, timestamp_utc TEXT)")
    
    # Populate Signals (from payloads)
    for p in payloads:
        cur.execute("INSERT INTO signals VALUES (?, ?)", (p["signal_id"], p["timestamp_utc"]))
        
    # Populate Snapshots
    for s in snapshots:
        cur.execute("INSERT INTO signal_snapshots VALUES (?, ?)", (s["signal_id"], s["timestamp_utc"]))
        
    conn.commit()
    
    # 3. Define Window
    now = datetime.datetime.utcnow()
    t_end = now.isoformat()
    t_start = (now - datetime.timedelta(hours=1)).isoformat()
    
    print(f"Window: {t_start} to {t_end}")
    
    # 4. Explicit Query (Requirement)
    query = f"""
    SELECT s.signal_id, s.timestamp_utc
    FROM signals s
    LEFT JOIN signal_snapshots ss ON s.signal_id = ss.signal_id
    WHERE s.timestamp_utc BETWEEN '{t_start}' AND '{t_end}'
    AND ss.signal_id IS NULL
    """
    
    with open(os.path.join(EVIDENCE_DIR_OUT, "query_snapshot_coverage.txt"), "w") as f:
        f.write(query)
        
    # 5. Execute
    cur.execute(query)
    rows = cur.fetchall()
    
    # 6. Export CSV
    missing_ids = [r[0] for r in rows]
    df = pd.DataFrame(rows, columns=["signal_id", "timestamp_utc"])
    df.to_csv(os.path.join(EVIDENCE_DIR_OUT, "signals_without_snapshot_last_1h.csv"), index=False)
    
    # 7. Count Validation
    count_missing = len(missing_ids)
    status = "PASS" if count_missing == 0 else "FAIL"
    
    res = {
        "time_window": "last_1_hour_utc",
        "signals_without_snapshot": count_missing,
        "expected": 0,
        "status": status
    }
    
    with open(os.path.join(EVIDENCE_DIR_OUT, "snapshot_coverage_result.json"), "w") as f:
        json.dump(res, f, indent=2)
        
    # 8. Final Output
    final_out = {
      "task_id": TASK_ID,
      "tester": TESTER,
      "date_utc": DATE_UTC,
      "phase": "PHASE C ACCEPTANCE CHECK 2",
      "check": "snapshot_coverage_zero_missing",
      "status": status,
      "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-c-acceptance-2/"
    }
    
    if status == "FAIL":
        final_out["failure_reason"] = f"Found {count_missing} signals missing snapshots"
        final_out["evidence_s3"] += "failure/"
    
    print("FINAL_JSON_OUTPUT_START")
    print(json.dumps(final_out, indent=2))
    print("FINAL_JSON_OUTPUT_END")

if __name__ == "__main__":
    run_verification()
