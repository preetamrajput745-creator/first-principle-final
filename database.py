from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import settings

DATABASE_URL = settings.DATABASE_URL

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Automation(Base):
    __tablename__ = "automations"
    
    id = Column(String, primary_key=True, default=lambda: f"auto_{int(datetime.utcnow().timestamp())}")
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="active")  # active / paused
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"

    unique_signal_id = Column(String, primary_key=True, index=True)
    automation_id = Column(String, default="False Breakout")
    symbol = Column(String, index=True)
    bar_time = Column(DateTime, index=True) # UTC
    
    # Features
    bar_open = Column(Float)
    bar_high = Column(Float)
    bar_low = Column(Float)
    bar_close = Column(Float)
    bar_volume = Column(Float)
    atr14 = Column(Float)
    wick_size = Column(Float)
    wick_ratio = Column(Float)
    vol_sma20 = Column(Float)
    vol_ratio = Column(Float)
    resistance_level = Column(Float)
    poke_distance = Column(Float)
    
    # Refs
    orderbook_ref_path = Column(String, nullable=True)
    raw_feature_snapshot_path = Column(String)
    
    # Score
    score = Column(Float)
    scoring_breakdown = Column(JSON)
    
    status = Column(String, default="new") # new / simulated / executed / paused
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    # Mistake 4 Checks
    realized_slippage = Column(Float)
    latency_ms = Column(Float)
    clock_drift_ms = Column(Float) # MATCHING common/models.py

class Order(Base):
    __tablename__ = "orders"
    
    order_id = Column(String, primary_key=True)
    signal_id = Column(String, index=True)
    symbol = Column(String)
    side = Column(String) # BUY / SELL
    quantity = Column(Float)
    price = Column(Float)
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    simulated_slippage = Column(Float)
    realized_slippage = Column(Float) # NEW: For Mistake #4 Monitoring
    pnl = Column(Float, default=0.0)
    status = Column(String) # FILLED / REJECTED / CLOSED
    created_at = Column(DateTime, default=datetime.utcnow)
    is_paper = Column(Boolean, default=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String)
    action = Column(String)
    details = Column(JSON)
    reason = Column(String)

class Backtest(Base):
    __tablename__ = "backtests"
    
    id = Column(Integer, primary_key=True, index=True)
    automation_id = Column(String)
    run_date = Column(DateTime, default=datetime.utcnow)
    total_signals = Column(Integer)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    total_pnl = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float, nullable=True)
    config_snapshot = Column(JSON)
    notes = Column(Text, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)
