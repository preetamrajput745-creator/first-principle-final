
import unittest
from unittest.mock import MagicMock, patch
import json
import time
import sys
import os
from datetime import datetime

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.fbe.scoring_engine import ScoringEngine
from config import settings

class TestIntegrationPipeline(unittest.TestCase):
    """
    Simulates the entire flow from Feature -> Scoring -> Signal.
    We mock the Kafka input/output to verify the transformation logic.
    """
    
    @patch('workers.fbe.scoring_engine.event_bus')
    def test_end_to_end_flow(self, mock_event_bus):
        # 1. Setup Mock Engine
        engine = ScoringEngine()
        # Mocking db to avoid actual inserts during test
        engine.db = MagicMock()
        
        # 3. Process the event directly via process_snapshot 
        # (Assuming the input 'feature_event' is formatted as the snapshot scoring engine expects)
        # Scoring engine expects: {'symbol': '...', 'features': {...}, 'ohlcv': {...}, 'bar_time': ...}
        
        snapshot = {
            "symbol": "TEST_INT",
            "bar_time": datetime.utcnow().isoformat(),
            "ohlcv": {"open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000},
            "features": {
                "wick_ratio": 2.5,
                "vol_ratio": 0.5, # Reduced to trigger condition (< 0.6)
                "is_poke": True,  # Renamed from poke_support to match calculate_score expectations
                "atr14": 1.0, "max_wick": 2.0, "vol_sma20": 2000, 
                "resistance_level": 106, "poke_distance": 0.5,
                "upper_wick": 3, "lower_wick": 1 # For buy/sell logic
            }
        }
        
        # Override settings for test
        original_trigger = settings.TRIGGER_SCORE
        settings.TRIGGER_SCORE = 50 
        
        try:
           engine.process_snapshot(snapshot)
        finally:
           settings.TRIGGER_SCORE = original_trigger
        
        # Assert Event Published
        mock_event_bus.publish.assert_called()
        args, _ = mock_event_bus.publish.call_args
        topic = args[0]
        payload = args[1]
        
        self.assertEqual(topic, "signal.false_breakout")
        self.assertEqual(payload['symbol'], "TEST_INT")
        self.assertGreaterEqual(payload['score'], 60)
        
        print("PASS: Integration Flow (Feature -> Score -> Signal) verified.")
        
        # Restore settings
        settings.TRIGGER_SCORE = original_trigger

if __name__ == '__main__':
    unittest.main()
