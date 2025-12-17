class FBEDetector:
    def __init__(self):
        self.state = {} # symbol -> {high, low, last_price, ...}

    def process_tick(self, symbol, price, timestamp):
        """
        Returns a signal payload if a false breakout is detected, else None.
        """
        if symbol not in self.state:
            self.state[symbol] = {
                "high": price,
                "low": price,
                "last_price": price,
                "trend": "neutral"
            }
            return None

        state = self.state[symbol]
        
        # Simple logic: 
        # 1. Update High/Low
        # 2. If price > high, check for reversal (next tick < high) -> False Breakout High
        # 3. If price < low, check for reversal (next tick > low) -> False Breakout Low
        
        signal = None
        
        # Check for False Breakout High
        if price > state["high"]:
            # New high, update
            state["prev_high"] = state["high"]
            state["high"] = price
            
        elif state.get("prev_high") and state["last_price"] > state["prev_high"] and price < state["prev_high"]:
             # We were above prev_high, now below -> False Breakout
             signal = {
                 "type": "FBE_BEARISH",
                 "symbol": symbol,
                 "price": price,
                 "timestamp": timestamp,
                 "reason": f"Price {price} fell back below previous high {state['prev_high']}"
             }
        
        # Update state
        state["last_price"] = price
        
        return signal
