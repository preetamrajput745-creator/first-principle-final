"""
Execution Service - Mistake #6 Compliance
The ONLY component authorized to execute trades.
Isolated from detection/signal logic.
"""

import time
import requests
import uuid
from datetime import datetime

import os
import sys

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class ExecutionService:
    """
    Handles order execution securely.
    In a real system, this would run in a separate VPC/Subnet.
    """
    
    
    def __init__(self):
        # MISTAKE #6 FIX: Fetch Credentials from Vault
        from infra.secure_vault import vault
        
        try:
            # RBAC Check: ExecutionService is ALLOWED
            self._broker_api_key = vault.get_secret("ExecutionService", "BROKER_API_KEY")
            self._broker_secret = vault.get_secret("ExecutionService", "BROKER_API_SECRET")
            print("EXECUTION SERVICE: Credentials successfully retrieved from Vault.")
        except Exception as e:
            print(f"EXECUTION SERVICE CRITICAL ERROR: Could not get secrets! {e}")
            self._broker_api_key = None
            self.is_active = False # Kill switch if no secrets
            return
            
        self._internal_auth_token = "INTERNAL_SECURE_TOKEN_XYZ" # Required to call this service
        self.is_active = True
        
    def validate_request(self, order_request: dict, auth_token: str) -> bool:
        """
        Validate authentication and order parameters.
        """
        # 1. Auth Check (Mistake #6 requirement)
        if auth_token != self._internal_auth_token:
            print(f"EXECUTION BLOCKED: Invalid Auth Token provided!")
            return False
            
        # 2. Field Check
        required_fields = ["symbol", "action", "quantity", "price"]
        for field in required_fields:
            if field not in order_request:
                print(f"EXECUTION BLOCKED: Missing {field}")
                return False
                
        # 3. Sanity Check (Mini-Circuit Breaker at Exec Level)
        if order_request["quantity"] > 1000:
             print(f"EXECUTION BLOCKED: Quantity {order_request['quantity']} exceeds hard limit")
             return False
             
        return True

    def check_gating(self, automation_id: str):
        """
        Mistake #7: Human Gating Check
        Returns: (passed: bool, reason: str)
        """
        from common.database import get_db
        from common.models import Automation
        import uuid
        
        with next(get_db()) as db:
            auto = db.query(Automation).filter(Automation.id == uuid.UUID(automation_id)).first()
            if not auto:
                return False, "Automation Not Found"
                
            if auto.is_fully_automated:
                return True, "Fully Automated"
            
            # Require Manual Approval if not fully automated
            return False, f"Human Gating Active. Completed {auto.approved_trade_count}/10 approvals."

    def verify_2fa(self, token: str) -> bool:
        """
        Verify the 2FA token.
        In production, this would validate against a TOTP secret or 2FA service.
        For this implementation, we check against a predefined pattern or mock.
        """
        # Mock 2FA validation
        # In a real scenario: return pyotp.TOTP(secret).verify(token)
        if not token:
            print("2FA FAILED: No token provided.")
            return False
            
        # Example: Accept '123456' or specific logic
        if token == "123456" or token == "VALID_2FA_TOKEN": 
            print("2FA VERIFIED.")
            return True
            
        print(f"2FA FAILED: Invalid token '{token}'")
        return False

    def execute_order(self, order_request: dict, auth_token: str, is_manual_approval: bool = False, otp_token: str = None) -> dict:
        """
        Execute the order if valid and authorized.
        """
        if not self.is_active:
            return {"status": "REJECTED", "reason": "Execution Service Paused"}
            
        if not self.validate_request(order_request, auth_token):
            return {"status": "REJECTED", "reason": "Validation/Auth Failed"}
            
        # MISTAKE #7 ENFORCEMENT
        automation_id = order_request.get("automation_id")
        if automation_id:
            passed, reason = self.check_gating(automation_id)
            if not passed:
                if not is_manual_approval:
                    print(f"GATING BLOCK: {reason}")
                    return {"status": "REJECTED_GATING", "reason": reason}
                
                # Enforce 2FA for Manual Approval
                if not self.verify_2fa(otp_token):
                     print("GATING BLOCK: 2FA Failed")
                     return {"status": "REJECTED_2FA", "reason": "Invalid or missing 2FA token for manual approval"}
            
        print(f"SECURE EXECUTION: Sending {order_request['action']} {order_request['symbol']} to BROKER")
        
        # Update Counter if Manual
        if is_manual_approval and automation_id:
             from common.database import get_db
             from common.models import Automation
             # import uuid removed (shadows global)
             with next(get_db()) as db:
                 auto = db.query(Automation).filter(Automation.id == uuid.UUID(automation_id)).first()
                 auto.approved_trade_count += 1
                 if auto.approved_trade_count >= 10:
                     auto.is_fully_automated = True
                     print("GRADUATION: Automation is now FULLY AUTOMATED!")
                 db.commit()
        
        # Simulate Broker Interaction...
        time.sleep(0.1)
        
        return {
            "status": "FILLED",
            "fill_price": order_request["price"],
            "filled_at": datetime.utcnow().isoformat(),
            "execution_id": f"EXEC-{str(uuid.uuid4())[:8]}"
        }

if __name__ == "__main__":
    # Test
    exec_svc = ExecutionService()
    order = {
        "symbol": "NIFTY",
        "action": "BUY",
        "quantity": 50,
        "price": 21500.0
    }
    # Should fail due to validation or no 2FA if gating assumes default (but gating req automation_id)
    result = exec_svc.execute_order(order, "INTERNAL_SECURE_TOKEN_XYZ")
    print(f"Execution Result (No Auto ID): {result}")
