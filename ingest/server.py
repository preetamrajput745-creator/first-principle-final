from fastapi import FastAPI, Request, HTTPException
import uvicorn
import sys
import os
import json
import redis
from datetime import datetime
from pydantic import BaseModel

# Add root to Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from infra.storage import storage

app = FastAPI(title="Ingest Service", description="Accepts TradingView Alert Webhooks")

# Redis Connection (with fallback)
try:
    r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    r.ping()  # Test connection
    REDIS_AVAILABLE = True
    print("[INGEST] Redis connected successfully")
except Exception as e:
    print(f"[INGEST] Redis not available: {e}")
    print("[INGEST] Running in FALLBACK mode (direct DB writes)")
    r = None
    REDIS_AVAILABLE = False

class TradeAlert(BaseModel):
    symbol: str
    price: float
    volume: float
    timestamp: str 
    # Add other fields as per TradingView spec

@app.post("/webhook/tradingview")
async def receive_alert(alert: dict):
    """
    Receives generic JSON payload from TradingView.
    Alert Format expected: {"symbol": "NIFTY_FUT", "price": 19500, "volume": 100, "time": "2023-..."}
    """
    try:
        print(f"[INGEST] Received Alert: {alert}")
        
        # 1. Validation & timestamp
        symbol = alert.get("symbol", "UNKNOWN")
        
        # 2. Persist Raw Tick to S3 (Append Only)
        s3_path = storage.save_raw_ticks(symbol, [alert])
        
        # 3. Publish to Redis Stream (if available)
        if REDIS_AVAILABLE:
            stream_key = f"market.tick.{symbol}"
            payload = {
                "data": json.dumps(alert),
                "s3_ref": s3_path or ""
            }
            r.xadd(stream_key, payload)
            print(f"[INGEST] Published to Redis: {stream_key}")
        else:
            # Fallback: Process immediately without event bus
            print(f"[INGEST] FALLBACK: Alert logged to S3, no Redis events")
        
        return {"status": "accepted", "s3_ref": s3_path, "redis": REDIS_AVAILABLE}
        
    except Exception as e:
        print(f"[INGEST] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok", "service": "ingest"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
