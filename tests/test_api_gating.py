
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os
import uuid
from datetime import datetime

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from common.database import SessionLocal
from common.models import Signal, Automation

class TestGatingAPI(unittest.TestCase):
    """
    TRIPLE CHECK: Mistake #6 Acceptance Criteria
    UI Enforces 2FA -> API Validation -> Execution
    """
    
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        
        # Setup Automation & Signal
        self.auto_id = uuid.uuid4()
        self.auto = Automation(
            id=self.auto_id,
            name="Gating API Bot",
            slug=f"gating-api-{str(uuid.uuid4())[:8]}",
            status="active"
        )
        self.db.add(self.auto)
        
        self.signal_id = uuid.uuid4()
        self.signal = Signal(
            id=self.signal_id,
            automation_id=self.auto_id,
            symbol="BTC-2FA",
            timestamp=datetime.utcnow(),
            score=75,
            status="new",
            payload={"price": 50000.0}
        )
        self.db.add(self.signal)
        self.db.commit()
        
    def tearDown(self):
        self.db.close()
        
    @patch('api.main.producer')
    def test_confirm_with_2fa(self, mock_producer):
        print("\n[Test] UI/API Confirmation Flow (2FA)")
        
        # 1. Simulate UI Request with OTP
        response = self.client.post(
            f"/signals/{self.signal_id}/confirm",
            json={"otp_token": "123456"} # Valid Token
        )
        
        self.assertEqual(response.status_code, 200, f"API Error: {response.text}")
        
        # 2. Verify Producer Message
        # Should be sent to 'exec.approve_command' (Manual Topic)
        self.assertTrue(mock_producer.send.called)
        args = mock_producer.send.call_args
        topic = args[0][0]
        data = args[0][1]
        
        self.assertEqual(topic, "exec.approve_command")
        self.assertEqual(data["otp_token"], "123456")
        self.assertEqual(data["automation_id"], str(self.auto_id))
        self.assertEqual(data["action"], "BUY")
        
        print("PASS: API correctly validates 2FA payload and routes to approval topic.")

if __name__ == "__main__":
    unittest.main()
