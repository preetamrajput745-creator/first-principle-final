import time
import json
from datetime import datetime, timedelta, timezone
import sys
import os
from kafka import KafkaConsumer, KafkaProducer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings

class BarBuilder:
    def __init__(self):
        self.current_bars = {} # {symbol: {open, high, low, close, volume, start_time}}
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def process_tick(self, tick):
        symbol = tick['symbol']
        price = float(tick['price'])
        volume = float(tick.get('volume', 0))
        ts_str = tick.get('timestamp')
        
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except:
                ts = datetime.now(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        
        # Determine minute boundary
        bar_start_time = ts.replace(second=0, microsecond=0)
        
        if symbol not in self.current_bars:
            self.current_bars[symbol] = {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
                "start_time": bar_start_time,
                "symbol": symbol
            }
        else:
            bar = self.current_bars[symbol]
            # Check if we moved to a new minute
            if bar_start_time > bar['start_time']:
                # Close previous bar
                self.publish_bar(bar)
                # Start new bar
                self.current_bars[symbol] = {
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": volume,
                    "start_time": bar_start_time,
                    "symbol": symbol
                }
            else:
                # Update current bar
                bar['high'] = max(bar['high'], price)
                bar['low'] = min(bar['low'], price)
                bar['close'] = price
                bar['volume'] += volume

    def publish_bar(self, bar):
        # Format for Kafka
        payload = {
            "symbol": bar['symbol'],
            "open": bar['open'],
            "high": bar['high'],
            "low": bar['low'],
            "close": bar['close'],
            "volume": bar['volume'],
            "time": bar['start_time'].isoformat()
        }
        print(f"Publishing Bar: {payload}")
        self.producer.send(f"market.bar.1m.{bar['symbol']}", payload)

    def run(self):
        print("Bar Builder Started (Kafka)...")
        
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id="bar_builder_group",
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        consumer.subscribe(pattern='^market\.tick\..*')
        
        print("Listening for ticks...")

        for message in consumer:
            try:
                tick_data = message.value
                self.process_tick(tick_data)
            except Exception as e:
                print(f"Error processing tick: {e}")

if __name__ == "__main__":
    builder = BarBuilder()
    builder.run()
