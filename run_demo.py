import time
import random
import json
import sys
import os
from datetime import datetime, timezone

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from workers.common.database import SessionLocal, engine, Base
from workers.common.models import Signal, Order, Automation
from workers.fbe.logic import FBEDetector
from infra.time_normalizer import clock # Time Control
import uuid

# Create Tables if not exist (using production schema)
Base.metadata.create_all(bind=engine)

# --- Mock Components ---

class DemoMarket:
    def __init__(self, symbols):
        self.symbols = symbols
        self.prices = {s: 1000.0 for s in symbols}
    
    def next_tick(self):
        for s in self.symbols:
            change = random.uniform(-0.5, 0.5)
            self.prices[s] = round(self.prices[s] + change, 2)
            yield {
                "symbol": s,
                "price": self.prices[s],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

class DemoExecutor:
    def __init__(self, db):
        self.db = db
        from workers.common.slippage import SlippageModel
        self.slippage_model = SlippageModel()
        
    def execute(self, signal_entry):
        from workers.execution.execution_service import ExecutionService
        
        print(f"EXECUTING: {signal_entry.symbol} SIGNAL @ {signal_entry.payload.get('price', 0)}")
        
        # Initialize Real Service
        exec_svc = ExecutionService()
        
        # Prepare Secure Request
        order_request = {
            "automation_id": str(signal_entry.automation_id),
            "symbol": signal_entry.symbol,
            "action": "SELL", # Demo is FBE Bearish
            "quantity": 1,
            "price": signal_entry.payload.get('price', 1000.0)
        }
        
        # 1. ATTEMPT EXECUTION via Secure Service
        # This will enforce Mistake #7 (Gating) and Mistake #6 (Isolation)
        result = exec_svc.execute_order(order_request, "INTERNAL_SECURE_TOKEN_XYZ")
        
        status = result["status"]
        print(f"   >>> EXECUTION SERVICE RESPONSE: {status} ({result.get('reason', '')})")
        
        # Calculate Simulated Slippage using Profile (Mistake #3)
        slip_data = self.slippage_model.calculate_slippage(
            symbol=signal_entry.symbol,
            price=order_request['price'],
            quantity=1
        )
        simulated_slip_amount = slip_data['estimated_sell_price'] - order_request['price'] if order_request['action'] == "SELL" else order_request['price'] - slip_data['estimated_buy_price']
        # Actually field expects PCT or Amount?
        # Monitor logic: delta calculation uses absolute difference? 
        # "delta_pct = ((realized - expected) / expected) * 100"
        # If order.simulated_slippage stores the AMOUNT (e.g. 5.0), then realized should also be AMOUNT.
        # Let's check monitor.py logic again.
        # Monitor checks `realized_slippage` and `simulated_slippage`.
        # Backtest engine log implies absolute values.
        # Let's store ABSOLUTE amount of slippage expected.
        expected_slip_abs = abs(slip_data['slippage_amount'])
        
        # 2. Record Order in DB based on REAL outcome
        order = Order(
            # id auto-generated
            signal_id=signal_entry.id,
            symbol=signal_entry.symbol,
            side="SELL",
            quantity=1,
            price=signal_entry.payload.get('price', 1000.0),
            simulated_slippage=expected_slip_abs,
            realized_slippage=0.0, 
            status=status, # FILLED or REJECTED
            is_paper=True
        )
        
        # Only apply slippage etc if FILLED
        if status == "FILLED":
            # --- MISTAKE 4: SLIPPAGE MODEL ---
            import random
            # Real world is messier than model
            actual_slip_factor = random.uniform(0.5, 2.5) 
            realized_slip = expected_slip_abs * actual_slip_factor
            
            order.realized_slippage = realized_slip
            
            # Apply cost
            order.price = order.price - realized_slip # SELL
                
            # MONITOR: Check Delta
            if realized_slip > (expected_slip_abs * 1.5):
                print(f"[WARN] HIGH SLIPPAGE DETECTED! Realized: {realized_slip:.5f} > 1.5x Expected")
                order.status = "FILLED_HIGH_SLIP"
        
        self.db.add(order)
        
        # Update signal
        signal_entry.status = "executed" if "FILLED" in status else "rejected"
        if status == "FILLED":
            signal_entry.realized_slippage = order.realized_slippage
            signal_entry.latency_ms = 100.0 + random.uniform(0, 50)
            
        self.db.commit()

from safety.circuit_breaker import CircuitBreaker

# --- Main Runner ---

def main():
    print("Starting Local Demo Mode (Unified Architecture)...")
    
    db = SessionLocal()
    
    # Init Circuit Breaker
    breaker = CircuitBreaker(db)
    
    # Ensure default automation
    auto = db.query(Automation).filter(Automation.slug == "fbe-default").first()
    if not auto:
        auto = Automation(name="False Breakout Default", slug="fbe-default", status="active", description="Default FBE Automation")
        db.add(auto)
        db.commit()
        db.refresh(auto)
    
    # 2. Setup Components
    market = DemoMarket(settings.SYMBOLS)
    detector = FBEDetector()
    executor = DemoExecutor(db)
    
    print(f"Running simulation for: {settings.SYMBOLS}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            # --- CHECK CIRCUIT BREAKER ---
            if not breaker.check_limits():
                print(f"[BLOCKED] System Paused: {breaker.reason}")
                time.sleep(5) # Wait before checking again (or exit)
                continue
                
            for tick in market.next_tick():
                symbol = tick['symbol']
                price = tick['price']
                ts = tick['timestamp']
                
                # Check Automation Status
                db.expire(auto) # Refresh instance
                if auto.status != "active":
                    continue # Skip if paused

                # Normalize Time Controls (Mistake #3)
                processed_time = clock.get_current_utc()
                event_time = clock.normalize_timestamp(ts)
                
                # Causal Check: If processed_time < event_time, we have a time travel bug (or major clock skew)
                if processed_time < event_time:
                     print(f"[WARN] Future timestamp detected! Diff: {(event_time - processed_time).total_seconds()}s")

                
                # Check Automation Status
                db.expire(auto) # Refresh instance
                if auto.status != "active":
                    continue # Skip if paused

                # Process Strategy
                signal_payload = detector.process_tick(symbol, price, ts)
                
                if signal_payload:
                    print(f"SIGNAL: {signal_payload}")
                    
                    # Construct Payload for Dashboard (Mocking features)
                    full_payload = {
                        "price": price,
                        "type": "BEARISH_FBE",
                        "wick_ratio": 0.8, # Mocked high quality
                        "vol_ratio": 2.5,
                        "score": 85
                    }
                    
                    # Save Signal
                    # Latency Calculation (Mistake #3 Metric)
                    latency = (clock.get_current_utc() - event_time).total_seconds() * 1000

                    sig_entry = Signal(
                        # id auto-generated
                        automation_id=auto.id,
                        symbol=symbol,
                        timestamp=event_time, # Use normalized event time
                        score=85.0, # Mocked
                        payload=full_payload,
                        raw_event_location="demo_stream",
                        status="new",
                        clock_drift_ms=latency # Storing processing latency as proxy for drift/lag
                    )
                    db.add(sig_entry)
                    db.commit()
                    db.refresh(sig_entry) # Get ID
                    
                    # Execute
                    executor.execute(sig_entry)
                    
            time.sleep(1) # Slow down for demo visibility
            
    except KeyboardInterrupt:
        print("Stopping demo...")
    finally:
        db.close()

if __name__ == "__main__":
    main()
