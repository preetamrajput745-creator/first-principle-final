--- ingestion-reader ---

path "antigravity/data/data/ingestion/*" { capabilities = ["read"] }
path "antigravity/data/metadata/ingestion/*" { capabilities = ["list", "read"] }
path "sys/internal/ui/mounts/*" { capabilities = ["read"] }


--- detection-reader ---

path "antigravity/data/data/detection/*" { capabilities = ["read"] }
path "antigravity/data/metadata/detection/*" { capabilities = ["list", "read"] }
path "antigravity/data/data/execution/*" { capabilities = ["deny"] }
path "antigravity/data/data/execution/broker_keys/*" { capabilities = ["deny"] }


--- execution-writer ---

path "antigravity/data/data/execution/*" { capabilities = ["read"] }
path "antigravity/data/data/execution/broker_keys/*" { capabilities = ["create", "update", "read"] }
path "antigravity/data/metadata/execution/*" { capabilities = ["list", "read"] }
path "antigravity/data/data/ingestion/*" { capabilities = ["deny"] }
path "antigravity/data/data/detection/*" { capabilities = ["deny"] }


--- monitoring-reader ---

path "antigravity/data/data/monitoring/*" { capabilities = ["read"] }
path "antigravity/data/metadata/monitoring/*" { capabilities = ["list", "read"] }


--- admin-full ---

path "*" { capabilities = ["create", "read", "update", "delete", "list", "sudo"] }


