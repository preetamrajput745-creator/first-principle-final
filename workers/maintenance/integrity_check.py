import boto3
import sys
import os
import time
import hashlib
from datetime import datetime, timedelta



# Add root directory
# (Going up two levels from workers/maintenance -> project root)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))) # Add workers dir

from config import settings
from event_bus import event_bus


from common.database import get_db
from common.models import Signal

class IntegrityChecker:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY
        )
    
    def calculate_checksum(self, bucket, key):
        try:
            # For MinIO, we can get ETag which is usually MD5
            # We can also read object and calc sha256
            obj = self.s3.get_object(Bucket=bucket, Key=key)
            data = obj['Body'].read()
            return hashlib.md5(data).hexdigest()
        except Exception as e:
            print(f"Error reading {key}: {e}")
            return None

    def verify_signal_snapshots(self):
        """
        Mistake #11 & Acceptance Criteria:
        Verify that every Signal has a corresponding L2 snapshot in S3.
        If missing -> Alert and Flag Signal.
        """
        print("Starting Signal Snapshot Verification...")
        issues = 0
        from sqlalchemy import update
        
        with next(get_db()) as db:
            # Check signals from last 24 hours (Hot storage window)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            signals = db.query(Signal).filter(
                Signal.timestamp >= cutoff,
                Signal.l2_snapshot_path.isnot(None)
            ).all()

            for signal in signals:
                # l2_snapshot_path might be full s3:// path or relative key
                # Example stored: s3://bucket/features/...
                # We need the key.
                path = signal.l2_snapshot_path
                if path.startswith("s3://"):
                    # Parse bucket/key
                    # s3://my-bucket/key/to/file
                    parts = path.replace("s3://", "").split("/", 1)
                    if len(parts) == 2:
                        bucket, key = parts
                    else:
                        print(f"Skipping malformed path: {path}")
                        continue
                else:
                    # Assume relative key in features bucket
                    bucket = settings.S3_BUCKET_FEATURES
                    key = path
                
                try:
                    self.s3.head_object(Bucket=bucket, Key=key)
                except Exception as e:
                    # Missing!
                    print(f"CRITICAL: Snapshot MISSING for Signal {signal.id} at {path}")
                    issues += 1
                    
                    # 1. Alert (Event Bus)
                    event_bus.publish("system.alert", {
                        "level": "CRITICAL",
                        "type": "MISSING_SNAPSHOT",
                        "signal_id": str(signal.id),
                        "message": f"L2 Snapshot missing for signal {signal.id}"
                    })
                    
                    # 2. Flag Signal (Update DB)
                    # We avoid 'rejected' to keep history, but flag it.
                    # Maybe append to status or new field. 
                    # For criteria: "Flag signal as incomplete"
                    signal.status = "INCOMPLETE_DATA"
                    db.add(signal)
            
            if issues > 0:
                db.commit()
                print(f"Flagged {issues} signals as INCOMPLETE_DATA.")
            else:
                print("All signal snapshots verified.")

    def run_check(self):
        print(f"Starting Integrity Check at {datetime.utcnow()}")
        
        # 1. Check Signal Snapshots (New)
        self.verify_signal_snapshots()
        
        # 2. Check Ticks Bucket (Existing)
        paginator = self.s3.get_paginator('list_objects_v2')
        try:
            pages = paginator.paginate(Bucket=settings.S3_BUCKET_TICKS, Prefix='ticks/')
            
            file_count = 0
            issues = 0
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        file_count += 1
                        key = obj['Key']
                        
                        # Verify if versioning is enabled (by checking if we can get versions)
                        # For MVP, we assume setup_minio run. 
                        # We can check if multiple versions exist for the same key (Overwrite detected)
                        versions = self.s3.list_object_versions(Bucket=settings.S3_BUCKET_TICKS, Prefix=key)
                        
                        if 'Versions' in versions:
                            # If more than 1 version (or 1 version + delete marker), it means it was overwritten/deleted
                            # Note: list_object_versions returns all versions. 
                            # Ideally, there should be only 1 version for immutable data.
                            v_list = versions['Versions']
                            if len(v_list) > 1:
                                print(f"⚠️ INTEGRITY WARNING: Multiple versions found for {key}. Potential overwrite!")
                                issues += 1
                                event_bus.publish("system.alert", {
                                    "level": "CRITICAL",
                                    "message": f"Integrity Violation: Multiple versions for {key}",
                                    "timestamp": datetime.utcnow().isoformat()
                                })
            
            print(f"Integrity Check Complete. Scanned {file_count} tick files. Found {issues} overwrite issues.")
            
            # Publish Report
            event_bus.publish("system.integrity_report", {
                "scanned": file_count,
                "issues": issues,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            print(f"Warning: Could not check tick bucket: {e}")

if __name__ == "__main__":
    checker = IntegrityChecker()
    checker.run_check()
