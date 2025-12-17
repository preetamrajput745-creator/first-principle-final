
import unittest
import sys
import os
import uuid
import json

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workers"))

from common.database import get_db
from common.models import Automation, ConfigAuditLog
from common.config_manager import ConfigManager

class TestAuditLog(unittest.TestCase):
    """
    TRIPLE CHECK: Mistake #8 - Config Audit Log
    Verifies that config changes are recorded with metadata (reason, user, diff).
    """

    def setUp(self):
        self.automation_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        
        with next(get_db()) as db:
            # Setup Automation
            auto = Automation(
                id=self.automation_id,
                name="Audit Test Bot",
                slug=f"audit-test-{str(uuid.uuid4())[:8]}",
                status="active",
                config={"risk_level": "low"}
            )
            db.add(auto)
            db.commit()

    def test_audit_workflow(self):
        print("\n[Test] Config Audit Integrity")
        
        # 1. Update WITHOUT reason -> Blocked
        try:
            ConfigManager.update_config(
                str(self.automation_id), 
                {"risk_level": "high"}, 
                reason="" 
            )
            self.fail("Update allowed without reason!")
        except ValueError as e:
            print("   PASS: Blocked update without reason.")

        # 2. Update WITH reason -> Logged
        new_conf = {"risk_level": "high", "leverage": 2}
        reason = "Increasing risk for high volatility session"
        
        ConfigManager.update_config(
            str(self.automation_id),
            new_conf,
            reason=reason,
            user_id=str(self.user_id),
            second_approver="AUDIT_TESTER"
        )
        
        # 3. Verify Log
        with next(get_db()) as db:
            log = db.query(ConfigAuditLog).filter(ConfigAuditLog.automation_id == self.automation_id).first()
            self.assertIsNotNone(log, "No audit log found!")
            self.assertEqual(log.change_reason, reason)
            self.assertEqual(log.new_config['risk_level'], "high")
            self.assertEqual(str(log.user_id), str(self.user_id))
            
        print("   PASS: Audit entry verified with metadata.")

if __name__ == "__main__":
    unittest.main()
