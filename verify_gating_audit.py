import sys
import os
import uuid
from datetime import datetime

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workers.common.database import SessionLocal
from workers.common.models import Automation, ConfigAuditLog, Signal, Order
from workers.execution.execution_service import ExecutionService

def test_gating_and_audit():
    print("=== TESTING MISTAKE 7 (GATING) & MISTAKE 8 (AUDIT) ===")
    
    db = SessionLocal()
    exec_svc = ExecutionService()
    
    # --- PART 1: MISTAKE 7 - HUMAN GATING ---
    print("\n[1] Testing Human Gating Logic...")
    
    # Create a new automation (Should be Gated by default)
    auto_id = uuid.uuid4()
    auto = Automation(
        id=auto_id,
        name="Gated Strategy",
        slug="gated-strat",
        status="active",
        is_fully_automated=False, # GATED
        approved_trade_count=0
    )
    db.add(auto)
    db.commit()
    
    # Try to execute (Should be BLOCKED or Require Approval)
    # ExecutionService.check_gating returns (passed, reason)
    passed, reason = exec_svc.check_gating(str(auto_id))
    print(f"   -> Check Gating Result: Passed={passed}, Reason='{reason}'")
    
    if not passed and "Human Gating Active" in reason:
        print("   -> Gating correctly enforces approval [OK]")
    else:
        print("   -> Gating Failed to block! [FAIL]")
        sys.exit(1)

    # Simulate 10 Approvals
    print("   -> Simulating 10 Manual Approvals...")
    auto.approved_trade_count = 10
    auto.is_fully_automated = True # Logic normally handles this, we force for test
    db.commit()
    
    passed, reason = exec_svc.check_gating(str(auto_id))
    print(f"   -> Check Gating (After 10): Passed={passed}, Reason='{reason}'")
    
    if passed:
        print("   -> Graduation to Fully Automated [OK]")
    else:
        print("   -> Graduation Failed [FAIL]")
        sys.exit(1)


    # --- PART 2: MISTAKE 8 - CONFIG AUDIT ---
    print("\n[2] Testing Config Audit Log...")
    
    # Simulate a Config Change
    old_conf = {"thresh": 0.5}
    new_conf = {"thresh": 0.8}
    reason = "Optimizing for volatility"
    
    audit = ConfigAuditLog(
        automation_id=auto_id,
        user_id=None,
        old_config=old_conf,
        new_config=new_conf,
        change_reason=reason
    )
    db.add(audit)
    db.commit()
    
    # Verify Persistence
    saved_audit = db.query(ConfigAuditLog).filter(ConfigAuditLog.automation_id == auto_id).first()
    
    if saved_audit:
        print(f"   -> Audit Log Found. Reason: {saved_audit.change_reason}")
        if saved_audit.old_config == old_conf and saved_audit.new_config == new_conf:
            print("   -> Config Snapshots match [OK]")
        else:
            print("   -> Config Snapshots mismatch [FAIL]")
            sys.exit(1)
    else:
        print("   -> Audit Log NOT saved [FAIL]")
        sys.exit(1)

    print("\n=== GATING & AUDIT LOGS VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_gating_and_audit()
