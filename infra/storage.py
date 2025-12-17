import boto3
import json
import os
import sys
from datetime import datetime
from botocore.exceptions import ClientError
from config import settings

class S3Storage:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        self._ensure_buckets()

    def _ensure_buckets(self):
        """Ensure required buckets exist."""
        buckets = [settings.S3_BUCKET_TICKS, settings.S3_BUCKET_FEATURES, settings.S3_BUCKET_BOOKS]
        try:
            existing = [b['Name'] for b in self.s3_client.list_buckets().get('Buckets', [])]
            for b in buckets:
                if b not in existing:
                    self.s3_client.create_bucket(Bucket=b)
                    print(f"[S3] Created bucket: {b}")
        except Exception as e:
            print(f"[S3] Buckets check failed (is MinIO running?): {e}")

    def save_raw_ticks(self, symbol: str, ticks_data: list):
        """
        Save raw ticks to S3/MinIO.
        Path: s3://data/ticks/<symbol>/YYYY/MM/DD/<symbol>_<HHMMSS>.json
        Append-only by timestamp.
        """
        now = datetime.utcnow()
        key = f"ticks/{symbol}/{now.year}/{now.month:02d}/{now.day:02d}/{symbol}_{now.strftime('%H%M%S')}.json"
        
        try:
            # 1. Immutability Check (Mistake #2)
            try:
                self.s3_client.head_object(Bucket=settings.S3_BUCKET_TICKS, Key=key)
                # If this succeeds, object exists -> BLOCK OVERWRITE
                msg = f"SECURITY ALERT: Attempt to overwrite immutable raw tick: {key}"
                print(f"[IMMUTABILITY] {msg}")
                # Log to dedicated security log (simulated)
                with open("security_audit.log", "a") as log:
                    log.write(f"{datetime.utcnow().isoformat()} - {msg}\n")
                raise FileExistsError(msg)
            except ClientError as e:
                if e.response['Error']['Code'] != "404":
                    raise # Real error
                # 404 is good, object doesn't exist. Proceed.

            self.s3_client.put_object(
                Bucket=settings.S3_BUCKET_TICKS,
                Key=key,
                Body=json.dumps(ticks_data)
            )
            return f"s3://{settings.S3_BUCKET_TICKS}/{key}"
        except Exception as e:
            print(f"[S3] Save error: {e}")
            return None

    def save_feature_snapshot(self, symbol: str, bar_time: datetime, snapshot: dict):
        """
        Save feature snapshot.
        Path: s3://data/features/<symbol>/YYYY/MM/DD/<bar_time>.json
        """
        key = f"features/{symbol}/{bar_time.year}/{bar_time.month:02d}/{bar_time.day:02d}/{bar_time.isoformat()}.json"
        
        try:
            self.s3_client.put_object(
                Bucket=settings.S3_BUCKET_FEATURES,
                Key=key,
                Body=json.dumps(snapshot)
            )
            return f"s3://{settings.S3_BUCKET_FEATURES}/{key}"
        except Exception as e:
            print(f"[S3] Save snapshot error: {e}")
            return None

storage = S3Storage()
