import os
import shutil
import subprocess
import time
import requests

TOOLS_DIR = os.path.abspath("tools")
GRAFANA_HOME = os.path.join(TOOLS_DIR, "grafana-10.2.0")
PROMETHEUS_HOME = os.path.join(TOOLS_DIR, "prometheus-2.45.0.windows-amd64")

# 1. Setup Provisioning
conf_prov = os.path.join(GRAFANA_HOME, "conf", "provisioning")
if os.path.exists(conf_prov):
    shutil.rmtree(conf_prov)
shutil.copytree("provisioning", conf_prov)

print(f"Provisioning copied to {conf_prov}")

# 2. Check Rules with Promtool
print("Checking Alert Rules...")
promtool = os.path.join(PROMETHEUS_HOME, "promtool.exe")
rules = os.path.abspath("prometheus/alert_rules.yml")
cmd = [promtool, "check", "rules", rules]
res = subprocess.run(cmd, capture_output=True, text=True)
print(res.stdout)
print(res.stderr)
with open("promtool_check.log", "w") as f:
    f.write(res.stdout + "\n" + res.stderr)

# 3. Start Grafana
print("Starting Grafana...")
env = os.environ.copy()
env["GF_AUTH_ANONYMOUS_ENABLED"] = "true"
env["GF_AUTH_ANONYMOUS_ORG_ROLE"] = "Admin"
env["GF_SECURITY_ADMIN_PASSWORD"] = "admin"

grafana_bin = os.path.join(GRAFANA_HOME, "bin", "grafana-server.exe")
# Run in background
grafana_proc = subprocess.Popen([grafana_bin], cwd=str(GRAFANA_HOME), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Wait for Grafana
print("Waiting for Grafana on port 3000...")
for i in range(30):
    try:
        r = requests.get("http://localhost:3000/api/health")
        if r.status_code == 200:
            print("Grafana is UP!")
            break
    except:
        pass
    time.sleep(2)
else:
    print("Grafana failed to start.")
    exit(1)

# 4. Verify Dashboards via API
print("Verifying Dashboards...")
r = requests.get("http://localhost:3000/api/search")
dashboards = r.json()
print("Found Dashboards:", json.dumps(dashboards, indent=2))

with open("grafana_api_dashboards.json", "w") as f:
    json.dump(dashboards, f, indent=2)

print("Setup Complete. Grafana is running.")
