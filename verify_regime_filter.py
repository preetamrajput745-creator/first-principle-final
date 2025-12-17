"""
Verification: Mistake #12 - Regime Filter Test (Manual Verification Step)

Test Requirement:
"Tag signals with regime metadata; apply a filter to pause automation in high-volatility regime and verify it pauses."

Steps:
1. Setup: Create an Active automation.
2. Signal Generation: Create a signal tagged with `regime_volatility="high_volatility"`.
3. Execution: Run `CircuitBreaker.check_market_regime(auto_pause=True)`.
4. Verification:
   - Check if the check returns False (Unsafe).
   - Check if the Automation status changed to 'paused_risk'.
   - Check for appropriate logging.
"""

import sys
import os
import io
import uuid
from datetime import datetime
from contextlib import redirect_stdout

# Path setup
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db
from common.models import Signal, Automation
from risk.circuit_breaker import CircuitBreaker

def verify_regime_filtering():
    print("TEST: Regime Filter & Auto-Pause (Mistake #12 Requirement)")
    print("=" * 60)
    
    with next(get_db()) as db:
        # 1. Setup Automation
        slug = f"regime-test-{str(uuid.uuid4())[:8]}"
        auto = Automation(name="Regime Tester", slug=slug, status="active")
        db.add(auto)
        db.commit()
        db.refresh(auto)
        print(f"1. Setup: Created Active Automation '{slug}'")
        
        # 2. Inject 'High Volatility' Signal
        # This simulates the Strategy or Market Classifier tagging the environment
        print("2. Simulation: Injecting Signal with 'high_volatility' regime...")
        sig = Signal(
            automation_id=auto.id,
            symbol="VOL_TEST",
            timestamp=datetime.utcnow(),
            score=0.9,
            payload={"action": "BUY"},
            clock_drift_ms=1.0,
            regime_volatility="high_volatility" # <--- The Trigger
        )
        db.add(sig)
        db.commit()
        
        # 3. Trigger Circuit Breaker Regime Check
        print("3. Execution: Checking Market Regime...")
        cb = CircuitBreaker()
        
        f = io.StringIO()
        with redirect_stdout(f):
             # auto_pause=True means it should ACT on the finding
             is_safe = cb.check_market_regime(auto_pause=True)
             
        output = f.getvalue()
        
        # 4. Verification
        print("\n   [LOG CAPTURE]:")
        for line in output.split('\n'):
            if line.strip(): print(f"   > {line}")
            
        # Check 1: Return Value
        if not is_safe:
            print("\n   [CHECK 1] Check Result: UNSAFE (Correct)")
        else:
            print("\n   [CHECK 1] Check Result: SAFE (FAILURE - Should be UNSAFE due to high volatility)")
            sys.exit(1)
            
        # Check 2: Automation Paused
        db.refresh(auto)
        if auto.status == "paused_risk":
            print(f"   [CHECK 2] Automation Paused: {auto.status} (Correct)")
        else:
             print(f"   [CHECK 2] Automation Status: {auto.status} (FAILURE - Should be 'paused_risk')")
             sys.exit(1)
             
        # Check 3: Log Message
        if "High Volatility Regime Detected" in output:
             print("   [CHECK 3] Detection Logged (Correct)")
        else:
             print("   [CHECK 3] Detection Log Missing (FAILURE)")
             sys.exit(1)

    print("\nVERIFICATION COMPLETE: Regime Filter pauses automation correctly.")

if __name__ == "__main__":
    verify_regime_filtering()
