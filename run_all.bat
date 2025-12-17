@echo off
echo Starting False Breakout Automation System...

start "API Server" cmd /k "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
start "Ingest Service" cmd /k "python ingest/ingest_service.py"
start "Bar Builder" cmd /k "python bar_builder/bar_builder.py"
start "Feature Engine" cmd /k "python workers/fbe/feature_engine.py"
start "Scoring Engine" cmd /k "python workers/fbe/scoring_engine.py"
start "Simulator" cmd /k "python simulator/simulator.py"
start "Monitoring" cmd /k "python monitoring/monitor.py"
start "Dashboard" cmd /k "streamlit run dashboard/dashboard_advanced.py"

echo All services started.
pause
