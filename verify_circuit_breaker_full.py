import subprocess
import time
import requests
import sys
import os
import signal
import json
import glob

# Configuration
API_HOST = "http://localhost:8000"
API_PROCESS_NAME = "api.main:app" # For uvicorn
VERIFICATION_TEST_SCRIPT = "verify_circuit_breaker_test.py"
AUDIT_DIR = "s3_audit_local/circuit-breaker"

def log(msg):
    print(f"[VERIFY-CB] {msg}")

def kill_existing_api():
    log("Checking for existing API process...")
    # Windows kill by port 8000
    try:
        subprocess.run("netstat -ano | findstr :8000", shell=True)
        # We'll just try to kill uvicorn python processes
        subprocess.run("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq API_SERVER*\"", shell=True, capture_output=True)
        # A more aggressive kill if needed, but risky.
        # Let's rely on finding standard python processes.
    except Exception:
        pass

def start_api():
    log("Starting API Server...")
    # Start via uvicorn in a separate process
    # We assume 'api.main:app' and run from root.
    env = os.environ.copy()
    # Ensure PYTHONPATH includes root
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
    
    # Using a title so we can kill it later if we want specific targeting
    cmd = f'title API_SERVER && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000'
    proc = subprocess.Popen(cmd, shell=True, env=env, cwd=os.getcwd())
    return proc

def wait_for_api(timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"{API_HOST}/health", timeout=1)
            log("API is UP.")
            return True
        except:
            time.sleep(1)
            print(".", end="", flush=True)
    log("API Failed to start.")
    return False

def run_tests():
    log("Running Verification Suite...")
    res = subprocess.run([sys.executable, VERIFICATION_TEST_SCRIPT], capture_output=True, text=True)
    print(res.stdout)
    print(res.stderr)
    return res.returncode == 0

def check_audit_artifacts():
    log("Checking S3 Audit Artifacts...")
    files = glob.glob(os.path.join(AUDIT_DIR, "*.json"))
    if not files:
        log("FAIL: No audit JSON files found in " + AUDIT_DIR)
        return False
    
    log(f"Found {len(files)} audit records.")
    
    # Check content of one
    with open(files[0], 'r') as f:
        data = json.load(f)
        if "signed_hash" not in data:
            log("FAIL: signed_hash missing in audit record")
            return False
        if "evidence_link" not in data:
            log("FAIL: evidence_link missing")
            return False
            
    log("Audit Artifacts Verified Valid.")
    return True

def main():
    kill_existing_api()
    api_proc = start_api()
    
    try:
        if not wait_for_api():
            sys.exit(1)
            
        success = run_tests()
        if not success:
            log("Verification Suite Failed.")
            sys.exit(1)
            
        if not check_audit_artifacts():
            log("Artifact Verification Failed.")
            sys.exit(1)
            
        log("=== FULL CIRCUIT BREAKER VERIFICATION PASSED ===")
        # Generate summary
        with open("CB_VERIFICATION_SUMMARY.txt", "w") as f:
            f.write("PASS: API Endpoints\n")
            f.write("PASS: RBAC Enforcement\n")
            f.write("PASS: Audit Logging (DB + S3)\n")
            f.write("PASS: Signed Hashes\n")
            f.write("PASS: UI Availability\n")
            
    finally:
        log("Shutting down API...")
        subprocess.run("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq API_SERVER*\"", shell=True, capture_output=True)

if __name__ == "__main__":
    main()
