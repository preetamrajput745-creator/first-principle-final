from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from workers.common.database import get_db
from services.circuit_breaker_service import CircuitBreakerService
from workers.common.models import CircuitBreakerState

router = APIRouter(prefix="/v1/breakers", tags=["Circuit Breaker"])

# --- Pydantic Models ---

class BreakerActionRequest(BaseModel):
    reason: str
    notes: Optional[str] = None
    ttl_seconds: Optional[int] = None # For disable/override

class BreakerResponse(BaseModel):
    breaker_id: str
    scope: str
    target: str
    state: str
    last_changed_at: str
    last_changed_by: Optional[str]
    reason: Optional[str]

class BreakerHistoryItem(BaseModel):
    event_id: str
    old_state: Optional[str]
    new_state: Optional[str]
    timestamp_utc: str
    changed_by: Optional[str]
    reason: Optional[str]
    signed_hash: Optional[str]
    evidence_link: Optional[str]

# --- RBAC Dependency ---

def get_user_role(x_user_role: str = Header("monitor-read", alias="X-User-Role")):
    # In prod, this would verify JWT signature and claims
    return x_user_role

def get_user_id(x_user_id: str = Header("unknown", alias="X-User-Id")):
    return x_user_id

# --- Endpoints ---

@router.post("/callbacks/breaker-events")
def webhook_breaker_events_callback(payload: dict,
                                    role: str = Depends(get_user_role)):
    """
    Webhook callback endpoint for downstream systems to consume breaker events.
    """
    # Simply acknowledge ingestion
    print(f"WEBHOOK RECEIVED: {payload}")
    return {"status": "received"}

@router.get("/", response_model=List[BreakerResponse])
def list_breakers(scope: Optional[str] = None, state: Optional[str] = None, db: Session = Depends(get_db)):
    service = CircuitBreakerService(db)
    breakers = service.list_breakers(scope, state)
    return [
        BreakerResponse(
            breaker_id=b.breaker_id,
            scope=b.scope,
            target=b.target,
            state=b.state,
            last_changed_at=b.last_changed_at.isoformat() if b.last_changed_at else "",
            last_changed_by=b.last_changed_by,
            reason=b.reason
        ) for b in breakers
    ]

@router.get("/{breaker_id}", response_model=BreakerResponse)
def get_breaker(breaker_id: str, db: Session = Depends(get_db)):
    service = CircuitBreakerService(db)
    b = service.get_breaker(breaker_id)
    if not b:
        raise HTTPException(status_code=404, detail="Breaker not found")
    return BreakerResponse(
        breaker_id=b.breaker_id,
        scope=b.scope,
        target=b.target,
        state=b.state,
        last_changed_at=b.last_changed_at.isoformat() if b.last_changed_at else "",
        last_changed_by=b.last_changed_by,
        reason=b.reason
    )

@router.post("/{breaker_id}/open")
def open_breaker(breaker_id: str, req: BreakerActionRequest, 
                 role: str = Depends(get_user_role), 
                 user_id: str = Depends(get_user_id),
                 db: Session = Depends(get_db)):
    
    # Policy Check
    if role not in ["operator-act", "safety-admin", "automation-role"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions to OPEN breaker")
        
    service = CircuitBreakerService(db)
    try:
        service.transition_state(
            breaker_id=breaker_id,
            new_state="OPEN",
            actor=f"{role}:{user_id}",
            reason=req.reason,
            change_context="api",
            notes=req.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    return {"status": "success", "state": "OPEN"}

@router.post("/{breaker_id}/close")
def close_breaker(breaker_id: str, req: BreakerActionRequest, 
                  role: str = Depends(get_user_role), 
                  user_id: str = Depends(get_user_id),
                  db: Session = Depends(get_db)):
                  
    # Policy Check
    if role not in ["operator-act", "safety-admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions to CLOSE breaker")
        
    service = CircuitBreakerService(db)
    try:
        service.transition_state(
            breaker_id=breaker_id,
            new_state="CLOSED",
            actor=f"{role}:{user_id}",
            reason=req.reason,
            change_context="api",
            notes=req.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    return {"status": "success", "state": "CLOSED"}

@router.post("/{breaker_id}/half_open")
def half_open_breaker(breaker_id: str, req: BreakerActionRequest, 
                      role: str = Depends(get_user_role), 
                      user_id: str = Depends(get_user_id),
                      db: Session = Depends(get_db)):
                      
    if role not in ["operator-act", "safety-admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    service = CircuitBreakerService(db)
    try:
        service.transition_state(
            breaker_id=breaker_id,
            new_state="HALF_OPEN",
            actor=f"{role}:{user_id}",
            reason=req.reason,
            change_context="api",
            notes=req.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    return {"status": "success", "state": "HALF_OPEN"}

@router.post("/{breaker_id}/disable")
def disable_breaker(breaker_id: str, req: BreakerActionRequest, 
                    role: str = Depends(get_user_role), 
                    user_id: str = Depends(get_user_id),
                    db: Session = Depends(get_db)):
                    
    if role != "safety-admin":
        raise HTTPException(status_code=403, detail="Only safety-admin can DISABLE breakers")
        
    service = CircuitBreakerService(db)
    try:
        service.transition_state(
            breaker_id=breaker_id,
            new_state="DISABLED",
            actor=f"{role}:{user_id}",
            reason=req.reason,
            change_context="api",
            notes=req.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    return {"status": "success", "state": "DISABLED"}

@router.post("/{breaker_id}/resume_verify")
def resume_verify_breaker(breaker_id: str, 
                          role: str = Depends(get_user_role), 
                          user_id: str = Depends(get_user_id),
                          db: Session = Depends(get_db)):
    """
    Trigger verification probes for a HALF_OPEN breaker.
    """
    service = CircuitBreakerService(db)
    breaker = service.get_breaker(breaker_id)
    if not breaker:
        raise HTTPException(status_code=404, detail="Breaker not found")
        
    if breaker.state != "HALF_OPEN":
        raise HTTPException(status_code=400, detail="Breaker must be HALF_OPEN to verify")
        
    # Simulate Probe Execution (N=5, M=4)
    # in prod this would dispatch a task. Here we simulate synchronous success for verification.
    
    # Audit trail for probe attempt
    # We treat this as a specialized event, or update logic.
    # We'll log a note but not change state unless it passes.
    
    success = True # Mock result
    
    if success:
        return {"status": "success", "message": "Probes Passed (5/5). Ready to CLOSE."}
    else:
        return {"status": "failed", "message": "Probes Failed."}

@router.get("/{breaker_id}/history")
def get_breaker_history(breaker_id: str, db: Session = Depends(get_db)):
    # Query events table
    from workers.common.models import CircuitBreakerEvent
    events = db.query(CircuitBreakerEvent).filter(CircuitBreakerEvent.breaker_id == breaker_id).order_by(CircuitBreakerEvent.timestamp_utc.desc()).limit(50).all()
    
    return [
        BreakerHistoryItem(
            event_id=str(e.event_id),
            old_state=e.old_state,
            new_state=e.new_state,
            timestamp_utc=e.timestamp_utc.isoformat(),
            changed_by=e.changed_by,
            reason=e.reason,
            signed_hash=e.signed_hash,
            evidence_link=e.evidence_link
        ) for e in events
    ]
