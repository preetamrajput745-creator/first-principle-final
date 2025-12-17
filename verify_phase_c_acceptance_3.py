import sqlite3
import json
import os
import datetime
import pandas as pd
import sys

# Config
EVIDENCE_DIR_IN = "s3_audit_local/phase-c-shadow"
EVIDENCE_DIR_OUT = "s3_audit_local/phase-c-acceptance-3"
if not os.path.exists(EVIDENCE_DIR_OUT):
    os.makedirs(EVIDENCE_DIR_OUT)

TASK_ID = f"{datetime.datetime.utcnow().strftime('%Y%m%d')}-PHASEC-ACCEPT-3"
TESTER = "Mastermind"
DATE_UTC = datetime.datetime.utcnow().strftime("%Y-%m-%d")

def load_json(filename):
    path = os.path.join(EVIDENCE_DIR_IN, filename)
    if not os.path.exists(path):
        print(f"Warning: {filename} not found.")
        return []
    with open(path, "r") as f:
        return json.load(f)

def load_csv(filename):
    path = os.path.join(EVIDENCE_DIR_IN, filename)
    if not os.path.exists(path):
        print(f"Warning: {filename} not found.")
        return pd.DataFrame()
    return pd.read_csv(path)

def run_verification():
    print("[ACCEPTANCE] Starting Sim Fill Coverage Check...")
    
    # 1. Load Data
    exec_logs = load_json("exec_log_samples.json")
    sim_fills_df = load_csv("shadow_fills.csv")
    
    if not exec_logs and sim_fills_df.empty:
        print("No data found. Aborting.")
        sys.exit(1)

    # 2. Setup DB
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    
    cur.execute("CREATE TABLE exec_logs (exec_log_id TEXT, signal_id TEXT, derived_order_id TEXT, execution_mode TEXT, timestamp_utc TEXT)")
    cur.execute("CREATE TABLE sim_fills (order_id TEXT, timestamp_utc TEXT)")
    
    # 3. Populate Exec Logs
    # Note: verify_phase_c_detailed.py produces exec_logs with 'signal_id'.
    # Fills have 'order_id' = "ord_" + signal_id[:8].
    # We will derive the expected order_id here for joining.
    for log in exec_logs:
        # Assuming log has 'signal_id'
        sig_id = log.get("signal_id", "")
        derived = f"ord_{sig_id[:8]}"
        # We assume exec_log_id is essentially the list index or sig_id for this check if unique
        # verification prompt asks for "exec_logs.exec_log_id", let's use signal_id as proxy or uuid
        row_id = str(log.get("signal_id")) 
        cur.execute("INSERT INTO exec_logs VALUES (?, ?, ?, ?, ?)", 
                   (row_id, sig_id, derived, log.get("execution_mode"), log.get("timestamp_utc")))
                   
    # 4. Populate Sim Fills
    for _, row in sim_fills_df.iterrows():
        cur.execute("INSERT INTO sim_fills VALUES (?, ?)", 
                   (row["order_id"], row["timestamp_utc"]))
                   
    conn.commit()
    
    # 5. Define Window
    now = datetime.datetime.utcnow()
    t_end = now.isoformat()
    t_start = (now - datetime.timedelta(hours=1)).isoformat()
    
    print(f"Window: {t_start} to {t_end}")
    
    # 6. Queries
    
    # 6a. Missing Fills (Exec Logs without Fills)
    # Join on derived_order_id = order_id
    query_missing = f"""
    SELECT el.signal_id, el.timestamp_utc
    FROM exec_logs el
    LEFT JOIN sim_fills sf ON el.derived_order_id = sf.order_id
    WHERE el.timestamp_utc BETWEEN '{t_start}' AND '{t_end}'
    AND el.execution_mode = 'SHADOW'
    AND sf.order_id IS NULL
    """
    
    cur.execute(query_missing)
    missing_rows = cur.fetchall()
    
    # 6b. Orphan Fills (Fills without Logs)
    query_orphan = f"""
    SELECT sf.order_id, sf.timestamp_utc
    FROM sim_fills sf
    LEFT JOIN exec_logs el ON sf.order_id = el.derived_order_id
    WHERE sf.timestamp_utc BETWEEN '{t_start}' AND '{t_end}'
    AND el.signal_id IS NULL
    """
    
    cur.execute(query_orphan)
    orphan_rows = cur.fetchall()
    
    # 6c. Counts
    cur.execute(f"SELECT count(*) FROM exec_logs WHERE timestamp_utc BETWEEN '{t_start}' AND '{t_end}' AND execution_mode='SHADOW'")
    count_logs = cur.fetchone()[0]
    
    cur.execute(f"SELECT count(*) FROM sim_fills WHERE timestamp_utc BETWEEN '{t_start}' AND '{t_end}'")
    count_fills = cur.fetchone()[0]
    
    # 7. Exports
    pd.DataFrame(missing_rows, columns=["signal_id", "timestamp_utc"]).to_csv(os.path.join(EVIDENCE_DIR_OUT, "exec_logs_without_sim_fill.csv"), index=False)
    pd.DataFrame(orphan_rows, columns=["order_id", "timestamp_utc"]).to_csv(os.path.join(EVIDENCE_DIR_OUT, "sim_fills_without_exec_log.csv"), index=False)
    
    # 8. Validation
    missing_count = len(missing_rows)
    orphan_count = len(orphan_rows)
    
    status = "PASS"
    if missing_count > 0 or orphan_count > 0:
        status = "FAIL"
    if count_logs != count_fills:
        status = "FAIL"
        
    res = {
        "time_window": "last_1_hour_utc",
        "exec_log_count": count_logs,
        "sim_fill_count": count_fills,
        "missing_sim_fills": missing_count,
        "orphan_sim_fills": orphan_count,
        "status": status
    }
    
    with open(os.path.join(EVIDENCE_DIR_OUT, "sim_fill_coverage_result.json"), "w") as f:
        json.dump(res, f, indent=2)
        
    # Save Query Texts
    with open(os.path.join(EVIDENCE_DIR_OUT, "query_sim_fill_coverage.txt"), "w") as f:
        f.write(query_missing + "\n\n" + query_orphan)

    # 9. Final Output
    final_out = {
      "task_id": TASK_ID,
      "tester": TESTER,
      "date_utc": DATE_UTC,
      "phase": "PHASE C ACCEPTANCE CHECK 3",
      "check": "sim_fill_coverage",
      "status": status,
      "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-c-acceptance-3/"
    }
    
    if status == "FAIL":
        final_out["failure_reason"] = f"Counts mismatch or missing links: Logs={count_logs}, Fills={count_fills}, Missing={missing_count}"
        final_out["evidence_s3"] += "failure/"
    
    print("FINAL_JSON_OUTPUT_START")
    print(json.dumps(final_out, indent=2))
    print("FINAL_JSON_OUTPUT_END")

if __name__ == "__main__":
    run_verification()
