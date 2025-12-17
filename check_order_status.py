
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
sys.path.insert(0, os.path.join(os.getcwd(), 'workers'))
from common.models import Order
import datetime

DB_PATH = os.path.join(os.getcwd(), 'sql_app.db')
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=120)
orders = session.query(Order).filter(Order.created_at >= cutoff).all()

print(f"Recent Orders: {len(orders)}")
for o in orders:
    print(f"ID: {o.id} | Status: {o.status} | PnL: {o.pnl} | Slip: {o.realized_slippage}")
