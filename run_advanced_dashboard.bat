@echo off
echo Starting False Breakout Automation - ADVANCED UI...

start "Advanced Dashboard" cmd /k "streamlit run dashboard/dashboard_advanced.py --server.port 8501"

echo Advanced Dashboard started at http://localhost:8501
pause
