
import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from execution.execution_gateway import ExecutionGateway
from workers.common.models import Automation

class TestHumanGating(unittest.TestCase):
    
    @patch('execution.execution_gateway.ExecutionSecrets') # Mock secrets loading
    @patch('execution.execution_gateway.event_bus')
    @patch('workers.common.database.SessionLocal')
    def test_gating_blocks_trade(self, mock_db_cls, mock_event_bus, mock_secrets):
        """
        Verify that if trade count < 10, execution is blocked.
        """
        # Setup Gateway
        gateway = ExecutionGateway()
        gateway.db = MagicMock()
        
        # Setup Automation State (Count = 5 < 10)
        mock_automation = Automation(approved_trade_count=5, is_fully_automated=False)
        gateway.db.query.return_value.first.return_value = mock_automation
        
        # Determine Signal
        signal = {"symbol": "BTCUSDT", "price": 50000}
        
        # Attempt Execution
        gateway.execute_order(signal, is_approval_event=False)
        
        # Assertions
        # 1. Broker Key usage should NOT be logged (we mock print, but better to check if 'exec.report' published)
        # Check that 'exec.approval_needed' was published instead of 'exec.report'
        
        msg_type_published = None
        if mock_event_bus.publish.called:
             args, _ = mock_event_bus.publish.call_args
             msg_type_published = args[0]
             
        self.assertEqual(msg_type_published, "exec.approval_needed", 
                         "System executed trade instead of asking for approval!")
        
        print(f"PASS: Trade Blocked. Event '{msg_type_published}' sent.")

    @patch('execution.execution_gateway.ExecutionSecrets')
    @patch('execution.execution_gateway.event_bus')
    @patch('workers.common.database.SessionLocal')
    def test_approval_allows_trade(self, mock_db_cls, mock_event_bus, mock_secrets):
        """
        Verify that if is_approval_event=True, execution proceeds and count increments.
        """
        gateway = ExecutionGateway()
        gateway.db = MagicMock()
        mock_automation = MagicMock() 
        mock_automation.approved_trade_count = 5
        gateway.db.query.return_value.first.return_value = mock_automation
        
        signal = {"symbol": "BTCUSDT", "price": 50000}
        
        # Attempt Execution WITH Approval Flag
        gateway.execute_order(signal, is_approval_event=True)
        
        # Assertions
        # 1. Count should increment
        self.assertEqual(mock_automation.approved_trade_count, 6)
        
        # 2. 'exec.report' should be published (meaning fill happened)
        args, _ = mock_event_bus.publish.call_args
        self.assertEqual(args[0], "exec.report")
        
        print("PASS: Approved trade executed and count incremented.")

if __name__ == "__main__":
    unittest.main()
