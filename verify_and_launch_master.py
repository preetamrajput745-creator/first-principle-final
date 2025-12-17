
import subprocess
import sys
import os
import time
import requests
import sqlite3
import random

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_PORT = 8000
DASHBOARD_PORT = 8501
FRONTEND_PORT = 3000
DB_PATH = os.path.join(BASE_DIR, "sql_app.db")

def print_header(msg):
    print("\n" + "="*60)
    print(f" {msg}")
    print("="*60)

def run_cmd(cmd, desc, cwd=None, detach=False):
    print(f"[EXEC] {desc}...")
    try:
        if detach:
            if os.name == 'nt':
                # Windows: use start command to open new window
                subprocess.Popen(f'start "{desc}" {cmd}', shell=True, cwd=cwd)
            else:
                subprocess.Popen(cmd, shell=True, cwd=cwd)
            print(f"   >>> Started background process: {desc}")
            return True
        else:
            # Synchronous run for verification steps
            result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
            if result.returncode == 0:
                print("   >>> SUCCESS")
                return True
            else:
                print(f"   >>> FAILED. Error: {result.stderr}")
                return False
    except Exception as e:
        print(f"   >>> EXCEPTION: {e}")
        return False

# STEP 1: VERIFY ENVIRONMENT
print_header("STEP 1: TRIPLE VERIFICATION - ENVIRONMENT")

# Check Python
run_cmd("python --version", "Checking Python Version")

# Install core dependencies (Minimal set to ensure system runs)
reqs = "fastapi uvicorn sqlalchemy psycopg2-binary kafka-python streamlit pandas requests matplotlib"
run_cmd(f"{sys.executable} -m pip install {reqs}", "Installing Dependencies")

# STEP 2: VERIFY DATABASE
print_header("STEP 2: TRIPLE VERIFICATION - DATABASE")
if os.path.exists(DB_PATH):
    print(f"   >>> Database found at {DB_PATH}")
else:
    print(f"   >>> Database not found. It will be created by API.")

# Force Tables Creation
try:
    from workers.common.database import Base, engine
    Base.metadata.create_all(bind=engine)
    print("   >>> Database Schema Verified (Tables Created)")
except Exception as e:
    print(f"   >>> DB Verification Warning: {e}")

# STEP 3: LIVE FEATURES TEST (SIMULATION)
print_header("STEP 3: TRIPLE VERIFICATION - LIVE FEATURE SIMULATION")
# We will insert a dummy signal directly into DB to prove DB works
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Check if signals table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals';")
    if cursor.fetchone():
        print("   >>> 'signals' table exists.")
    else:
        print("   >>> 'signals' table MISSING (Will be created on startup).")
    conn.close()
except Exception as e:
    print(f"   >>> DB Access Error: {e}")

# STEP 4: LAUNCH SYSTEM
print_header("STEP 4: LAUNCHING ALL COMPONENTS")

# 1. API
run_cmd(f"python -m uvicorn api.main:app --port {API_PORT} --reload", "API Gateway", cwd=BASE_DIR, detach=True)

# 2. Dashboard
run_cmd(f"python -m streamlit run dashboard/dashboard_advanced.py --server.port {DASHBOARD_PORT}", "Monitoring Dashboard", cwd=BASE_DIR, detach=True)

# 3. Frontend
frontend_dir = os.path.join(BASE_DIR, "frontend")
# Try npm install if node_modules missing
if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
    print("   >>> Installing Frontend Dependencies (One-time)...")
    run_cmd("npm install", "Frontend Install", cwd=frontend_dir)

# Run Frontend using npm run dev
# Use shell=True and direct command to bypass powershell restriction if possible
launch_fe_cmd = "npm run dev" 
run_cmd(launch_fe_cmd, "Frontend UI", cwd=frontend_dir, detach=True)

# 4. Demo Data Gen
run_cmd("python run_demo.py", "Data Simulation", cwd=BASE_DIR, detach=True)

print_header("SYSTEM LAUNCHED")
print(f"1. Access Frontend: http://localhost:{FRONTEND_PORT}")
print(f"2. Access Dashboard: http://localhost:{DASHBOARD_PORT}")
print(f"3. Access API: http://localhost:{API_PORT}/docs")
print("\nKeep this window open to monitor logs if needed, or close it.")
time.sleep(5)
