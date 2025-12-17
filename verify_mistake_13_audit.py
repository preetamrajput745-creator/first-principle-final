
import sys
import os
import subprocess
import time
import uuid

# Add Root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers"))

from common.database import get_db, SessionLocal
from common.models import Automation, ConfigAuditLog
from common.config_manager import ConfigManager

def run_verification():
    print("============================================================")
    print("       AUDIT & CONFIG CHANGE VERIFICATION (Mistake #13)       ")
    print("============================================================")
    
    run_id = str(uuid.uuid4())[:8]
    unique_db = f"event_bus_adt_{run_id}.db"
    os.environ["EVENT_BUS_DB"] = unique_db
    print(f"[0] Using unique Event DB: {unique_db}")
    
    # 1. Start Monitor
    print("[1] Starting Monitor Service...")
    monitor_out = open("monitor_audit.log", "w")
    monitor_proc = subprocess.Popen([sys.executable, "-u", "monitoring/monitor.py"],
                                    stdout=monitor_out,
                                    stderr=subprocess.STDOUT,
                                    env=os.environ.copy())
    time.sleep(5)
    
    # 2. Setup Data
    db = SessionLocal()
    auto_id = uuid.uuid4()
    auto = Automation(id=auto_id, name="Audit Test", slug=f"audit-test-{run_id}", status="active", config={"param": 1})
    db.add(auto)
    db.commit()
    print("[2] Automation Created.")
    
    # 3. Perform Config Update via ConfigManager
    print("[3] Updating Config via ConfigManager...")
    try:
        # Simulate Out of Hours (if applicable) or Normal.
        # Check market hours first?
        # We can force second_approver just in case.
        new_config = {"param": 2}
        ConfigManager.update_config(
            automation_id=str(auto_id),
            new_config=new_config,
            reason="Testing Audit Log",
            user_id=str(uuid.uuid4()),
            second_approver="Approver_Bob"
        )
        print("    Update successful.")
    except Exception as e:
        print(f"    [FAIL] Update failed: {e}")
        monitor_proc.terminate()
        sys.exit(1)
        
    # 4. Verify DB Audit Log
    print("[4] Verifying Database Audit Log...")
    log_entry = db.query(ConfigAuditLog).filter(ConfigAuditLog.automation_id == auto_id).order_by(ConfigAuditLog.timestamp.desc()).first()
    if log_entry:
        print(f"    [PASS] Audit Log Found! Reason: {log_entry.change_reason}")
        if log_entry.new_config == new_config:
             print("    [PASS] Config content matches.")
        else:
             print(f"    [FAIL] Config content mismatch: {log_entry.new_config}")
    else:
        print("    [FAIL] Audit Log NOT found in DB.")
        
    db.close()
    
    # 5. Verify Monitor Alert
    print("[5] Waiting for Monitor Alert...")
    time.sleep(5)
    
    monitor_proc.terminate()
    monitor_out.close()
    
    with open("monitor_audit.log", "r") as f:
        logs = f.read()
        
    if "CONFIG ALERT: System Config Changed!" in logs:
        print("    [PASS] Monitor Alert Triggered.")
        print("SUCCESS: Audit & Config Change Verified.")
    else:
        print("    [FAIL] Monitor Alert NOT found!")
        print("    Tail of logs:")
        print(logs[-2000:])
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
