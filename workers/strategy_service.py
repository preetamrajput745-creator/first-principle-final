"""
Strategy Service - Isolation Demo (Mistake #5)
Responsibility: Consume market data, run logic, emit signals.
Failure Impact: Processing stops, but Raw Data is safe (handled by Ingest).
"""

import time
import sys
import os
import random

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.ingestion.feed import L1FeedSimulator
from workers.common.slippage import SlippageModel
from workers.risk.circuit_breaker import CircuitBreaker
from workers.common.database import get_db
from workers.common.models import Signal, Automation
from workers.common.time_normalizer import TimeNormalizer
from workers.ingestion.l2_recorder import L2Recorder

def run_strategy():
    print("[STRATEGY] Service Started. PID:", os.getpid())
    
    feed = L1FeedSimulator()
    slippage_model = SlippageModel()
    circuit_breaker = CircuitBreaker()
    l2_recorder = L2Recorder()
    
    # Simulate finding an active automation
...
                # L2 Snapshot (Mistake #11)
                l2_data = l2_recorder.generate_simulated_l2(price)
                import uuid
                temp_sig_id = uuid.uuid4()
                l2_path = l2_recorder.store_snapshot(l2_data, str(temp_sig_id))

                # Calculate Drift
                drift = TimeNormalizer.calculate_drift_ms(tick.source_clock)

                # Mistake #12: Regime Classification
                # For demo, we use the feed's known volatility config
                # Low = < 2.0, Normal = 2.0-10.0, High = > 10.0
                known_vol = feed.volatility.get(tick.symbol, 5.0)
                if known_vol < 2.0:
                    regime_vol = "low"
                elif known_vol > 10.0:
                    regime_vol = "high"
                else:
                    regime_vol = "normal"
                    
                regime_session = "mid" # Default for now

                # DB Write
                with next(get_db()) as db:
                    # In a monolith, if this DB write fails or hangs, INGEST stops.
                    # In microservices, INGEST is unaware and keeps running.
                    sig = Signal(
                        id=temp_sig_id,
                        automation_id=None, # Orphan for demo
                        symbol=tick.symbol,
                        status="new",
                        timestamp=TimeNormalizer.now_utc(),
                        payload={"price": price, "type": signal_type},
                        estimated_slippage=slippage['slippage_amount'],
                        execution_price=slippage['estimated_buy_price'] if signal_type=="BUY" else slippage['estimated_sell_price'],
                        l2_snapshot_path=l2_path,
                        l1_snapshot=l2_data, # Keeping legacy
                        clock_drift_ms=round(drift, 3),
                        regime_volatility=regime_vol,
                        regime_session=regime_session
                    )
                    db.add(sig)
                    db.commit()
                    print(f"[STRATEGY] Generated Signal: {tick.symbol} {signal_type} | Drift: {drift:.2f}ms")
            
            time.sleep(0.1)

    except Exception as e:
        print(f"[STRATEGY] CRASHED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_strategy()
