import shutil
import os

SRC = "s3_audit_local/deliverables"
DST = "s3_audit_local/COMPLIANCE_DELIVERABLES_PACK"

shutil.make_archive(DST, 'zip', SRC)
print(f"Created Archive: {DST}.zip")
