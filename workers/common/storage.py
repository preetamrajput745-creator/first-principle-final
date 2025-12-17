import os
import boto3
from botocore.exceptions import ClientError
import json
from datetime import datetime

class Storage:
    def __init__(self):
        self.endpoint_url = os.getenv("S3_ENDPOINT", "http://localhost:9000")
        self.access_key = os.getenv("MINIO_ROOT_USER", "admin")
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", "password")
        self.bucket_name = os.getenv("S3_BUCKET", "data")
        
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )
        
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                self.s3.create_bucket(Bucket=self.bucket_name)
            except ClientError as e:
                print(f"Could not create bucket: {e}")

    def upload_tick(self, symbol, data):
        """
        Uploads tick data to S3.
        Path: ticks/<YYYY>/<MM>/<DD>/<symbol>.parquet (or json for now)
        """
        now = datetime.now()
        path = f"ticks/{now.year}/{now.month:02d}/{now.day:02d}/{symbol}_{now.strftime('%H%M%S')}.json"
        
        try:
            # Mistake #2: Strict Immutability Check
            try:
                self.s3.head_object(Bucket=self.bucket_name, Key=path)
                msg = f"CRITICAL: Overwrite attempt blocked on {path}"
                print(msg)
                with open("security_audit.log", "a") as f:
                    f.write(f"{datetime.utcnow()} {msg}\n")
                raise FileExistsError(msg)
            except ClientError as e:
                if e.response['Error']['Code'] != "404":
                    raise

            body_bytes = json.dumps(data).encode('utf-8')
            
            # Mistake #8: Checksum Automation
            import hashlib
            checksum = hashlib.sha256(body_bytes).hexdigest()
            
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=body_bytes,
                ContentType='application/json'
            )
            
            # Log for reconciliation
            with open("ingest.log", "a") as f:
                f.write(f"{datetime.utcnow().isoformat()},{path},{checksum}\n")
                
            return path
        except ClientError as e:
            print(f"Error uploading tick: {e}")
            return None

    def upload_snapshot(self, symbol, data):
        """
        Uploads L2 snapshot.
        Path: book_snapshots/<YYYY>/<MM>/<DD>/<symbol>/<hhmmss>.ndjson
        """
        now = datetime.now()
        path = f"book_snapshots/{now.year}/{now.month:02d}/{now.day:02d}/{symbol}/{now.strftime('%H%M%S')}.json"
        
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=json.dumps(data).encode('utf-8'),
                ContentType='application/json'
            )
            return path
        except ClientError as e:
            print(f"Error uploading snapshot: {e}")
            return None
