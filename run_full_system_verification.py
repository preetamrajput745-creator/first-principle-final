"""
MASTER VERIFICATION SCRIPT
Runs all compliance checks for Mistakes 1-12.
"""
import subprocess
import sys
import os
import time

TESTS = [
    # Core Logic
    ("tests/test_scoring_logic.py", "Mistake #1 (Scoring Logic)"),
    ("tests/test_isolation.py", "Mistake #6 (Privilege Isolation)"),
    
    # Data & Storage
    ("tests/test_raw_data_immutability.py", "Mistake #2 (Immutable Data)"),
    ("tests/test_audit_log.py", "Mistake #8 (Audit Logs)"),
    ("verify_retention_archival.py", "Mistake #10/Retention (Archival Policies)"),
    ("verify_s3_overwrite.py", "Mistake #2 (S3 Overwrite Protection)"),
    ("verify_circuit_breaker_test.py", "Acceptance #6 (CB Drawdown Test)"),
    ("verify_regime_filter.py", "Acceptance #8 (Regime Filter)"),
    ("verify_mistake_2_clock.py", "Control #2 (Clock Norm Svc)"),
    ("verify_governance_enforcement.py", "Acceptance #5 (Governance)"),
    ("verify_mistake_9_10_complex.py", "Acceptance #9/10 (Obs Complex)"),
    ("verify_qa_acceptance_3_4.py", "QA Scenarios #3/#4 (Triple Check)"),
    ("verify_pnl_slippage_panel.py", "PnL/Slippage Panel & Alerts (Zero-Tolerance)"),
    
    # Risk & Safety
    ("tests/test_circuit_breaker_loss.py", "Mistake #7/#10 (Circuit Breaker & Limits)"),
    ("tests/test_slippage_adversarial.py", "Mistake #4 (Adversarial Slippage)"),
    ("tests/test_mistake5_fault_injection.py", "Mistake #5 (Fault Injection)"),
    
    # Integration & Gating
    ("tests/test_api_gating.py", "Mistake #6 (API Human Gating 2FA)"),
    ("tests/test_pipeline_end_to_end.py", "Mistake #9 (End-to-End Pipeline)"),
    ("tests/test_integration_replay.py", "Mistake #9 (Integration Replay)"),
    ("tests/test_smoke_ingest.py", "Mistake #9 (Ingest Smoke Test)"),
    
    # Legacy/Specific Verifications (Keep relevant ones)
    ("verify_human_gating.py", "Manual Gating Workflow (End-to-End)"),

    # NEW MISTAKE VERIFICATIONS (MONITORING & HARDENING)
    ("verify_env.py", "Environment & Installation Checks"),
    ("verify_signal_panel.py", "Signal Flow Panel & Alerts (Mistake #1/Metrics)"),
    ("verify_mistake_2_immutability.py", "Mistake #2 (Immutability Blocking)"),
    ("verify_mistake_5_heartbeat.py", "Mistake #5 (Heartbeat & Probes)"),
    ("verify_mistake_6_pentest.py", "Mistake #6 (RBAC Pen-Test)"),
    ("verify_mistake_7_slippage_pause.py", "Mistake #7/#10 (Slippage Pause)"),
    ("verify_mistake_8_checksum.py", "Mistake #8 (Checksum Log)"),
    ("verify_mistake_9_l2.py", "Mistake #9 (L2 Snapshot Completeness)"),
    ("verify_mistake_11_latency.py", "Mistake #11 (Latency Panel)"),
    ("verify_mistake_13_audit.py", "Mistake #13 (Audit Log & Alert)"),
]

def run_all():
    print("STARTING FULL SYSTEM VERIFICATION")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for script, desc in TESTS:
        print(f"\n>> RUNNING: {desc} ({script})")
        print("-" * 40)
        
        start = time.time()
        try:
            # Run script
            result = subprocess.run([sys.executable, script], 
                                  cwd=os.path.dirname(os.path.abspath(__file__)),
                                  capture_output=True,
                                  text=True)
            
            # Print output needed for debugging? Maybe just summary.
            # Printing first few lines of output
            output_lines = result.stdout.split('\n')
            for line in output_lines[:5]:
                if line.strip(): print(f"   {line}")
            if len(output_lines) > 5: print("   ...")
            
            if result.returncode == 0:
                print(f"PASS ({time.time() - start:.2f}s)")
                passed += 1
            else:
                print(f"FAIL (Exit Code: {result.returncode})")
                print("   ERROR OUTPUT:")
                print(result.stderr)
                failed += 1
                
        except Exception as e:
            print(f"CRASH: {e}")
            failed += 1
            
    print("\n" + "=" * 60)
    print(f"SUMMARY: {passed} PASSED | {failed} FAILED")
    print("=" * 60)
    
    if failed == 0:
        print("SYSTEM READY FOR NEXT PHASE.")
        return True
    else:
        print("SYSTEM NOT READY. FIX FAILURES.")
        return False

if __name__ == "__main__":
    success = run_all()
    if not success:
        sys.exit(1)
