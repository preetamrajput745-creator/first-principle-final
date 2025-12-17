
@echo off
color 0B
echo ===================================================
echo      FIRST PRINCIPLE - FIX AND LAUNCH
echo      Starting all components including Frontend
echo ===================================================

echo.
echo [1/4] Starting API Gateway (Port 8000)...
start "API Gateway" cmd /k "cd api && python -m uvicorn main:app --reload --port 8000"

echo.
echo [2/4] Starting Streamlit Dashboard (Port 8501)...
start "Monitoring Dashboard" cmd /k "python -m streamlit run dashboard/dashboard_advanced.py"

echo.
echo [3/4] Starting Next.js Frontend (Port 3000)...
cd frontend
if exist "node_modules" (
    start "Frontend UI" cmd /k "npm run dev"
) else (
    echo [WARN] node_modules not found in frontend. Installing...
    call npm install
    start "Frontend UI" cmd /k "npm run dev"
)
cd ..

echo.
echo [4/4] Starting Demo Simulation (Data Generator)...
start "Demo Simulation" cmd /k "python run_demo.py"

echo.
echo ===================================================
echo      ALL SYSTEMS LAUNCHED
echo ===================================================
echo.
echo 1. Frontend UI: http://localhost:3000
echo 2. Dashboard:   http://localhost:8501
echo 3. API Docs:    http://localhost:8000/docs
echo.
echo Please wait 10-20 seconds for services to boot.
echo.
pause
