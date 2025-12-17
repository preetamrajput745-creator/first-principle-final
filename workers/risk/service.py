
import time
import sys
import os

# Add root to python path to allow imports from common
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from workers.risk.circuit_breaker import CircuitBreaker

def run_risk_service():
    print("---------------------------------------------------")
    print("   RISK/CIRCUIT BREAKER SERVICE STARTED")
    print("   Monitoring: PnL, Error Rates, Signal Rates")
    print("---------------------------------------------------")
    
    cb = CircuitBreaker()
    
    # Loop Interval: 10 seconds? 
    # Real systems might be faster, but 10s is safe for polling DB.
    INTERVAL_SECONDS = 10
    
    while True:
        try:
            # 1. Check PnL (Daily Loss)
            if not cb.check_pnl_health(auto_pause=True):
                print("[RISK] PnL Breaker Tripped!")
                
            # 2. Check Signal Rate (Runaway Algo)
            if not cb.check_signal_rate(auto_pause=True):
                print("[RISK] Signal Rate Breaker Tripped!")
                
            # 3. Check Error Rates (System Health)
            if not cb.check_error_rate(auto_pause=True):
                 print("[RISK] Error Rate Breaker Tripped!")
            
            # Heartbeat logging?
            # print("[RISK] System Checks OK.")
            
            time.sleep(INTERVAL_SECONDS)
            
        except Exception as e:
            print(f"[RISK] Monitor Error: {e}")
            time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_risk_service()
