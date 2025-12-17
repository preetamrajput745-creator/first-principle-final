from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime, timezone
import uvicorn
import json
import sys
import os
# Add root directory to path to allow imports from config, storage, etc.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings
from storage import storage_client
from event_bus import event_bus

app = FastAPI(title="Ingest Service")

class TradingViewAlert(BaseModel):
    symbol: str
    price: float
    volume: float
    timestamp: str # ISO string or unix timestamp from TV
    source: str = "tradingview"
    # Add other fields as needed

@app.post("/webhook")
async def webhook(alert: TradingViewAlert):
    try:
        # 1. Time Normalization (Advanced)
        # Parse timestamp
        if alert.timestamp.isdigit():
             dt = datetime.fromtimestamp(int(alert.timestamp), tz=timezone.utc)
        else:
             dt = datetime.fromisoformat(alert.timestamp.replace("Z", "+00:00"))
        
        # Ensure UTC
        dt = dt.astimezone(timezone.utc)
        
        # Check Drift
        from utils.time_oracle import time_oracle
        is_ok, drift_ms = time_oracle.check_drift(dt, threshold_ms=5000) # 5s tolerance for webhooks
        
        if not is_ok:
            print(f"⚠️ HIGH CLOCK DRIFT: {drift_ms:.2f}ms. Timestamp: {dt}, System: {time_oracle.now()}")
            # We enforce usage of system time if drift is too high to prevent "signals from future"
            # Or we reject. For webhook (latency exists), we accept but warn.
            # dt = time_oracle.now() # Option: Override


        # 2. Prepare Raw Tick
        tick_data = alert.dict()
        tick_data['ingest_timestamp'] = server_time.isoformat()
        tick_data['normalized_timestamp'] = dt.isoformat()
        
        # 3. Save to S3 (Immutable)
        s3_path = storage_client.save_raw_tick(alert.symbol, tick_data, dt)
        
        # 4. Publish to Event Bus
        event_payload = {
            "symbol": alert.symbol,
            "price": alert.price,
            "volume": alert.volume,
            "timestamp": dt.isoformat(),
            "s3_path": s3_path
        }
        event_bus.publish(f"market.tick.{alert.symbol}", event_payload)
        
        return {"status": "success", "s3_path": s3_path}

    except Exception as e:
        print(f"Error processing webhook: {e}")
        
        if "Integrity Error" in str(e):
            # Critical Alert for Overwrite Attempt
            event_bus.publish("system.alert", {
                "level": "CRITICAL",
                "message": f"DATA INTEGRITY BLOCKED: Attempted overwrite of {alert.symbol} at {dt}",
                "timestamp": datetime.utcnow().isoformat()
            })
            raise HTTPException(status_code=409, detail=f"Integrity Error: Data already exists. {str(e)}")
            
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
