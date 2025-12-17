"""
Verification: Mistake #2 - S3 Overwrite Protection (Manual Verification Step)
Verifies:
1. Uploading a file to specific S3 path.
2. Attempting to upload to the SAME path (collision).
3. Verifying the operation is BLOCKED (FileExistsError).
4. Verifying the event is logged to security_audit.log.
"""

import sys
import os
import io
import contextlib
import time
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add root to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from common.storage import Storage

def verify_s3_overwrite():
    print("TEST: S3 Overwrite Protection (Manual Verification Automation)")
    print("=" * 60)
    
    # 1. Setup Mock for S3 (We don't want to rely on real MinIO for this logic test if possible,
    #    but Storage code tries to connect. Ideally we check the LOGIC of blocking.)
    #    The Storage class connects in __init__. We might need to mock boto3.client.
    
    with patch('boto3.client') as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        
        # Instantiate Storage (will use mock s3)
        store = Storage()
        
        # Mock behavior: 
        # First head_object raises 404 (Not Found) -> Allow Upload
        # Second head_object returns success (Found) -> Block Upload
        
        # Setup the "Existing File" scenario checking
        # When upload_tick is called, it calls head_object first.
        
        # Scenario 1: First Upload (File does not exist)
        print("1. Attempting First Upload (New File)...")
        from botocore.exceptions import ClientError
        
        # head_object raises 404
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        mock_s3.head_object.side_effect = ClientError(error_response, 'HeadObject')
        
        # Freeze time to ensure same path
        fixed_time = datetime(2025, 12, 25, 10, 0, 0)
        
        with patch('common.storage.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.utcnow.return_value = fixed_time
            
            # Call upload
            store.upload_tick("TEST_SYM", {"price": 100})
            
            # Verify put_object was called
            if mock_s3.put_object.called:
                print("   SUCCESS: First upload proceeded.")
            else:
                print("   FAILURE: First upload was not attempted.")
                sys.exit(1)
                
        # Scenario 2: Second Upload (File EXISTS)
        print("\n2. Attempting Overwrite (Same Path)...")
        
        # head_object returns None (Success, file exists)
        mock_s3.head_object.side_effect = None 
        
        # Clean audit log before test
        if os.path.exists("security_audit.log"):
            os.remove("security_audit.log")
            
        with patch('common.storage.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.utcnow.return_value = fixed_time
            
            try:
                store.upload_tick("TEST_SYM", {"price": 200})
                print("   FAILURE: Overwrite was ALLOWED! (Should have raised FileExistsError)")
                sys.exit(1)
            except FileExistsError as e:
                print(f"   SUCCESS: Overwrite BLOCKED. Caught expected error: {e}")
                
        # 3. Check Audit Log
        print("\n3. Verifying Audit Log...")
        if os.path.exists("security_audit.log"):
            with open("security_audit.log", "r") as f:
                content = f.read()
                print(f"   [Log Content]: {content.strip()}")
                if "CRITICAL: Overwrite attempt blocked" in content:
                    print("   SUCCESS: Security event logged.")
                else:
                    print("   FAILURE: Log file exists but missing specific alert.")
                    sys.exit(1)
        else:
            print("   FAILURE: security_audit.log was not created.")
            sys.exit(1)

    print("\nVERIFICATION COMPLETE: S3 Overwrite Protection Verified.")

if __name__ == "__main__":
    verify_s3_overwrite()
