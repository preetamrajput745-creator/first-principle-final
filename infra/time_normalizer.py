import time
from datetime import datetime, timezone

class TimeNormalizer:
    """
    Control for Mistake #3: Clock/Timestamp Mismatch.
    Ensures all services operate on a unified, high-precision UTC time.
    Detects and logs drift from system clock vs 'ideal' or external sources (simulated).
    """
    
    def __init__(self, source_name="system"):
        self.source_name = source_name
        self._reference_time = None
        
    def get_current_utc(self):
        """
        Returns guaranteed UTC timestamp.
        """
        return datetime.now(timezone.utc)

    def get_time_and_source(self):
        """
        Returns (canonical_utc_time, source_name).
        Controls #2 Requirement.
        """
        return self.get_current_utc(), self.source_name
    
    def normalize_timestamp(self, input_ts_iso):
        """
        Parses various string formats into a canonical UTC datetime object.
        """
        try:
            # Check if float/int (unix)
            if isinstance(input_ts_iso, (int, float)):
                return datetime.fromtimestamp(input_ts_iso, tz=timezone.utc)
                
            # Assume ISO string
            dt = datetime.fromisoformat(input_ts_iso.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                # Force UTC if naive
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception as e:
            # Fallback to now() with error log
            print(f"[TIME_NORM] Failed to parse {input_ts_iso}: {e}")
            return self.get_current_utc()

    def check_drift(self, remote_ts_ms):
        """
        Calculates drift between a remote timestamp (ms) and local now.
        Positive drift = Remote is ahead.
        Negative drift = Remote is behind (LAG).
        """
        local_ts_ms = time.time() * 1000
        drift = remote_ts_ms - local_ts_ms
        
        # Log basic monitoring metric
        if abs(drift) > 500: # 500ms warning threshold
            print(f"[TIME_NORM] [WARN] SIGNIFICANT CLOCK DRIFT: {drift:.2f}ms")
            
        return drift

# Global Instance
clock = TimeNormalizer()
