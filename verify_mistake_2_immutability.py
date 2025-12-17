
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infra.storage import S3Storage
from workers.common.storage import Storage as WorkerStorage

class TestImmutableStorage(unittest.TestCase):
    
    @patch('infra.storage.boto3')
    def test_overwrite_attempt_blocked(self, mock_boto3):
        # Setup Mock
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Setup list_buckets to prevent initialization errors
        mock_client.list_buckets.return_value = {'Buckets': []}
        
        storage = S3Storage()
        
        # SCENARIO: Pre-existing object (Overwrite Attempt)
        # return a valid response (not 404) to simulate existence
        mock_client.head_object.return_value = {"ContentLength": 123}
        
        symbol = "TEST_SYM"
        data = [{"price": 100}]
        
        print("\n\n[TEST] Verifying Overwrite Block...")
        
        # Execute
        result = storage.save_raw_ticks(symbol, data)
        
        # Assertions
        head_calls = mock_client.head_object.call_count
        put_calls = mock_client.put_object.call_count
        
        print(f"   Head Calls: {head_calls} (Expected: 1)")
        print(f"   Put Calls:  {put_calls}  (Expected: 0)")
        
        if head_calls == 1 and put_calls == 0:
            print("SUCCESS: Infra Storage Blocked Overwrite.")
        else:
            self.fail(f"Infra Compliance Failed! Head={head_calls}, Put={put_calls}")

    @patch('workers.common.storage.boto3')
    def test_worker_storage_blocked(self, mock_boto3):
        print("\n[TEST-2] Verifying Worker Storage Overwrite Block...")
        
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.head_bucket.return_value = {} # pass bucket string check
        
        storage = WorkerStorage()
        
        # SCENARIO: Pre-existing object
        mock_client.head_object.return_value = {"ContentLength": 123}
        
        try:
            storage.upload_tick("SYM", {"p": 1})
        except  FileExistsError:
            pass
        except Exception as e:
            # Code catches exceptions, maybe prints?
            pass

        # Assertions
        head_calls = mock_client.head_object.call_count
        put_calls = mock_client.put_object.call_count
        
        print(f"   Head Calls: {head_calls} (Expected: 1)")
        print(f"   Put Calls:  {put_calls}  (Expected: 0)")
        
        if head_calls == 1 and put_calls == 0:
            print("SUCCESS: Worker Storage Blocked Overwrite.")
        else:
            self.fail(f"Worker Compliance Failed! Head={head_calls}, Put={put_calls}")

if __name__ == "__main__":
    unittest.main()
