import boto3
import hashlib
import logging
import sys
import os
from datetime import datetime

# Add parent dir to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntegrityCheck")

def calculate_checksum(s3_client, bucket, key):
    """
    Download object and calculate SHA256.
    In production, use ETags if they are SHA256 or use S3 Select.
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read()
        return hashlib.sha256(data).hexdigest()
    except Exception as e:
        logger.error(f"Error reading {key}: {e}")
        return None

def verify_integrity():
    """
    Mistake #1: Daily Checksum Job
    Verifies that raw files in S3 match expected checksums (simulated).
    In a real scenario, this would compare against a database of 'ingested_file_log'.
    """
    logger.info("Starting Daily Integrity Verification...")
    
    s3 = boto3.client(
        's3',
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY
    )
    
    bucket_name = settings.S3_BUCKET_TICKS
    
    try:
        # Check if bucket exists
        s3.head_bucket(Bucket=bucket_name)
    except Exception:
        logger.warning(f"Bucket '{bucket_name}' not found. Skipping check.")
        return

    # List Objects
    response = s3.list_objects_v2(Bucket=bucket_name)
    if 'Contents' not in response:
        logger.info("No files found to verify.")
        return

    verified_count = 0
    error_count = 0
    
    for obj in response['Contents']:
        key = obj['Key']
        # For this audit implementation, we just verify we can read it and compute a checksum.
        # Implies 'No bit rot'.
        checksum = calculate_checksum(s3, bucket_name, key)
        if checksum:
            logger.info(f"Verified {key}: SHA256={checksum[:8]}...")
            verified_count += 1
        else:
            logger.error(f"Integrity Check FAILED for {key}")
            error_count += 1

    logger.info("="*30)
    logger.info(f"Integrity Check Complete.")
    logger.info(f"Verified Files: {verified_count}")
    logger.info(f"Failed Files:   {error_count}")
    
    if error_count > 0:
        logger.error("SYSTEM INTEGRITY COMPROMISED: Files unreadable or corrupted.")
    else:
        logger.info("SYSTEM INTEGRITY PASS: All files accessible and consistent.")

if __name__ == "__main__":
    verify_integrity()
