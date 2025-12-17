import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# 1. Setup Mocks BEFORE importing feature_engine
# This prevents actual connections to Redis/S3/EventBus
sys.modules['storage'] = MagicMock()
sys.modules['event_bus'] = MagicMock()
sys.modules['config'] = MagicMock()

# Mock Settings
mock_settings = MagicMock()
mock_settings.SYMBOLS = ["NIFTY_FUT"]
mock_settings.REDIS_HOST = "localhost"
sys.modules['config'].settings = mock_settings

# Now import valid codebase
# We need to add workers/fbe to path or just import by path
sys.path.append(os.path.join(os.getcwd(), 'workers', 'fbe'))

# Also need root for config/storage imports inside feature_engine if they are not caught by sys.modules above
# But we mocked them in sys.modules, so import should grab the mocks.

try:
    from workers.fbe.feature_engine import FeatureEngine
except ImportError:
    # Fallback if path issues
    sys.path.append(os.path.join(os.getcwd()))
    from workers.fbe.feature_engine import FeatureEngine

# Config
OUTPUT_DIR = "s3_audit_local/phase-d-feature-accuracy"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

TASK_ID = f"{datetime.utcnow().strftime('%Y%m%d')}-PHASED-TASK1"
DATE_UTC = datetime.utcnow().strftime("%Y-%m-%d")

