import ntplib
from datetime import datetime, timezone
import time
from config import settings

class TimeOracle:
    """
    Advanced Time Normalization & Drift Detection.
    Ensures all system components are synced to true UTC.
    """
    def __init__(self):
        self.offset = 0.0
        self.last_sync = 0
        self.sync_interval = 3600 # Sync every hour
        self.ntp_server = "pool.ntp.org"

    def sync(self):
        """Syncs local clock with NTP server to calculate offset."""
        try:
            client = ntplib.NTPClient()
            response = client.request(self.ntp_server, version=3)
            self.offset = response.offset
            self.last_sync = time.time()
            print(f"Time synced. Offset: {self.offset:.6f}s")
        except Exception as e:
            print(f"NTP Sync failed: {e}. Using local time.")
            pass

    def now(self) -> datetime:
        """Returns the TRUE UTC time (corrected for drift)."""
        if time.time() - self.last_sync > self.sync_interval:
            self.sync()
        
        corrected_timestamp = time.time() + self.offset
        return datetime.fromtimestamp(corrected_timestamp, tz=timezone.utc)

    def check_drift(self, external_timestamp: datetime, threshold_ms=500) -> bool:
        """
        Checks if an external timestamp is within acceptable drift threshold.
        Returns Tuple (is_acceptable, drift_ms)
        """
        system_now = self.now()
        drift = (system_now - external_timestamp).total_seconds() * 1000
        is_acceptable = abs(drift) <= threshold_ms
        return is_acceptable, drift

time_oracle = TimeOracle()
