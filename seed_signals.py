import sys
import os
from datetime import datetime, timedelta
import uuid

# Add workers to path
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db, engine, Base
from common.models import Automation, Signal

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Get First Principle Strategy automation
with next(get_db()) as db:
    automation = db.query(Automation).filter(Automation.slug == "first-principle-strategy").first()
    
    if not automation:
        print("First Principle Strategy automation not found!")
        exit(1)
    
    print(f"Found automation: {automation.name} (ID: {automation.id})")
    
    # Create demo signals
    demo_signals = [
        {
            "symbol": "NIFTY",
            "timestamp": datetime.now() - timedelta(hours=2),
            "score": 8.5,
            "payload": {
                "type": "BUY",
                "price": 21500.50,
                "target": 21650,
                "stop_loss": 21450,
                "reason": "False Breakout detected - Strong support level"
            },
            "status": "new"
        },
        {
            "symbol": "BANKNIFTY",
            "timestamp": datetime.now() - timedelta(hours=1, minutes=30),
            "score": 7.8,
            "payload": {
                "type": "SELL",
                "price": 46200.25,
                "target": 46000,
                "stop_loss": 46350,
                "reason": "Resistance rejection - False breakout pattern"
            },
            "status": "new"
        },
        {
            "symbol": "RELIANCE",
            "timestamp": datetime.now() - timedelta(hours=1),
            "score": 9.2,
            "payload": {
                "type": "BUY",
                "price": 2450.75,
                "target": 2485,
                "stop_loss": 2435,
                "reason": "High probability false breakout setup"
            },
            "status": "confirmed"
        },
        {
            "symbol": "TATASTEEL",
            "timestamp": datetime.now() - timedelta(minutes=45),
            "score": 6.5,
            "payload": {
                "type": "SELL",
                "price": 145.30,
                "target": 143.50,
                "stop_loss": 146.80,
                "reason": "Weak momentum - potential false breakout"
            },
            "status": "new"
        },
        {
            "symbol": "HDFCBANK",
            "timestamp": datetime.now() - timedelta(minutes=15),
            "score": 8.9,
            "payload": {
                "type": "BUY",
                "price": 1650.40,
                "target": 1670,
                "stop_loss": 1640,
                "reason": "Strong support zone - False breakout confirmed"
            },
            "status": "new"
        }
    ]
    
    # Add signals to database
    for signal_data in demo_signals:
        signal = Signal(
            automation_id=automation.id,
            symbol=signal_data["symbol"],
            timestamp=signal_data["timestamp"],
            score=signal_data["score"],
            payload=signal_data["payload"],
            status=signal_data["status"]
        )
        db.add(signal)
    
    db.commit()
    print(f"✅ Successfully added {len(demo_signals)} demo signals for First Principle Strategy!")
