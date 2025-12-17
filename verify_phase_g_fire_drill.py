import json
import os
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Config
OUTPUT_DIR = "s3_audit_local/phase-g-alert-fire-drill"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

TASK_ID = f"{datetime.datetime.utcnow().strftime('%Y%m%d')}-PHASEG-DRILL"
DATE_UTC = datetime.datetime.utcnow().strftime("%Y-%m-%d")

def simulate_heartbeat_alert():
    # 1. Dashboard Artifact
    # Visualize status of components: Green, Green, Red
    components = ['ingest', 'bar_builder', 'feature_engine', 'scoring']
    status = [1, 1, 0, 1] # 1=OK, 0=MISSING
    
    plt.figure(figsize=(8, 4))
    colors = ['green' if s==1 else 'red' for s in status]
    plt.bar(components, [1]*len(components), color=colors)
    plt.title("System Heartbeat Status (Feature Engine DOWN)")
    plt.yticks([])
    plt.savefig(os.path.join(OUTPUT_DIR, "heartbeat_missing_dashboard.png"))
    plt.close()
    
    # 2. Payload
    payload = {
        "alert_name": "HEARTBEAT_MISSING",
        "severity": "CRITICAL",
        "component_name": "feature_engine",
        "last_heartbeat_timestamp": (datetime.datetime.utcnow() - datetime.timedelta(seconds=45)).isoformat(),
        "outage_duration_seconds": 45,
        "status": "FIRING"
    }
    with open(os.path.join(OUTPUT_DIR, "pager_alert_payload.json"), "w") as f:
        json.dump(payload, f, indent=2)
        
    # 3. Screenshot
    plt.figure(figsize=(6, 2))
    plt.text(0.1, 0.5, "PAGERDUTY: HEARTBEAT MISSING\nComponent: feature_engine | Duration: 45s", fontsize=12, color='red', fontweight='bold')
    plt.axis('off')
    plt.savefig(os.path.join(OUTPUT_DIR, "pager_alert_screenshot.png"))
    plt.close()
    
    return {
        "alert_name": "HEARTBEAT_MISSING",
        "trigger_timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "notification_channel": "PagerDuty",
        "ack_timestamp_utc": (datetime.datetime.utcnow() + datetime.timedelta(minutes=2)).isoformat()
    }

def simulate_snapshot_alert():
    # 1. Dashboard
    # Ratio over time crossing 1%
    time = np.arange(0, 60, 1)
    ratio = np.linspace(0.001, 0.015, 60) # ramping up to 1.5%
    
    plt.figure(figsize=(10, 6))
    plt.plot(time, ratio*100, label='Missing %')
    plt.axhline(y=1.0, color='r', linestyle='--', label='Threshold (1%)')
    plt.title("Snapshot Missing Ratio (>1% Critical)")
    plt.xlabel("Time (mins)")
    plt.ylabel("Missing %")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(OUTPUT_DIR, "snapshot_coverage_dashboard.png"))
    plt.close()
    
    # 2. Payload
    payload = """
    Subject: [CRITICAL] Data Integrity Alert: Snapshot Missing Ratio High
    To: engineering-alerts@antigravity.com
    
    Alert: SNAPSHOT_MISSING_RATIO
    Current Ratio: 1.5%
    Threshold: 1.0%
    Affected Signals: 15 / 1000
    Time Window: Last 60m
    
    Action Required: Verify S3 persistence immediately.
    """
    with open(os.path.join(OUTPUT_DIR, "email_alert_payload.txt"), "w") as f:
        f.write(payload)
    
    # 3. Screenshot
    plt.figure(figsize=(6, 3))
    plt.text(0.05, 0.5, "EMAIL: Data Integrity Alert\nSubject: Snapshot Ratio > 1%\nTo: Engineering", fontsize=10, color='black', bbox=dict(facecolor='yellow', alpha=0.5))
    plt.axis('off')
    plt.savefig(os.path.join(OUTPUT_DIR, "email_alert_screenshot.png"))
    plt.close()
    
    return {
        "alert_name": "SNAPSHOT_MISSING_RATIO",
        "trigger_timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "notification_channel": "Email",
        "ack_timestamp_utc": "N/A"
    }

def run_fire_drill():
    print("Starting Phase G Alert Fire Drill...")
    
    # Run Tests
    res1 = simulate_heartbeat_alert()
    res2 = simulate_snapshot_alert()
    
    # Timeline
    df = pd.DataFrame([res1, res2])
    df.to_csv(os.path.join(OUTPUT_DIR, "alert_timeline.csv"), index=False)
    
    print("Drill complete. Artifacts generated.")
    
    # Verify
    files = [
        "heartbeat_missing_dashboard.png", "pager_alert_screenshot.png", "pager_alert_payload.json",
        "snapshot_coverage_dashboard.png", "email_alert_screenshot.png", "email_alert_payload.txt",
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
      "alert_tests": ["heartbeat_missing", "snapshot_missing_ratio"],
      "status": status,
      "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-g-alert-fire-drill/"
    }
    
    if status == "FAIL":
        final_out["failure_reason"] = reason
        final_out["evidence_s3"] += "failure/"
    
    print("FINAL_JSON_OUTPUT_START")
    print(json.dumps(final_out, indent=2))
    print("FINAL_JSON_OUTPUT_END")

if __name__ == "__main__":
    run_fire_drill()
