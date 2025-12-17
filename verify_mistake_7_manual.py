
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

class TestCircuitBreakerInjection(unittest.TestCase):
    
    def test_loss_injection_pause(self):
        print("\nVERIFICATION: Mistake #7 - Circuit Breaker Loss Injection")
        print("="*60)
        
        db = SessionLocal()
        
        # 1. Setup Active Automation
        auto_id = uuid.uuid4() # Keep as object
        auto = Automation(id=auto_id, name="Loss Test", slug=f"loss-test-{str(auto_id)[:8]}", status="active")
        db.add(auto)
        db.commit()
        print(f"Created Active Automation: {auto.name} (Status: {auto.status})")
        
        try:
            # 2. Inject Massive Loss (-$1000) -> Max Daily Loss is $500
            print("Injecting simulated LOSS of -$1000...")
            loss_order = Order(
                id=uuid.uuid4(),
                symbol="TEST_LOSS",
                status="FILLED",
                side="BUY",
                quantity=10,
                price=100.0,
                pnl=-1000.0, # LOSS
                created_at=datetime.utcnow()
            )
            db.add(loss_order)
            db.commit()
            
            # 3. Check Circuit Breaker
            cb = CircuitBreaker()
            print("Checking Circuit Breaker PnL Health...")
            is_safe = cb.check_pnl_health(auto_pause=True)
            
            # 4. Verify Status
            db.refresh(auto)
            print(f"Automation Status after Check: {auto.status}")
            
            if not is_safe and auto.status == "paused_risk":
                print("SUCCESS: Automation PAUSED due to max daily loss.")
            else:
                print(f"FAILURE: Automation did NOT pause. is_safe={is_safe}, status={auto.status}")
                sys.exit(1)
                
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
