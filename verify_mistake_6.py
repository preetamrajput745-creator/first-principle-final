import sys
import os
import time
from datetime import datetime, timedelta

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infra.secure_vault import vault
from workers.common.database import SessionLocal
from workers.common.models import VaultAccessLog

def test_rbcc_isolation():
    print("=== TESTING MISTAKE 6: ISOLATION & RBAC ===")
    
    db = SessionLocal()
    
    # Clean logs first
    db.query(VaultAccessLog).delete()
    db.commit()
    
    # 1. Test Authorized Access (ExecutionService)
    print("\n[1] Testing Authorized Access (ExecutionService)...")
    try:
        secret = vault.get_secret("ExecutionService", "BROKER_API_KEY")
        if secret:
            print(f"   -> Access Granted. Secret retrieved (masked): {secret[:5]}***")
            print("   -> Authorized Access [OK]")
        else:
            print("   -> Access Failed Unexpectedly [FAIL]")
            sys.exit(1)
    except Exception as e:
        print(f"   -> Exception: {e} [FAIL]")
        sys.exit(1)

    # 2. Test Unauthorized Access (DetectionService)
    print("\n[2] Testing Unauthorized Access (DetectionService)...")
    try:
        secret = vault.get_secret("DetectionService", "BROKER_API_KEY")
        print("   -> Access Granted (This should NOT happen) [FAIL]")
        sys.exit(1)
    except PermissionError as e:
        print(f"   -> Access Denied correctly: {e}")
        print("   -> Unauthorized Access Blocked [OK]")
    except Exception as e:
        print(f"   -> Unexpected Exception: {e} [FAIL]")
        sys.exit(1)

    # 3. Test Audit Logging
    print("\n[3] Verifying Audit Logs...")
    logs = db.query(VaultAccessLog).order_by(VaultAccessLog.timestamp).all()
    
    if len(logs) >= 2:
        print(f"   -> Found {len(logs)} audit logs.")
        
        # Check Log 1 (Granted)
        log1 = logs[-2]
        print(f"   -> Log 1: {log1.service_name} requested {log1.secret_name} -> {log1.status}")
        if log1.service_name == "ExecutionService" and log1.status == "GRANTED":
            print("   -> Audit Log 1 Correct [OK]")
        else:
            print("   -> Audit Log 1 Incorrect [FAIL]")
            
        # Check Log 2 (Denied)
        log2 = logs[-1]
        print(f"   -> Log 2: {log2.service_name} requested {log2.secret_name} -> {log2.status}")
        if log2.service_name == "DetectionService" and log2.status == "DENIED":
            print("   -> Audit Log 2 Correct [OK]")
        else:
            print("   -> Audit Log 2 Incorrect [FAIL]")
            
    else:
        print(f"   -> Not enough logs found ({len(logs)}) [FAIL]")
        sys.exit(1)

    print("\n=== ISOLATION & RBAC VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_rbcc_isolation()
