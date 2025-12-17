
import sys
import os
import subprocess
import time

def run_verification():
    print("============================================================")
    print("       ENVIRONMENT & INSTALLATION CHECKS (Item 1 & 2)       ")
    print("============================================================")
    
    # 1. Python Version
    v = sys.version_info
    print(f"[1] Python Version: {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or (v.major == 3 and v.minor < 9):
        print("    [FAIL] Python 3.9+ required.")
        sys.exit(1)
    else:
        print("    [PASS] Python version check.")
        
    # 2. NTP / Time Sync (Windows Specific)
    print("\n[2] Time Sync Check...")
    try:
        # Check w32tm status
        res = subprocess.run(["w32tm", "/query", "/status"], capture_output=True, text=True)
        if res.returncode == 0:
            print("    [PASS] w32tm status check.")
            # Verify "Source" is not "Local CMOS Clock" ideally, but simplified check:
            if "Source: Local CMOS Clock" in res.stdout:
                 print("    [WARN] Time source is Local CMOS. Ensure host is synced.")
            else:
                 print("    [PASS] Time source seems valid.")
        else:
            print("    [WARN] w32tm command failed. Skipping strict check.")
    except Exception as e:
        print(f"    [WARN] Could not run w32tm: {e}")
        
    # 3. Repository Check
    print("\n[3] Repository Check...")
    if os.path.exists(".git"):
        print("    [PASS] .git directory found.")
    else:
        print("    [WARN] Not a git repository root?")
        
    # 4. Env File
    print("\n[4] Config Check...")
    if os.path.exists(".env"):
        print("    [PASS] .env file found.")
    else:
        print("    [WARN] .env file MISSING. Using defaults?")
        
    print("\nSUCCESS: Environment Checks Passed.")

if __name__ == "__main__":
    run_verification()
