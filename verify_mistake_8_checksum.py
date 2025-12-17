
import unittest
import os
import json
import hashlib
from datetime import datetime
from workers.common.storage import Storage

# Mock S3 for local test if needed, or rely on Storage's handling
# We assume Storage uses LocalStack or Minio or Mock if env var set.
# For this verify script, we rely on the implementation in storage.py.

from unittest.mock import MagicMock, patch

class TestChecksum(unittest.TestCase):
    def setUp(self):
        if os.path.exists("ingest.log"):
            os.remove("ingest.log")

    @patch('workers.common.storage.boto3')
    def test_checksum_logging(self, mock_boto3):
        # Mock S3 Client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Ensure _ensure_bucket doesn't fail
        mock_client.head_bucket.return_value = {} 
        
        # Ensure head_object (overwrite check) throws 404 (Obj doesn't exist)
        from botocore.exceptions import ClientError
        mock_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}}, 
            'HeadObject'
        )

        storage = Storage()
        
        # Data
        data = {"price": 100.0, "vol": 50}
        body_bytes = json.dumps(data).encode('utf-8')
        expected_checksum = hashlib.sha256(body_bytes).hexdigest()
        
        # Upload
        print("Uploading tick data...")
        path = storage.upload_tick("TEST_CHK", data)
        print(f"Uploaded to {path}")
        
        # Verify ingest.log
        print("Verifying ingest.log...")
        found = False
        with open("ingest.log", "r") as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    log_path = parts[1]
                    log_checksum = parts[2]
                    
                    if log_path == path:
                        print(f"Found log entry: {line.strip()}")
                        self.assertEqual(log_checksum, expected_checksum)
                        found = True
                        break
        
        self.assertTrue(found, "Checksum entry not found in ingest.log")
        print("PASS: Checksum verification successful.")

if __name__ == "__main__":
    # Create failure trigger if file fails
    try:
        unittest.main()
    except Exception as e:
        print(f"FAIL: {e}")
        exit(1)
