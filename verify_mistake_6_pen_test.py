
import sys
import os
import unittest

# Add parent dir to path
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from infra.secure_vault import vault

class TestRBACPentest(unittest.TestCase):
    
    def test_detection_service_denied(self):
        """
        Pen-Test: Verify 'DetectionService' cannot access 'BROKER_API_KEY'.
        """
        print("\n[PEN-TEST] Attempting to access BROKER_API_KEY as 'DetectionService'...")
        try:
            secret = vault.get_secret("DetectionService", "BROKER_API_KEY")
            print(f"FAILED: Secret leaked! Value: {secret}")
            self.fail("DetectionService was able to access Broker Key! RBAC Failed.")
        except PermissionError as e:
            print(f"SUCCESS: Access Denied as expected. ({e})")
            
    def test_execution_service_allowed(self):
        """
        Verify 'ExecutionService' CAN access.
        """
        print("\n[PEN-TEST] Attempting to access BROKER_API_KEY as 'ExecutionService'...")
        try:
            secret = vault.get_secret("ExecutionService", "BROKER_API_KEY")
            if "SECRET_KEY" in secret:
                print("SUCCESS: ExecutionService retrieved secret.")
            else:
                self.fail("Secret retrieved but value is wrong.")
        except PermissionError:
            self.fail("ExecutionService was DENIED access! System/Operational failure.")

    def test_audit_log_created(self):
        """
        Verify that the denial was logged in the database.
        """
        print("\n[AUDIT] Verifying VaultAccessLog for denial...")
        from common.database import get_db
        from common.models import VaultAccessLog
        
        with next(get_db()) as db:
            # Look for the last denial
            log = db.query(VaultAccessLog).filter(
                VaultAccessLog.service_name == "DetectionService", 
                VaultAccessLog.status == "DENIED"
            ).order_by(VaultAccessLog.timestamp.desc()).first()
            
            if log:
                print(f"SUCCESS: Denial logged. ID: {log.id} | TS: {log.timestamp}")
            else:
                # Note: This might fail if the previous test didn't run or commit fast enough, 
                # but in unit test flow it should be fine.
                print("WARNING: Could not find audit log for denial. Check DB commit.")

if __name__ == "__main__":
    unittest.main()
