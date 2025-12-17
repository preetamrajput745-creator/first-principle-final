
import unittest
import sys
import os
import uuid
import time
from datetime import datetime

# Path setup
sys.path.append(os.path.join(os.getcwd(), 'workers'))
sys.path.append(os.getcwd())

from monitoring.monitor import Monitor

class TestMissingSnapshot(unittest.TestCase):
    
    def test_missing_snapshot_alert(self):
        print("\nVERIFICATION: Mistake #9 - Missing L2 Snapshot Alert")
        print("="*60)
        
        # Capture stdout
        from io import StringIO
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            mon = Monitor()
            
            # Case 1: Signal WITH Snapshot (Fake file)
            fake_path = "temp_snapshot.json"
            with open(fake_path, "w") as f: f.write("{}")
            
            sig_good = {
                "symbol": "TEST_GOOD",
                "timestamp": datetime.utcnow().isoformat(),
                "l2_snapshot_path": fake_path
            }
            mon.process_signal(sig_good)
            
            # Case 2: Signal WITHOUT Path
            sig_no_path = {
                "symbol": "TEST_NO_PATH",
                "timestamp": datetime.utcnow().isoformat(),
                "l2_snapshot_path": None
            }
            mon.process_signal(sig_no_path)
            
            # Case 3: Signal WITH Path but File Missing
            sig_missing_file = {
                "symbol": "TEST_MISSING_FILE",
                "timestamp": datetime.utcnow().isoformat(),
                "l2_snapshot_path": "non_existent_file.json"
            }
            mon.process_signal(sig_missing_file)
            
            # Cleanup
            if os.path.exists(fake_path):
                os.remove(fake_path)
                
        finally:
            sys.stdout = sys.__stdout__
            
        output = captured_output.getvalue()
        print(output)
        
        # Verify Alerts
        # Good signal should be silent (or just latency log)
        
        # No Path Alert
        if "ALERT: Signal TEST_NO_PATH has NO L2 Snapshot Path!" in output:
             print("SUCCESS: Detected missing path.")
        else:
             print("FAILURE: Did not detect missing path.")
             sys.exit(1)
             
        # Missing File Alert
        if "ALERT: Missing L2 Snapshot File: non_existent_file.json" in output:
             print("SUCCESS: Detected missing file on disk.")
        else:
             print("FAILURE: Did not detect missing file on disk.")
             sys.exit(1)

if __name__ == "__main__":
    unittest.main()
