@echo off
color 0A
title First Principle - System Verification & Launch
cls

echo ===================================================
echo      FIRST PRINCIPLE AUTOMATION SYSTEM
echo      FINAL PRE-FLIGHT VERIFICATION
echo ===================================================
echo.

echo [1/5] Checking Python Environment...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found! Please install Python 3.11+
    pause
    exit
)
echo [OK] Python found.

echo.
echo [2/5] Installing/Verifying Dependencies...
pip install -r api/requirements.txt > nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit
)
echo [OK] Dependencies installed.

echo.
echo [3/5] Verifying Database Schema...
python -c "from workers.common.database import Base, engine; Base.metadata.create_all(bind=engine)"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Database schema check failed.
    pause
    exit
)
echo [OK] Database ready.

echo.
echo [4/6] Running Safety Checks (Mistake 10 and Mistake 3)...
python verify_mistake_10.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] CIRCUIT BREAKER CHECK FAILED!
    pause
    exit
)

python verify_mistake_3.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] TIME SYNC CHECK FAILED!
    pause
    exit
)
echo [OK] Safety Checks PASSED.

python verify_mistake_6.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] ISOLATION ^& RBAC CHECK FAILED!
    pause
    exit
)


echo.
echo [5/7] Checking Governance & Audit Logs (Mistakes 5, 7, 8)...
python verify_mistake_5.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] CONFIG GOVERNANCE CHECK FAILED!
    pause
    exit
)
python verify_gating_audit.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] GATING/AUDIT CHECK FAILED!
    pause
    exit
)
echo [OK] Governance & Audits Verified.





echo.
echo [6/7] Final Safety Verification...
python -c "print('System Ready for Live Launch')"

echo.
echo [7/7] Launching FULL LIVE SYSTEM...
echo.
timeout /t 3

call run_system.bat


