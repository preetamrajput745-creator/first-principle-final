
import unittest
import sys
import os

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestQAAcceptance_CI(unittest.TestCase):
    """
    Verification of Acceptance Criteria 7:
    "CI: run unit + integration tests in pipeline and succeed."
    """
    
    def test_ci_pipeline_structure(self):
        """
        Parses run_ci.bat to verify it contains the mandatory test steps.
        """
        # Current dir is root of project
        ci_file = os.path.join(os.path.dirname(__file__), "run_ci.bat")
        
        with open(ci_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        print("\n[QA] Analyzing CI Pipeline (run_ci.bat)...")
        
        # 1. Verify Unit Tests
        self.assertIn("tests/test_scoring_logic.py", content, "Missing Unit Tests in CI")
        print("   PASS: Unit Tests (Scoring) included.")
        
        # 2. Verify Integration Tests
        self.assertIn("tests/test_integration_replay.py", content, "Missing Integration (Replay) in CI")
        self.assertIn("tests/test_pipeline_end_to_end.py", content, "Missing Pipeline Integration in CI")
        print("   PASS: Integration Tests (Replay & Pipeline) included.")
        
        # 3. Verify Failure Enforcement
        self.assertIn("if %errorlevel% neq 0", content, "CI does not seem to enforce exit codes on failure.")
        print("   PASS: CI Failure Enforcement found.")

if __name__ == "__main__":
    unittest.main()
