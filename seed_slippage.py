
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workers.common.database import get_db, engine, Base
from workers.common.models import SlippageProfile
from config import settings

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def seed_slippage_profiles():
    print("Seeding Slippage Profiles (Mistake #3 Violation Fix)...")
    
    defaults = [
        {"symbol": "NIFTY_FUT", "base": 0.01, "vol": 2.0, "tick": 0.05},
        {"symbol": "BANKNIFTY_FUT", "base": 0.02, "vol": 2.5, "tick": 0.05},
        {"symbol": "BTCUSDT", "base": 0.05, "vol": 3.0, "tick": 0.1},
        {"symbol": "L2_TEST", "base": 0.01, "vol": 2.0, "tick": 0.05},
    ]
    
    with next(get_db()) as db:
        for item in defaults:
            profile = db.query(SlippageProfile).filter(SlippageProfile.symbol == item["symbol"]).first()
            if not profile:
                profile = SlippageProfile(
                    symbol=item["symbol"],
                    base_slippage_pct=item["base"],
                    volatility_multiplier=item["vol"],
                    tick_size=item["tick"]
                )
                db.add(profile)
                print(f" + Added Profile for {item['symbol']}")
            else:
                profile.base_slippage_pct = item["base"]
                profile.volatility_multiplier = item["vol"]
                profile.tick_size = item["tick"]
                print(f" . Updated Profile for {item['symbol']}")
        
        db.commit()
    print("Slippage Validation Complete.\n")

if __name__ == "__main__":
    seed_slippage_profiles()
