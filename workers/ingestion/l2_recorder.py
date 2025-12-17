"""
L2 Recorder - Mistake #11 Compliance
Captures, compresses, and stores L2 (Orderbook) snapshots for debugging.
Hot retention: 90 days.
"""

import gzip
import json
import os
import random
from datetime import datetime
import uuid

class L2Recorder:
    def __init__(self, base_dir="data/snapshots"):
        # Use absolute path relative to project root (2 levels up from workers/ingestion)
        # But here __file__ is workers/ingestion/l2_recorder.py
        # So root is ../../
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.base_dir = os.path.join(root, base_dir)
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def generate_simulated_l2(self, mid_price: float, depth: int = 5) -> dict:
        """
        Simulates L2 depth for development.
        In PROD, this comes from the Exchange Websocket.
        """
        bids = []
        asks = []
        
        # Determine tick size
        tick_size = 0.05
        
        # Bids (Lower than mid)
        current_bid = mid_price - tick_size
        for _ in range(depth):
            qty = random.randint(50, 500)
            bids.append({"price": round(current_bid, 2), "qty": qty})
            current_bid -= tick_size * random.randint(1, 3)
            
        # Asks (Higher than mid)
        current_ask = mid_price + tick_size
        for _ in range(depth):
            qty = random.randint(50, 500)
            asks.append({"price": round(current_ask, 2), "qty": qty})
            current_ask += tick_size * random.randint(1, 3)
            
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "mid_price": mid_price,
            "bids": bids,
            "asks": asks
        }

    def store_snapshot(self, l2_data: dict, signal_id: str) -> str:
        """
        Compresses and saves L2 data. Returns relative path.
        Structure: data/snapshots/YYYY/MM/DD/signal_id.json.gz
        """
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        full_dir = os.path.join(self.base_dir, date_path)
        
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
            
        filename = f"{signal_id}.json.gz"
        full_path = os.path.join(full_dir, filename)
        
        # Serialize and Compress
        json_bytes = json.dumps(l2_data).encode('utf-8')
        with gzip.open(full_path, 'wb') as f:
            f.write(json_bytes)
            
        # Return path relative to base (or full path? keeping full path simplifies dev)
        return full_path

    def load_snapshot(self, path: str) -> dict:
        """
        Loads and decompresses a snapshot.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Snapshot not found: {path}")
            
        with gzip.open(path, 'rb') as f:
            content = f.read()
            return json.loads(content.decode('utf-8'))

if __name__ == "__main__":
    # Test
    rec = L2Recorder()
    data = rec.generate_simulated_l2(21500.0)
    sig_id = str(uuid.uuid4())
    path = rec.store_snapshot(data, sig_id)
    print(f"Stored at: {path}")
    
    loaded = rec.load_snapshot(path)
    print(f"Loaded Bids: {loaded['bids'][0]}")
