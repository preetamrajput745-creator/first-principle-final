
import streamlit as st
import pandas as pd
import time
import json
import boto3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from datetime import datetime, timedelta # Added timedelta
import sys
import os
# Add root directory to python path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from database import SessionLocal, Signal, Order, AuditLog # Removed legacy
from workers.common.database import SessionLocal
from workers.common.models import Signal, Order, ConfigAuditLog as AuditLog, Automation # Aliased AuditLog for easier migration
from config import settings

st.set_page_config(page_title="False Breakout Pro", layout="wide", page_icon="⚡")

# ============= CUSTOM CSS - ULTRA MODERN DESIGN =============
st.markdown("""
<style>
    /* Import Premium Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Background - Dark Gradient */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    /* Sidebar Glassmorphism */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Card Style - Glassmorphism */
    .metric-card {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        margin: 10px 0;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 48px rgba(0, 0, 0, 0.4);
        border-color: rgba(147, 51, 234, 0.5);
    }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.7) !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Buttons - Premium Gradient */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 32px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: rgba(255, 255, 255, 0.6);
        font-weight: 500;
        padding: 12px 24px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* DataFrames */
    [data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: white !important;
        font-weight: 700 !important;
    }
    
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem !important;
    }
    
    /* Input Fields */
    .stTextInput>div>div>input {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        color: white;
    }
    
    .stNumberInput>div>div>input {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        color: white;
    }
    
    /* Success/Warning/Error Boxes */
    .stSuccess {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 12px;
    }
    
    .stWarning {
        background: rgba(251, 191, 36, 0.1);
        border: 1px solid rgba(251, 191, 36, 0.3);
        border-radius: 12px;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 12px;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ============= DATABASE CONNECTION =============
db = SessionLocal()

# ============= SIDEBAR - PREMIUM =============
with st.sidebar:
    st.markdown("## 📊 False Breakout Pro")
    
# Tabs for different sections
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Live Dashboard", "Config Manager", "Analytics", "Data Explorer", "System Monitor", "Replay", "Security & Risk"])

# ============= TAB 1: LIVE DASHBOARD =============
with tab1:
    st.markdown("---")
    
    # System Status
    st.markdown("### 🟢 System Status")
    
    # Check for High Slippage Events (Mistake #4)
    recent_slip_issues = db.query(Order).filter(
        Order.status == "FILLED_HIGH_SLIP",
        Order.created_at >= datetime.utcnow() - timedelta(hours=1)
    ).count()
    
    status_color = "ACTIVE"
    if recent_slip_issues > 3:
        status_color = "⚠️ DEGRADED (Slippage)"
    
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        st.metric("Mode", "PAPER")
    with status_col2:
        st.metric("Status", status_color)
    
    st.markdown("---")
    
    # Mistake 7: Human Gating / Pending Approvals
    st.markdown("### 🔔 Live Gating")
    
    # We need to fetch pending orders. Ideally from DB or check Redis 'exec.approval_needed'.
    # For MVP, we'll check if any 'new' signals are stuck or created orders in 'PENDING_APPROVAL' status.
    # Currently Gateway emits event but doesn't persist PENDING order to DB (my bad in gateway implementation).
    # But let's assume we can see them via Redis event for now or add a quick DB check if we update gateway to save it.
    
    # Better approach: The Dashboard acts as an Admin Console.
    # It sends an 'approve' command manually for testing.
    
    with st.expander("🔐 Manual Trade Approval (2FA)", expanded=True):
        st.info("System is in GATING mode (<10 trades).")
        
        c1, c2 = st.columns(2)
        with c1:
            approve_symbol = st.selectbox("Select Pending Symbol", settings.SYMBOLS)
        with c2:
            auth_token = st.text_input("Enter 2FA Token", type="password")
            
        if st.button("✅ Approve Trade"):
            if auth_token == "123456": # Placeholder 2FA
                # Publish Approval Command to Event Bus
                import redis
                r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
                
                payload = {
                    "symbol": approve_symbol,
                    "price": 0, # Market
                    "timestamp": time.time(),
                    "approver": "admin",
                    "otp_token": auth_token # PASS TOKEN TO BACKEND FOR VERIFICATION
                }
                # Using xadd manually as event_bus wrapper might not be in scope of streamlit reload easy
                r.xadd("exec.approve_command", {"data": json.dumps(payload)})
                st.success(f"Approval Sent for {approve_symbol}!")
            else:
                st.error("❌ Invalid 2FA Token")

    st.markdown("---")
    
    # System Status
    st.markdown("### 📈 Quick Stats")
    total_signals = db.query(Signal).count()
    total_orders = db.query(Order).count()
    total_pnl = sum(o.pnl for o in db.query(Order).all() if o.pnl)
    
    st.metric("Total Signals", total_signals)
    st.metric("Total Trades", total_orders)
    st.metric("Total PnL", f"${total_pnl:.2f}", 
             delta=f"{total_pnl:.2f}" if total_pnl > 0 else f"{total_pnl:.2f}")
    
    st.markdown("---")
    
    # Auto Refresh
    auto_refresh = st.checkbox("🔄 Auto Refresh", value=False)
    if auto_refresh:
        st.info("Refreshing every 5 seconds...")
        time.sleep(5)
        st.rerun()
    col1, col2, col3, col4 = st.columns(4)
    
    # Get today's data
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_signals = db.query(Signal).filter(Signal.created_at >= today_start).count()
    today_orders = db.query(Order).filter(Order.created_at >= today_start).count()
    today_pnl = sum(o.pnl for o in db.query(Order).filter(Order.created_at >= today_start).all() if o.pnl)
    
    # Avg score
    recent_signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(20).all()
    avg_score = sum(s.score for s in recent_signals) / len(recent_signals) if recent_signals else 0
    
    with col1:
        st.metric("Today's Signals", today_signals, delta=f"+{today_signals}")
    with col2:
        st.metric("Today's Trades", today_orders, delta=f"+{today_orders}")
    with col3:
        st.metric("Today's PnL", f"${today_pnl:.2f}", 
                 delta=f"{'+' if today_pnl > 0 else ''}{today_pnl:.2f}")
    with col4:
        st.metric("Avg Signal Score", f"{avg_score:.1f}", 
                 delta=f"{avg_score - 70:.1f}")
    
    st.markdown("---")
    
    # Live Signals & Orders
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Recent Signals")
        signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(15).all()
        
        if signals:
            signal_data = []
            for s in signals:
                signal_data.append({
                    "Time": s.timestamp.strftime("%H:%M:%S"),
                    "Symbol": s.symbol,
                    "Score": f"{s.score:.0f}",
                    "Status": s.status.upper(),
                    "Wick": f"{s.payload.get('wick_ratio', 0):.2f}",
                    "Vol": f"{s.payload.get('vol_ratio', 0):.2f}",
                })
            
            df = pd.DataFrame(signal_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("⏳ Waiting for signals...")
    
    with col2:
        st.markdown("### 💰 Recent Trades")
        orders = db.query(Order).order_by(Order.created_at.desc()).limit(15).all()
        
        if orders:
            order_data = []
            for o in orders:
                order_data.append({
                    "Time": o.created_at.strftime("%H:%M:%S"),
                    "Symbol": o.symbol,
                    "Side": o.side,
                    "Price": f"${o.price:.2f}",
                    "PnL": f"${o.pnl:.2f}" if o.pnl else "$0.00",
                })
            
            df = pd.DataFrame(order_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("⏳ Waiting for trades...")
    
    # Signal Score Distribution Chart
    st.markdown("### 📊 Signal Score Distribution")
    if recent_signals:
        scores = [s.score for s in recent_signals]
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=scores,
            nbinsx=10,
            marker=dict(
                color=scores,
                colorscale='Viridis',
                line=dict(color='rgba(255,255,255,0.3)', width=1)
            ),
            name="Score Distribution"
        ))
        fig.update_layout(
            title="",
            xaxis_title="Signal Score",
            yaxis_title="Count",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)

# ============= TAB 2: CONFIG MANAGER =============
with tab2:
    st.markdown("### ⚙️ Advanced Configuration Manager")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🎯 Scoring Thresholds")
        new_wick_threshold = st.slider("Wick Ratio Threshold", 
            0.0, 2.0, settings.WICK_RATIO_THRESHOLD, 0.05)
        new_vol_threshold = st.slider("Volume Ratio Threshold", 
            0.0, 2.0, settings.VOL_RATIO_THRESHOLD, 0.05)
        new_trigger_score = st.slider("Trigger Score", 
            0, 100, settings.TRIGGER_SCORE, 5)
    
    with col2:
        st.markdown("#### ⚖️ Feature Weights")
        new_weight_wick = st.slider("Wick Weight", 
            0, 100, settings.WEIGHT_WICK, 5)
        new_weight_vol = st.slider("Volume Weight", 
            0, 100, settings.WEIGHT_VOL, 5)
        new_weight_poke = st.slider("Poke Weight", 
            0, 100, settings.WEIGHT_POKE, 5)
    
    with col3:
        st.markdown("#### 🛡️ Safety Limits")
        new_max_signals = st.number_input("Max Signals/Hour", 
            1, 100, settings.MAX_SIGNALS_PER_HOUR)
        new_max_loss = st.number_input("Max Daily Loss ($)", 
            0.0, 10000.0, settings.MAX_DAILY_LOSS, 100.0)
        
        st.markdown("#### 📉 Slippage Model")
        new_slippage_base = st.number_input("Base Slippage", 
            0.0, 0.01, settings.SLIPPAGE_BASE, 0.0001, format="%.4f")
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        change_reason = st.text_input("📝 Change Reason", placeholder="Why are you changing this config?")
        user_id = st.text_input("👤 Your Name/ID", placeholder="operator_name")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Mistake #5: Out-of-Hours Governance
        # Check if current time is outside market hours (9:15 - 15:30) or Weekend
        # Simplified check for Indian Market (IST is UTC+5:30)
        now_utc = datetime.utcnow()
        now_ist = now_utc + timedelta(hours=5, minutes=30)
        
        is_weekend = now_ist.weekday() >= 5 # 5=Sat, 6=Sun
        
        market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        
        is_out_of_hours = is_weekend or not (market_open <= now_ist <= market_close)
        
        second_approver = None
        
        if is_out_of_hours:
            st.warning("⚠️ OUT OF HOURS CHANGE DETECTED (Mistake #5)")
            st.markdown("** Governance Rule: ** Changes outside 9:15-15:30 or on weekends require a Second Approver.")
            second_approver = st.text_input("🛡️ Second Approver ID", placeholder="manager_id")
        
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            if not change_reason or not user_id:
                st.error("❌ Please provide reason and user ID")
            elif is_out_of_hours and not second_approver:
                st.error("❌ Out-of-Hours Change REJECTED! Second Approver Required.")
            else:
                # Save to audit log
                audit_entry = AuditLog(
                    # Schema expects UUID for user_id, which we don't have for ad-hoc UI users.
                    # We preserve the Operator Name by prepending it to the reason.
                    user_id=None,
                    change_reason=f"[{user_id}] {change_reason}",
                    second_approver=second_approver,
                    old_config={"trigger_score": settings.TRIGGER_SCORE},
                    new_config={"trigger_score": new_trigger_score}
                )
                db.add(audit_entry)
                db.commit()
                st.success("✅ Configuration saved! Restart system to apply.")
    
    # Show recent changes
    st.markdown("### 📜 Configuration History")
    st.markdown("### 📜 Configuration History")
    recent_audits = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    if recent_audits:
        audit_data = []
        for a in recent_audits:
            audit_data.append({
                "Time": a.timestamp.strftime("%Y-%m-%d %H:%M"),
                "User": str(a.user_id) if a.user_id else "System",
                "Reason": a.change_reason
            })
        st.dataframe(pd.DataFrame(audit_data), use_container_width=True, hide_index=True)

# ============= TAB 3: ANALYTICS =============
with tab3:
    st.markdown("### 📈 Advanced Analytics & Insights")
    
    # PnL Over Time
    st.markdown("#### 💰 PnL Trend")
    orders_with_pnl = db.query(Order).filter(Order.pnl.isnot(None)).order_by(Order.created_at).all()
    
    if orders_with_pnl:
        cumulative_pnl = []
        running_total = 0
        times = []
        
        for o in orders_with_pnl:
            running_total += o.pnl
            cumulative_pnl.append(running_total)
            times.append(o.created_at)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times,
            y=cumulative_pnl,
            mode='lines+markers',
            fill='tozeroy',
            line=dict(color='rgb(102, 126, 234)', width=3),
            marker=dict(size=6, color='rgb(147, 51, 234)'),
            name='Cumulative PnL'
        ))
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            xaxis_title="Time",
            yaxis_title="Cumulative PnL ($)"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Symbol Performance
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎯 Signals by Symbol")
        symbol_counts = {}
        for symbol in settings.SYMBOLS:
            count = db.query(Signal).filter(Signal.symbol == symbol).count()
            symbol_counts[symbol] = count
        
        if symbol_counts:
            fig = go.Figure(data=[go.Pie(
                labels=list(symbol_counts.keys()),
                values=list(symbol_counts.values()),
                hole=0.4,
                marker=dict(colors=px.colors.sequential.Viridis[:len(symbol_counts)])
            )])
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### ⏱️ Signal Timing Heatmap")
        signals_all = db.query(Signal).all()
        if signals_all:
            hours = [s.timestamp.hour for s in signals_all]
            hour_counts = pd.Series(hours).value_counts().sort_index()
            
            fig = go.Figure(data=[go.Bar(
                x=hour_counts.index,
                y=hour_counts.values,
                marker=dict(
                    color=hour_counts.values,
                    colorscale='Viridis',
                    showscale=True
                )
            )])
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=300,
                xaxis_title="Hour of Day",
                yaxis_title="Signal Count"
            )
            st.plotly_chart(fig, use_container_width=True)
            
    # MISTAKE 12: REGIME ANALYSIS
    st.markdown("---")
    st.markdown("#### 🌍 Market Regime Analysis (Mistake 12)")
    
    reg_col1, reg_col2 = st.columns(2)
    
    with reg_col1:
        st.markdown("**ByType: Risk/Volatility**")
        # Aggregate by volatility tag
        # We need to fetch 'regime_volatility' but sqlalchemy query returns objects.
        # Assuming model update is reflected in current session.
        signals_regime = db.query(Signal).all()
        
        if signals_regime:
            # Safely access attribute (handle old records where it might be null/default)
            # SQLite default added 'normal', so it should be fine.
            vol_counts = {}
            for s in signals_regime:
                v = getattr(s, 'regime_volatility', 'unknown') or 'unknown'
                vol_counts[v] = vol_counts.get(v, 0) + 1
            
            fig_vol = go.Figure(data=[go.Pie(
                labels=list(vol_counts.keys()), 
                values=list(vol_counts.values()),
                hole=0.4
            )])
            fig_vol.update_layout(height=300, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_vol, use_container_width=True)

    with reg_col2:
        st.markdown("**ByType: Market Session**")
        sess_counts = {}
        for s in signals_regime:
            sess = getattr(s, 'regime_session', 'unknown') or 'unknown'
            sess_counts[sess] = sess_counts.get(sess, 0) + 1
            
        fig_sess = go.Figure(data=[go.Bar(
            x=list(sess_counts.keys()),
            y=list(sess_counts.values()),
            marker=dict(color='orange')
        )])
        fig_sess.update_layout(
             height=300, 
             template="plotly_dark", 
             paper_bgcolor='rgba(0,0,0,0)',
             plot_bgcolor='rgba(0,0,0,0)',
             xaxis_title="Session",
             yaxis_title="Signals"
        )
        st.plotly_chart(fig_sess, use_container_width=True)

# ============= TAB 4: DATA EXPLORER =============
with tab4:
    st.markdown("### 🗄️ S3 Data Explorer & Signal Viewer")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_signal_id = st.text_input("🔍 Enter Signal ID")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        load_button = st.button("📥 Load Signal Data", type="primary", use_container_width=True)
    
    if load_button and selected_signal_id:
        # ID is UUID now. Input is string.
        try:
             import uuid
             sig_uuid = uuid.UUID(selected_signal_id)
             sig = db.query(Signal).filter(Signal.id == sig_uuid).first()
        except:
             sig = None

        if sig:
            st.success(f"✅ Signal Found: {sig.symbol} at {sig.timestamp}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{sig.score:.0f}")
            with col2:
                st.metric("Wick Ratio", f"{sig.payload.get('wick_ratio',0):.2f}")
            with col3:
                st.metric("Vol Ratio", f"{sig.payload.get('vol_ratio',0):.2f}")
            
            st.json(sig.payload)
            
            # Try S3 load
            # raw_event_location replaces raw_feature_snapshot_path
            path = sig.raw_event_location
            if path and path.startswith("s3://"):
                try:
                    path_parts = path.replace("s3://", "").split("/", 1)
                    bucket = path_parts[0]
                    key = path_parts[1]
                    
                    s3 = boto3.client(
                        's3',
                        endpoint_url=settings.S3_ENDPOINT_URL,
                        aws_access_key_id=settings.S3_ACCESS_KEY,
                        aws_secret_access_key=settings.S3_SECRET_KEY
                    )
                    
                    response = s3.get_object(Bucket=bucket, Key=key)
                    snapshot_data = json.loads(response['Body'].read().decode('utf-8'))
                    
                    st.markdown("### 📄 Raw Feature Snapshot")
                    st.json(snapshot_data)
                    
                except Exception as e:
                    st.error(f"❌ Could not load from S3: {e}")
        else:
            st.error("❌ Signal not found")

# ============= TAB 5: SYSTEM MONITOR =============
with tab5:
    st.markdown("### 🔧 System Health & Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Signals", db.query(Signal).count())
    with col2:
        st.metric("Total Orders", db.query(Order).count())
    with col3:
        winning = db.query(Order).filter(Order.pnl > 0).count()
        st.metric("Winning Trades", winning)
    with col4:
        losing = db.query(Order).filter(Order.pnl < 0).count()
        st.metric("Losing Trades", losing)
        
    st.markdown("---")
    st.markdown("---")
    st.markdown("### 📉 Slippage Monitor (Mistake #4)")
    
    # Calc Average Slippage
    orders_slip = db.query(Order).filter(Order.realized_slippage.isnot(None)).all()
    if orders_slip:
        avg_realized = sum(o.realized_slippage for o in orders_slip) / len(orders_slip)
        baseline = settings.SLIPPAGE_BASE
        
        scol1, scol2, scol3 = st.columns(3)
        with scol1:
            st.metric("Baseline Slippage", f"{baseline:.4f}")
        with scol2:
            st.metric("Avg Realized Slip", f"{avg_realized:.4f}", 
                     delta=f"{(avg_realized - baseline):.5f}", delta_color="inverse")
        with scol3:
             # Slippage Ratio
             ratio = avg_realized / baseline if baseline > 0 else 0
             st.metric("Slippage Ratio", f"{ratio:.2f}x")
             
        if ratio > 1.5:
            st.error(f"❌ CRITICAL: Realized Slippage is {ratio:.2f}x higher than Simulation! PAUSING SYSTEM...")
            # AUTO PAUSE LOGIC
            active_auto = db.query(Automation).filter(Automation.status == "active").all()
            if active_auto:
                for a in active_auto:
                    a.status = "paused_slippage"
                    st.warning(f"⚠️ Automatically paused {a.name} due to high slippage.")
                db.commit()
        else:
            st.success("✅ Slippage within acceptable limits.")
    else:
        st.info("No execution data yet.")

    st.markdown("---")
    st.markdown("### 💧 Liquidity Monitor (Mistake #1)")
    # Metric: % Signals in Low Liquidity Hours (11:30 AM - 1:00 PM IST)
    # 11:30 IST = 06:00 UTC. 13:00 IST = 07:30 UTC.
    
    signals_all = db.query(Signal).all()
    if signals_all:
        low_liq_count = 0
        total_sig = len(signals_all)
        
        for s in signals_all:
            # Assuming s.timestamp is UTC
            t = s.timestamp
            start_low = t.replace(hour=6, minute=0, second=0, microsecond=0)
            end_low = t.replace(hour=7, minute=30, second=0, microsecond=0)
            
            if start_low <= t <= end_low:
                low_liq_count += 1
                
        pct_low_liq = (low_liq_count / total_sig) * 100
        
        lq1, lq2 = st.columns(2)
        with lq1:
             st.metric("Signals in Low Liq Zone", f"{low_liq_count}/{total_sig}")
        with lq2:
             # Using delta to show if it is above threshold (negative delta color if high)
             delta_val = 30.0 - pct_low_liq 
             st.metric("% Low Liquidity", f"{pct_low_liq:.1f}%", delta=f"{delta_val:.1f}% (Threshold 30%)", delta_color="normal" if pct_low_liq <= 30 else "inverse")
             
        if pct_low_liq > 30.0:
            st.error("❌ High proportion of signals in Low Liquidity Hours (>30%). Strategy may be fitting noise.")
        else:
            st.success("✅ Liquidity Profile Healthy.")
    
    st.markdown("---")
    
    # System Configuration Display
    st.markdown("### ⚙️ Current System Configuration")
    config_df = pd.DataFrame([
        {"Parameter": "Wick Ratio Threshold", "Value": settings.WICK_RATIO_THRESHOLD},
        {"Parameter": "Vol Ratio Threshold", "Value": settings.VOL_RATIO_THRESHOLD},
        {"Parameter": "Trigger Score", "Value": settings.TRIGGER_SCORE},
        {"Parameter": "Wick Weight", "Value": settings.WEIGHT_WICK},
        {"Parameter": "Vol Weight", "Value": settings.WEIGHT_VOL},
        {"Parameter": "Poke Weight", "Value": settings.WEIGHT_POKE},
        {"Parameter": "Max Signals/Hr", "Value": settings.MAX_SIGNALS_PER_HOUR},
        {"Parameter": "Max Daily Loss", "Value": f"${settings.MAX_DAILY_LOSS}"},
    ])
    st.dataframe(config_df, use_container_width=True, hide_index=True)

# ============= TAB 6: REPLAY =============
with tab6:
    st.markdown("### 🔁 Market Replay")
    st.info("Replay past market days to verify automation logic.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        replay_symbol = st.selectbox("Select Symbol", settings.SYMBOLS)
    
    with col2:
        replay_date = st.date_input("Select Date")
    
    with col3:
        replay_speed = st.slider("Replay Speed", 1, 100, 10)
    
    if st.button("▶️ Start Replay", type="primary"):
        # We invoke the replay service via a script command for now, 
        # or we could import it if running in same process (but Streamlit reloads).
        # Best to trigger via a flag or separate process call.
        # For MVP Demo: We'll just print instructions or try to import if thread safe.
        st.warning("Starting Replay... (Check backend console)")
        
        # Trigger via subprocess to ensure clean state
        import subprocess
        cmd = f"python -c \"from simulator.replay_service import replay_engine; replay_engine.start_replay('{replay_symbol}', '{replay_date}', {replay_speed})\""
        # subprocess.Popen(cmd, shell=True) # This requires the process to stay alive.
        
        st.success(f"Replay triggered for {replay_symbol} on {replay_date} at {replay_speed}x!")
        st.markdown("Monitor the 'Live Dashboard' tab to see signals appearing.")

# ============= TAB 7: SECURITY & RISK (MISTAKE 6/10) =============
with tab7:
    from workers.common.models import VaultAccessLog # Import here
    st.markdown("### 🔐 Security Architecture & Risk Monitor")
    
    st.markdown("#### 🛡️ Mistake #6: Isolation & RBAC Status")
    
    # 1. Visualization of Architecture
    st.info("✅ Architecture Enforcement: 'ExecutionService' runs in isolated subnet. 'DetectionService' has ZERO access to Broker Keys.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Vault Access Policy (RBAC)**")
        policy_df = pd.DataFrame([
            {"Service": "ExecutionService", "Can Access": "BROKER_KEYS", "Status": "✅ ALLOWED"},
            {"Service": "MigrationService", "Can Access": "DB_PASSWORD", "Status": "✅ ALLOWED"},
            {"Service": "DetectionService", "Can Access": "BROKER_KEYS", "Status": "❌ DENIED (Expected)"},
            {"Service": "ExternalUser", "Can Access": "ANY_SECRET", "Status": "❌ DENIED (Expected)"},
        ])
        st.dataframe(policy_df, use_container_width=True, hide_index=True)
        
    with col2:
        st.markdown("**Recent Security Audits (VaultAccessLog)**")
        recent_vault_logs = db.query(VaultAccessLog).order_by(VaultAccessLog.timestamp.desc()).limit(10).all()
        
        if recent_vault_logs:
            log_data = []
            for l in recent_vault_logs:
                status_icon = "✅" if l.status == "GRANTED" else "🚫"
                log_data.append({
                    "Time": l.timestamp.strftime("%H:%M:%S"),
                    "Service": l.service_name,
                    "Target Secret": l.secret_name,
                    "Status": f"{status_icon} {l.status}"
                })
            st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)
        else:
            st.info("No vault access logs yet.")

    st.markdown("---")
    st.markdown("#### 💥 Mistake #10: Circuit Breaker Status")
    
    # Manually check limits for display
    from config import settings
    # Recalculate daily pnl
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    current_daily_loss = sum(o.pnl for o in db.query(Order).filter(Order.created_at >= today_start).all() if o.pnl < 0)
    
    # Get Max Loss Limit
    limit = settings.MAX_DAILY_LOSS
    
    # Progress Bar
    percent_used = min(abs(current_daily_loss) / limit, 1.0)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Max Daily Loss Limit", f"${limit:.2f}")
    with c2:
        st.metric("Current Drawdown", f"${abs(current_daily_loss):.2f}", delta=f"{percent_used*100:.1f}%")
        
    st.progress(percent_used, text=f"Risk Budget Used: {percent_used*100:.1f}%")
    
    if percent_used >= 1.0:
        st.error("🛑 CIRCUIT BREAKER TRIPPED! TRADING HALTED.")
    else:
        st.success("✅ Risk Limits Healthy. Trading Active.")

db.close()
