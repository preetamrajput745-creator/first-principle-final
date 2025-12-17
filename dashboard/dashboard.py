import streamlit as st
import pandas as pd
import time
import json
import boto3
from datetime import datetime
from database import SessionLocal, Signal, Order, AuditLog
from config import settings

st.set_page_config(page_title="False Breakout Dashboard", layout="wide")

st.title("False Breakout Automation - Paper Mode")

# Database Connection
db = SessionLocal()

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Live Signals", "Config Editor", "Monitoring", "S3 Viewer"])

# ============= TAB 1: LIVE SIGNALS =============
with tab1:
    # Auto-refresh
    if st.checkbox("Auto Refresh", value=True):
        time.sleep(2)
        st.rerun()

    # Layout
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Live Signals")
        signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(20).all()
        
        if signals:
            data = []
            for s in signals:
                data.append({
                    "Time": s.bar_time,
                    "Symbol": s.symbol,
                    "Score": s.score,
                    "Status": s.status,
                    "Wick Ratio": f"{s.wick_ratio:.2f}",
                    "Vol Ratio": f"{s.vol_ratio:.2f}",
                    "ID": s.unique_signal_id
                })
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No signals yet.")

    with col2:
        st.subheader("Simulated Orders")
        orders = db.query(Order).order_by(Order.created_at.desc()).limit(20).all()
        
        if orders:
            data = []
            for o in orders:
                data.append({
                    "Time": o.created_at,
                    "Symbol": o.symbol,
                    "Side": o.side,
                    "Price": f"{o.price:.2f}",
                    "Slippage": f"{o.simulated_slippage:.4f}",
                    "PnL": f"{o.pnl:.2f}" if o.pnl else "0.00"
                })
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No orders yet.")

# ============= TAB 2: CONFIG EDITOR =============
with tab2:
    st.subheader("⚙️ Configuration Editor")
    
    st.warning("⚠️ Changes require system restart to take effect")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Scoring Thresholds")
        new_wick_threshold = st.number_input("Wick Ratio Threshold", 
            value=settings.WICK_RATIO_THRESHOLD, 
            min_value=0.0, max_value=2.0, step=0.1)
        
        new_vol_threshold = st.number_input("Volume Ratio Threshold", 
            value=settings.VOL_RATIO_THRESHOLD, 
            min_value=0.0, max_value=2.0, step=0.1)
        
        new_trigger_score = st.number_input("Trigger Score", 
            value=settings.TRIGGER_SCORE, 
            min_value=0, max_value=100, step=5)
        
        st.markdown("### Weights")
        new_weight_wick = st.number_input("Wick Weight", 
            value=settings.WEIGHT_WICK, 
            min_value=0, max_value=100, step=5)
        
        new_weight_vol = st.number_input("Volume Weight", 
            value=settings.WEIGHT_VOL, 
            min_value=0, max_value=100, step=5)
        
        new_weight_poke = st.number_input("Poke Weight", 
            value=settings.WEIGHT_POKE, 
            min_value=0, max_value=100, step=5)
    
    with col2:
        st.markdown("### Safety Limits")
        new_max_signals = st.number_input("Max Signals Per Hour", 
            value=settings.MAX_SIGNALS_PER_HOUR, 
            min_value=1, max_value=100, step=1)
        
        new_max_loss = st.number_input("Max Daily Loss", 
            value=settings.MAX_DAILY_LOSS, 
            min_value=0.0, step=100.0)
        
        st.markdown("### Slippage Model")
        new_slippage_base = st.number_input("Slippage Base", 
            value=settings.SLIPPAGE_BASE, 
            min_value=0.0, max_value=0.01, step=0.0001, format="%.4f")
        
        new_slippage_coeff = st.number_input("Slippage Vol Coefficient", 
            value=settings.SLIPPAGE_VOL_COEFF, 
            min_value=0.0, max_value=5.0, step=0.1)
    
    # Change reason
    change_reason = st.text_input("Reason for Change", placeholder="Required for audit...")
    user_id = st.text_input("Your Name/ID", placeholder="operator_name")
    
    if st.button("💾 Save Configuration", type="primary"):
        if not change_reason or not user_id:
            st.error("Please provide reason and user ID for audit trail")
        else:
            # Save to audit log
            audit_entry = AuditLog(
                user_id=user_id,
                action="config_change",
                details={
                    "old": {
                        "wick_threshold": settings.WICK_RATIO_THRESHOLD,
                        "vol_threshold": settings.VOL_RATIO_THRESHOLD,
                        "trigger_score": settings.TRIGGER_SCORE,
                        "weights": {
                            "wick": settings.WEIGHT_WICK,
                            "vol": settings.WEIGHT_VOL,
                            "poke": settings.WEIGHT_POKE
                        }
                    },
                    "new": {
                        "wick_threshold": new_wick_threshold,
                        "vol_threshold": new_vol_threshold,
                        "trigger_score": new_trigger_score,
                        "weights": {
                            "wick": new_weight_wick,
                            "vol": new_weight_vol,
                            "poke": new_weight_poke
                        }
                    }
                },
                reason=change_reason
            )
            db.add(audit_entry)
            db.commit()
            
            # Write to config file (for next restart)
            config_updates = f"""
# Updated by {user_id} on {datetime.utcnow().isoformat()}
# Reason: {change_reason}
WICK_RATIO_THRESHOLD = {new_wick_threshold}
VOL_RATIO_THRESHOLD = {new_vol_threshold}
TRIGGER_SCORE = {new_trigger_score}
WEIGHT_WICK = {new_weight_wick}
WEIGHT_VOL = {new_weight_vol}
WEIGHT_POKE = {new_weight_poke}
MAX_SIGNALS_PER_HOUR = {new_max_signals}
MAX_DAILY_LOSS = {new_max_loss}
SLIPPAGE_BASE = {new_slippage_base}
SLIPPAGE_VOL_COEFF = {new_slippage_coeff}
"""
            
            with open("config_updates.txt", "a") as f:
                f.write(config_updates)
            
            st.success("✅ Configuration saved to audit log! Restart system to apply changes.")
            st.info("📝 Changes written to: config_updates.txt")
    
    # Show recent changes
    st.markdown("### Recent Configuration Changes")
    recent_audits = db.query(AuditLog).filter(
        AuditLog.action == "config_change"
    ).order_by(AuditLog.timestamp.desc()).limit(5).all()
    
    if recent_audits:
        audit_data = []
        for a in recent_audits:
            audit_data.append({
                "Time": a.timestamp,
                "User": a.user_id,
                "Reason": a.reason
            })
        st.dataframe(pd.DataFrame(audit_data))

