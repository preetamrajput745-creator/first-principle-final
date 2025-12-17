
# RUNBOOK: Owner Approvals & Sign-off

## Role: OWNER
**Objective**: Authorize high-risk policy changes and approve live production promotions.

---

### A. Policy Approval Flow

1. **Receive Request**
   - Notification via Slack/Email: "Policy Change Proposal [ID: 123] from Operator"
   - Link: `https://admin.antigravity.trade/policies/123/review`

2. **Review Diff**
   - Check `old_value` vs `new_value`.
   - Verify `justification` is adequate.
   - Check risk score.

3. **Approve (CLI/API)**
   ```bash
   # Using dedicated owner element
   ./admin-cli policy approve --id 123 --reason "Approved for Q3 optimization" --checklist "path/to/checklist.pdf"
   ```
   **Output:** `SUCCESS: Policy 123 Approved. Audit: <ID>`

4. **Reject**
   ```bash
   ./admin-cli policy reject --id 123 --reason "Risk too high, add tests"
   ```

---

### B. Live Promotion Sign-off

**CRITICAL**: Live promotions require 2FA and attached evidence.

1. **Receive Sign-off Request**
   - CI/CD pauses at "Gate: Owner Sign-off".
   
2. **Execute Sign-off**
   - Use Vault-signed token or Hardware Key.
   - API Call:
     `POST /v1/promotions/PROMO-999/signoff`
     Body:
     ```json
     {
       "checklist_verified": true,
       "2fa_token": "123456",
       "notes": "Green light for rollout"
     }
     ```

3. **Emergency Stop**
   - If issues detected post-promotion:
     `./admin-cli promotion freeze --all`
     (Routes critical page to Security & Owner).
