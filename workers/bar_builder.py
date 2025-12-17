import redis
import json
import time
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

class BarBuilder:
    """
    Consumes market.tick.<symbol> from Redis.
    Aggregates into 1-minute bars.
    Publishes market.bar.1m.<symbol>.
    """
    def __init__(self):
        self.r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
        self.current_bars = {} # {symbol: {open, high, low, close, vol, start_time}}

    def process_stream(self):
        print("[BAR_BUILDER] Starting stream processing...")
        # In a real implementation, we'd use XREADGROUP. 
        # For simplicity, we loop available symbols or just listen to all.
        
        # Mocking the loop: Check streams for configured symbols
        while True:
            for symbol in settings.SYMBOLS:
                stream_key = f"market.tick.{symbol}"
                # Read new messages
                messages = self.r.xread({stream_key: '$'}, count=5, block=100)
                
                for stream, msgs in messages:
                    for message_id, data in msgs:
                        alert_json = data.get(b'data').decode('utf-8')
                        self.process_tick(symbol, json.loads(alert_json))
                        
            # Check for bar closure (time based)
            self.check_bar_closures()
            time.sleep(0.1)

    def process_tick(self, symbol, tick_data):
        price = float(tick_data.get('price', 0))
        vol = float(tick_data.get('volume', 0))
        ts_str = tick_data.get('time', datetime.utcnow().isoformat())
        
        # Simplified minute alignment
        # In real world: parse TS, floor to minute
        # Here we just aggregate in memory for demo
        
        if symbol not in self.current_bars:
            self.current_bars[symbol] = {
                'open': price, 'high': price, 'low': price, 'close': price,
                'volume': vol, 'count': 1, 'start_time': datetime.utcnow()
            }
        else:
            b = self.current_bars[symbol]
            b['high'] = max(b['high'], price)
            b['low'] = min(b['low'], price)
            b['close'] = price
            b['volume'] += vol
            b['count'] += 1

    def check_bar_closures(self):
        # Force close bars if minute changed (simplified)
        # Real impl needs strict time alignment
        now = datetime.utcnow()
        to_remove = []
        for symbol, bar in self.current_bars.items():
            # If bar is older than 60s (demo logic)
            if (now - bar['start_time']).total_seconds() > 60:
                self.publish_bar(symbol, bar)
                to_remove.append(symbol)
                
        for s in to_remove:
            del self.current_bars[s]

    def publish_bar(self, symbol, bar):
        print(f"[BAR_BUILDER] Closed Bar for {symbol}: {bar}")
        # Publish event
        topic = f"market.bar.1m.{symbol}"
        self.r.xadd(topic, {"data": json.dumps(bar, default=str)})

if __name__ == "__main__":
    builder = BarBuilder()
    try:
        builder.process_stream()
    except KeyboardInterrupt:
        print("Stopping Bar Builder")
