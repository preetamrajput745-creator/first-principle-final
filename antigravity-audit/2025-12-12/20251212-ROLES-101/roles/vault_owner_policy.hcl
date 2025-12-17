
# Owner - Full Control over Policies and Sign-off
path "antigravity/policies/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "antigravity/promotions/signoff/*" {
  capabilities = ["create", "update"]
}
path "antigravity/audit/*" {
  capabilities = ["create", "read"] # Write audit logs
}
# Cannot push unapproved promotions directly (enforced by pipeline logic reading signoff)
path "antigravity/promotions/live/*" {
  capabilities = ["read"] 
}
