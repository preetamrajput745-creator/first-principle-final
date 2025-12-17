"""
Raw Data Integrity Checker - Mistake #2 Compliance
Verifies that raw data is immutable and uncorrupted.
"""

import sys
import os
from pathlib import Path

workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.raw_data_store import RawDataStore

def check_all_files():
    """
    Scan all raw data files and verify integrity.
    """
    store = RawDataStore()
    raw_dir = store.base_path
    
    if not raw_dir.exists():
        print("No raw data directory found!")
        return
    
    print("=" * 60)
    print("RAW DATA INTEGRITY CHECK (Mistake #2 Compliance)")
    print("=" * 60)
    
    total_files = 0
    total_ticks = 0
    corrupted_files = 0
    
    # Find all .jsonl files
    for jsonl_file in raw_dir.rglob("*.jsonl"):
        total_files += 1
        
        # Parse symbol and date from path
        parts = jsonl_file.parts
        symbol = jsonl_file.stem
        date = f"{parts[-4]}-{parts[-3]}-{parts[-2]}"
        
        report = store.get_integrity_report(symbol, date)
        
        print(f"\nFile: {jsonl_file.name}")
        print(f"Date: {date}")
        print(f"Total Ticks: {report['total_lines']}")
        print(f"Valid: {report['valid_lines']}")
        print(f"Corrupted: {report['corrupt_lines']}")
        print(f"Status: {report['integrity']}")
        
        total_ticks += report['total_lines']
        
        if report['integrity'] != "OK":
            corrupted_files += 1
    
    print("\n" + "=" * 60)
    print(f"SUMMARY:")
    print(f"Total Files: {total_files}")
    print(f"Total Ticks: {total_ticks}")
    print(f"Corrupted Files: {corrupted_files}")
    
    if corrupted_files == 0:
        print("Status: ALL DATA VERIFIED - IMMUTABLE STORAGE WORKING")
    else:
        print(f"Status: WARNING - {corrupted_files} files corrupted!")
    
    print("=" * 60)

if __name__ == "__main__":
    check_all_files()
