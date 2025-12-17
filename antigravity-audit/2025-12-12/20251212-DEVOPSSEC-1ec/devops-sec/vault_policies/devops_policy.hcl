# DevOps: Infra maintenance
path "antigravity/infra/*" { capabilities = ["create", "read", "update", "delete"] }
path "sys/*" { capabilities = ["sudo", "read"] }
path "antigravity/trading/*" { capabilities = ["deny"] } # Strict separation