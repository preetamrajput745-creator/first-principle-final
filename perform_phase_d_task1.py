
import json
import csv
import datetime
import uuid
import sys
import os
import pandas as pd
import numpy as np
import random
from types import SimpleNamespace

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Import Feature Engine
# We need to mock config/storage/event_bus if they are imported at top level
# or if FeatureEngine uses them in __init__
# FeatureEngine imports settings, storage_client, event_bus at top level.
# We might need to mock these modules before importing FeatureEngine.

from unittest.mock import MagicMock
sys.modules['config'] = MagicMock()
sys.modules['storage'] = MagicMock()
sys.modules['event_bus'] = MagicMock()

# Now import FeatureEngine
# Use local path import trick if needed, but assuming standard import works if path is correct
from workers.fbe.feature_engine import FeatureEngine

# --- CONFIGURATION ---
DATE_UTC = datetime.datetime.utcnow().strftime("%Y-%m-%d")
TASK_ID = f"{DATE_UTC.replace('-', '')}-PHASED-TASK1-{uuid.uuid4().hex[:3]}"
BASE_DIR = os.path.abspath(".")
EVIDENCE_DIR = os.path.join(BASE_DIR, f"antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-d-feature-accuracy")

if not os.path.exists(EVIDENCE_DIR):
    os.makedirs(EVIDENCE_DIR)

print(f"Task ID: {TASK_ID}")
print(f"Evidence Directory: {EVIDENCE_DIR}")

# --- HELPERS ---

def write_csv(filename, headers, rows):
    filepath = os.path.join(EVIDENCE_DIR, filename)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return filepath

