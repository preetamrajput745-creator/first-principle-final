from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from kafka import KafkaProducer
import json
import os
import asyncio
import uuid
from sqlalchemy.orm import Session
from api.models import SignalConfirmRequest

# --- FIX: Standardized Absolute Imports (No sys.path hacking) ---
from workers.common.database import get_db, engine, Base
from workers.common.models import Automation, Signal, User, Order
from workers.common.config_manager import ConfigManager

# --- Circuit Breaker Imports ---
from workers.risk.circuit_breaker import CircuitBreaker
from api.routers import circuit_breaker as cb_router

app = FastAPI(title="Trading Automation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kafka Producer Setup
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
producer = None

@app.on_event("startup")
async def startup_event():
    global producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
    except Exception as e:
        print(f"Warning: Kafka not connected: {e}")

# Create Tables
Base.metadata.create_all(bind=engine)

# Seed Default Automation
try:
    with next(get_db()) as db:
        if not db.query(Automation).filter(Automation.slug == "first-principle-strategy").first():
            default_auto = Automation(
                name="First Principle Strategy",
                slug="first-principle-strategy",
                description="Default automation for First Principle Trading",
                status="active"
            )
            db.add(default_auto)
            db.commit()
            print("Seeded default automation: First Principle Strategy")
except Exception as e:
    print(f"Warning: Seed automation failed (DB might be locked or init issue): {e}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading Automation API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Pydantic Models for Requests ---
class AutomationCreate(BaseModel):
    name: str
    slug: str
    description: str = None
    config: dict = {}

class AutomationUpdate(BaseModel):
    status: str = None
    config: dict = None
    reason: str = None 
    user_id: str = None 
    second_approver: str = None 

@app.get("/automations")
def get_automations(db: Session = Depends(get_db)):
    automations = db.query(Automation).all()
    return automations

@app.post("/automations")
def create_automation(auto: AutomationCreate, db: Session = Depends(get_db)):
    if db.query(Automation).filter(Automation.slug == auto.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    new_auto = Automation(
        name=auto.name,
        slug=auto.slug,
        description=auto.description,
        config=auto.config,
        status="draft"
    )
    db.add(new_auto)
    db.commit()
    db.refresh(new_auto)
    return new_auto

@app.patch("/automations/{automation_id}")
def update_automation(automation_id: str, auto_update: AutomationUpdate, db: Session = Depends(get_db)):
    auto = db.query(Automation).filter(Automation.id == uuid.UUID(automation_id)).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    if auto_update.status:
        auto.status = auto_update.status
        db.commit()
        
    if auto_update.config is not None:
        try:
            if not auto_update.reason:
                 raise HTTPException(status_code=400, detail="Reason required for config changes.")
            
            ConfigManager.update_config(
                automation_id=str(auto.id),
                new_config=auto_update.config,
                reason=auto_update.reason,
                user_id=str(auto_update.user_id) if auto_update.user_id else "admin_ui_user",
                second_approver=auto_update.second_approver
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    db.refresh(auto)
    return auto

@app.get("/automations/{automation_id}/signals")
def get_signals(automation_id: str, db: Session = Depends(get_db)):
    signals = db.query(Signal).filter(Signal.automation_id == uuid.UUID(automation_id)).order_by(Signal.timestamp.desc()).limit(50).all()
    return signals

@app.post("/signals/{signal_id}/confirm")
def confirm_signal(signal_id: str, req: SignalConfirmRequest, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.id == uuid.UUID(signal_id)).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.status = "confirmed"
    db.commit()
    
    if producer:
        order_request = {
            "signal_id": str(signal.id),
            "automation_id": str(signal.automation_id),
            "symbol": signal.symbol,
            "quantity": 1, 
            "price": signal.payload.get("price", 0.0),
            "action": "BUY",
            "type": "MARKET",
            "timestamp": str(signal.timestamp),
            "otp_token": req.otp_token
        }
        producer.send("exec.approve_command", order_request)
        
    return {"status": "confirmed", "order_sent": True}

@app.delete("/signals/{signal_id}")
def delete_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.id == uuid.UUID(signal_id)).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.status = "rejected"
    db.commit()
    return {"status": "rejected"}

@app.post("/ingest/webhook")
async def ingest_webhook(payload: dict):
    if not producer:
        raise HTTPException(status_code=503, detail="Kafka producer not available")
    
    try:
        from infra.time_normalizer import clock
        utc_now, source_clock = clock.get_time_and_source()
        
        payload["_ingest_time"] = utc_now.isoformat()
        payload["_source_clock"] = source_clock
        
        if "timestamp" in payload:
            try:
                event_ts = clock.normalize_timestamp(payload["timestamp"])
                drift_ms = (utc_now - event_ts).total_seconds() * 1000
                payload["_clock_drift_ms"] = drift_ms
                print(f"[METRICS] Source: {source_clock} | Drift: {drift_ms:.2f}ms")
            except Exception as e:
                print(f"[WARN] Failed to calc drift: {e}")
        
        symbol = payload.get("symbol", "UNKNOWN")
        topic = f"market.tick.{symbol}" if symbol != "UNKNOWN" else "market.tick"
        
        producer.send(topic, payload)
        return {"status": "received", "topic": topic}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include Circuit Breaker Router
app.include_router(cb_router.router)

def get_current_admin(x_role: str = Header(None, alias="X-User-Role")):
    if x_role != "admin":
        raise HTTPException(status_code=403, detail="RBAC: Admin Access Required")
    return x_role

@app.post("/risk/pause", dependencies=[Depends(get_current_admin)])
def trigger_circuit_breaker(reason: str = "Manual Admin Action", db: Session = Depends(get_db)):
    cb = CircuitBreaker()
    try:
        cb.pause_all_active_automations(reason)
        return {"status": "triggered", "message": "Circuit Breaker Activated. All automations paused."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/risk/status")
def get_risk_status(db: Session = Depends(get_db)):
    cb = CircuitBreaker()
    return {
        "signal_rate_ok": cb.check_signal_rate(auto_pause=False),
        "error_rate_ok": cb.check_error_rate(auto_pause=False),
        "pnl_ok": cb.check_pnl_health(auto_pause=False),
        "limits": {
            "max_signals_per_hour": cb.max_signals_per_hour,
            "max_error_rate_pct": cb.max_error_rate_pct,
            "max_daily_loss": cb.max_daily_loss
        }
    }
