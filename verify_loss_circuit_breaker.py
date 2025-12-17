"""
Verification: Mistake #7 & #10 - Circuit Breaker Loss Protection
Verifies:
1. Injection of simulated losses (Orders with negative PnL).
2. Detection of daily loss limit breach.
3. Auto-pause of active automations.
4. Sending of alerts (Captured via stdout).
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

def verify_loss_breaker():
    print("TEST: Circuit Breaker Loss Protection (Acceptance Criteria)")
    print("=" * 60)
    
    cb = CircuitBreaker()
    max_loss = cb.max_daily_loss # Should be 500.0
    print(f"1. Configuration: Max Daily Loss Limit = ${max_loss}")
    
    with next(get_db()) as db:
        # 1. Setup: Create 'Active' Automation
        # We need a unique slug to avoid collisions with other tests
        test_slug = f"loss-test-{str(uuid.uuid4())[:8]}"
        auto = Automation(
            name="Loss Test Bot", 
            slug=test_slug, 
            status="active"
        )
        db.add(auto)
        db.commit()
        
        auto_id = auto.id
        print(f"2. Setup: Created active automation '{test_slug}'. Status: {auto.status}")
        
        # 2. Inject Losses
        # We need to inject enough loss to exceed 500.0
        # Creating a single large loss order for today
        print("3. Simulation: Injecting $600 simulated loss...")
        
        loss_order = Order(
            signal_id=None,
            symbol="TEST_LOSS",
            side="BUY",
            quantity=1,
            price=1000.0,
            status="FILLED",
            pnl=-600.0, # Exceeds 500
            is_paper=True,
            created_at=datetime.utcnow()
        )
        db.add(loss_order)
        db.commit()
        
        # 3. Trigger Breaker
        # Capture stdout to verify pager alert
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
             # Force check with auto-pause enabled
             is_safe = cb.check_pnl_health(auto_pause=True)
             
        output = f.getvalue()
        print(f"   [Circuit Breaker Output]:\n   {output.strip().replace(chr(10), chr(10)+'   ')}")
        
        # 4. Verification
        if is_safe:
            print("   FAILURE: Circuit Breaker reported SAFE status despite $600 loss!")
            sys.exit(1)
        else:
            print("   SUCCESS: Circuit Breaker reported UNSAFE status.")
            
        # Check Alert
        expected_msg = "PAGERDUTY_ALERT: GLOBAL CIRCUIT BREAKER TRIPPED"
        if expected_msg in output:
             print("   SUCCESS: Pager alert sent.")
        else:
             print(f"   FAILURE: Pager alert NOT found in output. Expected '{expected_msg}'")
             sys.exit(1)

        # Check Auto-Pause
        db.refresh(auto)
        if auto.status == "paused_risk":
             print(f"   SUCCESS: Automation status changed to '{auto.status}'.")
        else:
             print(f"   FAILURE: Automation status is '{auto.status}', expected 'paused_risk'.")
             sys.exit(1)

    print("=" * 60)
    print("VERIFICATION COMPLETE: Loss Protection Logic Verified.")

if __name__ == "__main__":
    verify_loss_breaker()
