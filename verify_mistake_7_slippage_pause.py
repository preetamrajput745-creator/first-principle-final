
import unittest
import sys
import os
import uuid
from datetime import datetime
from unittest.mock import MagicMock

# Path setup
sys.path.append(os.path.join(os.getcwd(), 'workers'))

from risk.circuit_breaker import CircuitBreaker
from common.database import get_db, SessionLocal
from common.models import Order, Automation

class TestSlippagePause(unittest.TestCase):
    
    def test_consecutive_slippage_pause(self):
        print("\nVERIFICATION: Mistake #7 - High Consecutive Slippage Pause")
        print("="*60)
        
        db = SessionLocal()
        
        # 1. Setup Active Automation
        auto_id = uuid.uuid4()
        auto = Automation(id=auto_id, name="Slippage Test", slug=f"slip-test-{str(auto_id)[:8]}", status="active")
        db.add(auto)
        db.commit()
        print(f"Created Active Automation: {auto.name}")
        
        try:
            # 2. Inject 10 Orders with > 50% Slippage
            print("Injecting 10 BAD Trades (Slippage > 50%)...")
            for i in range(10):
                bad_order = Order(
                    id=uuid.uuid4(),
                    symbol="TEST_SLIP",
                    status="FILLED",
                    side="BUY",
                    quantity=1,
                    price=100.0,
                    realized_slippage=60.0, # 60% of 100 is > 50%
                    pnl=0,
                    created_at=datetime.utcnow()
                )
                db.add(bad_order)
            db.commit()
            
            # 3. Check Circuit Breaker
            cb = CircuitBreaker()
            print("Checking Circuit Breaker Slippage Health...")
            is_safe = cb.check_slippage_health(auto_pause=True)
            
            # 4. Verify Status
            db.refresh(auto)
            print(f"Automation Status after Check: {auto.status}")
            
            if not is_safe and auto.status == "paused_risk":
                print("SUCCESS: Automation PAUSED due to consecutive high slippage.")
            else:
                print(f"FAILURE: Automation did NOT pause. is_safe={is_safe}, status={auto.status}")
                sys.exit(1)
                
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