# ============= TAB 3: MONITORING =============
with tab3:
    st.subheader("📊 System Monitoring")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Signals (24h)", 
            db.query(Signal).count())
    
    with col2:
        st.metric("Total Orders (24h)", 
            db.query(Order).count())
    
    with col3:
        total_pnl = sum(o.pnl for o in db.query(Order).all() if o.pnl)
        st.metric("Total PnL (Paper)", f"${total_pnl:.2f}")
    
    # Signal rate per symbol
    st.markdown("### Signals Per Symbol")
    signal_counts = {}
    for symbol in settings.SYMBOLS:
        count = db.query(Signal).filter(Signal.symbol == symbol).count()
        signal_counts[symbol] = count
    
    st.bar_chart(signal_counts)

# ============= TAB 4: S3 VIEWER =============
with tab4:
    st.subheader("🗄️ S3 Snapshot Viewer")
    
    selected_signal_id = st.text_input("Enter Signal ID to View Snapshot")
    
    if st.button("Load Snapshot"):
        if selected_signal_id:
            sig = db.query(Signal).filter(Signal.unique_signal_id == selected_signal_id).first()
            if sig:
                st.write(f"**Symbol:** {sig.symbol} | **Score:** {sig.score} | **Time:** {sig.bar_time}")
                
                # Display stored data
                st.json(sig.scoring_breakdown)
                
                st.markdown("### Feature Snapshot Path")
                st.code(sig.raw_feature_snapshot_path)
                
                # Try to load from S3
                if sig.raw_feature_snapshot_path and sig.raw_feature_snapshot_path.startswith("s3://"):
                    try:
                        # Parse S3 path
                        path_parts = sig.raw_feature_snapshot_path.replace("s3://", "").split("/", 1)
                        bucket = path_parts[0]
                        key = path_parts[1]
                        
                        # Connect to S3
                        s3 = boto3.client(
                            's3',
                            endpoint_url=settings.S3_ENDPOINT_URL,
                            aws_access_key_id=settings.S3_ACCESS_KEY,
                            aws_secret_access_key=settings.S3_SECRET_KEY
                        )
                        
                        # Fetch object
                        response = s3.get_object(Bucket=bucket, Key=key)
                        snapshot_data = json.loads(response['Body'].read().decode('utf-8'))
                        
                        st.markdown("### 📄 Raw Feature Snapshot from S3")
                        st.json(snapshot_data)
                        
                    except Exception as e:
                        st.error(f"Could not load from S3: {e}")
                        st.info("Make sure MinIO/S3 is running and accessible")
                else:
                    st.warning("No S3 path available for this signal")
            else:
                st.error("Signal not found")
        else:
            st.warning("Please enter a signal ID")

db.close()
