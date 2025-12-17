
# ==========================================
# VAULT POLICY: OWNER
# ==========================================
# Authority: Final Approver & Sign-off

# Policy Management: Approve Policies
path "antigravity/policies/approve/*" {
  capabilities = ["create", "update"]
}

# Promotions: Sign-off Release
path "antigravity/promotions/signoff/*" {
  capabilities = ["create", "update"]
}

# Critical Secrets: Read Access (Emergency only)
path "antigravity/data/critical/*" {
  capabilities = ["read"]
  audit_non_hmac_request_keys = ["reason"]
}

# General Read Access
path "antigravity/data/*" {
  capabilities = ["read", "list"]
}

# Maintenance: Audit Lock Override (2FA required)
path "antigravity/audit/lock/override" {
  capabilities = ["update"]
  mfa_constraint {
    enforce = true
  }
}
