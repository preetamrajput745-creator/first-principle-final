import json
import time
import random
from datetime import datetime
import sys
import os
from kafka import KafkaConsumer, KafkaProducer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings
from database import SessionLocal, Order, Signal

class ExecutionSimulator:
    def __init__(self):
        self.db = SessionLocal()
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def calculate_slippage(self, price, volume, volatility=1.0):
        # Simple slippage model
        base_slip = settings.SLIPPAGE_BASE * price
        vol_slip = settings.SLIPPAGE_VOL_COEFF * volatility * 0.01 * price 
        random_factor = random.uniform(0.8, 1.2)
        total_slippage = (base_slip + vol_slip) * random_factor
        return total_slippage

    def process_signal(self, signal_data):
        symbol = signal_data['symbol']
        # FBE signal payload might not have signal_id, but the DB entry does.
        # The FBE worker sends the payload directly.
        # Let's assume the payload has what we need or we look up the latest signal.
        # For simplicity, we'll generate an ID if missing or use timestamp.
        
        signal_type = signal_data.get('type')
        price = signal_data.get('price')
        timestamp = signal_data.get('timestamp')
        
        # Determine action based on signal type
        action = "SELL" if "BEARISH" in signal_type else "BUY"
        
        print(f"Simulating execution for {symbol} ({action} @ {price})")
        
        # Calculate Slippage
        # We can use ATR from signal as volatility proxy if available, else default
        slippage = self.calculate_slippage(price, 0, volatility=1.0)
        
        if action == "BUY":
            fill_price = price + slippage
        else:
            fill_price = price - slippage
            
        # Create Order Record
        order_id = f"ord_{symbol}_{int(time.time())}"
        
        order = Order(
            order_id=order_id,
            signal_id=f"sig_{int(time.time())}", # Placeholder link
            symbol=symbol,
            side=action,
            quantity=1, # Default qty
            price=fill_price,
            simulated_slippage=slippage,
            status="FILLED",
            is_paper=True
        )
        
        self.db.add(order)
        self.db.commit()
        
        print(f"Order {order_id} FILLED at {fill_price:.2f} (Slippage: {slippage:.2f})")
        
        # Publish Order Event
        self.producer.send("exec.order.status", {
            "order_id": order_id,
            "symbol": symbol,
            "price": fill_price,
            "side": action,
            "status": "FILLED",
            "timestamp": time.time()
        })

    def run(self):
        print("Execution Simulator Started (Kafka)...")
        
        consumer = KafkaConsumer(
            "signal.false_breakout",
            bootstrap_servers=self.bootstrap_servers,
            group_id="simulator_group",
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        print("Listening for signals...")
        
        for message in consumer:
            try:
                signal_data = message.value
                self.process_signal(signal_data)
            except Exception as e:
                print(f"Error processing signal: {e}")

if __name__ == "__main__":
    sim = ExecutionSimulator()
    sim.run()
