"""
Raw Data Storage Module - Mistake #2 Compliance
Immutable, append-only storage for all market ticks.
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

class RawDataStore:
    """
    Append-only storage for raw market ticks.
    
    Features:
    - Immutable writes (append-only)
    - Integrity checksums
    - Daily file rotation
    - S3-ready structure
    """
    
    def __init__(self, base_path="raw_data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
    def _get_file_path(self, symbol: str, date: str = None) -> Path:
        """
        Get file path for a symbol and date.
        Structure: raw_data/{YYYY}/{MM}/{DD}/{SYMBOL}.jsonl
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        year, month, day = date.split("-")
        symbol_dir = self.base_path / year / month / day
        symbol_dir.mkdir(parents=True, exist_ok=True)
        
        return symbol_dir / f"{symbol}.jsonl"
    
    def append_tick(self, tick_data: dict):
        """
        Append a tick to raw storage.
        
        CRITICAL: This is APPEND-ONLY. No overwrites allowed.
        Each line is a JSON object with checksum.
        """
        symbol = tick_data.get("symbol")
        if not symbol:
            raise ValueError("Tick data must have 'symbol' field")
        
        file_path = self._get_file_path(symbol)
        
        # Add metadata
        tick_data["_stored_at"] = datetime.utcnow().isoformat()
        
        # Calculate checksum
        tick_json = json.dumps(tick_data, sort_keys=True)
        checksum = hashlib.sha256(tick_json.encode()).hexdigest()
        
        # Create record with checksum
        record = {
            "checksum": checksum,
            "data": tick_data
        }
        
        # Append-only write (mode='a')
        with open(file_path, 'a') as f:
            f.write(json.dumps(record) + "\n")
    
    def read_ticks(self, symbol: str, date: str = None):
        """
        Read ticks for a symbol and date.
        Verifies checksums on read.
        """
        file_path = self._get_file_path(symbol, date)
        
        if not file_path.exists():
            return []
        
        ticks = []
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line.strip())
                    
                    # Verify checksum
                    tick_json = json.dumps(record["data"], sort_keys=True)
                    expected_checksum = hashlib.sha256(tick_json.encode()).hexdigest()
                    
                    if record["checksum"] != expected_checksum:
                        print(f"WARNING: Checksum mismatch at line {line_num}")
                        continue
                    
                    ticks.append(record["data"])
                except json.JSONDecodeError:
                    print(f"WARNING: Invalid JSON at line {line_num}")
                    continue
        
        return ticks
    
    def get_integrity_report(self, symbol: str, date: str = None):
        """
        Generate integrity report for a symbol/date.
        """
        file_path = self._get_file_path(symbol, date)
        
        if not file_path.exists():
            return {"error": "File not found"}
        
        total_lines = 0
        valid_lines = 0
        corrupt_lines = 0
        
        with open(file_path, 'r') as f:
            for line in f:
                total_lines += 1
                try:
                    record = json.loads(line.strip())
                    tick_json = json.dumps(record["data"], sort_keys=True)
                    expected_checksum = hashlib.sha256(tick_json.encode()).hexdigest()
                    
                    if record["checksum"] == expected_checksum:
                        valid_lines += 1
                    else:
                        corrupt_lines += 1
                except:
                    corrupt_lines += 1
        
        return {
            "file": str(file_path),
            "total_lines": total_lines,
            "valid_lines": valid_lines,
            "corrupt_lines": corrupt_lines,
            "integrity": "OK" if corrupt_lines == 0 else "CORRUPTED"
        }

if __name__ == "__main__":
    # Test
    store = RawDataStore()
    
    test_tick = {
        "symbol": "NIFTY",
        "bid": 21500.0,
        "ask": 21500.5,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    store.append_tick(test_tick)
    print("Test tick appended successfully")
    
    # Verify
    ticks = store.read_ticks("NIFTY")
    print(f"Read {len(ticks)} ticks from storage")
    
    # Integrity check
    report = store.get_integrity_report("NIFTY")
    print(f"Integrity Report: {report}")
