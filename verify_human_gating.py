"""
Verification: Mistake #7 - Human Gating
Ensures system enforces N manual approvals before allowing full automation.
"""

import sys
import os
import uuid
import time

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from execution.execution_service import ExecutionService
from common.database import get_db
from common.models import Automation

def verify_gating():
    print("TEST: Human Gating Logic (Mistake #7)")
    print("=" * 60)
    
    automation_id = uuid.uuid4()
    exec_svc = ExecutionService()
    INTERNAL_TOKEN = "INTERNAL_SECURE_TOKEN_XYZ"
    
    with next(get_db()) as db:
        # 1. Setup Automation
        auto = Automation(
            id=automation_id,
            name="Gating Test Bot",
            slug=f"gate-test-{str(uuid.uuid4())[:8]}",
            status="active",
            approved_trade_count=0,
            is_fully_automated=False
        )
        db.add(auto)
        db.commit()
        print(f"1. Setup: Created bot {auto.slug} (Approvals: 0/10)")
        
        # 2. Cycle 10 Trades
        for i in range(1, 12):
            print(f"\n--- Trade Attempt #{i} ---")
            
            order = {
                "symbol": "TEST",
                "action": "BUY",
                "quantity": 1,
                "price": 100.0,
                "automation_id": str(automation_id)
            }
            
            # A) Attempt AUTO (Should Fail until graduated)
            res_auto = exec_svc.execute_order(order, INTERNAL_TOKEN, is_manual_approval=False)
            
            if res_auto["status"] == "REJECTED_GATING":
                print(f"   [AUTO] REJECTED as expected: {res_auto['reason']}")
            elif res_auto["status"] == "FILLED":
                 if i <= 10:
                     print(f"   [AUTO] FAILURE! Auto-trade allowed too early! (Iter {i})")
                     sys.exit(1)
                 else:
                     print(f"   [AUTO] SUCCESS! Full Automation Active.")
            
            # If not graduated, Manual Approve it
            if i <= 10:
                print("   [USER] Performing Manual Approval (Checking 2FA)...")
                
                # Test Invalid 2FA first (Security Check)
                res_invalid = exec_svc.execute_order(order, INTERNAL_TOKEN, is_manual_approval=True, otp_token="WRONG_TOKEN")
                if res_invalid["status"] != "REJECTED_2FA":
                    print(f"   [SECURITY FAILURE] Allowed manual trade with WRONG 2FA! Result: {res_invalid}")
                    sys.exit(1)
                else:
                    print(f"   [SECURITY PASS] Rejected invalid 2FA as expected.")

                # Test Valid 2FA
                res_manual = exec_svc.execute_order(order, INTERNAL_TOKEN, is_manual_approval=True, otp_token="VALID_2FA_TOKEN")
                
                if res_manual["status"] == "FILLED":
                    print("   [USER] Manual Trade Executed (2FA Info Verified).")
                else:
                    print(f"   [USER] FAILURE: Manual trade rejected: {res_manual}")
                    sys.exit(1)
        
    print("VERIFICATION COMPLETE: Gating logic enforced.")

if __name__ == "__main__":
    verify_gating()
