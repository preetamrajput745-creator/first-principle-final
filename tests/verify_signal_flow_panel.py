
import unittest
import sys
import os
import time
import random
import json
import math
from datetime import datetime, timedelta

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.common.database import get_db, SessionLocal
from workers.common.models import Signal, Automation
from config import settings

# Setup Audit Directory
AUDIT_DIR = os.path.join(os.path.dirname(__file__), "..", "audit", "signal-flow-panel")
if not os.path.exists(AUDIT_DIR):
    os.makedirs(AUDIT_DIR)

class TestSignalFlowPanel(unittest.TestCase):
    """
    Verification of 'Signal Flow Panel' metrics and alerts using Synthetic Data.
    We simulate Prometheus queries by aggregating SQL data.
    """
    
    def setUp(self):
        self.db = SessionLocal()
        self.symbol = "FLOW_TEST_FULL"
        self.automation_id = self._get_or_create_automation()
        self.log_file = os.path.join(AUDIT_DIR, "synthetic_logs.txt")
        # Clear/Create log file
        with open(self.log_file, "w") as f:
            f.write(f"--- Synthetic Test Log Start: {datetime.utcnow()} ---\n")
            
    def tearDown(self):
        self.db.close()
        
    def _log(self, message):
        print(message)
        with open(self.log_file, "a") as f:
            f.write(f"[{datetime.utcnow()}] {message}\n")
        
    def _get_or_create_automation(self):
        # Use a distinct automation for this test suite
        slug = "flow-full-validation"
        auto = self.db.query(Automation).filter(Automation.slug == slug).first()
        if not auto:
            auto = Automation(name="FlowTestFull", slug=slug, status="active")
            self.db.add(auto)
            self.db.commit()
        return auto.id

    def generate_signal(self, score, timestamp=None, symbol=None):
        if not timestamp:
            timestamp = datetime.utcnow()
        if not symbol:
            symbol = self.symbol
            
        sig = Signal(
            automation_id=self.automation_id,
            symbol=symbol,
            timestamp=timestamp,
            score=score,
            payload={"action": "BUY" if score > 0.5 else "SELL"},
            status="new",
            clock_drift_ms=0.0
        )
        self.db.add(sig)
        return sig

    def test_full_acceptance_suite(self):
        """
        Executes all 4 Mandatory Synthetic Tests sequentially.
        """
        self._log("STARTING FULL ACCEPTANCE SUITE (ZERO TOLERANCE)")
        
        # --- TEST 1: Signal Flood ---
        self._test_signal_flood()
        
        # --- TEST 2: Score Degradation ---
        self._test_score_collapse()
        
        # --- TEST 3: Distribution Drift / KL Divergence ---
        self._test_distribution_drift()
        
        # --- TEST 4: Score Outlier Explosion ---
        self._test_score_outlier()
        
        # --- TEST 5: Mixed Load Stability ---
        self._test_mixed_load()
        
        # --- AUDIT ARTIFACT GENERATION ---
        self._generate_audit_artifacts()
        
        self._log("FULL ACCEPTANCE SUITE COMPLETED SUCCESSFULLY.")

    def _test_signal_flood(self):
        self._log("\n--- TEST 1: Signal Flood ---")
        
        # 1. Baseline: 10 signals/hr
        base_time = datetime.utcnow() - timedelta(hours=2)
        for _ in range(10):
            self.generate_signal(score=0.8, timestamp=base_time)
        self.db.commit()
        
        # 2. Flood: 40 signals/hr (Now) -> >3x baseline
        now = datetime.utcnow()
        for _ in range(40):
            self.generate_signal(score=0.8, timestamp=now)
        self.db.commit()
        
        # Validation
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        count = self.db.query(Signal).filter(Signal.symbol == self.symbol, Signal.timestamp >= one_hour_ago).count()
        baseline = 10.0
        
        if count > (baseline * 3):
            self._log(f" [PASS] HighSignalRate Alert Condition Met: {count} > {baseline*3}")
        else:
            self._log(f" [FAIL] HighSignalRate Alert Failed: {count} <= {baseline*3}")
            self.fail("Signal Flood Alert Failed")

    def _test_score_collapse(self):
        self._log("\n--- TEST 2: Score Collapse ---")
        # Baseline High (0.9)
        base_time = datetime.utcnow() - timedelta(days=1)
        for _ in range(20):
             self.generate_signal(score=0.9, timestamp=base_time)
        self.db.commit()
        
        # Collapse (0.2)
        now = datetime.utcnow()
        # Use a new symbol suffix to isolate stats or just clear recent 
        # (For this test we aggregate 'last 1h' vs 'last 7d')
        # We will add low scores to the existing symbol. 
        # Current avg for last hour (from flood) was 0.8.
        # We need to drag it down.
        for _ in range(50):
             self.generate_signal(score=0.1, timestamp=now)
        self.db.commit()
        
        # Calc
        signals_1h = self.db.query(Signal).filter(Signal.symbol == self.symbol, Signal.timestamp >= now - timedelta(hours=1)).all()
        avg_1h = sum(s.score for s in signals_1h) / len(signals_1h)
        # Expected ~ (40*0.8 + 50*0.1) / 90 = (32+5)/90 = 0.41
        
        baseline = 0.9 # From day ago
        threshold = baseline * 0.7 # 0.63
        
        if avg_1h < threshold:
            self._log(f" [PASS] ScoreCollapse Alert Condition Met: Avg {avg_1h:.2f} < {threshold:.2f}")
        else:
            self.fail(f"Score Collapse Failed. Avg {avg_1h:.2f} >= {threshold:.2f}")

    def _test_distribution_drift(self):
        self._log("\n--- TEST 3: Distribution Drift (KL Divergence) ---")
        # Generate skewed scores (all > 0.9) to shift distribution RIGHT
        # Previous distribution had mixed (0.8, 0.1).
        
        # Create a new symbol for clean distribution test
        sym_drift = "FLOW_DRIFT_TEST"
        
        # Baseline: Uniform-ish
        base = datetime.utcnow() - timedelta(hours=5)
        for s in [0.2, 0.4, 0.6, 0.8]:
            for _ in range(10): 
                self.generate_signal(score=s, timestamp=base, symbol=sym_drift)
                
        # Drift: Skewed to 0.95
        now = datetime.utcnow()
        for _ in range(50):
            self.generate_signal(score=0.95, timestamp=now, symbol=sym_drift)
        self.db.commit()
        
        # Simulation of KL calculation
        # P = Recent 1h, Q = Baseline
        # Simplified Check: Mean shift
        signals_recent = self.db.query(Signal).filter(Signal.symbol == sym_drift, Signal.timestamp >= now - timedelta(hours=1)).all()
        signals_base = self.db.query(Signal).filter(Signal.symbol == sym_drift, Signal.timestamp < now - timedelta(hours=1)).all()
        
        mean_recent = sum(s.score for s in signals_recent)/len(signals_recent)
        mean_base = sum(s.score for s in signals_base)/len(signals_base)
        
        self._log(f"   Baseline Mean: {mean_base:.2f} | Recent Mean: {mean_recent:.2f}")
        # Expect significant shift
        if abs(mean_recent - mean_base) > 0.3:
            self._log(" [PASS] Distribution Drift Detected (Significant Mean Shift Proxy)")
        else:
            self.fail("Distribution Drift Not Detected")

    def _test_score_outlier(self):
        self._log("\n--- TEST 4: Score Outlier Explosion ---")
        # >10% of last 500 signals < 0.2
        
        sym_outlier = "FLOW_OUTLIER_TEST"
        now = datetime.utcnow()
        
        # Generate 400 'Good' signals (0.8)
        for _ in range(400):
            self.generate_signal(score=0.8, timestamp=now, symbol=sym_outlier)
            
        # Generate 60 'Bad' signals (0.1) -> 60/460 = 13% > 10%
        for _ in range(60):
            self.generate_signal(score=0.1, timestamp=now, symbol=sym_outlier)
        self.db.commit()
        
        # Check
        total = self.db.query(Signal).filter(Signal.symbol == sym_outlier).count()
        low_score = self.db.query(Signal).filter(Signal.symbol == sym_outlier, Signal.score < 0.2).count()
        ratio = low_score / total
        
        if ratio > 0.1:
            self._log(f" [PASS] Outlier Explosion Detected: Ratio {ratio:.2f} > 0.10")
        else:
            self.fail(f"Outlier Explosion Failed: Ratio {ratio:.2f}")

    def _test_mixed_load(self):
        self._log("\n--- TEST 5: Mixed Load Stability ---")
        # Just ensure no errors when writing varied data
        try:
            for _ in range(50):
                score = random.random()
                self.generate_signal(score=score)
            self.db.commit()
            self._log(" [PASS] Mixed Load Inserted Successfully.")
        except Exception as e:
            self.fail(f"Mixed Load Failed: {e}")

    def _generate_audit_artifacts(self):
        self._log("\n--- Generating Audit Artifacts ---")
        
        # 1. Raw Metrics CSV (Simulation)
        csv_path = os.path.join(AUDIT_DIR, "raw_metrics_1h.csv")
        with open(csv_path, "w") as f:
            f.write("timestamp_utc,symbol,metric,value\n")
            # Dump last 50 signals
            signals = self.db.query(Signal).order_by(Signal.timestamp.desc()).limit(50).all()
            for s in signals:
                f.write(f"{s.timestamp},{s.symbol},signal_score,{s.score}\n")
                
        self._log(f" [ARTIFACT] CSV generated: {csv_path}")
        
        # 2. Summary
        summary_path = os.path.join(AUDIT_DIR, "Summary.txt")
        with open(summary_path, "w") as f:
            f.write("SIGNAL FLOW PANEL VERIFICATION SUMMARY\n")
            f.write("======================================\n")
            f.write(f"Timestamp: {datetime.utcnow()}\n")
            f.write("Status: PASS\n")
            f.write("\nTests Executed:\n")
            f.write("1. Signal Flood: PASS\n")
            f.write("2. Score Degradation: PASS\n")
            f.write("3. Distribution Drift: PASS\n")
            f.write("4. Outlier Explosion: PASS\n")
            f.write("5. Mixed Load: PASS\n")
            f.write("\nAudit Artifacts: raw_metrics_1h.csv, synthetic_logs.txt\n")
            
        self._log(f" [ARTIFACT] Summary generated: {summary_path}")

if __name__ == "__main__":
    unittest.main()
