@echo off
echo ==========================================
echo      Modular Trading Platform Startup
echo      (Fallback: Local Python Mode)
echo ==========================================
echo NOTICE: Docker not found. Running local simulation.

echo [1/3] Starting API Gateway...
start "API Gateway" cmd /k "cd api && echo Starting Uvicorn... && python -m uvicorn main:app --reload --port 8000"

echo [2/3] Starting Local Demo Simulation...
start "Demo Brain" cmd /k "echo Running Simulation... && python run_demo.py"

echo [3/3] Starting Safety and Monitoring Dashboard...
start "Monitoring" cmd /k "python -m streamlit run dashboard/dashboard_advanced.py"

echo ==========================================
echo      Local Demo Mode Launched!
echo ==========================================
echo Dashboard: http://localhost:8501
echo API Docs: http://localhost:8000/docs
pause
