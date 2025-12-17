import sys
import os
import time
import json
import uuid
from datetime import datetime

# Add workers to path
# Add Root to path
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_path)
sys.path.insert(0, os.path.join(root_path, "workers"))

from common.database import get_db, engine, Base
from common.models import Automation, Signal
from common.slippage import SlippageModel
from common.raw_data_store import RawDataStore
from common.time_normalizer import TimeNormalizer
from risk.circuit_breaker import CircuitBreaker # NEW
from ingestion.feed import L1FeedSimulator

# Initialize components
feed = L1FeedSimulator()
slippage_model = SlippageModel()
raw_store = RawDataStore()
circuit_breaker = CircuitBreaker() # NEW
from event_bus import event_bus # Import at top level

def start_heartbeat():
    def heartbeat_loop():
        while True:
            try:
                event_bus.publish("system.heartbeat", {
                    "service": "signal_engine",
                    "timestamp": datetime.utcnow().isoformat()
                })
                time.sleep(5)
            except Exception as e:
                print(f"Heartbeat failed: {e}")
                time.sleep(5)
    
    import threading
    t = threading.Thread(target=heartbeat_loop, daemon=True)
    t.start()
    print("Heartbeat thread started.")

def run_signal_engine():
    print("Starting Signal Engine with L1 Feed & Slippage Model...")
    
    # Get the automation ID
    with next(get_db()) as db:
        automation = db.query(Automation).filter(Automation.slug == "first-principle-strategy").first()
        if not automation:
            print("First Principle Strategy automation not found!")
            return
        automation_id = automation.id
        print(f"Linked to Automation: {automation.name}")
        
    # Start Heartbeat
    start_heartbeat()

    # Start processing ticks
    try:
        for tick in feed.stream():
            # MISTAKE #3 FIX: Normalize Time & Check Drift
            tick_dict = tick.to_dict()
            tick_dict = TimeNormalizer.normalize_tick(tick_dict)
            
            # MISTAKE #2 FIX: Store raw tick (append-only, immutable)
            raw_store.append_tick(tick_dict)
            
            # Simple Logic: Generate signal randomly for demo purposes (in real life, this is the strategy)
            # We use a probability to simulate rare signals
            import random
            if random.random() < 0.5: # 50% chance per tick update (High for demo/test)
                
                # MISTAKE #10 FIX: Check Circuit Breaker
                if not circuit_breaker.check_signal_rate():
                    # Trip breaker: Pause automation
                    circuit_breaker.trigger_pause(str(automation_id))
                    print("SIGNAL REJECTED: Circuit Breaker Tripped")
                    time.sleep(10) # Cooling off
                    continue

                signal_type = "BUY" if random.random() > 0.5 else "SELL"
                price = tick.ask if signal_type == "BUY" else tick.bid
                
                # 1. Low Liquidity Check (Mistake #1 Monitor)
                is_low_liquidity = tick.volume < 10 # Arbitrary low threshold for demo
                if is_low_liquidity:
                    print(f"WARNING: Signal candidate in LOW LIQUIDITY (Vol: {tick.volume})")
                    # In production, we might skip this signal or tag it
                
                # 2. Calculate Slippage (Mistake #4 & #1 Fix)
                slippage_result = slippage_model.calculate_slippage(
                    symbol=tick.symbol,
                    price=price,
                    quantity=100, # Demo qty
                    is_volatile=(tick.symbol == "BANKNIFTY" or is_low_liquidity) # Volatility increases in low liq
                )
                
                # 2. Create Signal Object
                with next(get_db()) as db:
                    signal = Signal(
                        automation_id=automation_id,
                        symbol=tick.symbol,
                        timestamp=tick.timestamp,
                        score=round(random.uniform(7.0, 9.9), 1),
                        status="new",
                        payload={
                            "type": signal_type,
                            "price": price,
                            "target": round(price * 1.01, 2),
                            "stop_loss": round(price * 0.99, 2),
                            "reason": "L1 Tick Breakout (Simulated)"
                        },
                        # 3. Store Risk & Execution Data (Mistake #1 & #11 Fix)
                        estimated_slippage=slippage_result["slippage_amount"],
                        execution_price=slippage_result["estimated_buy_price"] if signal_type == "BUY" else slippage_result["estimated_sell_price"],
                        l1_snapshot=tick_dict, # Storing the Normalized Tick context
                        clock_drift_ms=tick_dict.get("clock_drift_ms", 0.0)
                    )
                    db.add(signal)
                    db.commit()
                    
                    print(f"Signal Generated: {tick.symbol} {signal_type} @ {price}")
                    print(f"   Slippage: {slippage_result['slippage_amount']} | Exec Price: {signal.execution_price}")
                    print(f"   L1 Snapshot stored.")
                    
                    # Generate Simulated L2 Snapshot (Mistake #9)
                    # In real system, this is a file dump of the order book
                    snapshot_dir = os.path.join(root_path, "snapshots")
                    if not os.path.exists(snapshot_dir):
                        os.makedirs(snapshot_dir)
                    
                    snapshot_filename = f"{signal.symbol}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}.json"
                    snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
                    
                    try:
                        with open(snapshot_path, "w") as f:
                            json.dump(tick_dict, f)
                    except Exception as e:
                        print(f"Failed to write snapshot: {e}")
                        snapshot_path = None # Mark as missing
                    
                    # MISTAKE #9 FIX: Publish to Event Bus for Execution & Monitoring
                    from event_bus import event_bus
                    event_bus.publish("signal.new", {
                        "signal_id": str(signal.id),
                        "automation_id": str(automation_id),
                        "symbol": signal.symbol,
                        "action": signal_type,
                        "quantity": 100, # Demo qty
                        "price": signal.execution_price, # Limit price comes from strategy (using est execution price as limit for now)
                        "timestamp": signal.timestamp.isoformat() if signal.timestamp else datetime.utcnow().isoformat(),
                        "l2_snapshot_path": snapshot_path
                    })
                    
            time.sleep(0.5) # Slow down for demo visibility

    except KeyboardInterrupt:
        print("Signal Engine Stopped.")

if __name__ == "__main__":
    run_signal_engine()
