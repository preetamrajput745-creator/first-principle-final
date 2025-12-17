import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = os.path.abspath(".")
AUDIT_DIR = os.path.join(BASE_DIR, "antigravity-audit/2025-12-12/20251212-ROLES-101/roles")
MOCK_FILE = os.path.join(BASE_DIR, "mock_owner_ui.html")

print("Initializing Browser for UI Capture...")
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--window-size=1200,800")
options.add_argument("--disable-gpu")

try:
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    
    # Load local file
    url = f"file:///{MOCK_FILE.replace(os.sep, '/')}"
    print(f"Loading {url}...")
    driver.get(url)
    time.sleep(2)
    
    screenshot_path = os.path.join(AUDIT_DIR, "owner_approval_flow_ui.png")
    driver.save_screenshot(screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")
    
    driver.quit()
except Exception as e:
    print(f"Failed to capture screenshot: {e}")
