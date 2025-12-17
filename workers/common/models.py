from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Uuid, Integer, Boolean
from sqlalchemy.sql import func
import uuid
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    role = Column(String, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Automation(Base):
    __tablename__ = "automations"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(String)
    owner_id = Column(Uuid, ForeignKey("users.id"))
    status = Column(String) # active, paused, stopped
    config = Column(JSON)
    
    # Mistake #7: Human Gating
    approved_trade_count = Column(Integer, default=0)
    is_fully_automated = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

class ConfigAuditLog(Base):
    """
    Mistake #8: Immutable Audit Log for Config Changes.
    Tracks every change to automation strategy.
    """
    __tablename__ = "config_audit_logs"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    automation_id = Column(Uuid, ForeignKey("automations.id"))
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=True) # Nullable for system updates
    
    old_config = Column(JSON)
    new_config = Column(JSON)
    change_reason = Column(String, nullable=False)
    
    # Mistake #5: Out-of-hours governance
    second_approver = Column(String, nullable=True)
    
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Enhanced Audit Fields (Zero-Tolerance Spec)
    actor_device = Column(String, nullable=True)
    actor_role = Column(String, nullable=True) # viewer, operator, approver, audit-admin
    ui_page = Column(String, nullable=True) # /admin/config/edit
    
    resource_type = Column(String, default="automation") # config, dashboard, alert...
    change_context = Column(String, default="api") # ui, api, ci, automation
    
    evidence_link = Column(String) # S3 URI
    signed_hash = Column(String) # SHA256 signature from Vault
    
    change_type = Column(String, default="update") # create, update, delete
    diff = Column(String, nullable=True) # Compact diff or JSONPath
    notes = Column(String, nullable=True) # Optional investigator notes
    
    # State for Approval Flow
    status = Column(String, default="committed") # pending, approved, committed, rejected

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    automation_id = Column(Uuid, ForeignKey("automations.id"))
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    score = Column(Float)
    payload = Column(JSON)
    raw_event_location = Column(String)
    status = Column(String, default="new")
    
    # Risk & Execution Fields (Section 2 Controls)
    estimated_slippage = Column(Float, default=0.0)
    execution_price = Column(Float)
    l1_snapshot = Column(JSON) # Stores Bid/Ask at time of signal
    l2_snapshot_path = Column(String) # Mistake #11: Path to compressed L2 data
    latency_ms = Column(Float) # MATCHING database.py
    clock_drift_ms = Column(Float) # NEW: Mistake #3 Visibility
    
    # Mistake #12: Market Regime Tagging
    # Strategies must be aware of the environment
    regime_volatility = Column(String, default="normal") # low, normal, high
    regime_session = Column(String, default="mid") # open, mid, close

    
    # Mistake #4: Realized Slippage
    # estimated_slippage is already defined above
    realized_slippage = Column(Float) # NEW
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Order(Base):
    __tablename__ = "orders"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    signal_id = Column(Uuid, ForeignKey("signals.id"))
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    
    # Mistake 4 & 7 Support
    simulated_slippage = Column(Float, default=0.0)
    realized_slippage = Column(Float)
    
    pnl = Column(Float, default=0.0)
    status = Column(String) # FILLED / REJECTED / FILLED_HIGH_SLIP
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_paper = Column(Boolean, default=True)

class Backtest(Base):
    __tablename__ = "backtests"
    
    id = Column(Integer, primary_key=True, index=True)
    automation_id = Column(String)
    run_date = Column(DateTime(timezone=True), server_default=func.now())
    total_signals = Column(Integer)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    total_pnl = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float, nullable=True)
    config_snapshot = Column(JSON)
    notes = Column(String, nullable=True)

class SlippageProfile(Base):
    """
    Mistake #3: Controls - Default slippage profile per instrument.
    """
    __tablename__ = "slippage_profiles"
    
    symbol = Column(String, primary_key=True)
    base_slippage_pct = Column(Float, default=0.01) # Default 1 bps (0.01%)
    volatility_multiplier = Column(Float, default=2.0)
    tick_size = Column(Float, default=0.05)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class VaultAccessLog(Base):
    """
    Mistake #6: Vault Access Audit Log
    Tracks which service accessed which secret.
    """
    __tablename__ = "vault_access_logs"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    service_name = Column(String, nullable=False)
    secret_name = Column(String, nullable=False)
    status = Column(String) # GRANTED, DENIED
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class SafetyEvent(Base):
    """
    Safety Panel: Immutable Audit Log for Circuit Breakers & Auto-Pauses.
    """
    __tablename__ = "safety_events"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id = Column(String, unique=True, nullable=False) # UUID String
    timestamp_utc = Column(DateTime(timezone=True), server_default=func.now())
    component = Column(String, nullable=False) # execution|ingest|risk|automation
    event_type = Column(String, nullable=False) # auto_pause|manual_pause|breaker_open...
    target = Column(String, nullable=True)
    trigger_rule = Column(String, nullable=True)
    trigger_value = Column(String, nullable=True) # Stored as string/json
    threshold_value = Column(String, nullable=True)
    actor = Column(String, nullable=False) # system|user|service_account
    actor_ip = Column(String, nullable=True)
    reason = Column(String)
    evidence_link = Column(String) # S3 URI
    signed_hash = Column(String, nullable=False)
    notes = Column(String, nullable=True)

class CircuitBreakerState(Base):
    """
    Tracks the CURRENT state of a circuit breaker.
    """
    __tablename__ = "circuit_breaker_states"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    breaker_id = Column(String, unique=True, nullable=False) # e.g. "global", "exec-strategy-A"
    scope = Column(String, nullable=False) # global|component|instrument|strategy
    target = Column(String, nullable=False) # execution|NIFTY-50|strategy-A
    state = Column(String, default="CLOSED") # CLOSED|OPEN|HALF_OPEN|DISABLED
    last_changed_at = Column(DateTime(timezone=True), server_default=func.now())
    last_changed_by = Column(String)
    reason = Column(String)
    recovery_config = Column(JSON) # e.g. {"probe_count": 5, "required_success": 4}

class CircuitBreakerEvent(Base):
    """
    Immutable audit log for circuit breaker state changes.
    """
    __tablename__ = "circuit_breaker_events"
    event_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    breaker_id = Column(String, nullable=False)
    scope = Column(String, nullable=False)
    target = Column(String, nullable=False)
    old_state = Column(String)
    new_state = Column(String)
    timestamp_utc = Column(DateTime(timezone=True), server_default=func.now())
    changed_by = Column(String)
    changed_by_id = Column(String)
    actor_ip = Column(String)
    reason = Column(String)
    change_context = Column(String) # ui|api|rule|automation
    related_metrics = Column(JSON)
    evidence_link = Column(String) # S3 URI
    signed_hash = Column(String) # SHA256 signature
    notes = Column(String)
