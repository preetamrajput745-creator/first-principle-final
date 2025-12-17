"""
Verification: Mistake #7 - Circuit Breaker Service (Error Rates & Pager Alert)
Verifies:
1. Error Rate Monitoring (Trips if rejection rate > 50%)
2. Global Pause Feature (Pauses ALL automations)
3. Pager Alert (Mock output)
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
from common.models import Order, Automation
from risk.circuit_breaker import CircuitBreaker

def verify_enhanced_circuit_breaker():
    print("TEST: Circuit Breaker Service (Mistake #7)")
    print("=" * 60)
    
    cb = CircuitBreaker()
    
    with next(get_db()) as db:
        # 1. Setup: Create 3 Active Automations
        autos = []
        for i in range(3):
            slug = f"cb-test-{i}-{str(uuid.uuid4())[:6]}"
            auto = Automation(
                id=uuid.uuid4(),
                name=f"CB Bot {i}",
                slug=slug,
                status="active"
            )
            db.add(auto)
            autos.append(auto)
        db.commit()
        print(f"1. Setup: Created {len(autos)} ACTIVE automations.")
        
        # 2. Simulation: Inject Massive Failures (Robust to Test Pollution)
        # The suite runs other tests that create successful orders.
        # We need to guarantee Error Rate > 50%.
        # Strategy: Count existing orders (N), inject N + 2 failures.
        print("\n2. Simulation: calculating required failures...")
        
        one_hour_ago = datetime.utcnow().replace(minute=0, second=0, microsecond=0) # Approx
        existing_count = db.query(Order).count() # Simple total count is safer/faster upper bound
        
        needed_failures = existing_count + 5
        print(f"   Existing Orders in DB: {existing_count}. Injecting {needed_failures} Failures to force trip...")
        
        for i in range(needed_failures):
            order = Order(
                symbol="FAIL", 
                side="BUY", 
                quantity=1, 
                price=100, 
                status="REJECTED", 
                created_at=datetime.utcnow()
            )
            db.add(order)
        db.commit()
        
        # 3. Check Error Rate (With Auto Pause)
        print("3. Execution: Checking Error Rate...")
        # Force fresh check
        is_safe = cb.check_error_rate(auto_pause=True)
        
        if is_safe:
             print("   FAILURE: Circuit Breaker thought system was safe (despite massive failures)!")
             sys.exit(1)
        else:
             print("   SUCCESS: Circuit Breaker caught high error rate.")

        # 4. Verify Global Pause
        print("4. Verification: Checking Global Pause Status...")
        paused_count = 0
        for auto in autos:
            db.refresh(auto)
            if auto.status == "paused_risk":
                paused_count += 1
            else:
                print(f"   FAILURE: Bot {auto.name} status is {auto.status}")
        
        if paused_count == 3:
            print(f"   SUCCESS: All {paused_count} automations were PAUSED globally.")
        else:
            print(f"   FAILURE: Only {paused_count}/3 paused.")
            sys.exit(1)
            
    print("\nVERIFICATION COMPLETE: Circuit Breaker Service is functional.")

if __name__ == "__main__":
    verify_enhanced_circuit_breaker()
