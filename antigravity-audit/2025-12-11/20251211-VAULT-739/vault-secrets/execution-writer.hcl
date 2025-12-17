
path "antigravity/data/data/execution/*" { capabilities = ["read"] }
path "antigravity/data/data/execution/broker_keys/*" { capabilities = ["create", "update", "read"] }
path "antigravity/data/metadata/execution/*" { capabilities = ["list", "read"] }
path "antigravity/data/data/ingestion/*" { capabilities = ["deny"] }
path "antigravity/data/data/detection/*" { capabilities = ["deny"] }
