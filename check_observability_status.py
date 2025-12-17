
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add workers path to sys.path
workers_path = os.path.join(os.getcwd(), 'workers')
sys.path.insert(0, workers_path)

from common.models import Order, Signal, ConfigAuditLog
from common.database import Base

# Database path
DB_PATH = os.path.join(os.getcwd(), 'sql_app.db')
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

def check_observability_data():
    print("TRIPLE CHECK: Observability Data Completeness")
    print("="*60)

    # 1. PnL Check
    orders_with_pnl = session.query(Order).filter(Order.pnl != 0).count()
    print(f"Orders with PnL != 0: {orders_with_pnl}")
    
    # 2. Realized Slippage Check
    orders_with_slip = session.query(Order).filter(Order.realized_slippage != None).count()
    print(f"Orders with Realized Slippage: {orders_with_slip}")
    
    # 3. Config Audit Check
    config_logs = session.query(ConfigAuditLog).count()
    print(f"Config Audit Log Entries: {config_logs}")
    
    # 4. Signal Snapshots Check
    signals_with_l2 = session.query(Signal).filter(Signal.l2_snapshot_path != None).count()
    print(f"Signals with L2 Snapshot Path: {signals_with_l2}")
    
    print("="*60)
    
    if orders_with_pnl == 0:
        print("FAIL: No PnL data found. 'Simulated PnL' metric is effectively dead.")
    
    if orders_with_slip == 0:
        print("FAIL: No Realized Slippage data found.")
        
    if config_logs == 0:
        print("WARNING: No Config Changes recorded.")
        
    if signals_with_l2 == 0:
        print("WARNING: No L2 Snapshots linked to signals.")

if __name__ == "__main__":
    check_observability_data()
