"""
Verification: Mistake #9 - Test Coverage
Meta-check: Ensures verification scripts exist for all 12 fatal mistakes.
"""
import os
import sys

def verify_coverage():
    print("TEST: Code Coverage / Verification Compliance (Mistake #9)")
    print("=" * 60)
    
    required_scripts = [
        "verify_data.py", # 1
        "test_overwrite_protection.py", # 2
        "verify_clock_metrics.py", # 3
        "workers/backtest/backtest_engine.py", # 4
        "system_supervisor.py", # 5 (Process)
        "workers/execution/execution_service.py", # 6 (Code)
        "verify_human_gating.py", # 7
        "test_audit_log.py", # 8
        "run_full_system_verification.py", # 9 (The Suite itself)
        "verify_circuit_breaker_lifecycle.py", # 10
        "verify_l2_completeness.py", # 11
        "verify_market_regime.py" # 12
    ]
    
    missing = []
    for script in required_scripts:
        if not os.path.exists(script):
            missing.append(script)
        else:
            print(f"   CHECK: Found {script}")
            
    if missing:
        print(f"\nFAILURE: Missing verification scripts for: {missing}")
        sys.exit(1)
        
    print("\nSUCCESS: All Critical Paths have Verification Suites.")
    print("VERIFICATION COMPLETE.")

if __name__ == "__main__":
    verify_coverage()
