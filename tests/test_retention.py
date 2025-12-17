
import unittest
from unittest.mock import MagicMock, call, patch
import sys
import os
from datetime import datetime, timedelta

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.maintenance.retention_manager import RetentionManager

class TestRetentionPolicy(unittest.TestCase):
    """
    TRIPLE CHECK: Mistake #10 Retention & Archival
    Verifies:
    1. Ticks moved to archive after N days.
    2. Snapshots moved & compressed after M days.
    """
    
    @patch('workers.maintenance.retention_manager.Storage')
    def setUp(self, mock_storage_cls):
        # Mock Storage Instance
        self.mock_storage_instance = mock_storage_cls.return_value
        self.mock_storage_instance.s3 = MagicMock()
        self.mock_storage_instance.bucket_name = "test-bucket"
        
        self.rm = RetentionManager()
        # Ensure our rm uses the mocked s3
        self.rm.s3 = self.mock_storage_instance.s3
        self.rm.bucket = self.mock_storage_instance.bucket_name
        
    def test_tick_archival_logic(self):
        print("\n[Test] Retention: Raw Ticks (Hot -> Cold)")
        
        test_days = 365
        cutoff = datetime.utcnow() - timedelta(days=test_days + 1)
        
        # Mock Side Effect
        def paginate_side_effect(Bucket, Prefix):
            if "ticks/" in Prefix:
                 return [{
                    'Contents': [
                        {'Key': 'ticks/BTC/old_tick.json', 'LastModified': cutoff},
                        {'Key': 'ticks/BTC/new_tick.json', 'LastModified': datetime.utcnow()}
                    ]
                 }]
            return [] 

        self.rm.s3.get_paginator.return_value.paginate.side_effect = paginate_side_effect
        self.rm.s3.get_object.return_value = {'Body': MagicMock(read=lambda: b"raw_data")}
        
        # Run
        results = self.rm.archive_cold_data(days_override=test_days)
        
        # Verify Copy/Put to new key
        # We expect a put_object call for the OLD file to "archive/ticks/..."
        put_calls = self.rm.s3.put_object.call_args_list
        self.assertEqual(len(put_calls), 1, "Should have archived exactly 1 file (the old one).")
        
        args, kwargs = put_calls[0]
        self.assertEqual(kwargs['Bucket'], "test-bucket")
        self.assertIn("archive/ticks/BTC/old_tick.json", kwargs['Key'])
        self.assertEqual(kwargs['StorageClass'], "GLACIER") # Cold Archive
        
        print("PASS: Correctly identified and moved aged ticks to Deep Archive.")

    def test_snapshot_compression_logic(self):
        print("\n[Test] Retention: L2 Snapshots (Hot -> Compressed Cold)")
        
        test_days = 90
        cutoff = datetime.utcnow() - timedelta(days=test_days + 1)
        
        def paginate_snapshot_side_effect(Bucket, Prefix):
            if "book_snapshots/" in Prefix:
                 return [{
                    'Contents': [
                       {'Key': 'book_snapshots/BTC/old_snap.json', 'LastModified': cutoff}
                    ]
                 }]
            return []

        self.rm.s3.get_paginator.return_value.paginate.side_effect = paginate_snapshot_side_effect
        self.rm.s3.get_object.return_value = {'Body': MagicMock(read=lambda: b"json_content")}
        
        # Run
        self.rm.archive_cold_data(days_override=test_days)
        
        # Verify PutObject with Compression
        put_calls = self.rm.s3.put_object.call_args_list
        
        found_snap = False
        for call_args in put_calls:
            k = call_args[1]['Key']
            if "archive/snapshots" in k and k.endswith(".gz"):
                found_snap = True
                self.assertIn("old_snap.json.gz", k)
                
        self.assertTrue(found_snap, "Should have found compressed snapshot in archive put calls.")
        print("PASS: Correctly compressed and archived aged snapshot.")

if __name__ == "__main__":
    unittest.main()
