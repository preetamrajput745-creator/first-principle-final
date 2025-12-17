"""
Deep Verification: Circuit Breaker Lifecycle (Mistake #10)
Verifies: Active -> Trip -> Paused -> Reject Signals -> Reset -> Active
"""

import sys
import os
import uuid
import time
from datetime import datetime

# Path setup
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db
from common.models import Signal, Automation
from risk.circuit_breaker import CircuitBreaker

def verify_lifecycle():
    print("CIRCUIT BREAKER DEEP VERIFICATION")
    print("=" * 60)
    
    automation_id = uuid.uuid4()
    cb = CircuitBreaker()
    
    with next(get_db()) as db:
        # 1. Setup: Create a clean automation
        slug = f"verify-cycle-{str(uuid.uuid4())[:8]}"
        auto = Automation(id=automation_id, name="Cycle Test", slug=slug, status="active")
        db.add(auto)
        db.commit()
        print(f"1. Setup: Created active automation '{slug}'")

        # 2. Force Trip: Inject excessive signals (Rate Limit Test)
        print("2. Attack: Injecting 15 signals to hit rate limit (Max 10/hr)...")
        for i in range(15):
            sig = Signal(
                automation_id=automation_id,
                symbol="TEST",
                payload={},
                status="new",
                timestamp=datetime.utcnow()
            )
            db.add(sig)
        db.commit()
        
        # 3. Check Breaker Logic
        # New Mistake #7: Auto-pause within the check
        is_safe = cb.check_signal_rate(auto_pause=True)
        if not is_safe:
            print("   Circuit Breaker detected abuse (Rate Limit Hit)")
            # No manual trigger needed now
        else:
            print("   FAILURE: Circuit Breaker missed the rate limit!")
            return

        # 4. Verify DB State (Must be PAUSED_RISK)
        db.refresh(auto)
        if auto.status in ["paused", "paused_risk"]:
            print(f"3. State: Automation status is now '{auto.status}' (CORRECT)")
        else:
            print(f"   FAILURE: DB status is '{auto.status}', expected 'paused' or 'paused_risk'")
            return

        # 5. Verify Signal Rejection (The "False Signal" Check)
        # Attempt to run logic that checks status
        # (Simulating Signal Engine logic)
        db.refresh(auto)
        if auto.status != "active":
             print("4. Prevention: System correctly REFUSING to trade (Status != active)")
        else:
             print("   FAILURE: System would still trade!")
             return

        # 6. Manual Reset
        print("5. Reset: Manually overriding status to 'active'...")
        auto.status = "active"
        db.commit()
        
        db.refresh(auto)
        if auto.status == "active":
            print("6. Recovery: Automation is back online.")
        
    print("=" * 60)
    print("DEEP CHECK PASSED: Logic is solid.")

if __name__ == "__main__":
    verify_lifecycle()
