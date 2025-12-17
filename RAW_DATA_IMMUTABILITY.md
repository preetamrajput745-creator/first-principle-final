# Raw Data Immutability & Integrity Plan

## Mistake 2: No raw immutable data (overwrite/delete ticks)
**Solution:** Enforce strict append-only policy + Enable Versioning + Daily Integrity Checks.

### 1. Immutability Enforcement
- **S3 Versioning:** Enabled via `infrastructure/setup_minio.py`.
- **Append-Only Code:** `storage.py` explicitly checks `_check_exists` before writing.
- **Fail-Safe:** `ingest_service.py` catches `Integrity Error` and raises HTTP 409 + Alerts.

### 2. Integrity Monitoring
- **Job:** `workers/maintenance/integrity_check.py`
  - Scans S3 bucket daily.
  - Detects if any file has multiple versions (indication of overwrite).
  - Publishes `system.alert` if integrity violated.

### 3. Verification
- **Unit Test:** `tests/test_raw_data_immutability.py`
  - Attempts to save same file twice.
  - Confirms second attempt fails with "Integrity Error".

### 4. How to Verify Manually
1. Run `python infrastructure/setup_minio.py` to enable versioning on buckets.
2. Run `python tests/test_raw_data_immutability.py` to confirm code blocks overwrites.
3. Run `python workers/maintenance/integrity_check.py` to scan for existing violations.

**NOTE:** Ensure MinIO/S3 is running at `localhost:9000` before running tests.
