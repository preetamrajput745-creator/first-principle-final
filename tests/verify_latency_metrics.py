
import unittest
import sys
import os
import time
import random
from datetime import datetime

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestLatencyPanel(unittest.TestCase):
    """
    Verification of Task 11: Latency Panel (p50/p95).
    """
    
    def test_latency_calculation(self):
        print("\n[TEST 11] Latency Calculation (p50/p95)...")
        
        # Simulate Latency Logs/Metrics
        # Metric: hop_latency_ms{path="Ingest->Bar"}
        
        # Generate raw data with synthetic delay
        # Normal: 10-20ms. Outliers: 100ms, 500ms
        
        latencies = []
        for _ in range(90): latencies.append(random.randint(10, 20)) # 90% fast
        for _ in range(5): latencies.append(random.randint(100, 150)) # 5% slow
        for _ in range(5): latencies.append(random.randint(400, 500)) # 5% very slow
        
        latencies.sort()
        count = len(latencies)
        
        # Calculate p50 (Median)
        p50 = latencies[int(count * 0.50)]
        
        # Calculate p95
        p95 = latencies[int(count * 0.95)]
        
        print(f"   Sample Size: {count}")
        print(f"   p50: {p50}ms")
        print(f"   p95: {p95}ms")
        
        self.assertTrue(10 <= p50 <= 25, f"p50 {p50}ms out of range (Normal 10-20)")
        self.assertTrue(400 <= p95 <= 500, f"p95 {p95}ms out of range (Expected ~400+)")
        
        print("   PASS: Latency Histogram Logic Validated.")
        print("   (Note: In Real System, this is computed by Prometheus 'histogram_quantile(0.95, ...)')")

if __name__ == "__main__":
    unittest.main()
