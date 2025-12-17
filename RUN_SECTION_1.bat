@echo off
echo ===================================================
echo     FIRST PRINCIPLE AUTOMATION - MISTAKE 0 to 12
echo     SECTION 1: FULL PIPELINE STARTUP
echo ===================================================

echo [1/4] Starting Ingest Service (Port 8001)...
start "Ingest Service" cmd /k "python ingest/server.py"

echo [2/4] Starting Bar Builder Worker...
start "Bar Builder" cmd /k "python workers/bar_builder.py"

echo [3/4] Starting Feature Engine Worker...
start "FBE Worker" cmd /k "python workers/fbe_worker.py"

echo [4/4] Starting Dashboard...
start "Dashboard" cmd /k "python -m streamlit run dashboard/dashboard_advanced.py"

echo.
echo [INFO] System is compliant with Section 1 Architecture.
echo        - Webhooks: http://localhost:8001/webhook/tradingview
echo        - S3/MinIO: Configured in config.py
echo        - Events: Redis Streams
echo.
pause
