
import sys
import os
import platform
import subprocess
import datetime
import shutil

AUDIT_DIR = os.path.join(os.path.dirname(__file__), "audit", "system-health-hardening")
if not os.path.exists(AUDIT_DIR):
    os.makedirs(AUDIT_DIR)

LOG_FILE = os.path.join(AUDIT_DIR, "env_verification_log.txt")

def log(msg):
    timestamp = datetime.datetime.utcnow().isoformat()
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

def verify_environment():
    log("STARTING TASK 1 & 2: ENVIRONMENT & INSTALLATION CHECKS")
    
    # 1. OS & Time
    log(f"OS Platform: {platform.platform()}")
    log(f"System Time (UTC): {datetime.datetime.utcnow()}")
    
    # 2. Python
    py_ver = sys.version.split()[0]
    log(f"Python Version: {py_ver}")
    if not py_ver.startswith("3."):
        log("FAIL: Python 3 required.")
    
    # 3. Pip Packages
    try:
        pip_freeze = run_cmd(f"{sys.executable} -m pip freeze")
        freeze_path = os.path.join(AUDIT_DIR, "pip_requirements.txt")
        with open(freeze_path, "w") as f:
            f.write(pip_freeze)
        log(f"Pip packages saved to {freeze_path}")
    except Exception as e:
        log(f"FAIL: Could not freeze pip packages: {e}")

    # 4. Node (Optional check)
    node_ver = run_cmd("node --version")
    if node_ver:
        log(f"Node Version: {node_ver}")
    else:
        log("WARN: Node.js not found (Skipping Node checks)")

    # 5. Git
    git_ver = run_cmd("git --version")
    log(f"Git Version: {git_ver}")
    
    # 6. Docker (Optional check)
    docker_ver = run_cmd("docker --version")
    if docker_ver:
        log(f"Docker Version: {docker_ver}")
    else:
        log("WARN: Docker not found (Skipping Docker checks)")

    log("ENVIRONMENT CHECKS COMPLETED.")

if __name__ == "__main__":
    verify_environment()
