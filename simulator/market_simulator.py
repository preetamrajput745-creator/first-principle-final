import time
import json
import random
import os
from datetime import datetime, timezone
from kafka import KafkaProducer

# Configuration
SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD"]
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

def generate_tick(symbol, base_price):
    # Random walk
    change = random.uniform(-0.5, 0.5)
    price = base_price + change
    
    return {
        "symbol": symbol,
        "price": round(price, 2),
        "volume": round(random.uniform(0.1, 5.0), 4),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, price

def main():
    print("Starting Market Data Simulator...")
    
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    prices = {s: 1000.0 for s in SYMBOLS} # Starting prices
    
    try:
        while True:
            for symbol in SYMBOLS:
                tick, new_price = generate_tick(symbol, prices[symbol])
                prices[symbol] = new_price
                
                topic = f"market.tick.{symbol}"
                producer.send(topic, tick)
                print(f"Published to {topic}: {tick['price']}")
                
            time.sleep(1) # 1 tick per second per symbol
            
    except KeyboardInterrupt:
        print("Stopping simulator...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
