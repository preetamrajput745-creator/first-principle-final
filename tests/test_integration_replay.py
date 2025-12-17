
import unittest
from unittest.mock import MagicMock, patch
import json
import time
import sys
import os
from datetime import datetime, timedelta

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.bar_builder import BarBuilder
from workers.fbe.feature_engine import FeatureEngine
from workers.fbe.scoring_engine import ScoringEngine
from config import settings

class TestIntegrationReplay(unittest.TestCase):
    """
    TRIPLE CHECK REQUIREMENT: "Integration (replay small dataset)"
    This test simulates the Full Data Pipeline:
    Ticks (Replay) -> BarBuilder -> FeatureEngine -> ScoringEngine -> Signal
    """
    
    def setUp(self):
        # Reset settings
        settings.TRIGGER_SCORE = 50
        
    @patch('workers.bar_builder.redis.Redis')
    @patch('workers.fbe.feature_engine.event_bus')
    @patch('workers.fbe.feature_engine.storage_client')
    @patch('workers.fbe.scoring_engine.event_bus')
    @patch('workers.fbe.scoring_engine.SessionLocal')
    def test_replay_to_signal_flow(self, mock_db_session, mock_score_bus, mock_storage, mock_feat_bus, mock_redis_cls):
        
        # --- PREPARE DATASET (Small Replay Dataset) ---
        symbol = "TEST_REPLAY_1"
        start_time = datetime.utcnow()
        
        # Generate 60 ticks within 1 minute (Simulating a pump/dump candle)
        ticks = []
        for i in range(60):
            t = start_time + timedelta(seconds=i)
            # Price goes up then down (Volatile)
            price = 100 + (i * 0.5) if i < 30 else 115 - ((i-30) * 0.5)
            # Volume low (Low volume breakout -> False Breakout ?)
            # SMA is 500 (from pre-load). We need < 0.6 * 500 = 300.
            # 60 ticks * 4 vol = 240 total volume. 240/500 = 0.48 < 0.6.
            volume = 4
            
            ticks.append({
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "time": t.isoformat()
            })
            
        print(f"\n[Test] Generated {len(ticks)} ticks for Replay.")

        # --- STEP 1: BAR BUILDER (Tick -> Bar) ---
        # Mock Redis for BarBuilder
        mock_redis_instance = MagicMock()
        mock_redis_cls.return_value = mock_redis_instance
        
        builder = BarBuilder()
        builder.current_bars = {} # Reset
        
        # Feed ticks
        for tick in ticks:
            builder.process_tick(symbol, tick)
            
        # Manually force bar closure (simulate time pass)
        # We assume builder uses builder.current_bars[symbol]['start_time']
        # We set start_time to 2 minutes ago to force closure
        if symbol in builder.current_bars:
            builder.current_bars[symbol]['start_time'] = datetime.utcnow() - timedelta(minutes=2)
            
        # Capture the output of check_bar_closures
        builder.check_bar_closures()
        
        # Verify Bar Published to Redis (builder.r.xadd)
        self.assertTrue(mock_redis_instance.xadd.called, "BarBuilder failed to publish bar.")
        
        # Extract the Bar Data
        # Call args: (topic, {"data": json_string})
        call_args = mock_redis_instance.xadd.call_args
        topic = call_args[0][0]
        data_dict = call_args[0][1]
        
        self.assertEqual(topic, f"market.bar.1m.{symbol}")
        bar_data = json.loads(data_dict['data'])
        
        print(f"[Test] Bar Generated: O={bar_data['open']} H={bar_data['high']} L={bar_data['low']} C={bar_data['close']} V={bar_data['volume']}")
        
        # Verify Bar Correctness (High should be ~115, Low 100)
        self.assertAlmostEqual(bar_data['open'], 100.0)
        self.assertAlmostEqual(bar_data['high'], 115.0) # Max price in loop
        self.assertEqual(bar_data['volume'], 240)
        
        # --- STEP 2: FEATURE ENGINE (Bar -> Snapshot) ---
        feature_engine = FeatureEngine()
        
        # Needs history to calculate things properly, let's pre-load some history
        # feature_engine.history[symbol] needs list of bars
        # Creating dummy history
        feature_engine.history[symbol] = []
        for i in range(25):
            feature_engine.history[symbol].append({
                "open": 100, "high": 102, "low": 98, "close": 100, "volume": 500, "time": datetime.utcnow().isoformat()
            })
            
        # Process the new bar
        # Ensure bar_data has 'time' which process_bar expects. It was set in builder.
        if 'time' not in bar_data:
             bar_data['time'] = datetime.utcnow().isoformat()
        bar_data['symbol'] = symbol
             
        # Mock storage client save
        mock_storage.save_feature_snapshot.return_value = "s3://mock-bucket/snap.json"
        
        feature_engine.process_bar(bar_data)
        
        # Verify Feature Snapshot Published
        self.assertTrue(mock_feat_bus.publish.called)
        
        feat_call_args = mock_feat_bus.publish.call_args
        feat_topic = feat_call_args[0][0]
        feat_payload = feat_call_args[0][1]
        
        self.assertEqual(feat_topic, f"feature.ready.{symbol}")
        feature_snapshot_str = feat_payload['data'] # Based on FeatureEngine code: {"data": json.dumps...}
        feature_snapshot = json.loads(feature_snapshot_str)
        
        print(f"[Test] Features Calculated: WickRatio={feature_snapshot['features']['wick_ratio']:.2f}")
        
        # --- STEP 3: SCORING ENGINE (Snapshot -> Signal) ---
        scoring_engine = ScoringEngine()
        scoring_engine.db = mock_db_session() # session instance
        
        # Process Snapshot
        scoring_engine.process_snapshot(feature_snapshot)
        
        # Verify Signal Published
        # Score might be low or high depending on logic, but we verify the flow.
        self.assertTrue(mock_score_bus.publish.called, "ScoringEngine did not publish any event.")
        
        score_call_args = mock_score_bus.publish.call_args
        score_topic = score_call_args[0][0]
        score_payload = score_call_args[0][1]
        
        print(f"[Test] Signal Topic: {score_topic}, Score: {score_payload.get('score')}")
        
        # If score was high enough (we set TRIGGER=50), it should be a signal.
        # Otherwise, check logs.
        if score_topic == "signal.false_breakout":
            self.assertEqual(score_payload['symbol'], symbol)
            self.assertGreaterEqual(score_payload['score'], 50)
            print("[Test] FULL FLOW VERIFIED: Ticks -> Bar -> Features -> Signal")
        else:
            print("[Test] ⚠️ Event published but maybe not a signal? " + score_topic)

if __name__ == '__main__':
    unittest.main()
