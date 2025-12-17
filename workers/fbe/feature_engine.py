import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from config import settings
from storage import storage_client
from event_bus import event_bus

class FeatureEngine:
    def __init__(self):
        # In-memory history for rolling calculations. 
        # Key: symbol, Value: DataFrame or list of dicts
        self.history = {} 
        self.min_history_len = 20 # Need at least 20 for SMA20, 14 for ATR
        self.lookback_window = 60 # For support/resistance

    def _calculate_atr(self, df, period=14):
        if len(df) < period + 1:
            return 0.0
        
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        return float(atr)

    def _calculate_sma(self, series, period=20):
        if len(series) < period:
            return 0.0
        return float(series.rolling(window=period).mean().iloc[-1])

    def _calculate_features(self, symbol, new_bar):
        # Update history
        if symbol not in self.history:
            self.history[symbol] = []
        
        self.history[symbol].append(new_bar)
        
        # Keep history manageable
        if len(self.history[symbol]) > 100:
            self.history[symbol].pop(0)
            
        df = pd.DataFrame(self.history[symbol])
        
        if len(df) < 20:
            print(f"Not enough data for {symbol}: {len(df)}")
            return None

        # 1. ATR 14
        atr14 = self._calculate_atr(df, 14)
        
        # 2. Volume SMA 20
        vol_sma20 = self._calculate_sma(df['volume'], 20)
        vol_ratio = float(new_bar['volume'] / vol_sma20) if vol_sma20 > 0 else 0.0
        
        # 2b. Price SMA 20 (Requested by Phase D)
        sma20 = self._calculate_sma(df['close'], 20)
        
        # 3. Wicks
        open_p = new_bar['open']
        close_p = new_bar['close']
        high_p = new_bar['high']
        low_p = new_bar['low']
        
        # Determine candle body and wicks
        body_top = max(open_p, close_p)
        body_bottom = min(open_p, close_p)
        
        upper_wick = high_p - body_top
        lower_wick = body_bottom - low_p
        
        # For False Breakout, we care about the "rejection" wick.
        # If Green candle (Close > Open), rejection is usually upper wick (failed to go higher)? 
        # Or if we are looking for Bear Trap (Hammer), it's lower wick.
        # The prompt implies generic "wick". Let's take the larger wick for now or both.
        # "wick_ratio (wick/ATR)"
        
        max_wick = max(upper_wick, lower_wick)
        wick_ratio = max_wick / atr14 if atr14 > 0 else 0.0
        
        # 4. Support/Resistance Poke
        # Simple logic: Find max/min of last N bars (excluding current)
        # If current High > Prev Max but Close < Prev Max -> False Breakout (Bearish)
        # If current Low < Prev Min but Close > Prev Min -> False Breakout (Bullish)
        
        prev_bars = df.iloc[:-1] # Exclude current
        recent_high = prev_bars['high'].tail(self.lookback_window).max()
        recent_low = prev_bars['low'].tail(self.lookback_window).min()
        
        resistance_level = float(recent_high)
        support_level = float(recent_low)
        
        resistance_level = float(recent_high)
        support_level = float(recent_low)
        
        # Phase D: "Resistance poke" = high > max(high of previous N bars)
        # N=60 (lookback_window)
        # This is strictly "Did we poke the resistance level?"
        resistance_poke = high_p > resistance_level if not np.isnan(resistance_level) else False

        poke_distance = 0.0
        is_poke = False
        
        # Check Bearish Fakeout (Upside)
        if high_p > resistance_level and close_p < resistance_level:
            poke_distance = high_p - resistance_level
            is_poke = True
            
        # Check Bullish Fakeout (Downside)
        elif low_p < support_level and close_p > support_level:
            poke_distance = support_level - low_p
            is_poke = True
            
        # Construct Snapshot
        snapshot = {
            "symbol": symbol,
            "bar_time": new_bar['time'],
            "ohlcv": new_bar,
            # Mistake #11: "L2" Snapshot (Actually L1/Top-of-Book for this MVP)
            "l1_snapshot": {
                "bid": new_bar.get('bid'), 
                "ask": new_bar.get('ask'),
                "timestamp": new_bar['time']
            },
            "features": {
                "atr14": atr14,
                "vol_sma20": vol_sma20,
                "vol_ratio": vol_ratio,
                "sma20": sma20,
                "upper_wick": upper_wick,
                "lower_wick": lower_wick,
                "max_wick": max_wick,
                "wick_ratio": wick_ratio,
                "resistance_level": resistance_level,
                "support_level": support_level,
                "resistance_poke": resistance_poke,
                "poke_distance": poke_distance,
                "is_poke": is_poke,
                "clock_drift_ms": new_bar.get('clock_drift_ms', 0.0)
            }
        }
        
        return snapshot

    def process_bar(self, bar_data):
        symbol = bar_data['symbol']
        print(f"Processing bar for {symbol} at {bar_data['time']}")
        
        snapshot = self._calculate_features(symbol, bar_data)
        
        if snapshot:
            # Save to S3
            bar_time = datetime.fromisoformat(bar_data['time'])
            s3_path = storage_client.save_feature_snapshot(symbol, snapshot, bar_time)
            
            # Add path to snapshot for downstream
            snapshot['s3_path'] = s3_path
            
            # Publish Feature Ready Event
            # Redis Streams requires flat dict of strings. Serialize the whole snapshot.
            event_bus.publish(f"feature.ready.{symbol}", {"data": json.dumps(snapshot)})

    def run(self):
        print("Feature Engine Started...")
        # Subscribe to bar events
        for symbol in settings.SYMBOLS:
            event_bus.subscribe(f"market.bar.1m.{symbol}", "feature_engine_group", "consumer_1")
            
        while True:
            for symbol in settings.SYMBOLS:
                messages = event_bus.read(f"market.bar.1m.{symbol}", "feature_engine_group", "consumer_1")
                for msg_id, msg_data in messages:
                    # msg_data values are strings in Redis, need to parse types if not using JSON codec
                    # But our EventBus wrapper uses decode_responses=True, so they are strings.
                    # We need to convert numeric fields.
                    # Wait, Redis Streams stores dicts of strings.
                    # We need to cast them back.
                        try:
                            clean_bar = {
                                "symbol": msg_data['symbol'],
                                "open": float(msg_data['open']),
                                "high": float(msg_data['high']),
                                "low": float(msg_data['low']),
                                "close": float(msg_data['close']),
                                "volume": float(msg_data['volume']),
                                "time": msg_data['time'],
                                "clock_drift_ms": float(msg_data.get('clock_drift_ms', 0.0)),
                                # Mistake #11: Capture L1 if available
                                "bid": float(msg_data.get('bid', 0.0)),
                                "ask": float(msg_data.get('ask', 0.0))
                            }
                            self.process_bar(clean_bar)
                            event_bus.ack(f"market.bar.1m.{symbol}", "feature_engine_group", msg_id)
                        except Exception as e:
                            print(f"Error processing bar msg {msg_id}: {e}")
            time.sleep(0.01)

if __name__ == "__main__":
    engine = FeatureEngine()
    engine.run()
