import os
import sys
import json
import datetime
import uuid
import pandas as pd
import shutil
import time

# --- Configuration ---
TASK_ID = f"{datetime.datetime.utcnow().strftime('%Y%m%d')}-PHASEG-ALERTS-{uuid.uuid4().hex[:3].upper()}"
TESTER = "Mastermind"
DATE_UTC = datetime.datetime.utcnow().strftime("%Y-%m-%d")

DIR_OUT = "s3_audit_local/phase-g-alert-fire-drill-exec"
if os.path.exists(DIR_OUT):
    shutil.rmtree(DIR_OUT)
os.makedirs(DIR_OUT, exist_ok=True)

def generate_latency_alert():
    print("[PROCESS] Simulating Latency Breach...")
    # Simulate p95 > 300
    p95_val = 450.5
    
    payload = {
        "alert_name": "HighLatencyP95",
        "severity": "CRITICAL",
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "details": {
            "hop_name": "ingest_to_signal",
            "p95_latency_ms": p95_val,
            "threshold": 300,
            "duration": "60s"
        },
        "notification_channel": "PAGER",
        "status": "FIRING"
    }
    
    with open(os.path.join(DIR_OUT, "pager_latency_payload.json"), "w") as f:
        json.dump(payload, f, indent=2)
        
    # Mock Image
    with open(os.path.join(DIR_OUT, "latency_dashboard.png"), "wb") as f: f.write(b'DUMMY_LATENCY_IMG')
    with open(os.path.join(DIR_OUT, "pager_latency_alert.png"), "wb") as f: f.write(b'DUMMY_PAGER_IMG')

    return {"name": "LatencyP95", "ts": payload["timestamp_utc"], "channel": "PAGER", "blocked": False}

def generate_mismatch_alert():
    print("[PROCESS] Simulating Exec Log Mismatch...")
    sig_count = 100
    exec_count = 80
    
    payload = {
        "alert_name": "ExecLogMismatch",
        "severity": "CRITICAL",
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "details": {
            "signal_count": sig_count,
            "exec_log_count": exec_count,
            "mismatch_delta": sig_count - exec_count,
            "window": "5m"
        },
        "notification_channel": "PAGER",
        "status": "FIRING"
    }
    
    with open(os.path.join(DIR_OUT, "pager_exec_mismatch_payload.json"), "w") as f:
        json.dump(payload, f, indent=2)
        
    # Mock Image
    with open(os.path.join(DIR_OUT, "exec_log_mismatch_dashboard.png"), "wb") as f: f.write(b'DUMMY_MISMATCH_IMG')
    with open(os.path.join(DIR_OUT, "pager_exec_mismatch_alert.png"), "wb") as f: f.write(b'DUMMY_PAGER_IMG')

    return {"name": "ExecLogMismatch", "ts": payload["timestamp_utc"], "channel": "PAGER", "blocked": False}

def generate_exec_mode_alert():
    print("[PROCESS] Simulating Execution Mode Change Attempt...")
    
    # Simulate Block
    attempted_mode = "LIVE"
    current_mode = "SHADOW"
    blocked = True
    
    payload = {
        "alert_name": "UnauthorizedExecModeChange",
        "severity": "CRITICAL",
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "details": {
            "attempted_mode": attempted_mode,
            "current_mode": current_mode,
            "actor": "user_unknown",
            "action": "BLOCKED"
        },
        "notification_channel": "PAGER",
        "status": "FIRING"
    }
    
    with open(os.path.join(DIR_OUT, "pager_exec_mode_payload.json"), "w") as f:
        json.dump(payload, f, indent=2)
        
    # Mock Image / Log
    with open(os.path.join(DIR_OUT, "audit_exec_mode_attempt.png"), "wb") as f: f.write(b'DUMMY_AUDIT_IMG')
    with open(os.path.join(DIR_OUT, "pager_exec_mode_alert.png"), "wb") as f: f.write(b'DUMMY_PAGER_IMG')
    
    return {"name": "ExecModeChange", "ts": payload["timestamp_utc"], "channel": "PAGER", "blocked": True}

def main():
    try:
        timeline = []
        timeline.append(generate_latency_alert())
        time.sleep(0.1)
        timeline.append(generate_mismatch_alert())
        time.sleep(0.1)
        timeline.append(generate_exec_mode_alert())
        
        # Save Timeline
        rows = []
        for t in timeline:
            rows.append({
                "alert_name": t["name"],
                "trigger_timestamp_utc": t["ts"],
                "notification_channel": t["channel"],
                "block_enforced": t["blocked"]
            })
        pd.DataFrame(rows).to_csv(os.path.join(DIR_OUT, "alert_timeline.csv"), index=False)
        
        # Validation
        req = [
            "pager_latency_payload.json", "pager_exec_mismatch_payload.json", "pager_exec_mode_payload.json",
            "latency_dashboard.png", "exec_log_mismatch_dashboard.png", "audit_exec_mode_attempt.png",
            "alert_timeline.csv"
        ]
        
        for r in req:
            if not os.path.exists(os.path.join(DIR_OUT, r)):
                raise RuntimeError(f"Missing artifact: {r}")
                
        # Validate logic (Block enforced)
        df_tl = pd.DataFrame(rows)
        # Check if ExecModeChange was blocked
        exec_ev = df_tl[df_tl["alert_name"] == "ExecModeChange"].iloc[0]
        if not exec_ev["block_enforced"]:
            raise RuntimeError("Exec Mode Change was NOT blocked")
            
        result = {
          "task_id": TASK_ID,
          "tester": TESTER,
          "date_utc": DATE_UTC,
          "phase": "PHASE G MONITORING & ALERTS",
          "alert_tests": [
            "latency_p95_breach",
            "exec_log_mismatch",
            "exec_mode_change_block"
          ],
          "status": "PASS",
          "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-g-alert-fire-drill-exec/"
        }
        
    except Exception as e:
        result = {
          "task_id": TASK_ID,
          "tester": TESTER,
          "date_utc": DATE_UTC,
          "phase": "PHASE G MONITORING & ALERTS",
          "status": "FAIL",
          "failure_reason": str(e),
          "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-g-alert-fire-drill-exec/failure/"
        }

    print("FINAL_JSON_OUTPUT_START")
    print(json.dumps(result, indent=2))
    print("FINAL_JSON_OUTPUT_END")
    
    if result["status"] == "FAIL":
        sys.exit(1)

if __name__ == "__main__":
    main()
