
# ==========================================
# VAULT RBAC POLICIES (ZERO-TRUST MODEL)
# ==========================================

# POLICY: ingestion-reader
# ------------------------------------------
path "antigravity/data/ingestion/*" {
  capabilities = ["read", "list"]
}

# Explicit Deny for other paths (Zero-Trust)
path "antigravity/data/detection/*" { capabilities = ["deny"] }
path "antigravity/data/execution/*" { capabilities = ["deny"] }
path "antigravity/data/monitoring/*" { capabilities = ["deny"] }
path "antigravity/data/system/*" { capabilities = ["deny"] }

# POLICY: detection-reader
# ------------------------------------------
path "antigravity/data/detection/*" {
  capabilities = ["read", "list"]
}

# Explicit Deny requirements
path "antigravity/data/execution/*" { capabilities = ["deny"] }
path "antigravity/data/execution/broker_keys/*" { capabilities = ["deny"] }

# POLICY: execution-writer
# ------------------------------------------
# Read access to general execution config
path "antigravity/data/execution/*" {
  capabilities = ["read", "list"]
}

# Write access ONLY to broker_keys
path "antigravity/data/execution/broker_keys/*" {
  capabilities = ["create", "update", "read", "list"]
}

# Explicit Deny
path "antigravity/data/ingestion/*" { capabilities = ["deny"] }
path "antigravity/data/detection/*" { capabilities = ["deny"] }

# POLICY: monitoring-reader
# ------------------------------------------
path "antigravity/data/monitoring/*" {
  capabilities = ["read", "list"]
}

# POLICY: admin-full
# ------------------------------------------
# Root-level maintenance only
path "*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
