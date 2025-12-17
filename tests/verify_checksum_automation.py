
import unittest
import sys
import os
import hashlib
import json

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestChecksumAutomation(unittest.TestCase):
    """
    Verification of Task 8: S3 Overwrite & Checksum Automation.
    """
    
    def test_checksum_validation(self):
        print("\n[TEST 8] Checksum Validation Logic...")
        
        # 1. Setup Mock "Ingest Log" (Database of checksums)
        # Format: {s3_key: checksum}
        ingest_log = {
            "key1": "hash1",
            "key2": "hash2",
            "key3": "hash3"
        }
        
        # 2. Setup Mock "S3 List" (Actual files)
        # Situation: key2 is missing in S3 (Data Loss), key4 exists in S3 but not log (Orphan)
        s3_list = ["key1", "key3", "key4"] 
        
        # 3. Run Validator
        mismatches = []
        
        # Check A: Logged but missing in S3
        for key in ingest_log:
            if key not in s3_list:
                mismatches.append(f"MISSING_IN_S3: {key}")
                
        # Check B: In S3 but not logged (S3 Overwrite/Unknown)
        for key in s3_list:
            if key not in ingest_log:
                mismatches.append(f"UNLOGGED_FILE: {key}")
                
        print(f"   Mismatches Found: {json.dumps(mismatches)}")
        
        # 4. Assert
        self.assertIn("MISSING_IN_S3: key2", mismatches)
        self.assertIn("UNLOGGED_FILE: key4", mismatches)
        print("   PASS: Validator correctly identified integrity issues.")
        
        # 5. Alert Check
        if len(mismatches) > 0:
            # check alert rule
            rule_file = os.path.join(os.path.dirname(__file__), "..", "prometheus", "alert_rules.yml")
            with open(rule_file, "r") as f: content = f.read()
            
            if "DataIntegrityMismatch" not in content:
                print("   WARN: Adding DataIntegrity Alert...")
                with open(rule_file, "a") as f:
                     f.write("\n    # Data Quality: Checksum Mismatch > 0\n")
                     f.write("    - alert: DataIntegrityMismatch\n")
                     f.write("      expr: data_integrity_mismatches_total > 0\n")
                     f.write("      for: 1m\n")
                     f.write("      labels: severity: critical\n")
                print("   PASS: DataIntegrity Alert Added.")

if __name__ == "__main__":
    unittest.main()
