"""
Config Manager - Mistake #8 Compliance
Ensures all configuration changes are audited.
"""

import json
from datetime import datetime
import uuid

from .database import get_db
from .models import Automation, ConfigAuditLog

class ConfigManager:
    
    @staticmethod
    def is_market_hours():
        """
        Check if current time is within trading hours (9:15 - 15:30 IST, Mon-Fri).
        IST = UTC + 5:30
        """
        from datetime import timezone, timedelta
        
        utc_now = datetime.now(timezone.utc)
        ist_now = utc_now + timedelta(hours=5, minutes=30)
        
        # Weekend Check
        if ist_now.weekday() >= 5: # Sat=5, Sun=6
            return False
            
        t = ist_now.time()
        start = datetime.strptime("09:15", "%H:%M").time()
        end = datetime.strptime("15:30", "%H:%M").time()
        
        return start <= t <= end

    @staticmethod
    def update_config(automation_id: str, new_config: dict, reason: str, 
                      user_id: str = None, ip_address: str = None, second_approver: str = None,
                      actor_role: str = "operator", ui_page: str = None, change_context: str = "api",
                      resource_type: str = "config", notes: str = None):
        """
        Updates automation config AND creates an audit log entry.
        Transactional: Both or neither.
        Enforces Mistake #5: Out-of-hours governance.
        """
        if not reason:
            raise ValueError("Change reason is MANDATORY for audit compliance.")
            
        # Mistake #5: Governance Check
        in_market = ConfigManager.is_market_hours()
        
        if not in_market:
            # Out of hours: Require Second Approver
            if not second_approver:
                raise ValueError("GOVERNANCE REJECTION: Out-of-hours changes require a 'second_approver'.")
            print(f"GOVERNANCE: Out-of-hours change approved by {second_approver}")
        
        with next(get_db()) as db:
            # 1. Fetch current automation
            # Safe UUID check
            try:
                auto_uuid = uuid.UUID(automation_id)
            except ValueError:
                # If not UUID, we can't fetch automation by ID (schema requires UUID). 
                # For this specific verify_audit_panel test, we used a generated ID. 
                # But existing code expects UUID.
                 raise ValueError("Invalid Automation ID format (UUID required)")

            auto = db.query(Automation).filter(Automation.id == auto_uuid).first()
            if not auto:
                raise ValueError("Automation not found")
                
            old_config = auto.config or {}
            
            # 2. Update Config
            # Note: SQLAlchemy requires resetting JSON fields to trigger detection sometimes, 
            # or we create a new dict.
            auto.config = new_config
            auto.updated_at = datetime.utcnow()
            
            # 3. Create Audit Log
            event_id = uuid.uuid4()
            timestamp = datetime.utcnow()
            
            # Resolve User/Actor
            db_user_id = None
            actor_name = "system"
            if user_id:
                try:
                    db_user_id = uuid.UUID(user_id)
                    actor_name = str(db_user_id)
                except ValueError:
                    db_user_id = None 
                    actor_name = str(user_id)
            
            audit_log = ConfigAuditLog(
                id=event_id, 
                automation_id=auto.id,
                user_id=db_user_id,
                old_config=old_config,
                new_config=new_config,
                change_reason=reason,
                second_approver=second_approver, 
                ip_address=ip_address,
                timestamp=timestamp, 
                
                # Enhanced Fields
                resource_type=resource_type,
                change_context=change_context, 
                change_type="update",
                actor_role=actor_role,
                ui_page=ui_page,
                notes=notes,
                status="committed"
            )
            
            # 3.5 Prepare Immutable Record for Signing & S3
            
            # REDACTION HELPER
            def redact(d):
                safe = d.copy() if isinstance(d, dict) else {}
                for k, v in safe.items():
                    # Naive secret detection
                    if any(s in k.lower() for s in ["key", "secret", "token", "password"]):
                        # Hash the secret for verification, don't store plain
                        import hashlib
                        safe[k] = f"SHA256:{hashlib.sha256(str(v).encode()).hexdigest()}"
                return safe
                
            safe_old = redact(old_config)
            safe_new = redact(new_config)

            record = {
                "event_id": str(event_id),
                "timestamp_utc": timestamp.isoformat(),
                "actor": actor_name,
                "actor_id": str(db_user_id) if db_user_id else None,
                "actor_role": actor_role,
                "actor_ip": ip_address,
                "actor_device": "unknown_device", # Could be passed in if available
                "ui_page": ui_page,
                "resource_type": resource_type,
                "resource_id": str(auto.id),
                "config_key": "config", 
                "change_type": "update",
                "old_value": json.dumps(safe_old),
                "new_value": json.dumps(safe_new),
                "change_context": change_context,
                "justification": reason,
                "notes": notes,
                "status": "committed"
            }
            
            from .audit_utils import AuditUtils
            
            # Sign
            signature = AuditUtils.sign_record(record)
            record["signed_hash"] = signature
            
            # Upload
            s3_link = AuditUtils.upload_to_s3_mock(record)
            record["evidence_link"] = s3_link
            
            # Update DB Obj
            audit_log.signed_hash = signature
            audit_log.evidence_link = s3_link
            
            db.add(audit_log)

            # 4. Commit transaction
            db.commit()
            
            print(f"AUDIT LOG: Config updated for {auto.name} | Reason: {reason} | S3: {s3_link}")
            
            # Publish Event for Monitor
            try:
                from event_bus import event_bus
                event_bus.publish("audit.event", record)
            except ImportError:
                print("WARNING: Event Bus not available, skipping event publish.")
            
            return audit_log.id

    @staticmethod
    def request_change(automation_id: str, new_config: dict, reason: str,
                       user_id: str = None, ip_address: str = None,
                       actor_role: str = "operator", ui_page: str = None, 
                       resource_type: str = "config", notes: str = None):
        """
        Logs a PRE-CHANGE request (Approval Flow).
        Does NOT update the actual automation config.
        Creates an audit entry with status='pending'.
        """
        with next(get_db()) as db:
            # 1. Fetch current automation for context
            try:
                auto_uuid = uuid.UUID(automation_id)
            except ValueError:
                 raise ValueError("Invalid Automation ID format (UUID required)")

            auto = db.query(Automation).filter(Automation.id == auto_uuid).first()
            if not auto:
                raise ValueError("Automation not found")
                
            old_config = auto.config or {}
            
            # 2. Create Pending Audit Log
            event_id = uuid.uuid4()
            timestamp = datetime.utcnow()
            
            # Resolve Actor
            db_user_id = None
            actor_name = "system"
            if user_id:
                try: 
                    db_user_id = uuid.UUID(user_id)
                    actor_name = str(db_user_id)
                except: 
                    actor_name = str(user_id)

            audit_log = ConfigAuditLog(
                id=event_id, 
                automation_id=auto.id,
                user_id=db_user_id,
                old_config=old_config,
                new_config=new_config,
                change_reason=reason,
                ip_address=ip_address,
                timestamp=timestamp, 
                resource_type=resource_type,
                change_context="ui", # Requests usually via UI
                change_type="update",
                actor_role=actor_role,
                ui_page=ui_page,
                notes=notes,
                status="pending" # PRE-CHANGE STATE
            )
            
            # 3. S3 Record
            # REDACTION HELPER
            def redact(d):
                safe = d.copy() if isinstance(d, dict) else {}
                for k, v in safe.items():
                    if any(s in k.lower() for s in ["key", "secret", "token", "password"]):
                        import hashlib
                        safe[k] = f"SHA256:{hashlib.sha256(str(v).encode()).hexdigest()}"
                return safe
                
            safe_old = redact(old_config)
            safe_new = redact(new_config)

            record = {
                "event_id": str(event_id),
                "timestamp_utc": timestamp.isoformat(),
                "actor": actor_name,
                "actor_role": actor_role,
                "actor_ip": ip_address,
                "resource_type": resource_type,
                "resource_id": str(auto.id),
                "change_type": "update",
                "old_value": json.dumps(safe_old),
                "new_value": json.dumps(safe_new),
                "change_context": "ui",
                "justification": reason,
                "status": "pending", # Explicit in JSON
                "notes": notes
            }
            
            from .audit_utils import AuditUtils
            
            signature = AuditUtils.sign_record(record)
            record["signed_hash"] = signature
            s3_link = AuditUtils.upload_to_s3_mock(record)
            record["evidence_link"] = s3_link
            
            audit_log.signed_hash = signature
            audit_log.evidence_link = s3_link
            
            db.add(audit_log)
            db.commit()
            
            print(f"AUDIT LOG (PENDING): Change requested for {auto.name} | S3: {s3_link}")
            
            # Publish
            try:
                from event_bus import event_bus
                event_bus.publish("audit.event", record)
            except: pass
            
            return audit_log.id

if __name__ == "__main__":
    # Test stub
    pass
