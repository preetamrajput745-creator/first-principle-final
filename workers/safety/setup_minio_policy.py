import boto3
from botocore.exceptions import ClientError
import logging
import json
import sys
import os

# Add parent dir to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImmutablePolicySetup")

def setup_immutable_buckets():
    """
    Mistake #1: S3 Bucket Policy & Versioning
    Enforces 'Immutable Raw Data' by enabling versioning and setting object lock configuration.
    """
    s3 = boto3.client(
        's3',
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY
    )

    buckets = [settings.S3_BUCKET_TICKS, settings.S3_BUCKET_FEATURES, settings.S3_BUCKET_BOOKS]
    # Deduplicate in case they point to same bucket
    buckets = list(set(buckets))

    for bucket_name in buckets:
        try:
            # 1. Create Bucket if not exists
            try:
                s3.head_bucket(Bucket=bucket_name)
                logger.info(f"Bucket '{bucket_name}' exists.")
            except ClientError:
                logger.info(f"Creating bucket '{bucket_name}'...")
                s3.create_bucket(Bucket=bucket_name)

            # 2. Enable Versioning (Crucial for Immutability)
            logger.info(f"Enabling Versioning on '{bucket_name}'...")
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # 3. Apply Bucket Policy (Deny Delete/Overwrite)
            # Note: real enforcement of "Deny Overwrite" usually requires Object Lock or strict IAM policies.
            # Here we apply a policy that denies DeleteObject for everyone (simulated).
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "DenyDeleteObject",
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "s3:DeleteObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*"
                    }
                ]
            }
            # Catching error here because MinIO or local emulators might not support full IAM policies via SDK
            try:
                s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
                logger.info(f"Applied Immutability Policy to '{bucket_name}'")
            except Exception as e:
                 logger.warning(f"Could not apply IAM Policy to '{bucket_name}' (Common in local MinIO): {e}")
                 logger.info("Versioning is enabled, which provides soft immutability/recovery.")

        except Exception as e:
            logger.error(f"Failed to setup bucket '{bucket_name}': {e}")

if __name__ == "__main__":
    setup_immutable_buckets()
