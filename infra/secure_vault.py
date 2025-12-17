import os
import sys
from datetime import datetime, timezone

# Add parent dir to path if needed (for local demo)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.common.database import SessionLocal
from workers.common.models import VaultAccessLog

class SecureVault:
    """
    Mistake #6: Isolation & RBAC Control.
    Mocks a HashiCorp Vault / AWS Secrets Manager.
    Enforces Role-Based Access Control (RBAC).
    """

    # Simulated Secret Store (Would be encrypted in real life)
    _SECRETS = {
        "BROKER_API_KEY": "sk_live_12345_SECRET_KEY",
        "BROKER_API_SECRET": "sk_live_67890_SECRET_KEY",
        "DATABASE_PASSWORD": "super_secure_password"
    }

    # RBAC: Only 'ExecutionService' can see Broker Keys
    _PERMISSIONS = {
        "ExecutionService": ["BROKER_API_KEY", "BROKER_API_SECRET"],
        "MigrationService": ["DATABASE_PASSWORD"],
        "DetectionService": [] # ZERO TRUST: Detection gets nothing
    }

    @staticmethod
    def get_secret(service_name: str, secret_key: str):
        db = SessionLocal()
        
        # 1. Check Permissions (RBAC)
        allowed_secrets = SecureVault._PERMISSIONS.get(service_name, [])
        
        status = "DENIED"
        value = None
        
        if secret_key in allowed_secrets:
            # 2. Release Secret
            status = "GRANTED"
            value = SecureVault._SECRETS.get(secret_key)
        
        # 3. Audit Logging (Mistake #6 Requirement)
        log = VaultAccessLog(
            service_name=service_name,
            secret_name=secret_key,
            status=status,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        db.close()
        
        if status == "DENIED":
            raise PermissionError(f"[VAULT] Access Denied: {service_name} cannot access {secret_key}")
            
        return value

# Global Singleton
vault = SecureVault()
