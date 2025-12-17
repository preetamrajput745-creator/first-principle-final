@echo off
echo ==========================================
echo      SAFE STARTUP MODE (Production-Like)
echo      Prevents White Screen & Memory Leaks
echo ==========================================

echo [1/4] Installing Python Dependencies...
pip install -r api/requirements.txt >nul 2>&1

echo [2/4] Cleaning Old Database Locks...
if exist *.db-journal del *.db-journal
if exist *.db-shm del *.db-shm
if exist *.db-wal del *.db-wal

echo [3/4] Building Frontend (One-Time Setup)...
cd frontend
if not exist .next (
    echo       Building optimized version... (This takes time)
    call npm install >nul 2>&1
    call npm run build
) else (
    echo       Using existing build (Fast Start)
)

echo [4/4] Launching System...
start "BACKEND_BRAIN" cmd /k "cd .. && python api/main.py"
start "WORKER_INGEST" cmd /k "cd .. && python workers/ingest/main.py"
start "FRONTEND_FACE" cmd /k "npm start"

echo.
echo ==========================================
echo      SYSTEM IS RUNNING STABLY
echo ==========================================
echo Access Dashboard: http://localhost:3000
echo.
echo DO NOT CLOSE THE BLACK WINDOWS.
pause
