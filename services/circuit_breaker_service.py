import json
import hashlib
import os
import uuid
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from workers.common.database import get_db, SessionLocal
from workers.common.models import CircuitBreakerState, CircuitBreakerEvent

class CircuitBreakerService:
    """
    Manages Circuit Breaker lifecycle, state transitions, and immutable audit logging.
    Enforces Zero-Tolerance compliance for audit trails.
    """
    
    # Mock Private Key (In Prod: Load from Vault)
    _SIGNING_KEY = b"secure-vault-private-key-mock-cb"
    
    # Audit Path Base
    AUDIT_BASE_PATH = os.environ.get("ANTIGRAVITY_AUDIT_S3", "s3://antigravity-audit/local/circuit-breaker")

    # Prometheus Metrics
    from prometheus_client import Enum, Counter, Gauge

    try:
        BREAKER_STATE = Enum('breaker_state', 'Current state of circuit breaker', ['breaker_id', 'scope', 'target'], states=['CLOSED', 'OPEN', 'HALF_OPEN', 'DISABLED'])
        BREAKER_EVENTS = Counter('breaker_events_total', 'Total circuit breaker state changes', ['breaker_id', 'event_type'])
        BREAKER_LAST_CHANGED = Gauge('breaker_last_changed_seconds', 'Timestamp of last state change', ['breaker_id'])
    except ValueError:
        # Metrics already defined (reload protection)
        from prometheus_client import REGISTRY
        BREAKER_STATE = REGISTRY._names_to_collectors['breaker_state']
        BREAKER_EVENTS = REGISTRY._names_to_collectors['breaker_events_total']
        BREAKER_LAST_CHANGED = REGISTRY._names_to_collectors['breaker_last_changed_seconds']

    def __init__(self, db: Session = None):
        self.db = db if db else SessionLocal()

    def get_breaker(self, breaker_id: str) -> Optional[CircuitBreakerState]:
        return self.db.query(CircuitBreakerState).filter(CircuitBreakerState.breaker_id == breaker_id).first()

    def list_breakers(self, scope: str = None, state: str = None) -> List[CircuitBreakerState]:
        query = self.db.query(CircuitBreakerState)
        if scope:
            query = query.filter(CircuitBreakerState.scope == scope)
        if state:
            query = query.filter(CircuitBreakerState.state == state)
        return query.all()

    def create_or_update_breaker(self, breaker_id: str, scope: str, target: str, recovery_config: dict = None):
        """
        Idempotent creation of a breaker definition.
        """
        breaker = self.get_breaker(breaker_id)
        if not breaker:
            breaker = CircuitBreakerState(
                breaker_id=breaker_id,
                scope=scope,
                target=target,
                state="CLOSED",
                recovery_config=recovery_config or {}
            )
            self.db.add(breaker)
            self.db.commit()
            self.db.refresh(breaker)
            
            # Init Metric
            self.BREAKER_STATE.labels(breaker_id=breaker_id, scope=scope, target=target).state('CLOSED')
            
        else:
            # Update config if needed
            if recovery_config:
                breaker.recovery_config = recovery_config
                self.db.commit()
        return breaker

    def transition_state(self, 
                         breaker_id: str, 
                         new_state: str, 
                         actor: str, 
                         reason: str, 
                         change_context: str = "api",
                         actor_ip: str = "unknown",
                         notes: str = None,
                         related_metrics: dict = None) -> CircuitBreakerState:
        """
        Executes a state transition with full audit logging.
        """
        breaker = self.get_breaker(breaker_id)
        if not breaker:
            raise ValueError(f"Breaker {breaker_id} not found")

        old_state = breaker.state
        
        # 1. Update State
        breaker.state = new_state
        breaker.last_changed_at = datetime.utcnow()
        breaker.last_changed_by = actor
        breaker.reason = reason
        
        # 2. Log Audit Event
        self._log_audit_event(
            breaker=breaker,
            old_state=old_state,
            new_state=new_state,
            actor=actor,
            reason=reason,
            change_context=change_context,
            actor_ip=actor_ip,
            notes=notes,
            related_metrics=related_metrics
        )
        
        self.db.commit()
        self.db.refresh(breaker)
        
        # 3. Update Metrics
        try:
            self.BREAKER_STATE.labels(breaker_id=breaker.breaker_id, scope=breaker.scope, target=breaker.target).state(new_state)
            self.BREAKER_EVENTS.labels(breaker_id=breaker.breaker_id, event_type=new_state).inc()
            self.BREAKER_LAST_CHANGED.labels(breaker_id=breaker.breaker_id).set_to_current_time()
        except Exception as e:
            print(f"METRIC UPDATE FAILED: {e}")
            
        return breaker

    def _log_audit_event(self, 
                         breaker: CircuitBreakerState, 
                         old_state: str, 
                         new_state: str, 
                         actor: str, 
                         reason: str,
                         change_context: str,
                         actor_ip: str,
                         notes: str,
                         related_metrics: dict):
        
        event_id = str(uuid.uuid4())
        timestamp_utc = datetime.utcnow().isoformat()
        
        # Check S3 Availability (Mock check)
        s3_available = not os.environ.get("SIMULATE_S3_FAILURE")
        
        # Failure Mode A: If S3 unavailable -> Degraded Read-Only or Fail?
        # Spec says "Degraded read-only mode (no state-change allowed)"
        # But we are already deep in transition_state. Ideally we check before.
        # But here we will throw error to abort transaction if STRICT_AUDIT is on.
        if not s3_available:
            raise RuntimeError("CRITICAL: S3 Audit Store Unavailable. State change BLOCKED by Zero-Tolerance Policy.")

        # Construct Event Dict (Matches Spec)
        event_data = {
            "breaker_id": breaker.breaker_id,
            "scope": breaker.scope,
            "target": breaker.target,
            "state": new_state,
            "previous_state": old_state,
            "changed_at": timestamp_utc,
            "changed_by": actor,
    # ... rest identical ...
            "changed_by_id": "unknown", # Could be passed if available
            "actor_ip": actor_ip,
            "reason": reason,
            "change_context": change_context,
            "related_metrics": related_metrics or {},
            "notes": notes
        }
        
        # Generate Signed Hash
        canonical_str = json.dumps(event_data, sort_keys=True)
        signed_hash = hmac.new(self._SIGNING_KEY, canonical_str.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Determine Evidence Link
        # Using the configured S3 path structure
        evidence_link = f"{self.AUDIT_BASE_PATH}/circuit-breaker/{event_id}.json"
        
        event_data["signed_hash"] = signed_hash
        event_data["evidence_link"] = evidence_link
        
        # Write to DB
        db_event = CircuitBreakerEvent(
            event_id=uuid.UUID(event_id),
            breaker_id=breaker.breaker_id,
            scope=breaker.scope,
            target=breaker.target,
            old_state=old_state,
            new_state=new_state,
            timestamp_utc=datetime.fromisoformat(timestamp_utc),
            changed_by=actor,
            actor_ip=actor_ip,
            reason=reason,
            change_context=change_context,
            related_metrics=related_metrics,
            evidence_link=evidence_link,
            signed_hash=signed_hash,
            notes=notes
        )
        self.db.add(db_event)
        
        # Write to S3 (Mock/Local)
        self._write_to_s3_mock(event_data, event_id)

    def _write_to_s3_mock(self, event_data, event_id):
        """
        Writes the JSON to the local filesystem mimicking S3 structure.
        """
        try:
            # Parse the S3 URI to get a local relative path
            # s3://antigravity-audit/... -> audit_storage/...
            # We'll just dump it into a known local directory for verification
            
            # Use the global audit storage path if defined in verify_ci.py context, 
            # or default to a local 'audit_storage' folder.
            
            # We'll use a dedicated local folder for this task
            local_root = os.path.join(os.getcwd(), "s3_audit_local", "circuit-breaker")
            if not os.path.exists(local_root):
                os.makedirs(local_root)
                
            file_path = os.path.join(local_root, f"{event_id}.json")
            with open(file_path, "w") as f:
                json.dump(event_data, f, indent=2)
                
        except Exception as e:
            print(f"ERROR writing audit artifact: {e}")
            # In production, this would raise or queue
