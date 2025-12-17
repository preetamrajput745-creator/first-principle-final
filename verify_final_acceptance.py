"""
FINAL TRIPLE CHECK: Acceptance Criteria Verification
Aggregates all specific tests for Section 4 of the Audit.

1. RBAC (Pen-Test)
2. Immutable Storage
3. Change Log
4. Human Gating
5. Circuit Breaker (Loss)
6. Missing Snapshot
7. CI Pipeline (Full Suite)
"""

import sys
import os
import io
import contextlib

# Add root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_test(name, script_func):
    print(f"\n>> VERIFYING: {name}")
    print("-" * 50)
    try:
        # Capture output to keep mostly clean, unless error
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            script_func()
        print(f"   PASS: {name}")
        return True
    except SystemExit as e:
        if e.code == 0:
            print(f"   PASS: {name}")
            return True
        else:
            print(f"   FAIL: {name} (Exit Code {e.code})")
            return False
    except Exception as e:
        print(f"   FAIL: {name} (Error: {e})")
        return False

def check_rbac_pen_test():
    """
    Simulate unauthenticated access to Execution Service.
    """
    from workers.execution.execution_service import ExecutionService
    service = ExecutionService()
    
    # Try to execute without token
    # Minimal order struct
    order = {"symbol":"TEST", "action":"BUY", "quantity":1, "price":100}
    response = service.execute_order(order, auth_token="HACKER_TOKEN")
    
    # We expect status=REJECTED (as per execution_service.py)
    if response["status"] == "REJECTED":
        print("Success: Unauthorized access blocked.")
    else:
        print(f"Failure: Hacker token accepted! {response}")
        sys.exit(1)

def main():
    print("STARTING FINAL ACCEPTANCE TRIPLE CHECK")
    print("========================================")
    
    results = {}
    
    # 1. RBAC
    results["RBAC"] = run_test("RBAC (Pen-Test)", check_rbac_pen_test)
    
    # 2. Immutable Storage
    from test_overwrite_protection import test_overwrite_protection
    results["Immutable Storage"] = run_test("Immutable Storage", test_overwrite_protection)
    
    # 3. Change Log
    from verify_audit_log_detailed import verify_audit_log
    results["Change Log"] = run_test("Change Log Metadata", verify_audit_log)

    # 4. Human Gating
    from verify_human_gating import verify_gating
    results["Human Gating"] = run_test("Human Gating (2FA)", verify_gating)

    # 5. Circuit Breaker (Loss)
    from verify_loss_circuit_breaker import verify_loss_breaker
    results["Circuit Breaker"] = run_test("Circuit Breaker (Simulated Loss)", verify_loss_breaker)

    # 6. Missing Snapshot
    from verify_mistake_9_monitoring import verify_monitoring
    results["Missing Snapshot"] = run_test("Missing Snapshot Alert", verify_monitoring)

    # 7. CI Pipeline (The 13-Test Suite)
    from run_full_system_verification import run_all
    # run_all returns boolean (True if 0 failures)
    results["CI Pipeline"] = run_test("CI Pipeline (Full Suite)", lambda: sys.exit(0 if run_all() else 1))

    print("\n========================================")
    print("FINAL RESULTS")
    print("========================================")
    all_pass = True
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} | {name}")
        if not passed: all_pass = False
        
    if all_pass:
        print("\nCONGRATS: All Acceptance Criteria MET.")
    else:
        print("\nWARNING: Some checks FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
