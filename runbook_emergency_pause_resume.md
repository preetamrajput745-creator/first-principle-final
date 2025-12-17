# EMERGENCY RUNBOOK: PAUSE & RESUME PROCEDURES
**Confidential - Operations Team Only**
**Last Updated:** 2025-12-11
**Version:** 1.0.0
**Status:** ACTIVE

---

## 1. PURPOSE

This runbook defines the mandatory protocols for the **Emergency PAUSE** (Circuit Breaker Trip) and **Safe RESUME** (Recovery) of the Antigravity Trading System. It is the single source of truth for handling system-critical risk events.

**Scope:**
*   Global Kill Switch (Pause All)
*   Component Pause (Execution, Ingest, Risk, Automation)
*   Instrument/Strategy Pause (e.g., BTC-USD, Strategy-A)

**Policy:**
*   **PAUSE** is treated as a "Circuit Breaker OPEN" event.
*   **RESUME** is treated as a controlled "HALF_OPEN" to "CLOSED" transition.
*   All actions must be logged, justified, and cryptographically signed (Audit Trail).

---

## 2. WHEN TO PAUSE (TRIGGERS)

Immediate PAUSE is required if ANY of the following conditions are met:

### A. Automatic Triggers (System Enforced)
1.  **Slippage Violation:** > 50% slippage delta for 10 consecutive trades.
2.  **Latency Anomaly:** p95 execution latency > 300ms for 2 minutes.
3.  **Error Rate:** Signal rejection rate > 50% in 1-hour window.
4.  **Daily Loss:** Global PnL loss > limit ($500.00).

### B. Manual Triggers (Operator Discretion)
1.  **Data Integrity:** Suspected data poisoning or out-of-order market feed.
2.  **Security:** `signed_hash` verification failure in Audit Logs.
3.  **Governance:** Unauthorized configuration change detected outside work-hours.
4.  **Market Anomaly:** Flash crash or exchange outage verification.
5.  **Operational:** Rule-engine auto-open misfire or "runaway" automation.

---

## 3. WHO CAN PAUSE (RBAC MATRIX)

| Role | Permissions | Scope |
| :--- | :--- | :--- |
| **safety-admin** | **FULL AUTHORITY** | Global, Component, Instrument |
| **operator-act** | Partial | Component, Instrument (NO Global) |
| **automation-role** | Rule-Based Only | Execution/Instrument via System Rule |
| **monitoring-read** | Read-Only | None |

---

## 4. HOW TO PAUSE (PROCEDURE)

### Method A: UI Procedure (Preferred)
1.  **Access:** Log in to **Admin Console** -> **Safety Panel**.
2.  **Target:** Locate the specific breaker (e.g., `global`, `exec-strategy-A`) in the dashboard table.
3.  **Action:** Click the red **OPEN (TRIP)** button.
4.  **Justification:**
    *   **Reason:** Select category (e.g., "Market Anomaly").
    *   **Notes:** Enter specific details (e.g., "Binance feed lag > 5s").
5.  **Confirm:** Click "CONFIRM TRIP".
6.  **Verify:** Ensure status badge turns **RED (OPEN)** within 5 seconds.

### Method B: API Procedure (Automation/CLI)
**Endpoint:** `POST /v1/breakers/{breaker_id}/open`

**Request:**
```json
{
  "reason": "Emergency Manual Trip: Data Feed Latency",
  "notes": "Runbook Proc 4.B Executed by On-Call",
  "ttl_seconds": 3600
}
```

**Headers:**
*   `X-User-Role`: `safety-admin` (or authorized role)
*   `X-User-Id`: `<your-id>`

**Success Response (200 OK):**
```json
{
  "status": "success",
  "state": "OPEN",
  "event_id": "uuid...",
  "evidence_link": "s3://..."
}
```

---

## 5. AFTER PAUSE: VERIFICATION

Immediately perform the following validations:
1.  **Halt Confirmation:** Verify `breaker_state` metric is `1` (OPEN).
2.  **Trading Stop:** Confirm no new orders in `recent_orders` table (DB) or logs.
3.  **Automation Status:** Confirm automations transitioned to `paused_risk` state.
4.  **Alerts:** Confirm PagerDuty/Slack alert received for "Breaker Open".
5.  **Audit:** Verify S3 audit JSON generated at `evidence_link`.

---

## 6. RESUME PROCEDURE (RECOVERY)

**CRITICAL:** Resume is ONLY allowed after Root Cause Analysis (RCA) and mitigation.

### A. Pre-Resume Checklist
*   [ ] Root cause identified and fixed.
*   [ ] Data feed / Latency / Slippage metrics returned to healthy baseline.
*   [ ] No new critical alerts in last 15 minutes.
*   [ ] **Risk Team Approval** obtained (if applicable).

### B. Resume Steps (Half-Open Protocol)
1.  **Set Half-Open:**
    *   **UI:** Click **RESUME (TEST)** button.
    *   **API:** `POST /v1/breakers/{id}/half_open`
    *   *Result:* State turns **ORANGE (HALF_OPEN)**.

2.  **Verification Probes:**
    *   System automatically runs N=5 probes (simulated trades or health checks).
    *   Monitor `breaker_probe_success_ratio` metric.
    *   *Requirement:* 4/5 success rate required.

3.  **Close Breaker (Full Resume):**
    *   If probes pass, UI button **CLOSE (RESUME)** becomes active.
    *   **UI:** Click **CLOSE**.
    *   **API:** `POST /v1/breakers/{id}/close`
    *   *Result:* State turns **GREEN (CLOSED)**.

### C. Negative Paths (Failures)
*   **Probe Failure:** If probes fail, breaker remains `HALF_OPEN` or reverts to `OPEN`. **DO NOT** force close. Re-investigate.
*   **Access Denied:** If `operator-act` attempts Global Resume, system checks RBAC and denies. Audit event logged.
*   **Audit Failure:** If `signed_hash` verification fails during history check, Resume is BLOCKED. Contact Security.

---

## 7. FAILURE MODES & CONTINGENCIES

| Failure Mode | Symptom | Contingency Action |
| :--- | :--- | :--- |
| **S3 Audit Unavailable** | API verification fails | System enters degraded mode. Pause allowed; Resume blocked until S3 restored. |
| **Vault Signing Key Error** | `signed_hash` missing | Manual Override by Safety Admin required (requires `admin:override` scope). |
| **API Down** | 503 Service Unavailable | Access specific pod/container via CLI and run `python scripts/emergency_trip.py`. |

---

## 8. DEPLOYMENT & ARTIFACTS
*   **Charts:** `helm/circuit-breaker`
*   **Logs:** `s3://antigravity-audit/.../circuit-breaker/`
*   **Metrics:** Grafana Dashboard `Risk > Circuit Breakers`

---
**End of Runbook**
