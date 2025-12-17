import json
import os

GRAFANA_DIR = "grafana"
if not os.path.exists(GRAFANA_DIR):
    os.makedirs(GRAFANA_DIR)

def create_dashboard(uid, title, panels):
    return {
        "uid": uid,
        "title": title,
        "timezone": "browser",
        "schemaVersion": 30,
        "version": 1,
        "panels": panels
    }

def panel_stat(title, expr, thresholds=None):
    return {
        "type": "stat",
        "title": title,
        "targets": [{"expr": expr}],
        "fieldConfig": {
            "defaults": {
                "thresholds": thresholds or {"mode": "absolute", "steps": [{"value": None, "color": "green"}, {"value": 80, "color": "red"}]}
            }
        }
    }

def panel_graph(title, targets):
    return {
        "type": "timeseries",
        "title": title,
        "targets": [{"expr": t["expr"], "legendFormat": t.get("legend", "")} for t in targets]
    }

# 1. System Health
system_health = create_dashboard("system-health", "System Health Panel", [
    panel_stat("Heartbeat Status", 'count(heartbeat_timestamp > (time()-30))', {"steps": [{"value":None, "color":"red"}, {"value":1, "color":"green"}]}),
    panel_graph("CPU Usage", [{"expr": "process_cpu_seconds_total", "legend": "{{service}}"}]),
    panel_graph("Memory Usage", [{"expr": "process_resident_memory_bytes", "legend": "{{service}}"}]),
])

# 2. Latency Panel
latency = create_dashboard("latency-panel", "Latency Panel", [
    panel_graph("Ingest -> Bar", [{"expr": "rate(latency_ingest_bar_sum[5m]) / rate(latency_ingest_bar_count[5m])", "legend": "Avg Latency"}]),
    panel_graph("Bar -> Feature", [{"expr": "rate(latency_bar_feature_sum[5m]) / rate(latency_bar_feature_count[5m])", "legend": "Avg Latency"}]),
    panel_graph("Feature -> Signal", [{"expr": "rate(latency_feature_signal_sum[5m]) / rate(latency_feature_signal_count[5m])", "legend": "Avg Latency"}]),
    panel_graph("End to End (99th)", [{"expr": "histogram_quantile(0.99, rate(latency_e2e_bucket[5m]))", "legend": "p99"}]),
])

# 3. Circuit Breaker
cb = create_dashboard("circuit-breaker", "Circuit Breaker Panel", [
    panel_stat("Breaker Status", "circuit_breaker_status", {"steps": [{"value":0, "color":"green"}, {"value":1, "color":"red"}]}),
    panel_graph("Trips", [{"expr": "increase(circuit_breaker_trips_total[1h])", "legend": "Trips"}]),
    panel_graph("Resume Attempts", [{"expr": "increase(correction_ui_resume_requests_total[1h])", "legend": "Resumes"}]),
])

# 4. Admin Change Log (Mocking as Table)
admin_log = {
    "uid": "admin-changelog",
    "title": "Admin UI Change-Log Panel",
    "panels": [
        {
            "type": "table",
            "title": "Recent Changes",
            "targets": [{"expr": "admin_changes_recent", "format": "table"}],
            "transformations": []
        }
    ]
}

# Write files
dashboards = {
    "system_health_dashboard.json": system_health,
    "latency_dashboard.json": latency,
    "circuit_breaker_dashboard.json": cb,
    "admin_changelog_dashboard.json": admin_log
}

for filename, content in dashboards.items():
    path = os.path.join(GRAFANA_DIR, filename)
    with open(path, "w") as f:
        json.dump(content, f, indent=2)
    print(f"Generated {path}")

# Helper: Create provisioning files
import yaml

prov_dash = {
    "apiVersion": 1,
    "providers": [
        {
            "name": "Antigravity",
            "folder": "Antigravity",
            "type": "file",
            "options": {"path": os.path.abspath(GRAFANA_DIR)}
        }
    ]
}

prov_ds = {
    "apiVersion": 1,
    "datasources": [
        {
            "name": "Prometheus",
            "type": "prometheus",
            "access": "proxy",
            "url": "http://localhost:9090",
            "isDefault": True
        }
    ]
}

# Write provisioning to tools (if exists) or local 'conf'
# We don't know where tools ended up exactly until extraction finishes, but we can guess pattern
# Assuming d:\...\tools\grafana-v10.2.0\conf\provisioning
# We'll write to a temp 'provisioning' dir and copy it later
if not os.path.exists("provisioning/dashboards"):
    os.makedirs("provisioning/dashboards")
if not os.path.exists("provisioning/datasources"):
    os.makedirs("provisioning/datasources")

with open("provisioning/dashboards/default.yaml", "w") as f:
    yaml.dump(prov_dash, f)

with open("provisioning/datasources/default.yaml", "w") as f:
    yaml.dump(prov_ds, f)

print("Provisioning configs generated.")
