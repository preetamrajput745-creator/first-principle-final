"""
PnL & Slippage Panel Monitor
Implements Zero-Tolerance Spec for PnL/Slippage Monitoring & Alerting.

Metrics:
1. Simulated vs Realized PnL
2. Avg Slippage (Rolling)
3. Slippage Delta (Actual vs Profile)

Alerts:
1. Slippage Delta > 1.5x Profile (Warning)
2. Slippage Delta > 50% for 10 trades (Critical -> Auto-Pause)
3. Realized PnL Drawdown > Threshold
4. Sim/Real Divergence > 25%
"""

import sys
import os
import statistics
from datetime import datetime, timedelta
from sqlalchemy import func

# Path setup to allow imports from workers
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workers"))

from common.database import get_db
from common.models import Order, Signal, SlippageProfile, Automation
from risk.circuit_breaker import CircuitBreaker

class PnLMonitor:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.alerts = [] # Store alerts for verification
        self.audit_log = [] # Store audit actions

    def get_slippage_profile(self, db, instrument):
        """Fetch slippage profile or default"""
        profile = db.query(SlippageProfile).filter(SlippageProfile.symbol == instrument).first()
        if not profile:
            return 0.01 # Default 1 bps (0.01%)
        return profile.base_slippage_pct

    def calculate_rolling_slippage(self, db, instrument, window=50):
        """
        Calculate rolling avg slippage and delta for last N trades.
        Returns: (avg_slippage_pct, delta_factor)
        """
        trades = db.query(Order).filter(
            Order.symbol == instrument,
            Order.status == "FILLED"
        ).order_by(Order.created_at.desc()).limit(window).all()

        if not trades:
            return 0.0, 0.0

        slippage_pcts = []
        for t in trades:
            # Slippage % = (Realized / Price) * 100 ? 
            # Or usually defined as (Exec - Expected) / Expected
            # In our model 'realized_slippage' is stored as the absolute delta value (price diff) or pct?
            # Looking at previous code, 'realized_slippage' was assigned 'settings.SLIPPAGE_BASE * factor'.
            # If SLIPPAGE_BASE is 0.01 (1%), then it's a percentage.
            # Let's assume realized_slippage column is PERCENTAGE (0.01 = 1%).
            if t.realized_slippage is None: continue
            slippage_pcts.append(t.realized_slippage)

        if not slippage_pcts:
            return 0.0, 0.0

        avg_slippage = statistics.mean(slippage_pcts)
        
        # Get Profile Baseline
        profile_base = self.get_slippage_profile(db, instrument)
        
        # Delta Factor = Avg / Base (e.g. 1.5x)
        delta_factor = avg_slippage / profile_base if profile_base > 0 else 0
        
        return avg_slippage, delta_factor

    def check_slippage_alerts(self, instrument):
        """
        Alert Rule A:
        - Warning: Avg Slippage (50) > Profile * 1.5
        - Critical: Slippage Delta > 0.5 (50%) for 10 CONSECUTIVE trades
        """
        with next(get_db()) as db:
            # 1. Warning Check (Rolling 50)
            avg, factor = self.calculate_rolling_slippage(db, instrument, 50)
            if factor > 1.5:
                self.trigger_alert("WARNING", f"High Slippage {instrument}: {avg:.4f}% ({factor:.2f}x Profile)")

            # 2. Critical Check (Consecutive 10)
            trades = db.query(Order).filter(
                Order.symbol == instrument,
                Order.status == "FILLED"
            ).order_by(Order.created_at.desc()).limit(10).all()
            
            if len(trades) < 10:
                return

            consecutive_breach = True
            profile_base = self.get_slippage_profile(db, instrument)
            
            # Critical threshold: Delta > 0.5 (i.e., Actual > Profile * 1.5 ?)
            # Spec says: "slippage_delta > 0.5 (i.e., >50%)"
            # If delta = (Actual - Profile)/Profile, then delta > 0.5 means Actual > 1.5 * Profile.
            
            for t in trades:
                val = t.realized_slippage or 0
                delta = (val - profile_base) / profile_base if profile_base > 0 else 0
                if delta <= 0.5:
                    consecutive_breach = False
                    break
            
            if consecutive_breach:
                self.trigger_alert("CRITICAL", f"Critical Slippage {instrument}: 10 Consecutive >50% Delta")
                self.trigger_auto_pause(instrument, "Critical Slippage Breach")

    def check_pnl_drawdown(self, threshold_pct=0.20):
        """
        Alert Rule C: Realized PnL drops below peak * (1 - threshold)
        """
        with next(get_db()) as db:
            # Get cumulative PnL time series
            trades = db.query(Order).filter(Order.status == "FILLED").order_by(Order.created_at.asc()).all()
            if not trades: return
            
            cum_pnl = 0.0
            peak_pnl = -float('inf')
            current_drawdown = 0.0
            
            for t in trades:
                pnl = t.pnl or 0.0
                cum_pnl += pnl
                peak_pnl = max(peak_pnl, cum_pnl)
                
            # If peak is positive, we can calc drawdown pct. If peak is neg, logic is tricky, usually PnL starts at 0.
            if peak_pnl > 0:
                dd = (peak_pnl - cum_pnl) / peak_pnl
                if dd > threshold_pct:
                    self.trigger_alert("CRITICAL", f"Realized PnL Drawdown: {dd*100:.1f}% > {threshold_pct*100}%")

    def check_sim_real_divergence(self, instrument=None):
        """
        Alert Rule D: |Sim - Real| / Max(|Sim|, 1) > 0.25
        """
        with next(get_db()) as db:
            query_real = db.query(func.sum(Order.pnl)).filter(Order.status == "FILLED", Order.is_paper == False)
            query_sim = db.query(func.sum(Order.pnl)).filter(Order.status == "FILLED", Order.is_paper == True)
            
            if instrument:
                query_real = query_real.filter(Order.symbol == instrument)
                query_sim = query_sim.filter(Order.symbol == instrument)
                
            realized = query_real.scalar() or 0.0
            simulated = query_sim.scalar() or 0.0
            
            diff = abs(simulated - realized)
            denominator = max(abs(simulated), 1.0)
            
            ratio = diff / denominator
            if ratio > 0.25:
                tag = f" ({instrument})" if instrument else ""
                self.trigger_alert("WARNING", f"Sim/Real Divergence{tag}: {ratio*100:.1f}% (Sim=${simulated}, Real=${realized})")

    def trigger_alert(self, level, message):
        """Mock Alerting"""
        alert = f"[{level}] {message}"
        print(f"ALERT_SYSTEM: {alert}")
        self.alerts.append(alert)

    def trigger_auto_pause(self, instrument, reason):
        """Execute Auto-Pause via Circuit Breaker"""
        print(f"AUTO_PAUSE_TRIGGER: Pausing due to {reason}")
        self.audit_log.append(f"PAUSE: {reason} on {instrument}")
        
        # Call actual Circuit Breaker logic
        self.circuit_breaker.pause_all_active_automations(reason)

if __name__ == "__main__":
    # Smoke Test
    mon = PnLMonitor()
    print("PnLMonitor Initialized.")
