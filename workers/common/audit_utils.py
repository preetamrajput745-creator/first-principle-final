import json
import hashlib
import hmac
import os
import uuid
import time
from datetime import datetime

# Mock specific Vault key
VAULT_PRIVATE_KEY = "s3cr3t_v4ult_k3y_f0r_s1gn1ng"

class AuditUtils:
    
    @staticmethod
    def sign_record(record: dict) -> str:
        """
        Generates a SHA256 HMAC signature of the record content.
        Simulates: Vault.sign("audit-key", record_hash)
        """
        # Canonicalize: Sort keys to ensure consistent hash
        # strip fields added after signing or the signature itself
        payload = record.copy()
        payload.pop("signed_hash", None)
        payload.pop("evidence_link", None)
        
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        signature = hmac.new(
            VAULT_PRIVATE_KEY.encode('utf-8'),
            serialized.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    @staticmethod
    def verify_signature(record: dict, signature: str) -> bool:
        """
        Verifies the signature matches the record.
        """
        expected = AuditUtils.sign_record(record)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def upload_to_s3_mock(record: dict) -> str:
        """
        Simulates immutable S3 upload. 
        Writes to local artifact directory for the Audit Pack.
        Returns s3:// URI.
        """
        # Ensure directory exists
        
        # We'll use a local 'audit_storage' dir in the workspace root
        # Base path logic
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        audit_dir = os.path.join(root_dir, "audit_storage")
        
        if not os.path.exists(audit_dir):
            try:
                os.makedirs(audit_dir)
            except OSError:
                pass
                
        # Key: YYYY-MM-DD/event_id.json
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        daily_dir = os.path.join(audit_dir, date_str)
        if not os.path.exists(daily_dir):
            try:
                os.makedirs(daily_dir)
            except OSError:
                pass
                
        event_id = record.get("event_id", str(uuid.uuid4()))
        filename = f"{event_id}.json"
        filepath = os.path.join(daily_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump(record, f, indent=2)
            
        # Mock S3 URI
        return f"s3://antigravity-audit/{date_str}/audit-panel/{filename}"
