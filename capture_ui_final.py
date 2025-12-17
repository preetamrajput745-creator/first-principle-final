import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Get correct dynamic path
BASE_DIR = os.path.abspath(".")
# Look for the latest directory created by the previous step
audit_root = os.path.join(BASE_DIR, "antigravity-audit", "2025-12-12")
dirs = [d for d in os.listdir(audit_root) if "ROLES" in d]
# Sort by creation time usually, but here we can look for the ID "0eb" from previous step output or just take the latest
latest_task = sorted(dirs)[-1] # Lexicographically works if timestamps match, uuid otherwise
AUDIT_DIR = os.path.join(audit_root, latest_task, "roles")

MOCK_FILE = os.path.join(BASE_DIR, "mock_ui.html")

print(f"Capturing UI for Task: {latest_task}")
print(f"Target: {AUDIT_DIR}")

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--window-size=800,600")

try:
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    url = f"file:///{MOCK_FILE.replace(os.sep, '/')}"
    driver.get(url)
    time.sleep(1)
    
    out_path = os.path.join(AUDIT_DIR, "owner_approval_flow_ui.png")
    driver.save_screenshot(out_path)
    print(f"Saved: {out_path}")
    driver.quit()
except Exception as e:
    print(f"Error: {e}")
