
"""
Daily Retention Job
Runs the RetentionManager to move hot data to cold archive.
"""
import sys
import os

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from workers.maintenance.retention_manager import RetentionManager

def run_retention_job():
    print("JOB: Daily Retention & Archival")
    rm = RetentionManager()
    # Default policy runs
    results = rm.archive_cold_data()
    print(f"JOB COMPLETE: {results}")

if __name__ == "__main__":
    run_retention_job()
