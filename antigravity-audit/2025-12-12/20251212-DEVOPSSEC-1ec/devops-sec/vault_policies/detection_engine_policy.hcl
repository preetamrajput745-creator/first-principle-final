# Detection engine: No broker keys
path "antigravity/detection/*" { capabilities = ["read"] }
path "antigravity/trading/*" { capabilities = ["deny"] }