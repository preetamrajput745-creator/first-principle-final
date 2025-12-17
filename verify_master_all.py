
import subprocess
import sys
import time

SCRIPTS = [
    ("Mistake #2: Immutable Storage", "verify_mistake_2_immutability.py"),
    ("Mistake #3: Clock Drift", "verify_mistake_3_drift_check.py"),
    ("Mistake #6: RBAC Pen-Test", "verify_mistake_6_pen_test.py"),
    ("Mistake #7: CB Loss Injection", "verify_mistake_7_manual.py"),
    ("Mistake #7: CB Slippage Pause", "verify_mistake_7_slippage_pause.py"),
    ("Mistake #9: Missing Snapshot", "verify_mistake_9_manual.py"),
    ("Mistake #9: Full Pipeline Integration", "verify_mistake_9_full.py"),
]

def run_triple_check():
    print("============================================================")
    print("       MASTER TRIPLE VERIFICATION SUITE       ")
    print("============================================================")
    print(f"Running {len(SCRIPTS)} critical verification scripts...\n")
    
    results = []
    
    for title, script in SCRIPTS:
        print(f"Executing: {title}...")
        start = time.time()
        try:
            # Run script and capture output
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                encoding='utf-8', # Force UTF-8 for subprocess reading
                timeout=120 
            )
            duration = time.time() - start
            
            if result.returncode == 0:
                print(f"   PASS ({duration:.2f}s)")
                results.append((title, "PASS", duration))
            else:
                print(f"   FAIL ({duration:.2f}s)")
                print(f"      [Stderr]: {result.stderr[:200]}...")
                # Also print stdout for debugging context if needed
                # print(f"      [Stdout]: {result.stdout[-200:]}...")
                results.append((title, "FAIL", duration))
                
        except Exception as e:
            print(f"   ERROR: {e}")
            results.append((title, "ERROR", 0))
            
    print("\n============================================================")
    print("                 FINAL REPORT                 ")
    print("============================================================")
    
    all_pass = True
    for title, status, duration in results:
        icon = "[OK]" if status == "PASS" else "[XX]"
        print(f"{icon} {title:<40} : {status} ({duration:.2f}s)")
        if status != "PASS":
            all_pass = False
            
    print("============================================================")
    if all_pass:
        print("ALL SYSTEMS GO. TRIPLE VERIFICATION SUCCESSFUL.")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED. CHECK LOGS.")
        sys.exit(1)

if __name__ == "__main__":
    run_triple_check()
