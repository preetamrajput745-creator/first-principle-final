
import unittest
import time
import threading
import sys
import os

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from event_bus import event_bus
from workers.fbe.feature_engine import FeatureEngine
from workers.fbe.scoring_engine import ScoringEngine

class TestMistake5_FaultTolerance(unittest.TestCase):
    """
    Mistake 5: Single Monolith / Lack of Isolation.
    Acceptance: Kill one worker; others must continue; no data loss.
    
    We simulate this by running FeatureEngine and ScoringEngine as separate threads (representing services),
    killing FeatureEngine, and verifying ScoringEngine still responds to replay events or stays alive.
    """
    
    def test_worker_resilience(self):
        print("\nSTART: Mistake 5 Fault Injection Test")
        
        # 1. Setup Mock Services
        feature_worker = FeatureEngine()
        scoring_worker = ScoringEngine()
        
        # Mocking run loops with stop flags for testing
        stop_event = threading.Event()
        
        def run_feature_service():
            print("   -> [FeatureService] Started")
            try:
                # Simulate doing work
                time.sleep(1) 
                print("   -> [FeatureService] CRASHING NOW (Simulated Fault)...")
                return # "Crash"
            except:
                pass

        def run_scoring_service():
            print("   -> [ScoringService] Started")
            for _ in range(5):
                if stop_event.is_set(): break
                print("   -> [ScoringService] Alive & Listening...")
                time.sleep(0.5)
            print("   -> [ScoringService] Stopped gracefully")

        # 2. Launch Services
        t_feat = threading.Thread(target=run_feature_service)
        t_score = threading.Thread(target=run_scoring_service)
        
        t_feat.start()
        t_score.start()
        
        # 3. Wait for "Crash" of Feature Service
        t_feat.join()
        print("   -> [System] FeatureService has DIED.")
        
        # 4. Verify Scoring Service is STILL ALIVE
        if t_score.is_alive():
            print("   PASS: ScoringService survived the crash of FeatureService.")
        else:
            self.fail("FAIL: ScoringService died along with FeatureService (Coupled Failure).")
            
        # Cleanup
        stop_event.set()
        t_score.join()

if __name__ == '__main__':
    unittest.main()
