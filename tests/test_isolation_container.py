
import unittest
import os
import sys
import re

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestContainerIsolation(unittest.TestCase):
    """
    MANUAL VERIFICATION CONTROL:
    4. Isolation test
    From detection container attempt to reach secret path (simulate). Confirm access denied.
    """
    
    def test_settings_blindness(self):
        """
        Verify that even if the SECRET environment variable exists (e.g. leaked into container),
        the Standard Settings object (used by Detection/FeatureEngine) remains BLIND to it.
        """
        print("\n[Test] Isolation: Container Env Leak Simulation")
        
        # 1. Simulate Leakage
        os.environ["BROKER_API_KEY"] = "LEAKED_SECRET_KEY"
        os.environ["BROKER_SECRET"] = "LEAKED_SECRET_VAL"
        
        # 2. Load Settings (Reload to ensure it parses env)
        from config import Settings
        # Force reload? Pydantic settings load at init
        settings = Settings()
        
        # 3. Verify Blindness
        self.assertFalse(hasattr(settings, "BROKER_API_KEY"), "FATAL: Standard Settings exposed BROKER_API_KEY from Env!")
        self.assertFalse(hasattr(settings, "BROKER_SECRET"), "FATAL: Standard Settings exposed BROKER_SECRET from Env!")
        
        # Cleanup
        del os.environ["BROKER_API_KEY"]
        del os.environ["BROKER_SECRET"]
        
        print("   PASS: Standard Settings ignored leaked env vars.")

    def test_feature_engine_imports(self):
        """
        Static Analysis: Confirm FeatureEngine does not import Vault or Execution Secrets.
        This simulates 'Access Denied' to the code path.
        """
        print("\n[Test] Isolation: Static Analysis of Feature Engine")
        
        target_file = os.path.join(os.path.dirname(__file__), '..', 'workers', 'fbe', 'feature_engine.py')
        
        with open(target_file, 'r') as f:
            content = f.read()
            
        # Check for forbidden imports
        forbidden_patterns = [
            r"from .*vault",
            r"import .*vault",
            r"from .*execution\.secrets",
            r"import .*execution\.secrets"
        ]
        
        for pattern in forbidden_patterns:
            match = re.search(pattern, content)
            self.assertIsNone(match, f"FATAL: FeatureEngine imports forbidden secret module! Found: {match.group(0) if match else ''}")
            
        print("   PASS: FeatureEngine source code does not import Secret modules.")

if __name__ == '__main__':
    unittest.main()
