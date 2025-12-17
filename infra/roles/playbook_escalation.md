
# PLAYBOOK: Escalation & Emergency

## Trigger: Owner Unresponsive
**Condition**: Critical alert unacknowledged for > 5 minutes.

### Level 1: Automatic Escalation
- **Action**: Alertmanager routes to `pagerduty-escalation`.
- **Target**: VP of Engineering / Head of Trading.
- **Message**: "ESCALATION: Owner Unresponsive on Critical Alert [ID: ...]"

### Level 2: Manual Intervention (Security Role)
- If neither Owner nor VP responds in 10 minutes:
- **Action**: Security Team initiates **KILL SWITCH**.
- **Command**: `./admin-cli system halt --reason "Unresponsive Leadership during Crisis"`
- **Consequence**: All trading suspended. All open orders cancelled.

---

## Trigger: PagerDuty Failure
**Condition**: Test page fails to reach device.

### Fallback
1. **SMS Blast**: Twilio API triggered by monitoring watchdog.
2. **Email**: "URGENT: PAGERDUTY DOWN - CHECK DASHBOARD".

## Audit
Every escalation event is logged to `s3://antigravity-audit/critical/escalations/` with immutable retention.
