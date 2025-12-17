import sqlite3
import pandas as pd
import os
import json
from datetime import datetime

DB_PATH = "sql_app.db"
OUTPUT_HTML = "system_status_snapshot.html"

def generate_snapshot():
    if not os.path.exists(DB_PATH):
        print("DB not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    
    # Queries
    try:
        signals = pd.read_sql("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10", conn)
    except: signals = pd.DataFrame()
    
    try:
        breakers = pd.read_sql("SELECT * FROM circuit_breaker_states", conn)
    except: breakers = pd.DataFrame()
    
    try:
        audit = pd.read_sql("SELECT * FROM circuit_breaker_events ORDER BY timestamp_utc DESC LIMIT 10", conn)
    except: audit = pd.DataFrame()
    
    try:
        config_audit = pd.read_sql("SELECT * FROM config_audit_logs ORDER BY timestamp DESC LIMIT 10", conn)
    except: config_audit = pd.DataFrame()

    conn.close()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>System Status Snapshot - {datetime.utcnow()}</title>
        <style>
            body {{ font-family: sans-serif; background: #f0f0f0; padding: 20px; }}
            .card {{ background: white; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h2 {{ border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 0.9em; }}
            th {{ background-color: #f8f9fa; }}
            .status-OPEN {{ color: red; font-weight: bold; }}
            .status-CLOSED {{ color: green; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Antigravity System Snapshot</h1>
        <p>Generated: {datetime.utcnow().isoformat()} UTC</p>
        
        <div class="card">
            <h2>Circuit Breaker Status (Safety Panel)</h2>
            {breakers.to_html(classes='table', index=False, escape=False) if not breakers.empty else "<p>No Data</p>"}
        </div>
        
        <div class="card">
            <h2>Recent Signals (Signal Flow)</h2>
            {signals.to_html(classes='table', index=False) if not signals.empty else "<p>No Data</p>"}
        </div>
        
        <div class="card">
            <h2>Circuit Breaker Audit Log (Immutable Events)</h2>
            {audit.to_html(classes='table', index=False) if not audit.empty else "<p>No Data</p>"}
        </div>
        
        <div class="card">
            <h2>Config Changelog (Governance)</h2>
            {config_audit.to_html(classes='table', index=False) if not config_audit.empty else "<p>No Data</p>"}
        </div>

    </body>
    </html>
    """
    
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Snapshot generated: {OUTPUT_HTML}")

if __name__ == "__main__":
    generate_snapshot()
