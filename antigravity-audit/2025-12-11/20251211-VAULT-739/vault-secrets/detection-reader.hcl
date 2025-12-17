
path "antigravity/data/data/detection/*" { capabilities = ["read"] }
path "antigravity/data/metadata/detection/*" { capabilities = ["list", "read"] }
path "antigravity/data/data/execution/*" { capabilities = ["deny"] }
path "antigravity/data/data/execution/broker_keys/*" { capabilities = ["deny"] }
