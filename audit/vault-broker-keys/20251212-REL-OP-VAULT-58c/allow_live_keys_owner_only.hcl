# RESTRICTED: REQUIRES OWNER TOTP + PRE-LIVE GATE
path "secrets/broker/live/*" {
    capabilities = ["read"]
    # Pseudocode for Sentinel/Path Enforcement
    allowed_parameters = { 
        "owner_totp" = [], 
        "prelive_token" = [] 
    }
    min_wrapping_ttl = "10s"
    max_wrapping_ttl = "120s"
}