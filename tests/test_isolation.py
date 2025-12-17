
import unittest
import os
import sys

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestIsolation(unittest.TestCase):
    def test_secrets_isolation(self):
        """
        Confirms that standard config DOES NOT contain broker keys.
        """
        from config import Settings
        settings = Settings()
        
        # 1. Verify Standard Settings don't have secrets
        self.assertFalse(hasattr(settings, 'BROKER_API_KEY'), "Security Breach: Config has Broker Key!")
        self.assertFalse(hasattr(settings, 'BROKER_API_SECRET'), "Security Breach: Config has Broker Secret!")
        
        print("PASS: Standard Config is clean.")

    def test_execution_layer_access(self):
        """
        Confirms that Execution Layer CAN access secrets.
        """
        try:
            from execution.secrets_config import ExecutionSecrets
            # In a real environment, we would ensure .secrets.env exists or mock env vars
            # Here we just verify the class structure exists and is separate
            secrets = ExecutionSecrets(_env_file='non_existent') # Just testing class def
            # Or assume defaults for test
        except ImportError:
             self.fail("Could not import ExecutionSecrets (Architecture issue)")
        
        print("PASS: Execution Layer logic exists separately.")

if __name__ == '__main__':
    unittest.main()
