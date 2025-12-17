
import unittest
import sys
import os
import uuid
from datetime import datetime

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.common.database import get_db, SessionLocal
from workers.common.models import Order
from workers.risk.circuit_breaker import CircuitBreaker

class TestSlippagePause(unittest.TestCase):
    """
    Verification of Task 10: Slippage Auto-Pause.
    If slippage_delta > 50% for 10 consecutive trades -> PAUSE.
    """
    
    def setUp(self):
        self.db = SessionLocal()
        self.cb = CircuitBreaker()
        
    def tearDown(self):
        self.db.close()
        
    def test_slippage_auto_pause(self):
        print("\n[TEST 10] Slippage Auto-Pause Chain...")
        
        # 1. Clean up recent orders to ensure fresh state (or work with new ID)
        # We can't delete easily, so let's rely on limit(10) taking the LATEST.
        # We will inject 10 BAD trades.
        
        # Inject 10 trades with 60% slippage
        # Price 100, Realized Slippage 60
        # consecutive > 10
        
        print("   Injecting 10 High Slippage Orders...")
        for _ in range(10):
            ord = Order(
                signal_id=uuid.uuid4(), # Pass UUID object
                symbol="SLIP_TEST",
                side="BUY",
                quantity=1,
                price=100.0,
                status="FILLED",
                simulated_slippage=1.0,
                realized_slippage=60.0, # 60% of 100
                is_paper=True,
                created_at=datetime.utcnow()
            )
            self.db.add(ord)
        self.db.commit()
        
        # 2. Run Check
        print("   Running Circuit Breaker Check...")
        
        # We mock pause_all to verify it trigger
        original_pause = self.cb.pause_all_active_automations
        self.cb.pause_all_active_automations = self._mock_pause
        self.pause_called = False
        
        try:
            is_healthy = self.cb.check_slippage_health(auto_pause=True)
            
            self.assertFalse(is_healthy, "Circuit Breaker should report UNHEALTHY")
            self.assertTrue(self.pause_called, "Circuit Breaker did not trigger PAUSE")
            print("   PASS: Auto-Pause Triggered by Slippage.")
            
        finally:
            self.cb.pause_all_active_automations = original_pause
            
    def _mock_pause(self, reason):
        print(f"   [MOCK PAUSE] {reason}")
        self.pause_called = True

if __name__ == "__main__":
    unittest.main()
