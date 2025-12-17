"""
Ingest Service - Isolation Demo (Mistake #5)
Responsibility: Capture L1 ticks and persist to immutable storage.
Criticality: HIGH. Must never stop even if strategy crashes.
"""

import time
import sys
import os

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.ingestion.feed import L1FeedSimulator
from workers.common.raw_data_store import RawDataStore
from workers.common.time_normalizer import TimeNormalizer

from event_bus import event_bus

def run_ingest():
    print("[INGEST] Service Started. PID:", os.getpid())
    
    feed = L1FeedSimulator()
    raw_store = RawDataStore()
    
    tick_count = 0
    try:
        for tick in feed.stream():
            # 1. Normalize
            tick_dict = tick.to_dict()
            tick_dict = TimeNormalizer.normalize_tick(tick_dict)
            
            # 2. Persist (Critical Path)
            raw_store.append_tick(tick_dict)
            
            # 3. Publish to Downstream (Simulating Bar Building here for simplicity)
            # In a real system, we'd aggregated ticks. Here: 1 tick = 1 bar update.
            bar_payload = {
                "symbol": tick_dict['symbol'],
                "open": tick_dict['last'],
                "high": tick_dict['last'],
                "low": tick_dict['last'],
                "close": tick_dict['last'],
                "volume": tick_dict['volume'],
                "time": tick_dict['timestamp'],
                "clock_drift_ms": tick_dict.get('clock_drift_ms', 0.0), # Mistake #2 Propagation
                "source_clock": tick_dict.get('source_clock'),
                # Mistake #11: Pass L1 Snapshot Data
                "bid": tick_dict.get('bid'),
                "ask": tick_dict.get('ask')
            }
            
            # Using xadd for Redis Streams
            event_bus.publish(f"market.bar.1m.{tick_dict['symbol']}", bar_payload)
            
            tick_count += 1
            if tick_count % 10 == 0:
                print(f"[INGEST] Processed {tick_count} ticks. Last: {tick_dict['symbol']} (Drift: {tick_dict.get('clock_drift_ms')}ms)")
                
            # Simulate work
            time.sleep(0.1)
            
    except Exception as e:
        print(f"[INGEST] CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_ingest()
