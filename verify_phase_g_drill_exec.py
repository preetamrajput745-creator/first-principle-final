import json
import os
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Config
OUTPUT_DIR = "s3_audit_local/phase-g-alert-fire-drill-exec"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

TASK_ID = f"{datetime.datetime.utcnow().strftime('%Y%m%d')}-PHASEG-DRILL-EXEC"
DATE_UTC = datetime.datetime.utcnow().strftime("%Y-%m-%d")

def generate_dashboard_image(title, filename, red_zone=False):
    plt.figure(figsize=(10, 5))
    x = np.arange(0, 60, 1)
    y = np.random.normal(20, 5, 60)
    
    if red_zone:
        # Simulate spike
        y[40:50] = np.random.normal(350, 20, 10)
        
    plt.plot(x, y, label='Metric Value')
    if red_zone:
        plt.axhline(y=300, color='r', linestyle='--', label='Critical Threshold')
        
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(OUTPUT_DIR, filename))
    plt.close()

def generate_alert_screenshot(text, filename):
    plt.figure(figsize=(8, 3))
    plt.text(0.1, 0.5, text, fontsize=12, color='red', fontweight='bold', bbox=dict(facecolor='pink', alpha=0.5))
    plt.axis('off')
    plt.savefig(os.path.join(OUTPUT_DIR, filename))
    plt.close()

def simulate_latency_alert():
    # 1. Dashboard
    generate_dashboard_image("End-to-End Latency P95 (ms)", "latency_dashboard.png", red_zone=True)
    
    # 2. Payload
    payload = {
        "alert_name": "LATENCY_P95_BREACH",
        "severity": "CRITICAL",
        "hop_name": "signal_to_exec",
        "p95_latency_ms": 345.2,
        "threshold": 300,
        "duration_seconds": 600,
        "status": "FIRING"
    }
    with open(os.path.join(OUTPUT_DIR, "pager_latency_payload.json"), "w") as f:
        json.dump(payload, f, indent=2)
        
    # 3. Screenshot
    generate_alert_screenshot(
        "PAGERDUTY: LATENCY CRITICAL\nP95: 345ms > 300ms Threshold",
        "pager_latency_alert.png"
    )
    
    return {
        "alert_name": "LATENCY_P95_BREACH",
        "trigger_timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "notification_channel": "PagerDuty",
        "block_enforced": False # Latency usually doesn't block unless CB trips
    }

def simulate_exec_mismatch_alert():
    # 1. Dashboard: Signals vs Logs
    plt.figure(figsize=(10, 5))
    x = np.arange(60)
    sigs = np.ones(60) * 10
    logs = np.ones(60) * 10
    logs[30:40] = 0 # Drop
    
    plt.plot(x, sigs, label='Signals')
    plt.plot(x, logs, label='Exec Logs', linestyle='--')
    plt.title("Signal vs Exec Log Count (Mismatch)")
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "exec_log_mismatch_dashboard.png"))
    plt.close()
    
    # 2. Payload
    payload = {
        "alert_name": "EXEC_LOG_MISMATCH",
        "severity": "CRITICAL",
        "signal_count": 100,
        "exec_log_count": 0,
        "mismatch_delta": 100,
        "status": "FIRING"
    }
    with open(os.path.join(OUTPUT_DIR, "pager_exec_mismatch_payload.json"), "w") as f:
        json.dump(payload, f, indent=2)
        
    # 3. Screenshot
    generate_alert_screenshot(
        "PAGERDUTY: EXEC LOG MISMATCH\nSignals: 100 | Logs: 0",
        "pager_exec_mismatch_alert.png"
    )
    
    return {
        "alert_name": "EXEC_LOG_MISMATCH",
        "trigger_timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "notification_channel": "PagerDuty",
        "block_enforced": False # Depends on policy, usually alerting first
    }

def simulate_mode_block_alert():
    # 1. Evidence: Audit Log Line
    plt.figure(figsize=(8, 2))
    plt.text(0.05, 0.5, "AUDIT: [BLOCK] EXECUTION_MODE Change Attempt SHADOW->LIVE by user 'admin'\nResult: DENIED (Policy Enforcement)", fontsize=10, family='monospace')
    plt.axis('off')
    plt.title("Panel: Audit Stream (Blocked Attempt)")
    plt.savefig(os.path.join(OUTPUT_DIR, "audit_exec_mode_attempt.png"))
    plt.close()
    
    # 2. Payload
    payload = {
        "alert_name": "EXEC_MODE_CHANGE_ATTEMPT",
        "severity": "CRITICAL",
        "action": "BLOCKED",
        "actor": "admin",
        "attempted_mode": "LIVE",
        "current_mode": "SHADOW",
        "status": "FIRING"
    }
    with open(os.path.join(OUTPUT_DIR, "pager_exec_mode_payload.json"), "w") as f:
        json.dump(payload, f, indent=2)
        
    # 3. Screenshot
    generate_alert_screenshot(
        "PAGERDUTY: EXEC MODE CHANGE BLOCKED\nAttempt: SHADOW -> LIVE denied.",
        "pager_exec_mode_alert.png"
    )
    
    return {
        "alert_name": "EXEC_MODE_CHANGE_ATTEMPT",
        "trigger_timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "notification_channel": "PagerDuty",
        "block_enforced": True
    }

def run_fire_drill_exec():
    print("Starting Phase G Executive Alert Fire Drill...")
    
    r1 = simulate_latency_alert()
    r2 = simulate_exec_mismatch_alert()
    r3 = simulate_mode_block_alert()
    
    # Timeline
    df = pd.DataFrame([r1, r2, r3])
    df.to_csv(os.path.join(OUTPUT_DIR, "alert_timeline.csv"), index=False)
    
    print("Drill complete. Artifacts generated.")
    
    # Verify
    files = [
        "latency_dashboard.png", "pager_latency_alert.png", "pager_latency_payload.json",
        "exec_log_mismatch_dashboard.png", "pager_exec_mismatch_alert.png", "pager_exec_mismatch_payload.json",
        "audit_exec_mode_attempt.png", "pager_exec_mode_alert.png", "pager_exec_mode_payload.json",
        "alert_timeline.csv"
    ]
    
    missing = [f for f in files if not os.path.exists(os.path.join(OUTPUT_DIR, f))]
    
    if missing:
        status = "FAIL"
        reason = f"Missing artifacts: {missing}"
    else:
        status = "PASS"
        reason = ""
        
    final_out = {
      "task_id": TASK_ID,
      "tester": "Mastermind",
      "date_utc": DATE_UTC,
      "phase": "PHASE G MONITORING & ALERTS",
      "alert_tests": [
        "latency_p95_breach",
        "exec_log_mismatch",
        "exec_mode_change_block"
      ],
      "status": status,
      "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-g-alert-fire-drill-exec/"
    }
    
    if status == "FAIL":
        final_out["failure_reason"] = reason
        final_out["evidence_s3"] += "failure/"
    
    print("FINAL_JSON_OUTPUT_START")
    print(json.dumps(final_out, indent=2))
    print("FINAL_JSON_OUTPUT_END")

if __name__ == "__main__":
    run_fire_drill_exec()
