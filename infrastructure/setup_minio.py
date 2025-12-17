"""
MinIO/S3 Setup Script - Mistake #2 Compliance
Configures S3 bucket with Object Locking (WORM) and Versioning.
"""

import boto3
import json

def setup_immutable_bucket(bucket_name="data"):
    """
    Sets up an S3 bucket with strict immutability policies.
    """
    # Connect to MinIO/S3 (Mocked for this script)
    s3 = boto3.client(
        's3',
        endpoint_url='http://localhost:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin'
    )
    
    try:
        # 1. Create Bucket with Object Lock Enabled
        s3.create_bucket(
            Bucket=bucket_name,
            ObjectLockEnabledForBucket=True  # CRITICAL for WORM
        )
        print(f"Bucket {bucket_name} created with Object Lock.")
        
        # 2. Enable Versioning
        s3.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print("Versioning enabled.")
        
        # 3. Set Default Retention Policy (Governance Mode)
        s3.put_object_lock_configuration(
            Bucket=bucket_name,
            ObjectLockConfiguration={
                'ObjectLockEnabled': 'Enabled',
                'Rule': {
                    'DefaultRetention': {
                        'Mode': 'GOVERNANCE',
                        'Days': 365 # 1 Year Retention
                    }
                }
            }
        )
        print("Retention policy set to 1 year.")
        
        # 4. Set Bucket Policy (Deny Delete/Overwrite)
        deny_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DenyDeleteRawData",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        s3.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(deny_policy)
        )
        print("Deny-Delete Policy applied.")
        
    except Exception as e:
        print(f"Setup failed (Expected if no MinIO running): {e}")

if __name__ == "__main__":
    setup_immutable_bucket()
