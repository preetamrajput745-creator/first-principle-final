"""
Verification: Mistake #10 - Max Concurrent Orders
"""
import sys
import os
import uuid
from datetime import datetime

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from common.database import get_db
from common.models import Order
from risk.circuit_breaker import CircuitBreaker

def test_concurrent_limit():
    print("TEST: Circuit Breaker - Concurrent Order Limit")
    print("=" * 60)
    
    cb = CircuitBreaker()
    
    with next(get_db()) as db:
        # Clear existing open orders for test purity (or careful filter)
        # For safety in this dev env, assuming we can add test orders.
        
        # 1. Inject 5 Open Orders (Hit Limit)
        print("1. Injecting 5 Active Orders...")
        for i in range(5):
            o = Order(
                symbol="LIMIT_TEST",
                side="BUY",
                quantity=1,
                price=100.0,
                status="FILLED",
                exit_time=None # Open
            )
            db.add(o)
        db.commit()
        
        # 2. Check Breaker
        print("2. Checking Circuit Breaker...")
        allowed = cb.check_concurrent_orders(str(uuid.uuid4()))
        
        if not allowed:
            print("   SUCCESS: Circuit Breaker blocked new orders (Limit Hit).")
        else:
            print("   FAILURE: Circuit Breaker allowed orders despite limit!")
            return

        # 3. Close one order
        print("3. Closing one order...")
        last_order = db.query(Order).filter(Order.symbol == "LIMIT_TEST").first()
        last_order.exit_time = datetime.utcnow()
        db.commit()
        
        # 4. Check Breaker Again
        allowed = cb.check_concurrent_orders(str(uuid.uuid4()))
        if allowed:
             print("   SUCCESS: Circuit Breaker allowed order (4/5 open).")
        else:
             print("   FAILURE: Circuit Breaker blocked despite being under limit!")
             return
             
    print("=" * 60)
    print("VERIFICATION COMPLETE: Concurrent Order Limit Working.")

if __name__ == "__main__":
    test_concurrent_limit()
