from .database import SessionLocal
from .models import SlippageProfile
import random

class SlippageModel:
    """
    Conservative Slippage Model to address Mistake #1.
    Calculates realistic execution prices based on instrument and volatility.
    DB-Driven Profiles (Mistake #3 Control).
    """
    
    def __init__(self):
        self.db = SessionLocal()
        # Cache for performance, in real system use Redis
        self.cache = {}
        
    def get_profile(self, symbol):
        if symbol in self.cache:
            return self.cache[symbol]
            
        profile = self.db.query(SlippageProfile).filter(SlippageProfile.symbol == symbol).first()
        if not profile:
            # Default fallback
            return {"base_slippage_pct": 0.01, "volatility_multiplier": 2.0, "tick_size": 0.05}
        
        self.cache[symbol] = {
            "base_slippage_pct": profile.base_slippage_pct,
            "volatility_multiplier": profile.volatility_multiplier,
            "tick_size": profile.tick_size
        }
        return self.cache[symbol]

    def calculate_slippage(self, symbol: str, price: float, quantity: int = 1, is_volatile: bool = False) -> dict:
        """
        Returns the estimated execution price and slippage amount.
        """
        profile = self.get_profile(symbol)
        
        # Convert % to bps for calculation (1% = 100 bps)
        # Profile stores PCT (0.01 = 0.01%). 
        # Wait, user said "Default slippage profile per instrument stored in DB".
        # Let's assume model stores % value directly. e.g. 0.01 means 0.01%.
        
        base_pct = profile["base_slippage_pct"]
        
        # 1. Volatility Multiplier (Mistake #12 awareness)
        if is_volatile:
            base_pct *= profile["volatility_multiplier"]
            
        # 2. Impact Slippage (Simulated based on quantity)
        # Simple model: +0.001% per 1000 qty
        impact_pct = (quantity / 1000.0) * 0.001
        
        total_pct = base_pct + impact_pct
        
        # Calculate absolute slippage value
        slippage_amount = price * (total_pct / 100.0)
        
        # Round to tick size
        tick_size = profile["tick_size"]
        slippage_amount = round(slippage_amount / tick_size) * tick_size
        
        # For BUY orders, we pay MORE (Price + Slippage)
        # For SELL orders, we get LESS (Price - Slippage)
        # This function returns the absolute "cost" of slippage
        
        return {
            "symbol": symbol,
            "original_price": price,
            "slippage_bps": total_pct * 100, # Convert back to bps for display
            "slippage_amount": slippage_amount,
            "estimated_buy_price": price + slippage_amount,
            "estimated_sell_price": price - slippage_amount
        }

    def simulate_latency(self) -> float:
        """
        Mistake #4: Simulates processing and network latency.
        Returns: Latency in milliseconds.
        Distribution: Log-normal (mostly fast, occasional spikes).
        """
        # Base latency 5ms, + random gamma distribution
        latency_ms = 5 + random.gammavariate(alpha=2.0, beta=5.0)
        return round(latency_ms, 2)

# Usage Example
if __name__ == "__main__":
    model = SlippageModel()
    result = model.calculate_slippage("NIFTY", 21500, quantity=50, is_volatile=True)
    lat = model.simulate_latency()
    print(f"Slippage Test: {result}")
    print(f"Latency Lag: {lat} ms")
