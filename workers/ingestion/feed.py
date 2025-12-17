import time
import random
import datetime
import uuid
from typing import Generator, Dict

class Tick:
    def __init__(self, symbol: str, bid: float, ask: float, last: float, volume: int):
        self.id = str(uuid.uuid4())
        self.symbol = symbol
        self.timestamp = datetime.datetime.utcnow()
        self.bid = bid
        self.ask = ask
        self.last = last
        self.volume = volume
        # Mistake #3: Source clock tracking
        self.source_clock = time.time_ns()

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "bid": self.bid,
            "ask": self.ask,
            "last": self.last,
            "volume": self.volume,
            "source_clock": self.source_clock
        }

class L1FeedSimulator:
    """
    Simulates L1 (Bid/Ask) data stream to avoid 'Candles-only' mistake.
    """
    def __init__(self):
        self.prices = {
            "NIFTY": 21500.0,
            "BANKNIFTY": 46000.0,
            "RELIANCE": 2450.0,
            "HDFCBANK": 1650.0
        }
        self.volatility = {
            "NIFTY": 5.0,
            "BANKNIFTY": 15.0,
            "RELIANCE": 2.0,
            "HDFCBANK": 1.5
        }

    def generate_tick(self, symbol: str) -> Tick:
        base_price = self.prices.get(symbol, 100.0)
        vol = self.volatility.get(symbol, 1.0)
        
        # Random walk
        change = random.gauss(0, vol * 0.1)
        self.prices[symbol] += change
        current_price = self.prices[symbol]
        
        # Simulate Spread (Bid < Last < Ask)
        spread = current_price * 0.0005 # 5 bps spread
        bid = current_price - (spread / 2)
        ask = current_price + (spread / 2)
        
        # Add noise to bid/ask
        bid -= random.random() * (spread * 0.1)
        ask += random.random() * (spread * 0.1)
        
        return Tick(
            symbol=symbol,
            bid=round(bid, 2),
            ask=round(ask, 2),
            last=round(current_price, 2),
            volume=random.randint(1, 100)
        )

    def stream(self) -> Generator[Tick, None, None]:
        """Yields ticks indefinitely"""
        while True:
            for symbol in self.prices.keys():
                yield self.generate_tick(symbol)
            time.sleep(0.1) # Simulate 100ms latency

# Usage Example
if __name__ == "__main__":
    feed = L1FeedSimulator()
    print("Starting L1 Feed Stream (Press Ctrl+C to stop)...")
    try:
        for i, tick in enumerate(feed.stream()):
            print(f"[{tick.timestamp}] {tick.symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Last: {tick.last}")
            if i >= 5: break # Stop after 5 ticks for demo
    except KeyboardInterrupt:
        print("Stopped.")
