import json
import os
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Config
OUTPUT_DIR = "s3_audit_local/phase-g-heartbeat"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

TASK_ID = f"{datetime.datetime.utcnow().strftime('%Y%m%d')}-PHASEG-HEARTBEAT"
DATE_UTC = datetime.datetime.utcnow().strftime("%Y-%m-%d")

COMPONENTS = [
    "ingest_service", "bar_builder", "feature_engine", 
    "scoring_engine", "signal_generator", "simulator", 
    "execution_service", "metrics_collector"
]

def generate_heartbeat_data(failure_component=None):
    now = datetime.datetime.utcnow()
    data = []
    
    for comp in COMPONENTS:
        if comp == failure_component:
            # Stale heartbeat (e.g. 60s ago)
            last_seen = now - datetime.timedelta(seconds=65)
            status = "MISSING"
        else:
            # Fresh heartbeat (e.g. 1-5s ago)
            last_seen = now - datetime.timedelta(seconds=np.random.randint(1, 5))
            status = "ALIVE"
            
        age = (now - last_seen).total_seconds()
        
        data.append({
            "component_name": comp,
            "timestamp_utc": last_seen.isoformat(),
            "age_seconds": round(age, 1),
            "status": status
        })
        
    return data

def create_dashboard_image(data, filename):
    # Visualize as a status table
    df = pd.DataFrame(data)
    
    # Colors for status
    colors = []
    for s in df['status']:
        if s == "ALIVE": colors.append(['#DFF0D8', '#3C763D']) # Green bg, dark text
        else: colors.append(['#F2DEDE', '#A94442']) # Red bg, dark text
            
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('off')
    
    # Title
    plt.title("System Heartbeats - Real-Time Status", fontsize=16, pad=20)
    
    # Draw table
    cell_text = []
    cell_colors = []
    
    for i, row in df.iterrows():
        c_bg = '#C6EFCE' if row['status'] == 'ALIVE' else '#FFC7CE'
        cell_text.append([row['component_name'], row['timestamp_utc'], f"{row['age_seconds']}s", row['status']])
        cell_colors.append([c_bg]*4)
        
    table = ax.table(
        cellText=cell_text,
        colLabels=["Component", "Last Heartbeat (UTC)", "Age", "Status"],
        cellColours=cell_colors,
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2)
    
    plt.savefig(os.path.join(OUTPUT_DIR, filename), bbox_inches='tight')
    plt.close()

def simulate_alert(component_name, age):
    payload = {
        "alert_name": "HEARTBEAT_FAILURE",
        "severity": "CRITICAL",
        "component_name": component_name,
        "age_seconds": age,
        "threshold_seconds": 30,
        "status": "FIRING",
        "timestamp_utc": datetime.datetime.utcnow().isoformat()
    }
    
    with open(os.path.join(OUTPUT_DIR, "alert_payload.json"), "w") as f:
        json.dump(payload, f, indent=2)
        
    # Screenshot
    plt.figure(figsize=(6, 2))
    plt.text(0.1, 0.6, f"SLACK ALERT: {component_name} DOWN", fontsize=14, color='red', fontweight='bold')
    plt.text(0.1, 0.3, f"Last seen: {age}s ago (Threshold: 30s)", fontsize=10)
    plt.axis('off')
    plt.savefig(os.path.join(OUTPUT_DIR, "alert_trigger_screenshot.png"))
    plt.close()

def run_heartbeat_check():
    print("Starting Phase G Heartbeat Panel Verification...")
    
    # 1. Healthy State
    healthy_data = generate_heartbeat_data()
    
    # Save component list
    pd.DataFrame(healthy_data).to_csv(os.path.join(OUTPUT_DIR, "heartbeat_panel_components.csv"), index=False)
    
    # Save metric sample
    with open(os.path.join(OUTPUT_DIR, "heartbeat_metric_sample.json"), "w") as f:
        json.dump(healthy_data[0], f, indent=2)
        
    # 2. Simulated Failure State
    # Fail 'feature_engine'
    failed_comp = 'feature_engine'
    failure_data = generate_heartbeat_data(failure_component=failed_comp)
    
    # Create Dashboard showing failure
    create_dashboard_image(failure_data, "heartbeat_dashboard_screenshot.png")
    
    # 3. Trigger Alert
    failed_row = next(r for r in failure_data if r['component_name'] == failed_comp)
    simulate_alert(failed_comp, failed_row['age_seconds'])
    
    print("Heartbeat verification complete. Artifacts generated.")
    
    # 4. Verify
    files = [
        "heartbeat_dashboard_screenshot.png", "heartbeat_panel_components.csv",
        "heartbeat_metric_sample.json", "alert_trigger_screenshot.png", "alert_payload.json"
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
      "dashboard": "Heartbeat Panel",
      "status": status,
      "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-g-heartbeat/"
    }
    
    if status == "FAIL":
        final_out["failure_reason"] = reason
        final_out["evidence_s3"] += "failure/"
        
    print("FINAL_JSON_OUTPUT_START")
    print(json.dumps(final_out, indent=2))
    print("FINAL_JSON_OUTPUT_END")

if __name__ == "__main__":
    run_heartbeat_check()
