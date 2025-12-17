
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
import os

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage import Storage
from botocore.exceptions import ClientError

class TestImmutability(unittest.TestCase):
    @patch('storage.boto3')
    def setUp(self, mock_boto):
        # Mock S3 Client
        self.mock_s3 = MagicMock()
        mock_boto.client.return_value = self.mock_s3
        self.storage = Storage() # This calls boto3.client which we mocked
        self.storage.s3 = self.mock_s3 # Ensure reference
        
        self.symbol = "TEST_INTEGRITY"
        self.timestamp = datetime(2025, 1, 1, 10, 0, 0)

    def test_save_success(self):
        print("\n[Test] Immutability: Save New File")
        
        # Mock check_exists -> False (Raise 404)
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        self.mock_s3.head_object.side_effect = ClientError(error_response, 'head_object')
        
        tick_data = {"price": 100, "volume": 10}
        result = self.storage.save_raw_tick(self.symbol, tick_data, self.timestamp)
        
        self.assertIn("s3://", result)
        self.assertTrue(self.mock_s3.put_object.called)
        print("PASS: New file saved successfully.")

    def test_overwrite_protection(self):
        print("\n[Test] Immutability: Block Overwrite")
        
        # Mock check_exists -> True (Return metadata)
        self.mock_s3.head_object.side_effect = None # Success
        self.mock_s3.head_object.return_value = {'ContentLength': 123}
        
        tick_data = {"price": 100, "volume": 10}
        
        with self.assertRaises(Exception) as cm:
            self.storage.save_raw_tick(self.symbol, tick_data, self.timestamp)
            
        self.assertIn("Integrity Error", str(cm.exception))
        self.assertIn("Overwrite denied", str(cm.exception))
        
        # Ensure put_object was NOT called
        self.mock_s3.put_object.assert_not_called()
        
        print("PASS: Overwrite blocked with Integrity Error.")

if __name__ == '__main__':
    unittest.main()
