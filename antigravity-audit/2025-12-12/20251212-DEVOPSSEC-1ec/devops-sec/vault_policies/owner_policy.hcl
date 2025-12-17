# Read-only for approvals metadata
path "antigravity/approvals/*" { capabilities = ["read", "list"] }
path "sys/policies/*" { capabilities = ["read", "list"] }