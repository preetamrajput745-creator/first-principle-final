
# Runbook: Owner Approvals & Sign-off

## Role Description
The Owner is the ultimate authority for policy changes and live promotions.

## Approval Flow
1. **Receive Request**: Notification via Email/Slack.
2. **Review**: Check diffs, risk score, and justification.
3. **Approve**:
   - Go to `/admin/approvals`
   - Select Policy
   - Enter Justification
   - **Confirm 2FA** (Authenticator App)
   - Click "Approve"
   
## Live Sign-off
1. Ensure all pre-flight checks passed (Green).
2. Review "Release Checklist".
3. Calculate Confirmation Hash (if manual) or use UI.
4. Execute Sign-off.

## Emergency Override
If Workflow UI is down, use Vault CLI:
`vault write antigravity/promotions/signoff/id override=true justification="Emergency"`
