"""
Verification: Retention & Archival (Control #10)
Verifies:
1. Ticks moving to archive/ticks/
2. Snapshots moving to archive/snapshots/ + Compression
"""

import sys
import os
import io
import gzip
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Path setup
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from maintenance.retention_manager import RetentionManager

# Mock Data Store
mock_s3_store = {}

# Mock S3 Client Methods
def mock_put_object(Bucket, Key, Body, **kwargs):
    # If body is bytes, store as is. If str, encode? 
    # Usually boto3 receives bytes or file-like.
    content = Body
    if hasattr(Body, 'read'):
        content = Body.read()
    mock_s3_store[Key] = content
    
def mock_get_object(Bucket, Key, **kwargs):
    if Key in mock_s3_store:
        return {'Body': io.BytesIO(mock_s3_store[Key])}
    raise Exception("NoSuchKey") # Simplified

def mock_delete_object(Bucket, Key, **kwargs):
    if Key in mock_s3_store:
        del mock_s3_store[Key]

def mock_head_object(Bucket, Key, **kwargs):
    if Key not in mock_s3_store:
        raise Exception("404")
    return {}

class MockPaginator:
    def paginate(self, Bucket, Prefix, **kwargs):
        # find matching keys
        contents = []
        for k in mock_s3_store:
            if k.startswith(Prefix):
                # Ensure we simulate "old" files for retention trigger
                contents.append({
                    'Key': k,
                    'LastModified': datetime.utcnow() - timedelta(days=1000) # Very old
                })
        if contents:
            return iter([{'Contents': contents}])
        return iter([])

def verify_archival():
    print("TEST: Retention & Archival Policies (Mocked S3)")
    print("=" * 60)
    
    with patch('boto3.client') as mock_client_ctor:
        mock_s3 = MagicMock()
        mock_client_ctor.return_value = mock_s3
        
        # Setup Mock Methods
        mock_s3.put_object.side_effect = mock_put_object
        mock_s3.get_object.side_effect = mock_get_object
        mock_s3.delete_object.side_effect = mock_delete_object
        mock_s3.head_object.side_effect = mock_head_object
        
        # Setup Paginator
        mock_paginator = MockPaginator()
        mock_s3.get_paginator.return_value = mock_paginator
        
        # 1. Setup Data
        tick_key = "ticks/2023/10/24/TEST_TICK.json"
        snap_key = "book_snapshots/2023/10/24/TEST_SNAP/120000.json"
        
        mock_s3_store[tick_key] = b'{"price": 100}'
        mock_s3_store[snap_key] = b'{"bids": []}'
        
        print(f"1. Setup: Created mock files: {list(mock_s3_store.keys())}")
        
        # 2. Run Manager
        rm = RetentionManager()
        # Force overwrite days_override to ensure our 1000-day old mock files are picked up
        # The logic in RetentionManager uses 'days_override' for cutoff calculation.
        # Logic: cutoff = now - days_override. 
        # If days_override=-1 -> cutoff = tomorrow. File date (old) < tomorrow -> True.
        stats = rm.archive_cold_data(days_override=-1) 
        
        print(f"   Stats: {stats}")
        
        # 3. Verify
        # Tick should move to archive/ticks/...
        if tick_key in mock_s3_store:
            print("   FAILURE: Tick file not deleted from source.")
            sys.exit(1)
        
        archive_tick = "archive/" + tick_key
        if archive_tick in mock_s3_store:
            print("   SUCCESS: Tick moved to archive.")
        else:
            print("   FAILURE: Tick not found in archive.")
            sys.exit(1)
            
        # Snapshot should move to archive/snapshots/... AND be .gz
        if snap_key in mock_s3_store:
            print("   FAILURE: Snapshot file not deleted from source.")
            sys.exit(1)
            
        archive_snap = snap_key.replace("book_snapshots", "archive/snapshots") + ".gz"
        if archive_snap in mock_s3_store:
            print("   SUCCESS: Snapshot moved to archive (compressed path).")
            # Check compression
            body = mock_s3_store[archive_snap]
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(body), mode='rb') as f:
                    content = f.read() 
                    if b"bids" in content:
                        print("   SUCCESS: Content decompressed correctly.")
            except:
                print("   FAILURE: Content is not valid gzip.")
                sys.exit(1)
        else:
            print(f"   FAILURE: Snapshot not found in archive: {archive_snap}")
            sys.exit(1)

    print("\nVERIFICATION COMPLETE: Archival logic functional.")

if __name__ == "__main__":
    verify_archival()
