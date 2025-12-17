
import unittest
import sys
import os
import uuid
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.main import app
from common.database import get_db, SessionLocal, Base, engine
from common.models import Automation, ConfigAuditLog

class TestAPIConfigAudit(unittest.TestCase):
    """
    MANUAL VERIFICATION CONTROL:
    5. Config change audit
    Change a weight via admin UI (API); verify audit entry with user and reason.
    """
    
    def setUp(self):
        # Override dependency with local session
        # For simplicity in this test environment, we rely on the main test db or mock
        # Ideally using TestClient with dependency override
        self.client = TestClient(app)
        
        self.db = SessionLocal()
        
        # Create a test automation
        self.automation_id = uuid.uuid4()
        auto = Automation(
             id=self.automation_id,
             name="UI Audit Test Bot",
             slug=f"ui-audit-{str(uuid.uuid4())[:8]}",
             status="active",
             config={"risk_level": "low", "weights": {"vol": 20}}
        )
        try:
             self.db.add(auto)
             self.db.commit()
        except:
             self.db.rollback()
             # Cleanup if exists
             self.db.query(Automation).delete()
             self.db.add(auto)
             self.db.commit()
             
    def tearDown(self):
        self.db.close()

    @patch('api.main.producer')
    def test_audit_via_api(self, mock_producer):
        print("\n[Test] Config Change via API")
        
        # 1. Update Config Request
        new_config = {"risk_level": "high", "weights": {"vol": 50}}
        reason = "Admin UI: Adjusting weights for volatility"
        user_id = str(uuid.uuid4()) # Must be valid UUID for ConfigAuditLog if enforced
        
        payload = {
            "config": new_config,
            "reason": reason,
            "user_id": user_id,
            "second_approver": "supervisor_01" # Safety net for OOH testing
        }
        
        response = self.client.patch(f"/automations/{self.automation_id}", json=payload)
        
        # 2. Verify Response
        if response.status_code != 200:
            print(f"API Error: {response.text}")
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['config']['risk_level'], "high")
        
        print("   PASS: API returned 200 OK with updated config.")
        
        # 3. Verify Database Audit
        # Re-query DB
        log = self.db.query(ConfigAuditLog).filter(
            ConfigAuditLog.automation_id == self.automation_id,
            ConfigAuditLog.change_reason == reason
        ).first()
        
        self.assertIsNotNone(log, "FATAL: No audit log found for API action!")
        self.assertEqual(log.new_config['weights']['vol'], 50)
        self.assertEqual(str(log.user_id), user_id)
        
        print(f"   PASS: Audit log verified. User: {log.user_id} | Reason: {log.change_reason}")

if __name__ == "__main__":
    unittest.main()
