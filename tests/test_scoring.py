import unittest
from workers.fbe.scoring_engine import ScoringEngine
from config import settings

class TestScoringEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ScoringEngine()
        # Mock settings if needed, or rely on default config
        
    def test_scoring_logic(self):
        # Case 1: Perfect False Breakout (Bearish)
        # Large upper wick, Low volume ratio, Poke resistance
        features = {
            "wick_ratio": 0.8, # > 0.7 (Threshold) -> +30
            "vol_ratio": 0.5,  # < 0.6 (Threshold) -> +20
            "is_poke": True,   # -> +10
            "upper_wick": 10,
            "lower_wick": 2
        }
        
        score, breakdown = self.engine.calculate_score(features)
        
        expected_score = settings.WEIGHT_WICK + settings.WEIGHT_VOL + settings.WEIGHT_POKE
        # 30 + 20 + 10 = 60. Wait, Trigger is 70.
        # My config has:
        # WEIGHT_WICK = 30
        # WEIGHT_VOL = 20
        # WEIGHT_POKE = 10
        # WEIGHT_BOOK_CHURN = 20
        # WEIGHT_DELTA = 20
        # Total max score = 100
        
        # In this case, we expect 60.
        self.assertEqual(score, 60)
        self.assertTrue('wick' in breakdown)
        self.assertTrue('vol' in breakdown)
        self.assertTrue('poke' in breakdown)

    def test_no_score(self):
        # Case 2: No signal
        features = {
            "wick_ratio": 0.1,
            "vol_ratio": 1.5,
            "is_poke": False,
            "upper_wick": 1,
            "lower_wick": 1
        }
        score, breakdown = self.engine.calculate_score(features)
        self.assertEqual(score, 0)
        self.assertEqual(len(breakdown), 0)

if __name__ == '__main__':
    unittest.main()
