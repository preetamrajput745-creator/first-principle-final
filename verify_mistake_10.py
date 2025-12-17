import sys
import os
import time
from datetime import datetime, timedelta

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workers.common.database import SessionLocal
from workers.common.models import Order, Signal, Automation
from safety.circuit_breaker import CircuitBreaker
from config import settings

def test_circuit_breaker():
    print("=== TESTING MISTAKE 10: CIRCUIT BREAKER ===")
    
    db = SessionLocal()
    breaker = CircuitBreaker(db)
    
    # 1. Reset State
    print("\n[1] Resetting DB State...")
    db.query(Order).delete()
    db.query(Signal).delete()
    db.query(Automation).delete()
    
    auto = Automation(name="Test Auto", slug="test-auto", status="active")
    db.add(auto)
    db.commit()
    
    assert breaker.check_limits() == True
    print("   -> System Healthy [OK]")
    
    # 2. Simulate Max Daily Loss Breach
    print(f"\n[2] Simulating Huge Loss (Limit: -${settings.MAX_DAILY_LOSS})...")
    
    # Create a dummy signal first to satisfy FK and UUID type
    import uuid
    dummy_signal = Signal(
        id=uuid.uuid4(),
        automation_id=auto.id,
        symbol="BTCUSDT",
        timestamp=datetime.utcnow(),
        score=0,
        payload={},
        raw_event_location="test",
        status="dummy"
    )
    db.add(dummy_signal)
    db.commit()

    # Insert a losing order exceeding limit
    bad_order = Order(
        signal_id=dummy_signal.id,
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0,
        simulated_slippage=0,
        realized_slippage=0,
        pnl= -1 * (settings.MAX_DAILY_LOSS + 100), # Breaches limit
        status="FILLED",
        is_paper=True,
        created_at=datetime.utcnow()
    )
    db.add(bad_order)
    db.commit()
    
    # Check Breaker
    is_safe = breaker.check_limits()
    print(f"   -> Breaker Check Result: {is_safe}")
    print(f"   -> Reason: {breaker.reason}")
    
    if not is_safe and "MAX DAILY LOSS" in breaker.reason:
        print("   -> LOSS BREAKER TRIPPED SUCCESSFULLY [OK]")
    else:
        print("   -> FAILED TO TRIP ON LOSS [FAIL]")
        sys.exit(1)
        
    # Verify Auto-Pause
    db.refresh(auto)
    print(f"   -> Automation Status: {auto.status}")
    if auto.status == "paused_risk":
        print("   -> AUTOMATION AUTO-PAUSED [OK]")
    else:
        print("   -> FAILED TO PAUSE AUTOMATION [FAIL]")
        sys.exit(1)

    # 3. Test Signal Rate (Reset first)
    print("\n[3] Testing Signal Rate Limit...")
    breaker.tripped = False # Manual Reset
    db.query(Order).delete() # Clear loss
    db.commit()
    
    # Spam signals
    limit = settings.MAX_SIGNALS_PER_HOUR
    print(f"   -> Inserting {limit + 5} signals (Limit: {limit})...")
    
    for i in range(limit + 5):
        sig = Signal(
            automation_id=auto.id,
            symbol="BTCUSDT",
            timestamp=datetime.utcnow(),
            score=50,
            payload={},
            raw_event_location="test",
            status="new"
        )
        db.add(sig)
    db.commit()
    
    # Check Breaker
    is_safe = breaker.check_limits()
    print(f"   -> Breaker Check Result: {is_safe}")
    print(f"   -> Reason: {breaker.reason}")
    
    if not is_safe and "MAX SIGNAL RATE" in breaker.reason:
        print("   -> RATE BREAKER TRIPPED SUCCESSFULLY [OK]")
    else:
        print("   -> FAILED TO TRIP ON RATE [FAIL]")
        sys.exit(1)

    print("\n=== ALL CIRCUIT BREAKER TESTS PASSED ===")

if __name__ == "__main__":
    test_circuit_breaker()
