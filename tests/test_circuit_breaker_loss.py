
import unittest
import sys
import os
import uuid
import json
from datetime import datetime
from unittest.mock import MagicMock

# Path setup
workers_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workers")
sys.path.insert(0, workers_path)

from risk.circuit_breaker import CircuitBreaker
from common.database import get_db, SessionLocal
from common.models import Signal, Automation, Order

class TestCircuitBreaker(unittest.TestCase):
    """
    TRIPLE CHECK: Circuit Breaker Mistake #7 & #10
    Verifies:
    1. PnL Monitor (Max Daily Loss) -> Auto Pause
    2. Error Rate Monitor (>50% Rejections) -> Auto Pause (New)
    3. Trade Count/Signal Rate -> Auto Pause
    4. API Integration (Mocked)
    """
    
    def setUp(self):
        self.db = SessionLocal()
        # Clean specific test data ? Ideally we use a test DB. 
        # For this setup, we create unique automation IDs.
        self.auto_id = uuid.uuid4()
        self.auto = Automation(
             id=self.auto_id,
             name=f"CB Test {str(uuid.uuid4())[:8]}",
             slug=f"cb-test-{str(uuid.uuid4())[:8]}",
             status="active"
        )
        self.db.add(self.auto)
        self.db.commit()
        
        # Clean global orders to prevent PnL interference/leakage from other tests
        try:
             self.db.query(Order).delete()
             self.db.commit()
        except:
             self.db.rollback()
        
    def tearDown(self):
        self.db.close()
        
    def test_pnl_loss_circuit_breaker(self):
        print("\n[Test] Circuit Breaker: PnL Loss Protection")
        
        # Inject Orders with Massive Loss
        # Limit is 500. We inject -600.
        order = Order(
            id=uuid.uuid4(),
            # automation_id removed as it is not in Order model
            symbol="TEST_PNL",
            status="FILLED",
            side="BUY",
            quantity=1,
            price=100.0,
            pnl=-600.0, # Massive Loss
            created_at=datetime.utcnow()
        )
        self.db.add(order)
        self.db.commit()
        
        # Check Breaker
        cb = CircuitBreaker()
        is_safe = cb.check_pnl_health(auto_pause=True)
        
        self.assertFalse(is_safe, "PnL Check should fail for -600 loss.")
        
        # Verify Automation Paused
        self.db.refresh(self.auto)
        self.assertEqual(self.auto.status, "paused_risk", "Automation should be paused by PnL breaker.")
        print("PASS: PnL Loss correctly tripped breaker.")

    def test_error_rate_circuit_breaker(self):
        print("\n[Test] Circuit Breaker: Error Rate Protection")
        
        # Reset Automation status
        self.auto.status = "active"
        self.db.commit()
        
        # Inject 10 Orders: 6 Rejected (60% Error Rate > 50% Limit)
        for i in range(10):
            status = "REJECTED" if i < 6 else "FILLED"
            order = Order(
                id=uuid.uuid4(),
                # automation_id removed
                symbol="TEST_ERR",
                status=status,
                side="BUY",
                quantity=1,
                price=100.0,
                created_at=datetime.utcnow()
            )
            self.db.add(order)
        self.db.commit()
        
        # Check Breaker
        cb = CircuitBreaker()
        cb.min_orders_for_error_check = 5 # Ensure our 10 orders count
        
        is_safe = cb.check_error_rate(auto_pause=True)
        
        self.assertFalse(is_safe, "Error Rate Check should fail for 60% rejections.")
        
        # Verify Automation Paused
        self.db.refresh(self.auto)
        self.assertEqual(self.auto.status, "paused_risk", "Automation should be paused by Error Rate breaker.")
        print("PASS: Error Rate correctly tripped breaker.")

    def test_api_integration_mock(self):
        """
        Verify the API endpoint logic (logic only, not full HTTP request here to avoid starting server)
        """
        print("\n[Test] Circuit Breaker: API Manual Pause")
        
        # Reset Autmation
        self.auto.status = "active"
        self.db.commit()
        
        # Instantiate directly what the API calls
        cb = CircuitBreaker()
        cb.pause_all_active_automations("Manual API Trigger")
        
        self.db.refresh(self.auto)
        self.assertEqual(self.auto.status, "paused_risk")
        print("PASS: Manual API Trigger paused automations.")

    def test_signal_rate_circuit_breaker(self):
        print("\n[Test] Circuit Breaker: Signal Rate Protection")
        
        # Reset Automation
        self.auto.status = "active"
        self.db.commit()
        
        # Inject 11 Signals (Limit is 10/hr)
        for i in range(11):
            sig = Signal(
                id=uuid.uuid4(),
                automation_id=self.auto_id,
                symbol="TEST_RATE",
                timestamp=datetime.utcnow(),
                score=60.0,
                status="new",
                payload={}
            )
            self.db.add(sig)
        self.db.commit()
        
        # Check Breaker
        cb = CircuitBreaker()
        is_safe = cb.check_signal_rate(auto_pause=True)
        
        self.assertFalse(is_safe, "Signal Rate Check should fail for >10 signals/hr.")
        
        # Verify Pause
        self.db.refresh(self.auto)
        self.assertEqual(self.auto.status, "paused_risk")
        print("PASS: Signal Rate correctly tripped breaker.")


if __name__ == "__main__":
    unittest.main()
