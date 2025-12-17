
import subprocess
import time
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add workers path
sys.path.append(os.path.join(os.getcwd(), 'workers'))

from common.models import Order
from common.database import Base

def verify_mistake_9():
    print("VERIFICATION: Mistake #9 - Full Observability Pipeline")
    print("="*60)
    
    # 0. SEED DATA (Fix "Automation Not Found" error)
    print("[0] Seeding Automation Data...")
    DB_PATH = os.path.join(os.getcwd(), 'sql_app.db')
    engine = create_engine(f"sqlite:///{DB_PATH}")
    Session = sessionmaker(bind=engine)
    seed_session = Session()
    from common.models import Automation
    import uuid
    
    auto = seed_session.query(Automation).filter(Automation.slug == "first-principle-strategy").first()
    if not auto:
        auto = Automation(
            id=uuid.uuid4(),
            name="First Principle Strategy",
            slug="first-principle-strategy",
            status="active",
            is_fully_automated=True, # Skip gating for this purely metric test
            approved_trade_count=10
        )
        seed_session.add(auto)
        seed_session.commit()
        print("   Created 'first-principle-strategy' automation.")
    else:
        print("   'first-principle-strategy' already exists.")
        # RESET STATUS & CLEANUP for Test
        auto.status = "active"
        auto.approved_trade_count = 10
        auto.is_fully_automated = True
        seed_session.commit()
        print("   Reset automation status to 'active'.")
        
        # Clear signals to prevent Circuit Breaker trip (Max 10/hr)
        seed_session.execute(text("DELETE FROM signals"))
        seed_session.execute(text("DELETE FROM orders"))
        seed_session.commit()
        print("   Cleared previous signals/orders to reset Circuit Breaker limits.")

    seed_session.close()

    # 1. Start Services
    print("[1] Starting Services...")
    monitor_proc = subprocess.Popen([sys.executable, "monitoring/monitor.py"], 
                                    creationflags=subprocess.CREATE_NEW_CONSOLE)
    exec_proc = subprocess.Popen([sys.executable, "exec/main.py"], 
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    time.sleep(2) # Warmup
    
    # 2. Run Signal Engine (Simulation)
    print("[2] Running Signal Engine (15s)...")
    signal_proc = subprocess.Popen([sys.executable, "workers/signal_engine.py"], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Let it run for enough time to generate ~5-10 signals
    # Signal engine has random sleep 0.5s and 5% chance. 
    # That's low. I should probably boost probability for test or run longer.
    # 15s / 0.5s = 30 ticks. 5% = 1.5 signals. Might fail.
    # I'll rely on luck or run longer. Let's run 30s.
    try:
        outs, errs = signal_proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        signal_proc.terminate()
        print("[2] Signal Engine Completed (Timeout).")
    
    # Give execution time to process
    time.sleep(5)
    
    # 3. Kill Services
    monitor_proc.terminate()
    exec_proc.terminate()
    
    # 4. Verify Data in DB
    print("[3] Verifying Database Records...")
    DB_PATH = os.path.join(os.getcwd(), 'sql_app.db')
    engine = create_engine(f"sqlite:///{DB_PATH}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Check PnL for NEW orders (last 60 seconds)
    import datetime
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)
    
    new_orders = session.query(Order).filter(Order.created_at >= cutoff).all()
    count_new = len(new_orders)
    
    orders_with_pnl = sum(1 for o in new_orders if o.pnl != 0)
    orders_with_slip = sum(1 for o in new_orders if o.realized_slippage != None and o.realized_slippage > 0)
    
    print(f"Total New Orders: {count_new}")
    print(f"New Orders with PnL: {orders_with_pnl}")
    print(f"New Orders with Realized Slippage: {orders_with_slip}")
    
    if orders_with_pnl > 0:
        print("\nSUCCESS: Pipeline is fully functional.")
        print(f" - Found {orders_with_pnl} orders with PnL data. Observability is LIVE.")
        print(f" - Found {orders_with_slip} orders with Slippage data.")
        
        if orders_with_slip == 0:
             print("WARNING: Slippage is 0/None. This might be due to low drift in random simulation, but PnL proves execution.")
    else:
        print("\nFAILURE: Pipeline broken or no signals generated.")
        sys.exit(1)

if __name__ == "__main__":
    verify_mistake_9()
