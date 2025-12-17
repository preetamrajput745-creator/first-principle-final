path "antigravity/infra/*" { capabilities = ["create", "read", "update", "delete"] }
path "sys/*" { capabilities = ["sudo", "read"] }
path "antigravity/trading/*" { capabilities = ["deny"] } # No access to broker keys