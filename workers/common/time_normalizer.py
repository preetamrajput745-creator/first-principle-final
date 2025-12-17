"""
Time Normalization Service - Mistake #3 Compliance
Ensures all timestamps are UTC and tracks clock drift.
"""

import time
import uuid
from datetime import datetime, timezone

class TimeNormalizer:
    """
    Central authority for time handling.
    """
    
    @staticmethod
    def now_utc() -> datetime:
        """Get current UTC timestamp (timezone aware)."""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def get_source_clock() -> int:
        """Get high-precision nanosecond clock for source timestamping."""
        return time.time_ns()
    
    @staticmethod
    def calculate_drift_ms(source_ns: int) -> float:
        """
        Calculate drift between source clock and current server clock in milliseconds.
        """
        current_ns = time.time_ns()
        diff_ns = current_ns - source_ns
        return diff_ns / 1_000_000.0  # Convert ns to ms
    
    @staticmethod
    def generate_monotonic_id() -> str:
        """
        Generate a unique ID that is time-ordered (Monotonic).
        Format: {timestamp_ms}-{random_suffix}
        This ensures DB sorting by ID matches sorting by Time.
        """
        # Current time in ms
        now_ms = int(time.time() * 1000)
        
        # Random component for uniqueness
        import random
        rand_suffix = random.randint(1000, 9999)
        
        # Format: T-1707070707000-1234
        return f"T-{now_ms}-{rand_suffix}"

    @staticmethod
    def normalize_tick(tick_data: dict) -> dict:
        """
        Enrich tick data with server timing info.
        """
        # Ensure timestamp is ISO UTC
        if "timestamp" not in tick_data:
            tick_data["timestamp"] = TimeNormalizer.now_utc().isoformat()
            
        # Add server reception clock
        tick_data["server_clock"] = TimeNormalizer.get_source_clock()
        
        # Calculate drift if source_clock exists
        if "source_clock" in tick_data:
            drift = TimeNormalizer.calculate_drift_ms(tick_data["source_clock"])
            tick_data["clock_drift_ms"] = round(drift, 3)
            
            # Mistake #3 Monitor: Alert on high drift
            if drift > 100:
                print(f"WARNING: High Clock Drift Detected! {drift:.2f}ms")
        
        return tick_data

    @staticmethod
    def check_system_drift(server="pool.ntp.org") -> dict:
        """
        Mistake #2: External NTP Check.
        Verifies system clock against atomic clock.
        Returns: {offset_ms: float, status: str, error: str}
        """
        try:
            import ntplib
            client = ntplib.NTPClient()
            response = client.request(server, version=3, timeout=2)
            offset_ms = response.offset * 1000
            
            return {
                "offset_ms": round(offset_ms, 2),
                "status": "OK" if abs(offset_ms) < 100 else "DRIFT",
                "error": None
            }
        except Exception as e:
            return {
                "offset_ms": 0,
                "status": "ERROR",
                "error": str(e)
            }

if __name__ == "__main__":
    # Test
    print("Testing Time Normalizer...")
    
    # Simulate a tick from "now"
    source_time = TimeNormalizer.get_source_clock()
    
    # Simulate network latency (50ms)
    time.sleep(0.05)
    
    tick = {
        "symbol": "TEST",
        "bid": 100.0,
        "source_clock": source_time
    }
    
    normalized = TimeNormalizer.normalize_tick(tick)
    print(f"Normalized Tick: {normalized}")
    print(f"Drift: {normalized['clock_drift_ms']}ms")
