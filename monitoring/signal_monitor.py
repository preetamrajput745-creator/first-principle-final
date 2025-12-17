"""
Signal Monitoring Service - Mistake #1 Compliance
Tracks signal metrics and alerts on anomalies.
"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

workers_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db
from common.models import Signal

class SignalMonitor:
    """
    Monitors signals for Mistake #1 requirements:
    - Alert if >30% signals in low-liquidity hours
    - Track signal rate per hour
    - Monitor slippage distribution
    """
    
    def __init__(self):
        self.alert_threshold_low_liq = 0.30  # 30%
        self.low_volume_threshold = 10
        
    def get_metrics(self, hours_back=24):
        """Get signal metrics for last N hours"""
        with next(get_db()) as db:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            signals = db.query(Signal).filter(Signal.timestamp >= cutoff_time).all()
            
            if not signals:
                return {"error": "No signals in time window"}
            
            total = len(signals)
            low_liq_count = 0
            slippage_values = []
            symbols = defaultdict(int)
            
            for s in signals:
                # Low liquidity check
                if s.l1_snapshot and s.l1_snapshot.get('volume', 100) < self.low_volume_threshold:
                    low_liq_count += 1
                
                # Slippage tracking
                if s.estimated_slippage:
                    slippage_values.append(s.estimated_slippage)
                
                # Symbol distribution
                symbols[s.symbol] += 1
            
            low_liq_pct = (low_liq_count / total) * 100 if total > 0 else 0
            
            metrics = {
                "total_signals": total,
                "time_window_hours": hours_back,
                "low_liquidity_signals": low_liq_count,
                "low_liquidity_percentage": round(low_liq_pct, 2),
                "alert_triggered": low_liq_pct > (self.alert_threshold_low_liq * 100),
                "avg_slippage": round(sum(slippage_values) / len(slippage_values), 2) if slippage_values else 0,
                "max_slippage": max(slippage_values) if slippage_values else 0,
                "min_slippage": min(slippage_values) if slippage_values else 0,
                "symbol_distribution": dict(symbols),
                "signals_per_hour": round(total / hours_back, 2)
            }
            
            return metrics
    
    def print_report(self):
        """Print monitoring report"""
        print("=" * 60)
        print("SIGNAL MONITORING REPORT (Mistake #1 Compliance)")
        print("=" * 60)
        
        metrics = self.get_metrics(hours_back=24)
        
        if "error" in metrics:
            print(f"Status: {metrics['error']}")
            return
        
        print(f"\nTotal Signals (24h): {metrics['total_signals']}")
        print(f"Signals per Hour: {metrics['signals_per_hour']}")
        
        print(f"\nLow Liquidity Signals: {metrics['low_liquidity_signals']} ({metrics['low_liquidity_percentage']}%)")
        if metrics['alert_triggered']:
            print("ALERT: Low liquidity signals exceed 30% threshold!")
        else:
            print("Status: Within acceptable limits")
        
        print(f"\nSlippage Stats:")
        print(f"  Average: {metrics['avg_slippage']}")
        print(f"  Min: {metrics['min_slippage']}")
        print(f"  Max: {metrics['max_slippage']}")
        
        print(f"\nSymbol Distribution:")
        for symbol, count in metrics['symbol_distribution'].items():
            print(f"  {symbol}: {count} signals")
        
        print("=" * 60)

if __name__ == "__main__":
    monitor = SignalMonitor()
    monitor.print_report()