def generate_synthetic_data(count=100):
    bars = []
    price = 100.0
    base_time = datetime.utcnow() - timedelta(minutes=count)
    
    # Generate random walk
    for i in range(count):
        mid = price + np.random.normal(0, 0.2)
        high = mid + abs(np.random.normal(0, 0.1))
        low = mid - abs(np.random.normal(0, 0.1))
        close = mid + np.random.normal(0, 0.05)
        
        # Ensure High/Low consistency
        high = max(high, max(mid, close))
        low = min(low, min(mid, close))
        
        # Volume
        vol = 100 + int(np.random.normal(0, 10))
        
        bars.append({
            "symbol": "NIFTY_FUT",
            "open": round(mid, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": vol,
            "time": (base_time + timedelta(minutes=i)).isoformat(),
            "clock_drift_ms": 10
        })
        price = close
        
    return bars

def calculate_manual_features(all_bars):
    # We only care about producing results for the last 20 bars
    # But we need history for calculation
    
    df = pd.DataFrame(all_bars)
    results = []
    
    # Engine Settings
    LOOKBACK_POKE = 60
    
    # We iterate through the LAST 20 bars
    start_idx = len(df) - 20
    
    for i in range(start_idx, len(df)):
        current_bar = df.iloc[i]
        bar_time = current_bar['time']
        
        # history subset for this bar (engine includes current bar in history usually? 
        # FeatureEngine._calculate_features: 
        # self.history[symbol].append(new_bar) -> then operations.
        # So yes, history includes current bar.
        
        history = df.iloc[:i+1] # up to current inclusive
        
        # 1. ATR 14
        # Engine: _calculate_atr(df, 14) -> rolling mean of TR
        # TR = max(h-l, abs(h-yc), abs(l-yc))
        # Need at least 15 bars? Engine says len >= period+1.
        
        if len(history) >= 15:
            # Reimplement TR
            high = history['high']
            low = history['low']
            close = history['close'].shift(1)
            
            tr1 = high - low
            tr2 = (high - close).abs()
            tr3 = (low - close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr14 = tr.rolling(window=14).mean().iloc[-1]
        else:
            atr14 = 0.0

        # 2. SMA 20
        # Engine: _calculate_sma(df['close'], 20) -> rolling mean
        if len(history) >= 20:
            sma20 = history['close'].rolling(window=20).mean().iloc[-1]
        else:
            sma20 = 0.0
            
        # 3. Wicks
        open_p = current_bar['open']
        close_p = current_bar['close']
        high_p = current_bar['high']
        low_p = current_bar['low']
        
        upper_wick = high_p - max(open_p, close_p)
        lower_wick = min(open_p, close_p) - low_p
        
        # 4. Resistance Poke (N=60)
        # Engine: prev_bars = df.iloc[:-1]
        # recent_high = prev_bars['high'].tail(60).max()
        # resistance_poke = high > recent_high
        
        prev_bars = history.iloc[:-1]
        if len(prev_bars) > 0:
            recent_high = prev_bars['high'].tail(LOOKBACK_POKE).max()
            resistance_poke = current_bar['high'] > recent_high
        else:
            resistance_poke = False
            
        results.append({
            "timestamp_utc": bar_time,
            "ATR14_manual": float(atr14),
            "upper_wick_manual": float(upper_wick),
            "lower_wick_manual": float(lower_wick),
            "SMA20_manual": float(sma20),
            "resistance_poke_manual": bool(resistance_poke)
        })
        
    return pd.DataFrame(results)

def main():
    print("Starting Phase D Task 1 Validation...")
    
    # 1. Generate Data
    bars = generate_synthetic_data(100) # 100 bars ensures we cover N=60 + 20 window
    
    # Save the last 20 as raw_bars_20.csv (The Deliverable)
    # We only expose the last 20 to the output, as requested, 
    # but strictly speaking we needed the history. 
    # The prompt says "Select 20... Manually compute". 
    # We will provide the manual results for these 20.
    
    df_bars_20 = pd.DataFrame(bars[-20:])
    raw_path = os.path.join(OUTPUT_DIR, "raw_bars_20.csv")
    csv_cols = ["time", "open", "high", "low", "close", "volume"]
    # Rename time -> timestamp_utc for requirement
    df_bars_20.rename(columns={"time": "timestamp_utc"}, inplace=True)
    df_bars_20[["timestamp_utc", "open", "high", "low", "close", "volume"]].to_csv(raw_path, index=False)
    
    # 2. Run Engine (Validation Target)
    engine = FeatureEngine()
    engine_results = []
    
    for bar in bars:
        # We need to simulate the engine processing bar by bar
        # Engine returns a snapshot if valid
        # We are only interested in the results for the last 20 bars
        
        # FeatureEngine._calculate_features returns a dict
        snap = engine._calculate_features("NIFTY_FUT", bar)
        
        # If this bar is in our target last 20, verify it
        if bar['time'] in df_bars_20['timestamp_utc'].values:
            if snap:
                feats = snap['features']
                engine_results.append({
                    "timestamp_utc": bar['time'],
                    "ATR14_engine": feats['atr14'],
                    "upper_wick_engine": feats['upper_wick'],
                    "lower_wick_engine": feats['lower_wick'],
                    "SMA20_engine": feats['sma20'],
                    "resistance_poke_engine": feats['resistance_poke']
                })
            else:
                 # Should not happen given 100 bars history
                 print(f"Warning: Engine returned None for {bar['time']}")
    
    df_engine = pd.DataFrame(engine_results)
    df_engine.to_csv(os.path.join(OUTPUT_DIR, "engine_features_20.csv"), index=False)
    
    # 3. Run Manual Calculation (The Verifier)
    df_manual = calculate_manual_features(bars)
    df_manual.to_csv(os.path.join(OUTPUT_DIR, "manual_features_20.csv"), index=False)
    
    # 4. Compare
    comparison_rows = []
    mismatches = 0
    
    # Merge on timestamp
    merged = pd.merge(df_manual, df_engine, on="timestamp_utc")
    
    features_map = [
        ("ATR14", "ATR14_manual", "ATR14_engine"),
        ("upper_wick", "upper_wick_manual", "upper_wick_engine"),
        ("lower_wick", "lower_wick_manual", "lower_wick_engine"),
        ("SMA20", "SMA20_manual", "SMA20_engine"),
        ("resistance_poke", "resistance_poke_manual", "resistance_poke_engine")
    ]
    
    for _, row in merged.iterrows():
        ts = row['timestamp_utc']
        
        for fname, col_man, col_eng in features_map:
            val_man = row[col_man]
            val_eng = row[col_eng]
            
            diff = 0.0
            diff_pct = 0.0
            
            if fname == "resistance_poke":
                # Boolean check
                if val_man != val_eng:
                    mismatches += 1
                    diff = 1.0
                pass
            else:
                # Float check
                diff = abs(val_eng - val_man)
                denom = max(abs(val_man), 1e-9)
                diff_pct = (diff / denom) * 100.0
                
                # Rule: <= 0.1%
                if diff_pct > 0.1:
                    mismatches += 1
            
            comparison_rows.append({
                "timestamp_utc": ts,
                "feature_name": fname,
                "manual_value": val_man,
                "engine_value": val_eng,
                "difference": diff,
                "difference_percent": diff_pct
            })
            
    df_comp = pd.DataFrame(comparison_rows)
    df_comp.to_csv(os.path.join(OUTPUT_DIR, "feature_comparison_20.csv"), index=False)
    
    # 5. Summary
    status = "PASS" if mismatches == 0 else "FAIL"
    summary = {
        "bars_checked": 20,
        "features_validated": ["ATR14","upper_wick","lower_wick","SMA20","resistance_poke"],
        "mismatches": mismatches,
        "status": status
    }
    
    with open(os.path.join(OUTPUT_DIR, "feature_accuracy_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
        
    print(f"Validation Finished. Status: {status}")
    
    # Final Output Json
    final_out = {
      "task_id": TASK_ID,
      "tester": "Mastermind",
      "date_utc": DATE_UTC,
      "phase": "PHASE D FEATURE ACCURACY",
      "task": "manual_vs_engine_feature_validation",
      "status": status,
      "evidence_s3": f"s3://antigravity-audit/{DATE_UTC}/{TASK_ID}/phase-d-feature-accuracy/"
    }
    
    if status == "FAIL":
        final_out["failure_reason"] = f"Found {mismatches} mismatches"
        final_out["evidence_s3"] += "failure/"
        
    print("FINAL_JSON_OUTPUT_START")
    print(json.dumps(final_out, indent=2))
    print("FINAL_JSON_OUTPUT_END")

if __name__ == "__main__":
    main()
