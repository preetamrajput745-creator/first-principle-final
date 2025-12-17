"""
Retention & Archival Manager
Compliance:
1. Raw Ticks: Hot (1 yr) -> Cold Archive (3+ yrs)
2. L2 Snapshots: Hot (90 days) -> Compressed Archive
3. Signals/Backtests: Index retention for 3+ years.
"""

import os
import sys
import boto3
import json
import time
from datetime import datetime, timedelta
import gzip
import io

# Path setup
workers_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, workers_path)

from common.storage import Storage

class RetentionManager:
    def __init__(self):
        self.storage = Storage()
        self.s3 = self.storage.s3
        self.bucket = self.storage.bucket_name
        
        # Policy Configuration
        self.TICK_RETENTION_DAYS = 365
        self.SNAPSHOT_HOT_DAYS = 90
        
    def archive_cold_data(self, test_mode=False, days_override=None):
        """
        Scans for data exceeding retention usage and moves to archive.
        """
        print("RETENTION MANAGER: Starting Archival Scan...")
        
        tick_days = days_override if days_override is not None else self.TICK_RETENTION_DAYS
        snap_days = days_override if days_override is not None else self.SNAPSHOT_HOT_DAYS
        
        results = {
            "ticks_moved": 0,
            "snapshots_compressed": 0,
            "errors": 0
        }
        
        # 1. Process Raw Ticks
        results["ticks_moved"] = self._process_prefix(
            prefix="ticks/",
            archive_prefix="archive/ticks/",
            age_days=tick_days,
            compress=False
        )
        
        # 2. Process L2 Snapshots
        results["snapshots_compressed"] = self._process_prefix(
            prefix="book_snapshots/",
            archive_prefix="archive/snapshots/",
            age_days=snap_days,
            compress=True
        )
        
        print(f"RETENTION MANAGER: Complete. Stats: {results}")
        return results

    def _process_prefix(self, prefix, archive_prefix, age_days, compress=False):
        moved_count = 0
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            cutoff_time = datetime.utcnow() - timedelta(days=age_days)
            
            for page in page_iterator:
                if "Contents" not in page:
                    continue
                    
                for obj in page['Contents']:
                    key = obj['Key']
                    last_modified = obj['LastModified'].replace(tzinfo=None)
                    
                    # If older than cutoff, archive it
                    if last_modified < cutoff_time:
                        if self._archive_file(key, archive_prefix, compress):
                            moved_count += 1
                        
        except Exception as e:
            print(f"Error processing prefix {prefix}: {e}")
            
        return moved_count

    def _archive_file(self, key, archive_prefix, compress):
        """
        Moves a file to archive, optionally compressing it.
        """
        try:
            # 1. Get object
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            body = response['Body'].read()
            
            new_key = key.replace(key.split('/')[0] + '/', archive_prefix, 1)
            
            # 2. Compress if needed
            if compress and not key.endswith('.gz'):
                new_key += '.gz'
                out = io.BytesIO()
                with gzip.GzipFile(fileobj=out, mode='wb') as f:
                    f.write(body)
                body = out.getvalue()
                
            try:
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=new_key,
                    Body=body,
                    StorageClass='GLACIER' if 'archive' in archive_prefix else 'STANDARD'
                )
            except self.s3.exceptions.ClientError as e:
                # MinIO (Local) does not support GLACIER. Fallback.
                if "InvalidStorageClass" in str(e):
                    print("   [INFO] GLACIER not supported, falling back to STANDARD.")
                    self.s3.put_object(
                        Bucket=self.bucket,
                        Key=new_key,
                        Body=body,
                        StorageClass='STANDARD'
                    )
                else:
                    raise e
            
            # 4. Delete Original
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            print(f"Archived: {key} -> {new_key}")
            return True
            
        except Exception as e:
            print(f"Failed to archive {key}: {e}")
            return False

if __name__ == "__main__":
    rm = RetentionManager()
    rm.archive_cold_data(test_mode=True, days_override=0) # Run immediate for test
