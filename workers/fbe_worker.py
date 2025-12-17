import redis
import json
import time
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from workers.common.database import SessionLocal
from workers.common.models import Signal
from infra.storage import storage
from workers.fbe.logic import FBEDetector

class FBEWorker:
    """
    Consumes market.bar.1m.<symbol>.
    Computes Features.
    Calculates Score.
    Persists Signal if triggered.
    """
    def __init__(self):
        self.r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
        self.detector = FBEDetector() # The core logic lib we already have
        self.db = SessionLocal()

    def process_stream(self):
        print("[FBE_WORKER] Listening for closed 1m bars...")
        while True:
            for symbol in settings.SYMBOLS:
                stream_key = f"market.bar.1m.{symbol}"
                # Last ID '$' means only new. 
                # For demo dev, we might miss messages if we restart. 
                # XREADGROUP is better but XREAD for simplicity.
                messages = self.r.xread({stream_key: '$'}, count=5, block=100)
                
                for stream, msgs in messages:
                    for message_id, data in msgs:
                        bar_json = data.get(b'data').decode('utf-8')
                        self.process_bar(symbol, json.loads(bar_json))
            time.sleep(0.1)

    def process_bar(self, symbol, bar_data):
        # 1. Compute Features
        # FBEDetector normally takes raw ticks or updates its state.
        # We'll adapt it to take the closed bar.
        # logic.py needs 'process_tick' but actually it aggregates bars internally.
        # We will assume process_tick handles the state update if we pass close price.
        
        # Adaptation: FBEDetector expects tick. We feed the CLOSE of the bar as a 'tick'.
        ts = bar_data.get('start_time', datetime.utcnow().isoformat())
        price = bar_data.get('close')
        
        # 2. Logic & Scoring
        # Ideally FBEDetector would expose a 'process_bar' method.
        # Check existing logic.py ... yes it uses process_tick.
        # We will feed it the OHLC logic if possible, or just the close price tick.
        
        payload = self.detector.process_tick(symbol, price, ts)
        
        if payload:
            print(f"[FBE_WORKER] 🔥 SIGNAL TRIGGERED: {symbol} Score: {payload.get('score')}")
            self.create_signal(symbol, bar_data, payload)
        else:
            # print(f"[FBE_WORKER] Processed bar {symbol}, no signal.")
            pass
            
            # Persist Feature Snapshot to S3 (Requirement 4)
            # Even if no signal, we might want to save features for training.
            # Extract features from detector state if possible.
            # For now, we only save snapshot if signal fires (as per payload).
            
    def create_signal(self, symbol, bar_data, payload):
        # 3. Save Feature Snapshot to S3 (Feature Engine -> Storage)
        ts_obj = datetime.fromisoformat(str(bar_data.get('start_time')).replace('Z', ''))
        snapshot_path = storage.save_feature_snapshot(symbol, ts_obj, {
            "bar": bar_data,
            "features": payload
        })
        
        # 4. Create Signal Record (Scoring -> Signal Publisher)
        new_signal = Signal(
            automation_id=uuid.uuid4(), # Default/None
            symbol=symbol,
            timestamp=ts_obj,
            score=payload.get('score', 0),
            payload=payload,
            raw_event_location=snapshot_path, # S3 Path
            status="new",
            clock_drift_ms=0.0 # Calc if needed
        )
        
        self.db.add(new_signal)
        self.db.commit()
        
        # 5. Publish Event (Signal -> Execution)
        # Event: signal.false_breakout
        sig_event = {
            "signal_id": str(new_signal.id),
            "symbol": symbol,
            "score": new_signal.score,
            "path": snapshot_path
        }
        self.r.xadd("signal.false_breakout", {"data": json.dumps(sig_event)})
        print(f"[FBE_WORKER] Published Signal Event -> Redis")

if __name__ == "__main__":
    worker = FBEWorker()
    try:
        worker.process_stream()
    except KeyboardInterrupt:
        print("Stopping FBE Worker")
