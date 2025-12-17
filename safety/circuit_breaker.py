from datetime import datetime
from sqlalchemy import func
from workers.common.models import Order, Signal, Automation
from config import settings

class CircuitBreaker:
    def __init__(self, db):
        self.db = db
        self.tripped = False
        self.reason = None

    def check_limits(self):
        """
        Checks global risk limits:
        1. Max Daily Loss
        2. Max Signals Per Hour
        Returns: True if SAFE, False if TRIPPED
        """
        if self.tripped:
            return False # Already tripped, stay tripped until manual reset

        # 1. Check Max Daily Loss
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Sum PnL for all orders created today
        # Note: We assume 'pnl' column stores realized P&L
        daily_pnl = self.db.query(func.sum(Order.pnl)).filter(
            Order.created_at >= today_start,
            Order.pnl.isnot(None)
        ).scalar() or 0.0

        if daily_pnl < (-1 * abs(settings.MAX_DAILY_LOSS)):
            self.tripped = True
            self.reason = f"MAX DAILY LOSS EXCEEDED: ${daily_pnl:.2f} < -${settings.MAX_DAILY_LOSS}"
            self._trigger_pause()
            return False

        # 2. Check Signal Rate (Max Signals / Hour)
        # For simplicity, we check total signals in last 1 hour
        # In a real system, use a sliding window or Redis counter
        from datetime import timedelta
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        signal_count = self.db.query(Signal).filter(
            Signal.created_at >= one_hour_ago
        ).count()

        if signal_count > settings.MAX_SIGNALS_PER_HOUR:
            self.tripped = True
            self.reason = f"MAX SIGNAL RATE EXCEEDED: {signal_count} > {settings.MAX_SIGNALS_PER_HOUR}/hr"
            self._trigger_pause()
            return False

        return True

    def _trigger_pause(self):
        """
        Auto-pause all active automations
        """
        print(f"!!! CIRCUIT BREAKER TRIPPED: {self.reason} !!!")
        print("!!! PAUSING ALL AUTOMATIONS !!!")
        
        automations = self.db.query(Automation).filter(Automation.status == "active").all()
        for auto in automations:
            auto.status = "paused_risk" # Special status
            print(f"   -> Paused {auto.name} ({auto.slug})")
        
        self.db.commit()

    def get_status(self):
        return {
            "is_tripped": self.tripped,
            "reason": self.reason
        }
