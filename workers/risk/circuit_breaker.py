"""
Circuit Breaker Service - Mistake #10 Compliance
Prevents system runaway by enforcing global limits.
"""

import sys
import os
from datetime import datetime, timedelta

# Correct path to include 'workers' directory so 'common' can be imported
current_dir = os.path.dirname(os.path.abspath(__file__)) # workers/risk
workers_dir = os.path.dirname(current_dir) # workers
sys.path.insert(0, workers_dir)

from common.database import get_db
from common.models import Signal, Automation
from sqlalchemy.sql import func

class CircuitBreaker:
    """
    Risk controller that can PAUSE automations.
    """
    
    def __init__(self):
        self.max_signals_per_hour = 10
        self.max_daily_loss = 500.0
        self.max_error_rate_pct = 0.5 # 50% failure rate triggers breaker
        self.min_orders_for_error_check = 5 # Minimum orders to calculate rate
        from workers.risk.safety_logger import SafetyLogger
        self.logger = SafetyLogger()
        pass

    def send_pager_alert(self, message: str):
        """
        Mock PagerDuty/OpsGenie Alert.
        In production, this would make an HTTP POST to the alerting provider.
        """
        print(f"PAGERDUTY_ALERT: {message}")
        
    def pause_all_active_automations(self, reason: str):
        """
        Global Kill Switch.
        Pauses ALL active automations.
        """
        with next(get_db()) as db:
            active_autos = db.query(Automation).filter(Automation.status == "active").all()
            count = 0
            for auto in active_autos:
                auto.status = "paused_risk"
                
                # LOG SAFETY EVENT (Task 12)
                self.logger.log_event(
                    component="circuit_breaker",
                    event_type="auto_pause",
                    actor="system",
                    reason=reason,
                    target=auto.name,
                    trigger_rule="global_kill_switch",
                notes=f"ID: {auto.id}"
                )
                
                count += 1
            db.commit()
            
            msg = f"GLOBAL CIRCUIT BREAKER TRIPPED: {reason}. Paused {count} automations."
            print(msg)
            self.send_pager_alert(msg)
            
            # Log Global Event (Legacy Safety Panel)
            self.logger.log_event(
                component="circuit_breaker",
                event_type="breaker_open",
                actor="system",
                reason=reason,
                trigger_rule="global_kill_switch",
                notes=f"Global Kill Switch Activated. Count: {count}"
            )
            
            # NEW: Deliverable #5 - Trip Global Breaker via Service (Audit Trail)
            try:
                from services.circuit_breaker_service import CircuitBreakerService
                # Re-use DB session? get_db() yields new session. Ideally share session.
                # Since we committed above, safe to start new transaction or use separate session.
                # However, get_db() context is already closed when 'with next(get_db()) as db' exits?
                # No, we are inside 'with next(get_db()) as db'.
                # But 'db' variable is available.
                
                service = CircuitBreakerService(db)
                # Ensure global breaker exists
                service.create_or_update_breaker("global", "global", "system")
                # Trip it
                service.transition_state(
                    breaker_id="global",
                    new_state="OPEN",
                    actor="system",
                    reason=reason,
                    change_context="rule",
                    notes="Auto-tripped by Risk Engine (Mistake #10)"
                )
                print("CIRCUIT BREAKER: Global State set to OPEN in CircuitBreakerService.")
            except Exception as e:
                print(f"ERROR updating CircuitBreakerService: {e}")

    def check_signal_rate(self, auto_pause: bool = False) -> bool:
        """
        Check if signal generation is within limits.
        """
        with next(get_db()) as db:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            count = db.query(Signal).filter(Signal.created_at >= one_hour_ago).count()
            
            if count >= self.max_signals_per_hour:
                reason = f"Signal rate exceeded ({count}/{self.max_signals_per_hour}/hr)"
                print(f"CIRCUIT BREAKER: {reason}")
                if auto_pause:
                    self.pause_all_active_automations(reason)
                return False
            return True

    def check_error_rate(self, auto_pause: bool = False) -> bool:
        """
        Check for high rejection rates (System Health).
        Mistake #7 Requirement: Watch error rates.
        """
        from common.models import Order
        with next(get_db()) as db:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            total_orders = db.query(Order).filter(Order.created_at >= one_hour_ago).count()
            
            if total_orders < self.min_orders_for_error_check:
                return True # Not enough data
                
            failed_orders = db.query(Order).filter(
                Order.created_at >= one_hour_ago,
                Order.status == "REJECTED"
            ).count()
            
            error_rate = failed_orders / total_orders
            
            if error_rate >= self.max_error_rate_pct:
                reason = f"High Error Rate Detected: {error_rate*100:.1f}% ({failed_orders}/{total_orders} Rejected)"
                print(f"CIRCUIT BREAKER: {reason}")
                if auto_pause:
                    self.pause_all_active_automations(reason)
                return False
                
            return True

    def check_concurrent_orders(self, automation_id: str) -> bool:
        """
        Check if we exceed max concurrent open/active positions (orders).
        Mistake #10 Requirement C.
        """
        from common.models import Order
        import uuid
        
        MAX_CONCURRENT = 5
        
        with next(get_db()) as db:
            # Check for orders that are FILLED but not Exited (exit_time is Null)
            # Assuming 'FILLED' means position open.
            open_count = db.query(Order).filter(
                Order.status == "FILLED",
                Order.exit_time == None
            ).count()
            
            if open_count >= MAX_CONCURRENT:
                print(f"CIRCUIT BREAKER: Max concurrent orders limit ({open_count}/{MAX_CONCURRENT}) hit!")
                return False
                
            return True

    def check_pnl_health(self, auto_pause: bool = False) -> bool:
        """
        Check if we hit daily loss limit.
        """
        with next(get_db()) as db:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check Daily PnL
            from common.models import Order
            
            # Sum PnL for today's filled orders
            daily_pnl = db.query(func.sum(Order.pnl)).filter(
                Order.created_at >= today_start,
                Order.pnl != None
            ).scalar() or 0.0
            
            # Loss is negative PnL. If daily_pnl is -600, and max_loss is 500, we trip.
            # max_daily_loss is positive float (e.g. 500.0)
            if daily_pnl < -(self.max_daily_loss):
                 reason = f"Max daily loss exceeded (PnL: ${daily_pnl:.2f} < Limit: -${self.max_daily_loss})"
                 print(f"CIRCUIT BREAKER: {reason}")
                 if auto_pause:
                     self.pause_all_active_automations(reason)
                 return False
                 
            return True
            
    def check_slippage_health(self, auto_pause: bool = False) -> bool:
        """
        Check for consecutive high slippage events.
        New Requirement: If slippage_delta > 50% for 10 consecutive trades -> PAUSE.
        """
        from common.models import Order
        with next(get_db()) as db:
            # Fetch last 10 filled orders
            orders = db.query(Order).filter(Order.status == "FILLED").order_by(Order.created_at.desc()).limit(10).all()
            
            if len(orders) < 10:
                return True
                
            consecutive_high_slippage = 0
            for order in orders:
                # We assume 'realized_slippage' is stored in Order
                # Slippage Delta % = (Realized / Price) * 100? Or just raw count?
                # Spec says "slippage_delta > 50%".
                # Standard slippage calculation: |(Fill - Request) / Request|
                # If > 0.5 (50%), it's high.
                
                # Check if we have necessary fields
                if not order.price or order.price == 0: continue
                if order.realized_slippage is None: continue
                
                # Calculate % slippage
                # Note: realized_slippage in model is usually absolute amount ($).
                slippage_pct = abs(order.realized_slippage) / order.price
                
                if slippage_pct > 0.5: # 50%
                    consecutive_high_slippage += 1
                else:
                    # Break sequence if we find a good trade? 
                    # Spec says "10 consecutive trades". So yes, must be all 10.
                    break
            
            if consecutive_high_slippage >= 10:
                reason = "Circuit Breaker: 10 Consecutive High Slippage Trades (>50%)"
                print(f"CIRCUIT BREAKER: {reason}")
                if auto_pause:
                    self.pause_all_active_automations(reason)
                return False
                
            return True

    def check_market_regime(self, auto_pause: bool = False) -> bool:
        """
        Mistake #12: Regime Filtering.
        Checks if the current market regime permits trading.
        """
        with next(get_db()) as db:
            # Check latest signal for regime tag
            latest_signal = db.query(Signal).order_by(Signal.timestamp.desc()).first()
            
            if not latest_signal or not latest_signal.regime_volatility:
                return True # No data, assume normal (or fail safe? Project usually assumes continue)
                
            if latest_signal.regime_volatility == "high_volatility":
                reason = "High Volatility Regime Detected (Regime Filter)"
                print(f"CIRCUIT BREAKER: {reason}")
                
                if auto_pause:
                    self.pause_all_active_automations(reason)
                return False
                
            return True


    def trigger_pause(self, automation_id: str):
        """
        Pause an automation due to risk breach.
        """
        with next(get_db()) as db:
            import uuid
            auto = db.query(Automation).filter(Automation.id == uuid.UUID(automation_id)).first()
            if auto and auto.status == "active":
                auto.status = "paused_risk"
                db.commit()
                msg = f"Automation {auto.name} PAUSED due to risk breach."
                print(f"CIRCUIT BREAKER: {msg}")
                self.send_pager_alert(msg)
                
                # LOG SAFETY EVENT (Task 12)
                self.logger.log_event(
                    component="automation",
                    event_type="auto_pause",
                    actor="system",
                    reason=msg,
                    target=auto.name,
                    trigger_rule="risk_breach",
                    notes=f"ID: {auto.id}"
                )

if __name__ == "__main__":
    cb = CircuitBreaker()
    is_safe = cb.check_signal_rate()
    print(f"System Safe: {is_safe}")
