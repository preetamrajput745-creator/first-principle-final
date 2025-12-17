
import unittest
import sys
import os

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings

class TestScoringLogic(unittest.TestCase):
    def calculate_score_locally(self, wick_ratio, vol_ratio, is_poke):
        """Replicating logic from scoring_engine to verify math independently"""
        score = 0
        
        # Wick Logic
        if wick_ratio > settings.WICK_RATIO_THRESHOLD:
            score += settings.WEIGHT_WICK
        
        # Vol Logic
        if vol_ratio > settings.VOL_RATIO_THRESHOLD:
            score += settings.WEIGHT_VOL
            
        # Poke Logic
        if is_poke:
            score += settings.WEIGHT_POKE
            
        return score

    def test_strong_signal(self):
        # Case: Strong Wick (1.5), Strong Vol (2.0), Poke (True)
        # Weights: Wick=30, Vol=20, Poke=10 => Total 60 (Wait, weights are dynamic in config)
        # Assuming defaults: Wick=30, Vol=20, Poke=10. Total = 60.
        # Thresholds: Wick=0.7, Vol=0.6
        
        score = self.calculate_score_locally(wick_ratio=1.5, vol_ratio=2.0, is_poke=True)
        expected = settings.WEIGHT_WICK + settings.WEIGHT_VOL + settings.WEIGHT_POKE
        self.assertEqual(score, expected, f"Score mismatch! Calculated: {score}, Expected: {expected}")

    def test_weak_signal(self):
        # Case: Weak Wick (0.2), Weak Vol (0.1), No Poke
        score = self.calculate_score_locally(wick_ratio=0.2, vol_ratio=0.1, is_poke=False)
        self.assertEqual(score, 0, "Weak signal should have 0 score")

    def test_mixed_signal(self):
        # Case: Strong Wick, Weak Vol
        score = self.calculate_score_locally(wick_ratio=1.5, vol_ratio=0.1, is_poke=False)
        self.assertEqual(score, settings.WEIGHT_WICK, "Mixed signal failed")

if __name__ == '__main__':
    unittest.main()
