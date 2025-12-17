
# Owner Policy - Antigravity Control Plane
# Managed by Terraform/Vault-Admin

# Allow managing policies (Approve/Reject)
path "antigravity/policies/approve/*" {
  capabilities = ["create", "update"]
  allowed_parameters = {
    "justification" = []
    "2fa_token" = []
  }
}

# Allow Sign-off on Promotions
path "antigravity/promotions/signoff/*" {
  capabilities = ["create", "update"]
}

# Read-only on live config (cannot push directly)
path "antigravity/config/live/*" {
  capabilities = ["read", "list"]
}

# Audit Access
path "antigravity/audit/logs/*" {
  capabilities = ["create", "read"]
}
