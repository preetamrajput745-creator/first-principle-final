import requests
import json
import os
import shutil
import hashlib
import time

TASK_ID = "20251211-GRAFANA-832"
DATE = "2025-12-11"
AUDIT_DIR = f"antigravity-audit/{DATE}/{TASK_ID}/grafana"
if not os.path.exists(AUDIT_DIR):
    os.makedirs(AUDIT_DIR)

print(f"Exporting to {AUDIT_DIR}")

# 1. Export Dashboards
r = requests.get("http://localhost:3000/api/search")
dashboards = r.json()
print(f"Found {len(dashboards)} dashboards.")

manifest_dash = []

for d in dashboards:
    uid = d['uid']
    title = d['title']
    print(f"Exporting {title} ({uid})...")
    
    # Get Full JSON
    try:
        dr = requests.get(f"http://localhost:3000/api/dashboards/uid/{uid}")
        full_json = dr.json()
        
        # Save JSON
        filename = f"dashboard-{uid}.json"
        filepath = os.path.join(AUDIT_DIR, filename)
        with open(filepath, "w") as f:
            json.dump(full_json, f, indent=2)
            
        # Metadata
        meta_filename = f"dashboard-{uid}-metadata.json"
        with open(os.path.join(AUDIT_DIR, meta_filename), "w") as f:
            json.dump({
                "uid": uid,
                "title": title,
                "url": d.get('url'),
                "folder": d.get('folderTitle', 'General')
            }, f, indent=2)

        manifest_dash.append({"uid": uid, "title": title, "file": filename})
    except Exception as e:
        print(f"Failed to export {uid}: {e}")

# 2. Export Alerts
shutil.copy("prometheus/alert_rules.yml", os.path.join(AUDIT_DIR, "prometheus_rules.yml"))
if os.path.exists("promtool_check.log"):
    shutil.copy("promtool_check.log", os.path.join(AUDIT_DIR, "promtool_check.log"))

# 3. Create Manifest
manifest = {
    "run_id": TASK_ID,
    "date": DATE,
    "dashboards": manifest_dash,
    "rules": ["prometheus_rules.yml"],
    "tester": "Mastermind"
}
with open(os.path.join(AUDIT_DIR, "grafana_manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)

print("Export Complete.")
