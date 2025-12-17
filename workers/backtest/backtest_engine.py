"""
Backtest Engine - Mistake #4 Verification
Replays market data to compare "Ideal" vs "Realistic" PnL.
"""

import random
import time
import sys
import os

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.slippage import SlippageModel

class BacktestEngine:
    def __init__(self):
        self.slippage_model = SlippageModel()
        self.pnl_ideal = 0.0
        self.pnl_real = 0.0
        self.history = []

    def run_simulation(self, ticks=100):
        print("RUNNING BACKTEST SIMULATION (100 Ticks)")
        print("-" * 60)
        print(f"{'Tick':<5} | {'Action':<6} | {'Ideal Price':<10} | {'Real Price':<10} | {'Slip':<6} | {'Lag':<5} | {'PnL Gap':<10}")
        print("-" * 60)
        
        current_price = 21500.0
        position = 0 # 1 for Long, -1 for Short, 0 flat
        entry_price_ideal = 0.0
        entry_price_real = 0.0
        
        for i in range(ticks):
            # 1. Random Walk Price
            change = random.choice([-5, -2, 0, 2, 5])
            current_price += change
            is_volatile = abs(change) >= 5
            
            # 2. Simple Strategy: Mean Reversion
            action = "HOLD"
            if current_price < 21450 and position == 0:
                action = "BUY"
            elif current_price > 21550 and position == 0:
                action = "SELL"
            elif position == 1 and current_price > entry_price_ideal + 20:
                action = "EXIT"
            elif position == -1 and current_price < entry_price_ideal - 20:
                action = "EXIT"
                
            if action == "HOLD":
                continue
                
            # 3. Execution Simulation
            
            # Scenario A: Ideal (Mid Price, Instant)
            exec_ideal = current_price
            
            # Scenario B: Realistic (Slippage + Latency)
            # Latency means price might have moved against us while waiting
            latency_ms = self.slippage_model.simulate_latency()
            
            # Simulate price drift during latency (Micro-movement)
            drift = 0
            if latency_ms > 10: # If slow, price moves
                drift = random.choice([-1, 0, 1]) 
                
            price_at_arrival = current_price + drift
            
            # Apply Slippage
            slip_data = self.slippage_model.calculate_slippage("NIFTY", price_at_arrival, 1, is_volatile)
            
            if action == "BUY":
                exec_real = slip_data["estimated_buy_price"]
                position = 1
                entry_price_ideal = exec_ideal
                entry_price_real = exec_real
            elif action == "SELL":
                exec_real = slip_data["estimated_sell_price"]
                position = -1
                entry_price_ideal = exec_ideal
                entry_price_real = exec_real
            elif action == "EXIT":
                # Close Position
                if position == 1: # Selling to close
                    exec_real = slip_data["estimated_sell_price"]
                    pnl_i = exec_ideal - entry_price_ideal
                    pnl_r = exec_real - entry_price_real
                else: # Buying to close
                    exec_real = slip_data["estimated_buy_price"]
                    pnl_i = entry_price_ideal - exec_ideal
                    pnl_r = entry_price_real - exec_real
                
                self.pnl_ideal += pnl_i
                self.pnl_real += pnl_r
                position = 0
                
            # Log
            slip_val = round(abs(exec_real - exec_ideal), 2)
            gap = round(self.pnl_ideal - self.pnl_real, 2)
            print(f"{i:<5} | {action:<6} | {exec_ideal:<10.2f} | {exec_real:<10.2f} | {slip_val:<6.2f} | {latency_ms:<5.1f} | {gap:<10}")

        print("-" * 60)
        print(f"FINAL RESULTS:")
        print(f"Ideal PnL: {self.pnl_ideal:.2f}")
        print(f"Real PnL:  {self.pnl_real:.2f}")
        print(f"DIFFERENCE: {self.pnl_ideal - self.pnl_real:.2f} (This is the Cost of Lie)")
        print("-" * 60)

if __name__ == "__main__":
    engine = BacktestEngine()
    engine.run_simulation(200)
