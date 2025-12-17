"""
Verification: Mistake #5 - Change Management Governance
Requirement: "Out-of-hours change approvals require owner + second approver."

Steps:
1. Setup: Create automation.
2. Mock Time: Force system to appear as "Sunday" (Out of Hours).
3. Test 1: Update config WITHOUT second approver -> Expect REJECTION.
4. Test 2: Update config WITH second approver -> Expect SUCCESS.
"""

import sys
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

# Path setup
workers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workers")
sys.path.insert(0, workers_path)

from common.database import get_db
from common.models import Automation
from common.config_manager import ConfigManager

def verify_governance():
    print("TEST: Change Management Governance (Mistake #5)")
    print("=" * 60)
    
    with next(get_db()) as db:
        slug = f"gov-test-{str(uuid.uuid4())[:8]}"
        auto = Automation(name="Governance Tester", slug=slug, status="active", config={"param": 1})
        db.add(auto)
        db.commit()
        db.refresh(auto)
        auto_id = str(auto.id)
        
    print(f"1. Setup: Created automation '{slug}'")

    # Mock datetime to SUNDAY (Out of Hours)
    # 2023-10-22 was a Sunday
    mock_sunday = datetime(2023, 10, 22, 10, 0, 0, tzinfo=timezone.utc)
    
    with patch('common.config_manager.datetime') as mock_dt:
        mock_dt.now.return_value = mock_sunday
        mock_dt.utcnow.return_value = mock_sunday
        
        # Test 1: Negative Case
        print("2. Test: Attempting update on SUNDAY without Second Approver...")
        try:
            ConfigManager.update_config(
                automation_id=auto_id,
                new_config={"param": 2},
                reason="Routine Update"
            )
            print("   FAILURE: Update succeeded when it should have failed!")
            sys.exit(1)
        except ValueError as e:
            if "GOVERNANCE REJECTION" in str(e):
                print(f"   SUCCESS: Blocked as expected. Error: {e}")
            else:
                print(f"   FAILURE: Unexpected error: {e}")
                sys.exit(1)
                
        # Test 2: Positive Case
        print("\n3. Test: Attempting update on SUNDAY WITH Second Approver...")
        try:
            ConfigManager.update_config(
                automation_id=auto_id,
                new_config={"param": 3},
                reason="Critical Hotfix",
                second_approver="VP_Trading"
            )
            print("   SUCCESS: Update allowed with Second Approver.")
        except Exception as e:
            print(f"   FAILURE: Valid update blocked! Error: {e}")
            sys.exit(1)

    print("\nVERIFICATION COMPLETE: Governance logic checked.")

if __name__ == "__main__":
    verify_governance()
