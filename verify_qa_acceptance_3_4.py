"""
Verification: QA Acceptance Criteria #3 & #4 (Triple Check)
Specific QA Scenarios:
1. Change log: change config in UI -> entry appears in audit table with metadata.
2. Human gating: switch automation to live and attempt first trade -> UI enforces 2FA.
"""

import sys
import os
import uuid
from datetime import datetime

# Path setup
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db
from common.models import Automation, ConfigAuditLog
from common.config_manager import ConfigManager
from execution.execution_service import ExecutionService

def verify_qa_scenarios():
    print("TEST: QA Acceptance Criteria #3 & #4 (Targeted Triple Check)")
    print("=" * 60)
    
    # --- SCENARIO 1: Change Log Metadata ---
    print("1. QA Scenario: Change Config -> Verify Metadata...")
    
    with next(get_db()) as db:
        # Setup: Existing Automation
        slug = f"qa-config-{str(uuid.uuid4())[:8]}"
        auto = Automation(name="QA Config Tester", slug=slug, status="active", config={"risk": "low"})
        db.add(auto)
        db.commit()
        db.refresh(auto)
        auto_id = str(auto.id)
        
    print(f"   [Step] Automation '{slug}' created with config {{'risk': 'low'}}")
    
    # Action: Simulate UI Update
    new_conf = {"risk": "high", "stop_loss": 0.05}
    reason = "QA Manual Update"
    user = str(uuid.uuid4()) # Mock User ID
    ip = "192.168.1.100"
    
    # We call ConfigManager directly (Backend of UI)
    log_id = ConfigManager.update_config(
        automation_id=auto_id,
        new_config=new_conf,
        reason=reason,
        user_id=user,
        ip_address=ip,
        second_approver="QA_LEAD" # Required for Out-Of-Hours Compliance
    )
    
    # Verification: Check Table
    with next(get_db()) as db:
        entry = db.query(ConfigAuditLog).filter(ConfigAuditLog.id == log_id).first()
        
        if not entry:
            print("   FAILURE: Audit log entry NOT found.")
            sys.exit(1)
            
        print("   [Check] Entry found in `config_audit_logs` table.")
        
        # Verify Metadata
        errors = []
        if entry.automation_id != uuid.UUID(auto_id): errors.append("Automation ID mismatch")
        if entry.user_id != uuid.UUID(user): errors.append("User ID mismatch")
        if entry.change_reason != reason: errors.append(f"Reason mismatch: {entry.change_reason}")
        if entry.old_config != {"risk": "low"}: errors.append(f"Old Config mismatch: {entry.old_config}")
        if entry.new_config != new_conf: errors.append("New Config mismatch")
        if entry.ip_address != ip: errors.append("IP Address mismatch")
        
        if not errors:
            print("   SUCCESS: All metadata (User, IP, Reason, Diff) verified.")
        else:
            print(f"   FAILURE: Metadata errors: {errors}")
            sys.exit(1)

    # --- SCENARIO 2: Human Gating 2FA ---
    print("\n2. QA Scenario: First Trade -> Enforce 2FA...")
    
    exec_svc = ExecutionService()
    token = "INTERNAL_SECURE_TOKEN_XYZ"
    
    with next(get_db()) as db:
        # Setup: New Automation (0 trades)
        slug_gate = f"qa-gate-{str(uuid.uuid4())[:8]}"
        auto_gate = Automation(name="QA Gate Tester", slug=slug_gate, status="active", 
                               is_fully_automated=False, approved_trade_count=0)
        db.add(auto_gate)
        db.commit()
        db.refresh(auto_gate)
        gate_id = str(auto_gate.id)
        
    print(f"   [Step] Automation '{slug_gate}' live (Trades: 0). Attempting execution...")
    
    # Mock Order Request
    order_req = {
        "automation_id": gate_id,
        "symbol": "QA_GATE",
        "action": "BUY",
        "quantity": 1,
        "price": 100.0
    }
    
    # Test A: No 2FA Token -> Expect Failure
    result_no_2fa = exec_svc.execute_order(order_req, token, is_manual_approval=False) 
    # Note: is_manual_approval=False simulates the "System" trying to trade. 
    # But wait, if it's NOT fully automated, system trade should be REJECTED demanding manual approval.
    
    if result_no_2fa["status"] == "REJECTED_GATING":
        print(f"   [Check] Automatic Execution Rejected: {result_no_2fa['reason']} (Correct)")
    else:
        print(f"   FAILURE: Automatic Execution allowed without graduation! Status: {result_no_2fa['status']}")
        sys.exit(1)
        
    # Test B: Manual Approval WITHOUT Token -> Expect Failure
    # This simulates clicking "Approve" in UI but failing 2FA
    result_bad_2fa = exec_svc.execute_order(order_req, token, is_manual_approval=True, otp_token=None)
    
    if result_bad_2fa["status"] == "REJECTED_2FA":
        print("   [Check] Manual Approval without Token Rejected (Correct)")
    else:
        print(f"   FAILURE: Manual Approval allowed without 2FA! Status: {result_bad_2fa['status']}")
        sys.exit(1)
        
    # Test C: Manual Approval WITH Token -> Expect Success
    # Simulates entering correct code on phone
    result_good_2fa = exec_svc.execute_order(order_req, token, is_manual_approval=True, otp_token="123456")
    
    if result_good_2fa["status"] == "FILLED":
        print("   SUCCESS: Manual Approval with 2FA Accepted.")
    else:
        print(f"   FAILURE: Valid 2FA Rejected! Status: {result_good_2fa}")
        sys.exit(1)

    print("\nVERIFICATION COMPLETE: QA Criteria #3 & #4 Verified.")

if __name__ == "__main__":
    verify_qa_scenarios()
