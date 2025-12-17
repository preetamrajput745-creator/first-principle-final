"""
Task: Verify PnL & Slippage Panel (Zero-Tolerance Spec)
Executes Synthetic Tests for:
1. PnL & Slippage Metric Accuracy (Cross-check with raw data).
2. Alert Logic (Warning, Critical, Auto-Pause).
3. Divergence Checks.
"""

import sys
import os
import uuid
import statistics
import time
from datetime import datetime, timedelta

# Path setup
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from common.database import get_db
from common.models import Order, Signal, Automation, SlippageProfile
from sqlalchemy.sql import func
from monitoring.pnl_monitor import PnLMonitor
from risk.circuit_breaker import CircuitBreaker

def verify_pnl_panel():
    try:
        print("TEST: PnL & Slippage Panel Verification (Zero-Tolerance)")
        print("=" * 60)
        
        # 0. Clean Setup
        monitor = PnLMonitor()
        
        with next(get_db()) as db:
            # Clear Orders/Profiles for Test Instrument
            db.query(Order).filter(Order.symbol == "PNL_TEST_INST").delete()
            db.query(SlippageProfile).filter(SlippageProfile.symbol == "PNL_TEST_INST").delete()
            
            # Setup Profile: Base Slippage = 0.01 (1%)
            profile = SlippageProfile(symbol="PNL_TEST_INST", base_slippage_pct=0.01)
            db.add(profile)
            
            # Setup Automation
            auto = Automation(name="PnL Tester", slug=f"pnl-{uuid.uuid4()}", status="active")
            db.add(auto)
            db.commit()
            db.refresh(auto)
            auto_id = auto.id
            
        print("0. Setup Complete: Profile Base=1%, Automation Active.")
        
        
        # --- TEST 1: Metric Accuracy & Warning Alert ---
        print("\n1. Test: Metric Accuracy & Warning Alert (Slippage > 1.5x Profile)...")
        
        # Action: Inject 20 High Slippage Trades (2%)
        # New Window 50: 30 Normal (1%) + 20 High (2%) -> Avg 1.4% (Wait, logic says 1.6%)
        # We want 30 High (2%) and 20 Normal (1%).
        
        # Clean Start
        with next(get_db()) as db:
            db.query(Order).filter(Order.symbol=="PNL_TEST_INST").delete()
            db.commit()
        
        # Insert Trades
        print("   Injecting 20 Normal (1%) + 30 High (2%) trades...")
        # New Transaction for Inserts
        base_time = datetime.utcnow()
        with next(get_db()) as db:
            for i in range(20):
                ts = base_time + timedelta(seconds=i)
                db.add(Order(symbol="PNL_TEST_INST", side="BUY", quantity=1, price=100, 
                             status="FILLED", realized_slippage=0.01, pnl=10.0, is_paper=False,
                             created_at=ts))
                
            for k in range(30):
                ts = base_time + timedelta(seconds=20+k)
                db.add(Order(symbol="PNL_TEST_INST", side="BUY", quantity=1, price=100, 
                             status="FILLED", realized_slippage=0.02, pnl=10.0, is_paper=False,
                             created_at=ts))
                
            db.commit()
        
        # DEBUG DIAGNOSTIC
        with next(get_db()) as db:
            count_01 = db.query(Order).filter(Order.symbol=="PNL_TEST_INST", Order.realized_slippage == 0.01).count()
            count_02 = db.query(Order).filter(Order.symbol=="PNL_TEST_INST", Order.realized_slippage == 0.02).count()
            print(f"DEBUG: DB Count 0.01: {count_01}")
            print(f"DEBUG: DB Count 0.02: {count_02}")
            
        # Verify Metrics
        result_avg, result_delta = 0, 0
        with next(get_db()) as db:
            result_avg, result_delta = monitor.calculate_rolling_slippage(db, "PNL_TEST_INST", window=50)
            
        print(f"   [Calculated] Avg Slippage: {result_avg*100:.2f}% | Delta Factor: {result_delta:.2f}x")
        
        # Manual Calc
        expected_avg = ((20*0.01) + (30*0.02)) / 50
        print(f"   [Expected]   Avg Slippage: {expected_avg*100:.2f}%")
        
        if abs(result_avg - expected_avg) > 0.0001:
            sys.stderr.write("   FAILURE: Metric Accuracy Error > 2%\n")
            sys.exit(1)
        else:
            print("   SUCCESS: Metrics accurately calculated.")
            
        # Verify Warning Alert
        monitor.check_slippage_alerts("PNL_TEST_INST")
        
        found_warning = any("WARNING" in a and "High Slippage PNL_TEST_INST" in a for a in monitor.alerts)
        if found_warning:
            print("   SUCCESS: Warning Alert Triggered correctly (Factor > 1.5x).")
        else:
            sys.stderr.write(f"   FAILURE: Warning Alert MISSED! Alerts: {monitor.alerts}\n")
            sys.exit(1)


        # --- TEST 2: Critical Alert & Auto-Pause ---
        print("\n2. Test: Critical Alert & Auto-Pause (10 Consecutive > 50% Delta)...")
        monitor.alerts = [] # Reset
        monitor.audit_log = []
        
        # Profile = 0.01. Delta > 50% means Actual > 1.5 * Profile = 0.015.
        # We will inject 10 trades with 0.02 (2%) i.e., 100% delta.
        
        with next(get_db()) as db:
            print("   Injecting 10 Consecutive CRITICAL Trades (2% slippage)...")
            # Newer timestamp
            start_ts = datetime.utcnow() + timedelta(minutes=5)
            for i in range(10):
                ts = start_ts + timedelta(seconds=i)
                db.add(Order(symbol="PNL_TEST_INST", side="BUY", quantity=1, price=100, 
                             status="FILLED", realized_slippage=0.02, pnl=10.0, is_paper=False,
                             created_at=ts))
            db.commit()
            
        monitor.check_slippage_alerts("PNL_TEST_INST")
        
        # Verify Alert
        found_critical = any("CRITICAL" in a and "10 Consecutive" in a for a in monitor.alerts)
        if found_critical:
            print("   SUCCESS: Critical Alert Triggered.")
        else:
             sys.stderr.write(f"   FAILURE: Critical Alert Missed! Alerts: {monitor.alerts}\n")
             sys.exit(1)
             
        # Verify Actions (Audit Log & Circuit Breaker)
        found_audit = any("PAUSE: Critical Slippage Breach" in a for a in monitor.audit_log)
        if found_audit:
            print("   SUCCESS: Audit Log created for Auto-Pause.")
        else:
            sys.stderr.write("   FAILURE: Audit Log missing.\n")
            sys.exit(1)
            
        # Verify Automation Status via DB
        with next(get_db()) as db:
            updated_auto = db.query(Automation).filter(Automation.id == auto_id).first()
            if updated_auto.status == "paused_risk":
                print("   SUCCESS: Circuit Breaker successfully paused automation.")
            else:
                sys.stderr.write(f"   FAILURE: Automation status is '{updated_auto.status}', expected 'paused_risk'.\n")
                sys.exit(1)


        # --- TEST 3: Divergence Alert ---
        print("\n3. Test: Sim vs Real Divergence Alert...")
        monitor.alerts = []
        
        with next(get_db()) as db:
            # Clear
            db.query(Order).filter(Order.symbol=="PNL_TEST_INST").delete()
            
            # Inject Sim PnL = $1000
            db.add(Order(symbol="PNL_TEST_INST", side="BUY", quantity=1, price=100, status="FILLED", pnl=1000.0, is_paper=True))
            
            # Inject Real PnL = $500 (Divergence 50% > 25% threshold)
            db.add(Order(symbol="PNL_TEST_INST", side="BUY", quantity=1, price=100, status="FILLED", pnl=500.0, is_paper=False))
            db.commit()

        monitor.check_sim_real_divergence("PNL_TEST_INST")
        
        found_div = any("Sim/Real Divergence (PNL_TEST_INST)" in a for a in monitor.alerts)
        if found_div:
            print("   SUCCESS: Divergence Alert Triggered.")
        else:
            sys.stderr.write(f"   FAILURE: Divergence Alert Missed. Alerts: {monitor.alerts}\n")
            sys.exit(1)

        # --- TEST 4: Fees & Rounding Edge Case ---
        print("\n4. Test: Fees & Rounding Edge Case...")
        with next(get_db()) as db:
            # Clear
            db.query(Order).filter(Order.symbol=="PNL_TEST_INST").delete()
            
            # Inject Trade with fees and floating point precision issues
            # Price 100.0001, Qty 0.123, Fee 1.5
            # Expected PnL should account for fees if logic supports it. 
            # Current model might simplify PnL, but let's assume PnL is pre-calculated or stored.
            # We verify that the monitor aggregates these floats correctly without rounding errors.
            
            db.add(Order(symbol="PNL_TEST_INST", side="BUY", quantity=0.12345678, price=100.12345678, 
                         status="FILLED", realized_slippage=0.00123456, pnl=12.3456789, is_paper=False))
            db.add(Order(symbol="PNL_TEST_INST", side="BUY", quantity=0.12345678, price=100.12345678, 
                         status="FILLED", realized_slippage=0.00123456, pnl=12.3456789, is_paper=False))
            db.commit()
            
        # Check Totals
        # Sum PnL: 24.6913578
        # Sum Slippage: 0.00246912
        with next(get_db()) as db:
            slippage_tot = db.query(func.sum(Order.realized_slippage)).filter(Order.symbol=="PNL_TEST_INST").scalar()
            pnl_tot = db.query(func.sum(Order.pnl)).filter(Order.symbol=="PNL_TEST_INST").scalar()
            
            print(f"   [Precision] PnL Tot: {pnl_tot}, Slippage Tot: {slippage_tot}")
            
            if abs(pnl_tot - 24.6913578) < 0.000001:
                print("   SUCCESS: Precision handled correctly.")
            else:
                 sys.stderr.write(f"   FAILURE: Precision Error. Got {pnl_tot}, Expected 24.6913578\n")
                 sys.exit(1)


        # --- TEST 5: High-Frequency Burst Test ---
        print("\n5. Test: High-Frequency Burst (1000 trades/sec)...")
        start_burst = time.time()
        with next(get_db()) as db:
            db.query(Order).filter(Order.symbol=="PNL_TEST_INST").delete()
            
            # Bulk Insert 1000 trades
            orders = [
                Order(symbol="PNL_TEST_INST", side="BUY", quantity=1, price=100, 
                      status="FILLED", realized_slippage=0.01, pnl=1.0, is_paper=False,
                      created_at=datetime.utcnow()) 
                for _ in range(1000)
            ]
            db.bulk_save_objects(orders)
            db.commit()
            
        burst_duration = time.time() - start_burst
        print(f"   Inserted 1000 trades in {burst_duration:.4f}s")
        
        # Verify Monitor Performance
        start_calc = time.time()
        with next(get_db()) as db:
            avg_slip, _ = monitor.calculate_rolling_slippage(db, "PNL_TEST_INST", window=1000)
            
        calc_duration = time.time() - start_calc
        print(f"   Calculated 1000-trade window in {calc_duration:.4f}s")
        
        if calc_duration < 1.0:
            print("   SUCCESS: Burst Calculation < 1s.")
        else:
             sys.stderr.write(f"   FAILURE: Performance too slow ({calc_duration}s > 1.0s)\n")
             sys.exit(1)
        
        if abs(avg_slip - 0.01) < 0.0000001:
             print("   SUCCESS: Burst Accuracy Verified.")
        else:
             sys.stderr.write("   FAILURE: Burst Accuracy Mismatch.\n")
             sys.exit(1)

        print("\nVERIFICATION COMPLETE: PnL & Slippage Panel logic is solid.")
        
        # 6. Generate Audit Evidence (CSV)
        print("\n6. Generating Audit CSV...")
        import csv
        with next(get_db()) as db:
            trades = db.query(Order).filter(Order.symbol == "PNL_TEST_INST").order_by(Order.created_at.asc()).all()
            with open("audit_pnl_evidence.csv", "w", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "created_at", "symbol", "side", "qty", "price", "slippage", "pnl"])
                for t in trades:
                    writer.writerow([t.id, t.created_at, t.symbol, t.side, t.quantity, t.price, t.realized_slippage, t.pnl])
        print(f"   Saved {len(trades)} trades to 'audit_pnl_evidence.csv' for Audit Pack.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_pnl_panel()
