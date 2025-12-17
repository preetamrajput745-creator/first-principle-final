# False Breakout Automation - Runbook

## Starting the System

### All Services at Once
```bash
run_all.bat
```

### Individual Services
```bash
# Ingest Service
python ingest/ingest_service.py

# Bar Builder
python bar_builder/bar_builder.py

# Feature Engine
python workers/fbe/feature_engine.py

# Scoring Engine
python workers/fbe/scoring_engine.py

# Simulator
python simulator/simulator.py

# Dashboard
streamlit run dashboard/dashboard.py

# Monitoring
python monitoring/monitor.py
```

## Stopping the System

Close each command window or press `Ctrl+C` in each terminal.

## Pausing Automation

### Via Python (Manual)
```python
from safety.circuit_breaker import circuit_breaker
circuit_breaker.trip("Manual pause by operator")
```

### Via Redis
```bash
redis-cli SET system.status PAUSED
redis-cli SET system.pause_reason "Manual pause"
```

## Resuming Automation

```python
from safety.circuit_breaker import circuit_breaker
circuit_breaker.reset()
```

Or via Redis:
```bash
redis-cli SET system.status RUNNING
```

## Viewing Last 100 Signals

### Via Dashboard
1. Open http://localhost:8501
2. Scroll to "Live Signals" section
3. Signals are shown in descending order (newest first)

### Via Database Query
```sql
SELECT * FROM signals 
ORDER BY created_at DESC 
LIMIT 100;
```

### Via Python
```python
from database import SessionLocal, Signal

db = SessionLocal()
signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(100).all()

for s in signals:
    print(f"{s.bar_time} | {s.symbol} | Score: {s.score} | Status: {s.status}")
```

## Common Operations

### Check System Status
```bash
redis-cli GET system.status
```

### View Worker Health
Check monitoring dashboard or:
```bash
redis-cli KEYS system.heartbeat.*
```

### Check Signal Rate
```sql
SELECT symbol, COUNT(*) as signal_count
FROM signals
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY symbol;
```

### View Daily PnL
```sql
SELECT 
    DATE(created_at) as trade_date,
    SUM(pnl) as daily_pnl,
    COUNT(*) as trades
FROM orders
WHERE is_paper = TRUE
GROUP BY DATE(created_at)
ORDER BY trade_date DESC;
```

## Troubleshooting

### Service Won't Start
1. Check if Redis is running: `redis-cli PING`
2. Check if Postgres is running
3. Check if MinIO/S3 is accessible
4. Review logs in terminal window

### No Signals Being Created
1. Check if Bar Builder is receiving ticks
2. Verify Feature Engine is processing bars
3. Check scoring threshold (might be too high)
4. Review Circuit Breaker status

### Dashboard Not Updating
1. Verify database connection
2. Check "Auto Refresh" checkbox
3. Refresh browser manually

## Emergency Procedures

### Runaway Signal Generation
```python
# Immediate pause
from safety.circuit_breaker import circuit_breaker
circuit_breaker.trip("Runaway signals detected")
```

### Database Connection Lost
1. Stop all workers
2. Verify Postgres is running
3. Restart workers one by one

### S3 Storage Full
1. Pause automation
2. Archive old data
3. Update retention policies
4. Resume automation

## Logs Location

All logs are printed to console (stdout). To save:
```bash
python ingest/ingest_service.py > logs/ingest.log 2>&1
```

## Contact

**Owner**: [Your Name]  
**On-Call**: Check monitoring alerts  
**Emergency**: Pause via Circuit Breaker, contact owner
