
import unittest
import sys
import os
import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.maintenance.integrity_check import IntegrityChecker
from common.models import Signal
from common.database import SessionLocal

class TestMissingSnapshot(unittest.TestCase):
    """
    TRIPLE CHECK: Mistake #11 Acceptance Criteria
    Missing snapshot test: delete one L2 snapshot → system alerts and flags signal as incomplete.
    """
    
    @patch('workers.maintenance.integrity_check.boto3')
    @patch('workers.maintenance.integrity_check.event_bus')
    def test_missing_snapshot_alert(self, mock_event_bus, mock_boto):
        print("\n[Test] Integrity Checker: Missing Snapshot Detection")
        
        # 1. Setup Mock S3
        mock_s3_client = MagicMock()
        mock_boto.client.return_value = mock_s3_client
        
        # Simulate 'head_object' raising ClientError (404 Not Found)
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'head_object')
        
        # 2. Setup DB with a Signal pointing to a missing snapshot
        db = SessionLocal()
        signal_id = uuid.uuid4()
        
        # Clean up prev run
        try:
             db.query(Signal).delete()
             db.commit()
        except: pass
        
        signal = Signal(
            id=signal_id,
            symbol="MISSING_SNAP_TEST",
            timestamp=datetime.utcnow(),
            score=50,
            status="new",
            l2_snapshot_path="s3://features/missing_file.json",
            payload={}
        )
        db.add(signal)
        db.commit()
        
        # 3. Run Integrity Checker
        checker = IntegrityChecker()
        # Ensure it uses our mock s3 even if init happened before patch (it happens inside init so patch works)
        # Re-assign just in case init used the return value of the mock
        checker.s3 = mock_s3_client
        
        checker.verify_signal_snapshots()
        
        # 4. Verify Alert
        # Expect event_bus.publish("system.alert", ...)
        self.assertTrue(mock_event_bus.publish.called, "EventBus should publish an alert")
        
        call_args = mock_event_bus.publish.call_args_list[0]
        topic = call_args[0][0]
        payload = call_args[0][1]
        
        self.assertEqual(topic, "system.alert")
        self.assertEqual(payload["level"], "CRITICAL")
        self.assertEqual(payload["type"], "MISSING_SNAPSHOT")
        self.assertEqual(payload["signal_id"], str(signal_id))
        
        print("PASS: System alerted on missing snapshot.")
        
        # 5. Verify Signal Flag
        db.refresh(signal)
        self.assertEqual(signal.status, "INCOMPLETE_DATA", "Signal status should be flagged INCOMPLETE_DATA")
        print("PASS: Signal flagged as INCOMPLETE_DATA.")
        
        db.close()

if __name__ == "__main__":
    unittest.main()
