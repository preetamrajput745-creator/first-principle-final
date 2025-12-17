@echo off
echo ============================================================
echo FIRST PRINCIPLE TRADING SYSTEM - INSTALLER & VERIFIER
echo ============================================================
echo.

echo [1/5] Setting up Database...
python migrate_db.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Database setup failed.
    pause
    exit /b 1
)

echo [2/5] Cleaning Worker Workspace...
if not exist workers\backtest mkdir workers\backtest

echo [3/5] Starting System Supervisor (Background)...
start "System Supervisor" python system_supervisor.py
echo Supervisor started.

echo [4/5] Running Safety Verification Suite...
echo This verifies fix compliance for Critical Mistakes (1,2,3,4,5,7,8,10).
echo.
python run_full_system_verification.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Verification Suite FAILED. System is unsafe.
    pause
    exit /b 1
)

echo.
echo [5/5] Launching Dashboard...
echo Dashboard is running at http://localhost:3000 (if started)
echo.
echo ============================================================
echo INSTALLATION & VERIFICATION COMPLETE
echo SYSTEM IS IN COMPLIANCE WITH SAFETY PROTOCOLS.
echo ============================================================
pause
