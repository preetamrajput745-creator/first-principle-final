# Execution engine needs broker keys
path "antigravity/trading/execution/*" { capabilities = ["read"] }
path "antigravity/detection/*" { capabilities = ["deny"] }