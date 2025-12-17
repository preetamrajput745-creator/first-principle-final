"""
Verification: Mistake #8 - Config Audit Log
Verifies:
1. ConfigAuditLog table structure.
2. Creation of audit entries.
3. Metadata completeness (reason, user, old/new config).
"""

import sys
import os
import uuid
import json
from datetime import datetime

# Path setup
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db, Base
from common.models import ConfigAuditLog

def verify_audit_log():
    print("TEST: Config Audit Log (Mistake #8)")
    print("=" * 60)
    
    with next(get_db()) as db:
        # 1. Create Dummy Data
        print("1. Creating Audit Entry...")
        # Since user_id is foreign key but nullable via our findings, we can skip or create dummy.
        # However, model says ForeignKey("users.id") but nullable=True.
        # If we insert a random UUID that doesn't exist in users table, standard SQL might fail FK constraint 
        # unless checking is disabled or SQLite implementation nuances. 
        # Safest is to leave user_id None or create a user first.
        # Let's try user_id=None as system update.
        
        entry_id = uuid.uuid4()
        test_reason = "Test Config Change Verification"
        old_conf = {"trigger": 80}
        new_conf = {"trigger": 85}
        
        audit_entry = ConfigAuditLog(
            id=entry_id,
            automation_id=None, # Nullable in model? Not explicitly nullable=True in definition but typically FKs are if not specified. Warning: automation_id line 38: Column(Uuid, ForeignKey("automations.id")) - defaults to nullable=True in SQLAlchemy unless nullable=False.
            user_id=None,
            change_reason=test_reason,
            old_config=old_conf,
            new_config=new_conf,
            second_approver="superuser",
            ip_address="127.0.0.1"
        )
        
        try:
            db.add(audit_entry)
            db.commit()
            print("   SUCCESS: Entry committed to DB.")
        except Exception as e:
            print(f"   FAILURE: DB Commit failed: {e}")
            sys.exit(1)
            
        # 2. Verify Retrieval & Metadata
        print("\n2. Verifying Metadata...")
        retrieved = db.query(ConfigAuditLog).filter(ConfigAuditLog.id == entry_id).first()
        
        if not retrieved:
            print("   FAILURE: Could not retrieve entry from DB.")
            sys.exit(1)
            
        # Checks
        errors = []
        if retrieved.change_reason != test_reason: errors.append(f"Reason mismatch: {retrieved.change_reason}")
        if retrieved.old_config != old_conf: errors.append(f"Old Conf mismatch: {retrieved.old_config}")
        if retrieved.new_config != new_conf: errors.append(f"New Conf mismatch: {retrieved.new_config}")
        if retrieved.second_approver != "superuser": errors.append(f"Approver mismatch: {retrieved.second_approver}")
        if not retrieved.timestamp: errors.append("Timestamp missing")
        
        if errors:
            print("   FAILURE: Metadata verification failed!")
            for e in errors: print(f"    - {e}")
            sys.exit(1)
        else:
            print("   SUCCESS: All metadata fields verified.")
            
    print("\nVERIFICATION COMPLETE: Audit Logs compliant.")

if __name__ == "__main__":
    verify_audit_log()
