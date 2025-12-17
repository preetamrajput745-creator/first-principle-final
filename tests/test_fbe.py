import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.fbe.logic import FBEDetector

class TestFBEDetector(unittest.TestCase):
    def test_fbe_bearish(self):
        detector = FBEDetector()
        symbol = "TEST"
        
        # 1. Initial tick
        detector.process_tick(symbol, 100, "t1")
        
        # 2. Make a new high
        detector.process_tick(symbol, 105, "t2")
        self.assertEqual(detector.state[symbol]["high"], 105)
        
        # 3. Go higher
        detector.process_tick(symbol, 110, "t3")
        self.assertEqual(detector.state[symbol]["high"], 110)
        self.assertEqual(detector.state[symbol]["prev_high"], 105)
        
        # 4. Drop below prev_high (105)
        # Previous last_price was 110. Now we drop to 104.
        signal = detector.process_tick(symbol, 104, "t4")
        
        self.assertIsNotNone(signal)
        self.assertEqual(signal["type"], "FBE_BEARISH")
        self.assertEqual(signal["price"], 104)

    def test_no_signal(self):
        detector = FBEDetector()
        symbol = "TEST"
        detector.process_tick(symbol, 100, "t1")
        detector.process_tick(symbol, 102, "t2")
        signal = detector.process_tick(symbol, 103, "t3") # New high, but no reversal yet
        self.assertIsNone(signal)

if __name__ == '__main__':
    unittest.main()