def write_json(filename, data):
    filepath = os.path.join(EVIDENCE_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath

# --- DATA GENERATION ---

def generate_bars(count=100):
    bars = []
    start_time = datetime.datetime.utcnow().replace(second=0, microsecond=0) - datetime.timedelta(minutes=count)
    
    price = 1000.0
    
    for i in range(count):
        # Random walk
        change = random.uniform(-2.0, 2.0)
        price += change
        
        # Create OHLC
        open_p = price
        high_p = price + random.uniform(0, 5.0)
        low_p = price - random.uniform(0, 5.0)
        close_p = (open_p + high_p + low_p) / 3 + random.uniform(-1.0, 1.0)
        
        # Ensure High is highest, Low is lowest
        high_p = max(open_p, high_p, close_p)
        low_p = min(open_p, low_p, close_p)
        
        vol = random.uniform(100, 500)
        
        bar_time = start_time + datetime.timedelta(minutes=i)
        
        bar = {
            "symbol": "BTC-USD",
            "time": bar_time.isoformat() + "Z", # ISO format
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": round(vol, 2),
            "clock_drift_ms": 10.0
        }
        bars.append(bar)
    return bars

# --- MANUAL CALCULATION ---

def calculate_manual_features(all_bars):
    """
    Calculates features for the LAST 20 bars in all_bars.
    Uses strict definition from prompt.
    """
    df = pd.DataFrame(all_bars)
    # Ensure correct types
    cols = ['open', 'high', 'low', 'close']
    for c in cols:
        df[c] = df[c].astype(float)
        
    results = []
    
    # We only want results for the last 20 bars
    # But we need full history for calculation
    start_index = len(df) - 20
    
    for i in range(start_index, len(df)):
        current_bar = df.iloc[i]
        timestamp = current_bar['time']
        
        # 1. ATR(14)
        # Definition: average of true range over last 14 bars
        # Assuming last 14 includes current? Usually yes for rolling.
        # Window: df.iloc[i-13 : i+1] (length 14)
        
        # Calculate TR for the window ending at i
        # We need to look back enough
        # We can calculate TR for the whole DF then take rolling
        
        # TR calculation
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR 14 (SMA of TR)
        atr_series = tr.rolling(window=14).mean()
        atr14_manual = atr_series.iloc[i]
        
        # 2. Upper Wick
        # high - max(open, close)
        calc_body_top = max(current_bar['open'], current_bar['close'])
        upper_wick_manual = current_bar['high'] - calc_body_top
        
        # 3. Lower Wick
        # min(open, close) - low
        calc_body_bottom = min(current_bar['open'], current_bar['close'])
        lower_wick_manual = calc_body_bottom - current_bar['low']
        
        # 4. SMA(20)
        # average(close price of last 20 bars)
        sma20_series = df['close'].rolling(window=20).mean()
        sma20_manual = sma20_series.iloc[i]
        
        # 5. Resistance Poke
        # high > max(high of previous N bars)
        # N = 60
        # previous 60 bars EXCLUDING current? "previous N bars" usually excludes current.
        # "previous N bars" -> iloc[i-N : i]
        
        N = 60
        if i >= N:
            prev_highs = df['high'].iloc[i-N : i]
            max_prev_high = prev_highs.max()
            resistance_poke_manual = current_bar['high'] > max_prev_high
        else:
            resistance_poke_manual = False # Not enough data
            
        results.append({
            "timestamp_utc": timestamp,
            "ATR14_manual": atr14_manual,
            "upper_wick_manual": upper_wick_manual,
            "lower_wick_manual": lower_wick_manual,
            "SMA20_manual": sma20_manual,
            "resistance_poke_manual": bool(resistance_poke_manual)
        })
        
    return results

# --- MAIN EXECUTION ---

def run_task():
    try:
        # 1. Generate Data (100 bars for context)
        # 80 bars context + 20 bars test
        bars = generate_bars(100) 
        
        # Export "Selected 20 bars" (The test set)
        test_bars = bars[-20:]
        
        # We export raw_bars_20.csv with columns requested
        raw_headers = ["timestamp_utc", "open", "high", "low", "close", "volume"]
        raw_rows = []
        for b in test_bars:
            raw_rows.append({
                "timestamp_utc": b['time'],
                "open": b['open'],
                "high": b['high'],
                "low": b['low'],
                "close": b['close'],
                "volume": b['volume']
            })
        write_csv("raw_bars_20.csv", raw_headers, raw_rows)
        
        # 2. Manual Calculation
        # We pass ALL bars to manual calculator but it returns only the last 20 results
        manual_results = calculate_manual_features(bars)
        
        # Export manual_features_20.csv
        manual_headers = ["timestamp_utc", "ATR14_manual", "upper_wick_manual", "lower_wick_manual", "SMA20_manual", "resistance_poke_manual"]
        write_csv("manual_features_20.csv", manual_headers, manual_results)
        
        # 3. Engine Execution
        engine = FeatureEngine()
        engine_outputs = []
        
        # We feed ALL bars into the engine to build state
        for bar in bars:
            snapshot = engine._calculate_features(bar['symbol'], bar)
            if snapshot:
                # Capture outputs for the test set timestamps
                # Check if this bar is in our test set
                if bar['time'] in [b['time'] for b in test_bars]:
                    engine_outputs.append({
                        "timestamp_utc": bar['time'],
                        "ATR14_engine": snapshot['features'].get('atr14'),
                        "upper_wick_engine": snapshot['features'].get('upper_wick'),
                        "lower_wick_engine": snapshot['features'].get('lower_wick'),
                        "SMA20_engine": snapshot['features'].get('sma20'),
                        "resistance_poke_engine": snapshot['features'].get('resistance_poke')
                    })
                    
        # Export engine_features_20.csv
        engine_headers = ["timestamp_utc", "ATR14_engine", "upper_wick_engine", "lower_wick_engine", "SMA20_engine", "resistance_poke_engine"]
        write_csv("engine_features_20.csv", engine_headers, engine_outputs)
        
        # 4. Validation (Compare)
        comparison_rows = []
        mismatches = 0
        
        # Convert lists to lookup
        manual_map = {r['timestamp_utc']: r for r in manual_results}
        engine_map = {r['timestamp_utc']: r for r in engine_outputs}
        
        # Features to check
        feature_map = [
            ("ATR14", "ATR14_manual", "ATR14_engine"),
            ("upper_wick", "upper_wick_manual", "upper_wick_engine"),
            ("lower_wick", "lower_wick_manual", "lower_wick_engine"),
            ("SMA20", "SMA20_manual", "SMA20_engine"),
            ("resistance_poke", "resistance_poke_manual", "resistance_poke_engine")
        ]
        
        for ts, m_row in manual_map.items():
            e_row = engine_map.get(ts)
            if not e_row:
                print(f"Missing engine row for {ts}")
                mismatches += 1
                continue
                
            for fname, m_key, e_key in feature_map:
                m_val = m_row[m_key]
                e_val = e_row[e_key]
                
                diff = 0
                diff_pct = 0
                status = "PASS"
                
                if isinstance(m_val, bool) or isinstance(e_val, bool):
                    # Boolean check
                     if m_val != e_val:
                         diff = 1
                         status = "FAIL"
                         mismatches += 1
                else:
                    # Numeric check
                    diff = abs(m_val - e_val)
                    if m_val != 0:
                        diff_pct = (diff / abs(m_val)) * 100
                    else:
                        diff_pct = 0 if diff == 0 else 100
                        
                    if diff_pct > 0.1: # 0.1% tolerance
                        status = "FAIL"
                        mismatches += 1
                
                comparison_rows.append({
                    "timestamp_utc": ts,
                    "feature_name": fname,
                    "manual_value": m_val,
                    "engine_value": e_val,
                    "difference": diff,
                    "difference_percent": diff_pct,
                    "status": status
                })
        
        write_csv("feature_comparison_20.csv", ["timestamp_utc", "feature_name", "manual_value", "engine_value", "difference", "difference_percent", "status"], comparison_rows)
        
        # JSON Summary
        summary_json = {
            "bars_checked": len(test_bars),
            "features_validated": ["ATR14","upper_wick","lower_wick","SMA20","resistance_poke"],
            "mismatches": mismatches,
            "status": "PASS" if mismatches == 0 else "FAIL"
        }
        write_json("feature_accuracy_summary.json", summary_json)
        
        if mismatches == 0:
            final_res = {
                "task_id": TASK_ID,
                "tester": "Mastermind",
                "date_utc": DATE_UTC,
                "phase": "PHASE D FEATURE ACCURACY",
                "task": "manual_vs_engine_feature_validation",
                "status": "PASS",
                "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-d-feature-accuracy/"
            }
            print(json.dumps(final_res, indent=2))
        else:
            final_res = {
                "task_id": TASK_ID,
                "tester": "Mastermind",
                "date_utc": DATE_UTC,
                "phase": "PHASE D FEATURE ACCURACY",
                "task": "manual_vs_engine_feature_validation",
                "status": "FAIL",
                "failure_reason": f"Mismatches detected: {mismatches}",
                "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-d-feature-accuracy/failure/"
            }
            print(json.dumps(final_res, indent=2))
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_task()
