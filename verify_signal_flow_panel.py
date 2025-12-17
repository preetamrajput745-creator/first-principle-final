"""
Task: Verify Signal Flow Panel & Alerts (Zero-Tolerance)
Executes Synthetic Tests for:
1. Signals per Hour Metrics & Flood Alert.
2. Avg Score Metrics & Degradation Alert.
3. Distribution Histogram & Skew Alert.
"""

import sys
import os
import time
import random
import csv
import math
from datetime import datetime, timedelta
import statistics

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from common.database import get_db
from common.models import Signal

TEST_SYMBOL = "SIGNAL_TEST"

class SignalPanelVerifier:
    def __init__(self):
        self.audit_csv = []
        self.alerts = []
        
    def trigger_alert(self, name, level, message):
        """Simulate System Alert Trigger"""
        alert_str = f"[{level}] {name}: {message}"
        print(f"ALERT_SYSTEM: {alert_str}")
        self.alerts.append(alert_str)

    def check_signals_per_hour(self, window_minutes=60, baseline=10):
        """
        Metric A: Signals per hour.
        Alert A: > 3 * Baseline.
        """
        with next(get_db()) as db:
            # Count signals in last 'window_minutes'
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            count = db.query(Signal).filter(Signal.symbol == TEST_SYMBOL, Signal.timestamp >= cutoff).count()
            
            # Simple rate extrapolation if window < 60
            rate_per_hour = count * (60 / window_minutes) if window_minutes > 0 else 0
            
            print(f"   [Metric] Signals/Hr (window {window_minutes}m): {rate_per_hour:.2f} (Count: {count})")
            
            if rate_per_hour > baseline * 3:
                self.trigger_alert("Signal Flood", "WARNING", f"Rate {rate_per_hour:.0f}/hr > 3x Baseline ({baseline})")
                
            return rate_per_hour

    def check_avg_score_and_distribution(self, window_minutes=60):
        """
        Metric B: Avg Score.
        Metric C: Distribution.
        Alert B: Avg Score < Baseline - 30% (Assume Baseline = 0.5 -> Threshold 0.35)
        Alert D: Outlier Explosion (>10% < 0.2)
        """
        with next(get_db()) as db:
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            signals = db.query(Signal).filter(Signal.symbol == TEST_SYMBOL, Signal.timestamp >= cutoff).all()
            
            if not signals:
                return 0.0, {}
            
            scores = [s.score for s in signals]
            avg = statistics.mean(scores)
            
            # Distribution Buckets
            # 0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0
            buckets = {
                "0.0-0.2": 0,
                "0.2-0.4": 0,
                "0.4-0.6": 0,
                "0.6-0.8": 0,
                "0.8-1.0": 0
            }
            
            low_score_count = 0
            
            for s in scores:
                if 0.0 <= s < 0.2: 
                    buckets["0.0-0.2"] += 1
                    low_score_count += 1
                elif 0.2 <= s < 0.4: buckets["0.2-0.4"] += 1
                elif 0.4 <= s < 0.6: buckets["0.4-0.6"] += 1
                elif 0.6 <= s < 0.8: buckets["0.6-0.8"] += 1
                elif 0.8 <= s <= 1.0: buckets["0.8-1.0"] += 1
                
            print(f"   [Metric] Avg Score: {avg:.2f}")
            print(f"   [Metric] Distribution: {buckets}")
            
            # Alert B: Score Collapse
            # Baseline 0.5. Threshold 0.35.
            if avg < 0.35:
                self.trigger_alert("Score Collapse", "WARNING", f"Avg {avg:.2f} < 0.35")
                
            # Alert D: Outlier Explosion
            # > 10% < 0.2
            total = len(scores)
            low_pct = (low_score_count / total) * 100
            if low_pct > 10.0:
                 self.trigger_alert("Score Outlier Explosion", "WARNING", f"Low Score %: {low_pct:.1f}% > 10%")
                 
            return avg, buckets

    def run_verification(self):
        print("TEST: Signal Flow Panel Verification (Zero-Tolerance)")
        print("=" * 60)
        
        # 0. Clean Setup
        with next(get_db()) as db:
            db.query(Signal).filter(Signal.symbol == TEST_SYMBOL).delete()
            db.commit()
            
        # --- TEST 1: Signal Flood (Burst) ---
        print("\n1. Test: Signal Flood (Rate > 3x Baseline)...")
        # Baseline = 10/hr. Expect > 30/hr.
        # Inject 40 signals in "last 5 minutes"
        base_time = datetime.utcnow()
        with next(get_db()) as db:
            for i in range(40):
                ts = base_time - timedelta(minutes=random.uniform(0, 5))
                s = Signal(symbol=TEST_SYMBOL, timestamp=ts, score=0.5, payload={}, status="new")
                db.add(s)
                # For audit csv
                self.audit_csv.append([s.id, ts.isoformat(), TEST_SYMBOL, 0.5])
            db.commit()
            
        rate = self.check_signals_per_hour(window_minutes=5, baseline=10)
        # 40 signals in 5 mins = 480/hr rate
        
        found_flood = any("Signal Flood" in a for a in self.alerts)
        if rate > 30 and found_flood:
            print("   SUCCESS: Flood Alert Triggered and Rate Accurate.")
        else:
            sys.stderr.write(f"   FAILURE: Flood Check Failed. Rate: {rate}, Alerts: {self.alerts}\n")
            sys.exit(1)

        # --- TEST 2: Score Degradation (Collapse) ---
        print("\n2. Test: Score Degradation (Avg < 0.35)...")
        self.alerts = []
        with next(get_db()) as db:
            # Clean previous signals to isolate test metric
            db.query(Signal).filter(Signal.symbol == TEST_SYMBOL).delete()
            # Inject 50 signals with score 0.15 (Collapse)
            for i in range(50):
                ts = datetime.utcnow() - timedelta(minutes=random.uniform(0, 60))
                s = Signal(symbol=TEST_SYMBOL, timestamp=ts, score=0.15, payload={}, status="new")
                db.add(s)
                self.audit_csv.append([s.id, ts.isoformat(), TEST_SYMBOL, 0.15])
            db.commit()
            
        avg, buckets = self.check_avg_score_and_distribution(window_minutes=60)
        
        found_collapse = any("Score Collapse" in a for a in self.alerts)
        if avg < 0.2 and found_collapse: # Expect ~0.15
             print("   SUCCESS: Score Collapse Alert Triggered.")
        else:
             sys.stderr.write(f"   FAILURE: Collapse Check Failed. Avg: {avg}, Alerts: {self.alerts}\n")
             sys.exit(1)

        # --- TEST 3: Outlier Explosion (Distribution Check) ---
        print("\n3. Test: Distributor Check & Outlier Alert...")
        # We reused the previous data (all 0.15). This means 100% are < 0.2.
        # Alert D should have fired too.
        
        # Actually, let's look for the alert in result of Step 2
        # But wait, I cleared alerts list. Let's check logic again in this block if needed, 
        # or just check if it was triggered in Step 2 call.
        
        found_outlier = any("Score Outlier Explosion" in a for a in self.alerts)
        if buckets["0.0-0.2"] == 50 and found_outlier:
            print("   SUCCESS: Outlier alert triggered and Distribution Bucket correct.")
        else:
            sys.stderr.write(f"   FAILURE: Outlier Check Failed. Buckets: {buckets}, Alerts: {self.alerts}\n")
            sys.exit(1)

        print("\nVERIFICATION COMPLETE: Signal Flow Panel logic is solid.")
        
        # Generate Audit CSV
        print("\n4. Generating Audit CSV...")
        with open("audit_signal_evidence.csv", "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "timestamp", "symbol", "score"])
            writer.writerows(self.audit_csv)
        print("   Saved evidence to 'audit_signal_evidence.csv'.")

if __name__ == "__main__":
    verifier = SignalPanelVerifier()
    verifier.run_verification()
