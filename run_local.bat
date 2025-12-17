@echo off
echo ==========================================
echo      Modular Trading Platform - Local Mode
echo      (Fallback: Docker not detected)
echo ==========================================

echo [1/8] Installing Dependencies...
pip install -r api/requirements.txt

echo [2/8] Initializing Kafka Topics...
python infra/init_kafka.py

echo [3/8] Running DB Migrations...
python migrate_db.py

echo [4/8] Starting API Gateway...
start "API Gateway" cmd /k "cd api && python -m uvicorn main:app --reload --port 8000"

echo [5/8] Starting Ingestion Worker...
start "Ingest Worker" cmd /k "python workers/ingest/main.py"

echo [6/8] Starting Bar Builder (NEW)...
start "Bar Builder" cmd /k "python bar_builder/bar_builder.py"

echo [7/8] Starting FBE Worker...
start "FBE Worker" cmd /k "python workers/fbe/main.py"

echo [8/8] Starting Execution Service...
start "Exec Service" cmd /k "python exec/main.py"

echo [Front] Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo ==========================================
echo      System Launched (Local Process Mode)
echo ==========================================
echo NOTE: For full Mistake 5 compliance (Isolation), install Docker Desktop
echo and run 'run_system.bat'.
echo.
echo Dashboard: http://localhost:3000
echo API Docs: http://localhost:8000/docs
pause
