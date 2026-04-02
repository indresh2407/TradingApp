#!/usr/bin/env python3
"""
SIDDHI - Intelligent Trading Platform
A beautiful real-time dashboard using Streamlit
"""

import os
import sys
import json
import subprocess
import signal
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

import streamlit as st
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.risk_manager import RiskManager, RiskConfig
from src.core.order_manager import OrderManager, Order, OrderStatus
from src.core.position_tracker import PositionTracker, Position
from src.utils import load_config, load_instruments
from src.utils.helpers import format_currency, is_market_open, get_credentials
from src.api.live_data import get_live_data_provider, LiveDataProvider
from src.api.stock_analyzer import get_quick_tips, analyze_stock, get_available_indices, detect_big_move_stocks, get_tomorrow_outlook, get_long_term_picks, get_multi_timeframe_signals
from src.api.backtester import quick_backtest
from src.core.trade_logger import get_daily_summary

# Page config
st.set_page_config(
    page_title="SIDDHI - Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Trading process management
PIDFILE = Path("logs/.trading.pid")

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .profit { color: #00c853 !important; }
    .loss { color: #ff1744 !important; }
    .stMetric > div { background-color: #f8f9fa; padding: 10px; border-radius: 8px; }
    .big-number { font-size: 2.5em; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def is_trading_running():
    """Check if trading system is running"""
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            return True, pid
        except (ProcessLookupError, ValueError):
            PIDFILE.unlink(missing_ok=True)
    return False, None


def get_current_mode():
    """Get current mode - always analysis"""
    return "analysis"


def _deprecated_set_trading_mode(mode):
    """Deprecated - trading mode removed"""
    pass


def _deprecated_config_update():
    """Placeholder for removed config update"""
    import yaml
    config_path = Path("config/settings.yaml")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    config["trading"]["mode"] = mode
    
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


class DashboardState:
    """Manages dashboard state and data"""
    
    def __init__(self):
        self.config = load_config()
        self.instruments = load_instruments()
        
        # Initialize components
        trading_config = self.config.get("trading", {})
        risk_config = self.config.get("risk", {})
        
        self.risk_manager = RiskManager(RiskConfig(
            capital=trading_config.get("capital", 100000),
            max_position_pct=risk_config.get("max_position_pct", 10),
            max_daily_loss_pct=risk_config.get("max_daily_loss_pct", 2),
            max_open_positions=risk_config.get("max_open_positions", 3),
        ))
        
        # Sample data for demo
        self._init_sample_data()
    
    def _init_sample_data(self):
        """Initialize sample data for demonstration"""
        if "daily_pnl_history" not in st.session_state:
            st.session_state.daily_pnl_history = []
        
        if "trading_mode" not in st.session_state:
            st.session_state.trading_mode = get_current_mode()


def load_general_logs(limit=50):
    """Load recent logs from trading.log"""
    logs = []
    log_file = Path("logs/trading.log")
    
    if log_file.exists():
        with open(log_file, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                logs.append(line.strip())
    
    return logs


def main():
    # Initialize state
    state = DashboardState()
    
    # Sidebar - Modern Design
    with st.sidebar:
        # Logo & Branding
        st.markdown("""
        <div style="text-align: center; padding: 15px 0 20px 0;">
            <div style="font-size: 2.5em; margin-bottom: 5px;">📈</div>
            <div style="font-size: 1.4em; font-weight: 700; color: #f8fafc; letter-spacing: 1px;">SIDDHI</div>
            <div style="font-size: 0.75em; color: #64748b; margin-top: 3px;">Intelligent Trading Platform</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Market Status Card
        market_open = is_market_open()
        
        mkt_dot = "🟢" if market_open else "🟠"
        mkt_text = "Open" if market_open else "Closed"
        current_time = datetime.now().strftime("%I:%M %p")
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 12px; padding: 15px; margin-bottom: 20px; border: 1px solid #334155;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="color: #94a3b8; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px;">Market</span>
                <span style="font-size: 0.9em;">{mkt_dot} <span style="color: #e2e8f0;">{mkt_text}</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #94a3b8; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px;">Time</span>
                <span style="font-size: 0.9em; color: #e2e8f0;">{current_time}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Analysis Mode Badge
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%); border: 1px solid #3b82f6; border-radius: 10px; padding: 10px; text-align: center; margin-bottom: 15px;">
            <span style="font-size: 1.1em; font-weight: 600; color: white;">📊 ANALYSIS MODE</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("Get intraday tips, signals, and analysis for stocks.")
        
        # Footer
        st.markdown("""
        <div style="position: fixed; bottom: 15px; left: 0; width: 260px; text-align: center; color: #475569; font-size: 0.7em;">
            ⚡ SIDDHI v1.0
        </div>
        """, unsafe_allow_html=True)
    
    # Custom CSS for beautiful tabs
    st.markdown("""
    <style>
    /* Tab container styling */
    .stTabs {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 10px 15px;
        border-radius: 15px;
        margin-bottom: 20px;
        border: 1px solid #334155;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* Tab list styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        padding: 5px;
        border-radius: 10px;
    }
    
    /* Individual tab styling */
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
        border-radius: 10px;
        padding: 12px 20px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.9em;
        border: 1px solid #475569;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Tab hover effect */
    .stTabs [data-baseweb="tab"]:hover {
        background: linear-gradient(135deg, #4b5563 0%, #374151 100%);
        color: #f1f5f9;
        border-color: #60a5fa;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(96, 165, 250, 0.3);
    }
    
    /* Active/Selected tab */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: white !important;
        border-color: #60a5fa !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
    }
    
    /* Tab highlight bar */
    .stTabs [data-baseweb="tab-highlight"] {
        background: transparent !important;
    }
    
    /* Tab border */
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }
    
    /* Tab panel content */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Navigation header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 5px;">
        <span style="color: #64748b; font-size: 0.75em; text-transform: uppercase; letter-spacing: 2px;">
            Navigation
        </span>
    </div>
    """, unsafe_allow_html=True)
        
    # Navigation at top using tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Dashboard", 
        "⚡ DayTrade",
        "🔍 Analyzer",
        "🌅 Tomorrow",
        "📈 Long Term",
        "⚙️ Settings", 
        "📜 Logs"
    ])
    
    with tab1:
        show_dashboard(state)
    with tab2:
        show_intraday_strategy(state)
    with tab3:
        show_stock_analyzer(state)
    with tab4:
        show_tomorrow_outlook(state)
    with tab5:
        show_long_term(state)
    with tab6:
        show_settings(state)
    with tab7:
        show_logs()


def show_dashboard(state):
    # Top metrics row - using HTML for reliable display
    try:
        capital = state.config.get("trading", {}).get("capital", 100000)
        daily_pnl = state.risk_manager.daily_stats.total_pnl
        pnl_color = "#4ade80" if daily_pnl >= 0 else "#f87171"
        pnl_pct = (daily_pnl/capital)*100 if capital > 0 else 0
        
        # Calculate time to square-off
        from datetime import datetime
        now = datetime.now()
        current_mins = now.hour * 60 + now.minute
        squareoff_mins = 15 * 60 + 15  # 3:15 PM
        time_to_squareoff = max(0, squareoff_mins - current_mins)
        
        if current_mins < 9 * 60 + 15:
            market_status = "Pre-Market"
            status_color = "#64748b"
        elif current_mins >= squareoff_mins:
            market_status = "Closed"
            status_color = "#ef4444"
        elif time_to_squareoff <= 30:
            market_status = f"{time_to_squareoff}m left"
            status_color = "#f97316"
        else:
            hours = time_to_squareoff // 60
            mins = time_to_squareoff % 60
            market_status = f"{hours}h {mins}m"
            status_color = "#22c55e"
        
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 10px;">
            <div style="background: #1f2937; padding: 15px; border-radius: 10px; text-align: center;">
                <div style="color: #9ca3af; font-size: 0.85em;">💰 Capital</div>
                <div style="color: white; font-size: 1.4em; font-weight: bold;">₹{capital:,.0f}</div>
            </div>
            <div style="background: #1f2937; padding: 15px; border-radius: 10px; text-align: center;">
                <div style="color: #9ca3af; font-size: 0.85em;">📈 Today's P&L</div>
                <div style="color: {pnl_color}; font-size: 1.4em; font-weight: bold;">₹{daily_pnl:,.0f}</div>
                <div style="color: {pnl_color}; font-size: 0.8em;">{pnl_pct:+.2f}%</div>
            </div>
            <div style="background: #1f2937; padding: 15px; border-radius: 10px; text-align: center;">
                <div style="color: #9ca3af; font-size: 0.85em;">⏱️ To Square-off</div>
                <div style="color: {status_color}; font-size: 1.4em; font-weight: bold;">{market_status}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading metrics: {e}")
    
    st.markdown("---")
    
    # Quick Stock Analyzer at TOP
    st.subheader("🔍 Quick Stock Analyzer")
    
    with st.form(key="stock_analyzer_form"):
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            analyze_symbol = st.text_input(
                "Enter Stock Symbol",
                placeholder="e.g., RELIANCE, TCS, ONGC",
                label_visibility="collapsed"
            ).upper().strip()
        with col_btn:
            analyze_btn = st.form_submit_button("Analyze", use_container_width=True, type="primary")
    
    # Store result in session state to persist after form submit
    if analyze_btn and analyze_symbol:
        try:
            result = analyze_stock(analyze_symbol)
            if result:
                st.session_state.analyzer_result = result
                st.session_state.analyzer_symbol = analyze_symbol
            else:
                st.session_state.analyzer_result = None
                st.error(f"Could not analyze {analyze_symbol}. Check symbol name.")
        except Exception as e:
            st.session_state.analyzer_result = None
            st.error(f"Error: {str(e)}")
    
    # Display result from session state
    if "analyzer_result" in st.session_state and st.session_state.analyzer_result:
        result = st.session_state.analyzer_result
        symbol = st.session_state.get("analyzer_symbol", "")
        
        try:
            # Time context
            time_warning = result.get("time_warning")
            can_trade = result.get("can_trade", True)
            mins_to_squareoff = result.get("mins_to_squareoff", 0)
            time_phase = result.get("time_phase", "UNKNOWN")
            
            # Show time warning if applicable
            if time_warning:
                st.warning(time_warning)
            if not can_trade:
                st.error("⛔ Market closing - no new positions recommended!")
            
            signal = result.get("signal", "NEUTRAL")
            ltp = float(result.get("ltp", 0))
            change_pct = float(result.get("change_pct", 0))
            entry = float(result.get("entry", ltp))
            stoploss = float(result.get("stoploss", ltp * 0.99))
            target1 = float(result.get("target1", ltp * 1.01))
            rsi = float(result.get("rsi", 50))
            reason = str(result.get("reason", "Analysis"))
            outlook = str(result.get("outlook", ""))
            
            # SUPERTREND data
            supertrend = str(result.get("supertrend", "NEUTRAL"))
            st_value = float(result.get("supertrend_value", ltp))
            st_crossover = result.get("supertrend_crossover", False)
            
            # VWAP data
            vwap = float(result.get("vwap", ltp))
            vwap_signal = str(result.get("vwap_signal", "NEUTRAL"))
            vwap_distance = float(result.get("vwap_distance", 0))
            
            # VOLATILITY data
            vol_score = int(result.get("volatility_score", 0))
            vol_rank = str(result.get("volatility_rank", "LOW"))
            atr_pct = float(result.get("atr_pct", 0))
            daily_range_pct = float(result.get("daily_range_pct", 0))
            is_volatile = result.get("is_volatile", False)
            
            # Confidence data
            confidence = str(result.get("confidence", "LOW"))
            st_vwap_aligned = result.get("st_vwap_aligned", False)
            
            # Signal display with confidence
            if signal == "LONG":
                if confidence == "HIGH" and st_vwap_aligned:
                    signal_color = "#166534"
                    signal_text = "📈 STRONG BUY"
                elif confidence == "MEDIUM":
                    signal_color = "#15803d"
                    signal_text = "📈 BUY (Medium)"
                else:
                    signal_color = "#4d7c0f"
                    signal_text = "📈 WEAK BUY"
            elif signal == "SHORT":
                if confidence == "HIGH" and st_vwap_aligned:
                    signal_color = "#991b1b"
                    signal_text = "📉 STRONG SELL"
                elif confidence == "MEDIUM":
                    signal_color = "#b91c1c"
                    signal_text = "📉 SELL (Medium)"
                else:
                    signal_color = "#c2410c"
                    signal_text = "📉 WEAK SELL"
            else:
                signal_color = "#92400e"
                signal_text = "⏸️ WAIT"
            
            # Supertrend display
            if supertrend == "BULLISH":
                st_color = "#22c55e"
                st_icon = "🟢"
                st_text = "BULLISH"
                if st_crossover:
                    st_text = "🔥 BUY!"
            elif supertrend == "BEARISH":
                st_color = "#ef4444"
                st_icon = "🔴"
                st_text = "BEARISH"
                if st_crossover:
                    st_text = "🔥 SELL!"
            else:
                st_color = "#f59e0b"
                st_icon = "🟡"
                st_text = "NEUTRAL"
            
            # VWAP display
            if vwap_signal == "BULLISH":
                vwap_color = "#22c55e"
                vwap_icon = "🟢"
                vwap_text = "ABOVE"
            elif vwap_signal == "BEARISH":
                vwap_color = "#ef4444"
                vwap_icon = "🔴"
                vwap_text = "BELOW"
            else:
                vwap_color = "#f59e0b"
                vwap_icon = "🟡"
                vwap_text = "AT VWAP"
            
            # VOLATILITY display
            if vol_rank == "HIGH":
                vol_color = "#ef4444"
                vol_icon = "🔥"
                vol_text = "HIGH"
            elif vol_rank == "MEDIUM":
                vol_color = "#f59e0b"
                vol_icon = "⚡"
                vol_text = "MEDIUM"
            else:
                vol_color = "#64748b"
                vol_icon = "💤"
                vol_text = "LOW"
            
            change_color = "#4ade80" if change_pct >= 0 else "#f87171"
            
            # Display as HTML card for reliability
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {signal_color} 0%, #1f2937 100%); 
                        padding: 15px; border-radius: 10px; margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div style="background: rgba(255,255,255,0.1); padding: 10px 20px; border-radius: 8px;">
                        <span style="font-size: 1.5em; font-weight: bold; color: white;">{signal_text}</span>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">{symbol}</div>
                        <div style="color: white; font-size: 1.3em; font-weight: bold;">₹{ltp:,.2f}</div>
                        <div style="color: {change_color};">{change_pct:+.2f}%</div>
                    </div>
                    <div style="text-align: center; background: {st_color}22; padding: 6px 10px; border-radius: 8px; border: 1px solid {st_color};">
                        <div style="color: #9ca3af; font-size: 0.65em;">SUPERTREND</div>
                        <div style="color: {st_color}; font-size: 0.85em; font-weight: bold;">{st_icon} {st_text}</div>
                        <div style="color: #9ca3af; font-size: 0.65em;">₹{st_value:,.0f}</div>
                    </div>
                    <div style="text-align: center; background: {vwap_color}22; padding: 6px 10px; border-radius: 8px; border: 1px solid {vwap_color};">
                        <div style="color: #9ca3af; font-size: 0.65em;">VWAP</div>
                        <div style="color: {vwap_color}; font-size: 0.85em; font-weight: bold;">{vwap_icon} {vwap_text}</div>
                        <div style="color: #9ca3af; font-size: 0.65em;">₹{vwap:,.0f} ({vwap_distance:+.1f}%)</div>
                    </div>
                    <div style="text-align: center; background: {vol_color}22; padding: 6px 10px; border-radius: 8px; border: 1px solid {vol_color};">
                        <div style="color: #9ca3af; font-size: 0.65em;">VOLATILITY</div>
                        <div style="color: {vol_color}; font-size: 0.85em; font-weight: bold;">{vol_icon} {vol_text}</div>
                        <div style="color: #9ca3af; font-size: 0.65em;">ATR: {atr_pct:.2f}%</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">ENTRY</div>
                        <div style="color: #60a5fa; font-size: 1.1em; font-weight: bold;">₹{entry:,.2f}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">SL</div>
                        <div style="color: #f87171; font-size: 1.1em; font-weight: bold;">₹{stoploss:,.2f}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">TARGET</div>
                        <div style="color: #4ade80; font-size: 1.1em; font-weight: bold;">₹{target1:,.2f}</div>
                    </div>
                </div>
                <div style="color: #9ca3af; font-size: 0.85em; margin-top: 10px;">
                    📊 {reason} | RSI: {rsi:.0f} | 🎯 {outlook}
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Display error: {e}")
    
    st.markdown("---")
    
    # My Positions Section
    st.subheader("💼 My Positions - Hold/Sell Advisor")
    
    # Initialize positions in session state
    if "my_positions" not in st.session_state:
        st.session_state.my_positions = []
    
    # Add new position form
    with st.form(key="add_position_form"):
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        with col1:
            pos_symbol = st.text_input("Stock Symbol", placeholder="e.g., RELIANCE").upper().strip()
        with col2:
            pos_type = st.selectbox("Type", ["LONG (Buy)", "SHORT (Sell)"])
        with col3:
            pos_entry_price = st.number_input("Entry Price (₹)", min_value=0.0, step=0.1, format="%.2f")
        with col4:
            pos_quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
        with col5:
            add_btn = st.form_submit_button("Search", type="primary")
    
    if add_btn and pos_symbol and pos_entry_price > 0:
        # Check if position already exists
        existing = [p for p in st.session_state.my_positions if p["symbol"] == pos_symbol]
        if existing:
            st.warning(f"{pos_symbol} already in your positions. Remove it first to update.")
        else:
            position_type = "LONG" if "LONG" in pos_type else "SHORT"
            st.session_state.my_positions.append({
                "symbol": pos_symbol,
                "entry_price": pos_entry_price,
                "quantity": pos_quantity,
                "type": position_type
            })
            st.success(f"Added {position_type} {pos_symbol} @ ₹{pos_entry_price}")
            st.rerun()
    
    # Display positions with signals
    if st.session_state.my_positions:
        for i, pos in enumerate(st.session_state.my_positions):
            try:
                symbol = pos["symbol"]
                entry_price = pos.get("entry_price", pos.get("buy_price", 0))  # backward compat
                quantity = pos["quantity"]
                pos_type = pos.get("type", "LONG")  # default to LONG for old positions
                
                # Get current analysis
                result = analyze_stock(symbol)
                
                if result:
                    ltp = result.get("ltp", 0)
                    rsi = result.get("rsi", 50)
                    momentum = result.get("momentum", 0)
                    signal = result.get("signal", "NEUTRAL")
                    
                    # Calculate P&L based on position type
                    if pos_type == "LONG":
                        # LONG: Profit when price goes UP
                        pnl = (ltp - entry_price) * quantity
                        pnl_pct = ((ltp - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                    else:
                        # SHORT: Profit when price goes DOWN
                        pnl = (entry_price - ltp) * quantity
                        pnl_pct = ((entry_price - ltp) / entry_price) * 100 if entry_price > 0 else 0
                    
                    # Determine Hold/Sell/Wait signal based on position type
                    if pos_type == "LONG":
                        # LONG position advice
                        if pnl_pct >= 2:  # In profit 2%+
                            if signal == "SHORT" or rsi > 70:
                                action = "🔴 SELL - Take Profit"
                                action_color = "#dc2626"
                            elif momentum < -1:
                                action = "🟡 TRAIL SL - Momentum weakening"
                                action_color = "#f59e0b"
                            else:
                                action = "🟢 HOLD - Let profits run"
                                action_color = "#16a34a"
                        elif pnl_pct <= -2:  # In loss 2%+
                            if signal == "SHORT" or momentum < -2:
                                action = "🔴 EXIT - Cut losses"
                                action_color = "#dc2626"
                            elif signal == "LONG":
                                action = "🟡 HOLD - Wait for recovery"
                                action_color = "#f59e0b"
                            else:
                                action = "🟡 REVIEW - Consider exit"
                                action_color = "#f59e0b"
                        else:  # Near breakeven
                            if signal == "LONG" and momentum > 0:
                                action = "🟢 HOLD - Momentum positive"
                                action_color = "#16a34a"
                            elif signal == "SHORT":
                                action = "🔴 EXIT - Bearish signal"
                                action_color = "#dc2626"
                            else:
                                action = "⏸️ WAIT - No clear direction"
                                action_color = "#6b7280"
                    else:
                        # SHORT position advice (inverted logic)
                        if pnl_pct >= 2:  # In profit 2%+ (price dropped)
                            if signal == "LONG" or rsi < 30:
                                action = "🔴 COVER - Take Profit"
                                action_color = "#dc2626"
                            elif momentum > 1:
                                action = "🟡 TRAIL SL - Reversal possible"
                                action_color = "#f59e0b"
                            else:
                                action = "🟢 HOLD SHORT - Let profits run"
                                action_color = "#16a34a"
                        elif pnl_pct <= -2:  # In loss 2%+ (price went up)
                            if signal == "LONG" or momentum > 2:
                                action = "🔴 COVER - Cut losses"
                                action_color = "#dc2626"
                            elif signal == "SHORT":
                                action = "🟡 HOLD - Wait for drop"
                                action_color = "#f59e0b"
                            else:
                                action = "🟡 REVIEW - Consider covering"
                                action_color = "#f59e0b"
                        else:  # Near breakeven
                            if signal == "SHORT" and momentum < 0:
                                action = "🟢 HOLD SHORT - Momentum negative"
                                action_color = "#16a34a"
                            elif signal == "LONG":
                                action = "🔴 COVER - Bullish signal"
                                action_color = "#dc2626"
                            else:
                                action = "⏸️ WAIT - No clear direction"
                                action_color = "#6b7280"
                    
                    pnl_color = "#4ade80" if pnl >= 0 else "#f87171"
                    type_badge = "📈 LONG" if pos_type == "LONG" else "📉 SHORT"
                    type_color = "#4ade80" if pos_type == "LONG" else "#f87171"
                    
                    # Display position card
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid {action_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                            <div>
                                <span style="font-size: 1.2em; font-weight: bold; color: white;">{symbol}</span>
                                <span style="color: {type_color}; margin-left: 10px; font-size: 0.85em;">{type_badge}</span>
                                <span style="color: #9ca3af; margin-left: 10px;">{quantity} shares</span>
                            </div>
                            <div style="background: {action_color}; padding: 5px 15px; border-radius: 5px;">
                                <span style="color: white; font-weight: bold;">{action}</span>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 10px;">
                            <div style="text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.75em;">ENTRY</div>
                                <div style="color: #60a5fa; font-weight: bold;">₹{entry_price:,.2f}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.75em;">CURRENT</div>
                                <div style="color: white; font-weight: bold;">₹{ltp:,.2f}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.75em;">P&L</div>
                                <div style="color: {pnl_color}; font-weight: bold;">₹{pnl:,.0f} ({pnl_pct:+.1f}%)</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.75em;">RSI</div>
                                <div style="color: white;">{rsi:.0f}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(f"Could not fetch data for {symbol}")
                    
            except Exception as e:
                st.error(f"Error with {pos.get('symbol', 'unknown')}: {e}")
        
        # Clear all button
        if st.button("🗑️ Clear All Positions", key="clear_my_positions"):
            st.session_state.my_positions = []
            st.rerun()
    else:
        st.info("No positions added. Enter your stock, buy price, and quantity above to get hold/sell signals.")
    
    st.markdown("---")
    
    # Two column layout - 50% each
    left_col, right_col = st.columns([1, 1])
    
    with left_col:
        # Trading Tips Section - Loads FIRST
        st.subheader("💡 Intraday Tips")
        
        # Index selector
        available_indices = get_available_indices()
        
        # Initialize session state for selected index
        if "selected_index" not in st.session_state:
            st.session_state.selected_index = "NIFTY 50"
        
        # Index selection buttons in a row
        st.markdown("**Select Index/Sector:**")
        
        # First row: Main indices
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("NIFTY 50", key="idx_nifty50", use_container_width=True, 
                        type="primary" if st.session_state.selected_index == "NIFTY 50" else "secondary"):
                st.session_state.selected_index = "NIFTY 50"
                st.session_state.tips_refresh = True
        with col2:
            if st.button("NIFTY 100", key="idx_nifty100", use_container_width=True,
                        type="primary" if st.session_state.selected_index == "NIFTY 100" else "secondary"):
                st.session_state.selected_index = "NIFTY 100"
                st.session_state.tips_refresh = True
        with col3:
            if st.button("NIFTY BANK", key="idx_niftybank", use_container_width=True,
                        type="primary" if st.session_state.selected_index == "NIFTY BANK" else "secondary"):
                st.session_state.selected_index = "NIFTY BANK"
                st.session_state.tips_refresh = True
        
        # Second row: Sector indices
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("NIFTY IT", key="idx_niftyit", use_container_width=True,
                        type="primary" if st.session_state.selected_index == "NIFTY IT" else "secondary"):
                st.session_state.selected_index = "NIFTY IT"
                st.session_state.tips_refresh = True
        with col2:
            if st.button("NIFTY AUTO", key="idx_niftyauto", use_container_width=True,
                        type="primary" if st.session_state.selected_index == "NIFTY AUTO" else "secondary"):
                st.session_state.selected_index = "NIFTY AUTO"
                st.session_state.tips_refresh = True
        with col3:
            if st.button("NIFTY PHARMA", key="idx_niftypharma", use_container_width=True,
                        type="primary" if st.session_state.selected_index == "NIFTY PHARMA" else "secondary"):
                st.session_state.selected_index = "NIFTY PHARMA"
                st.session_state.tips_refresh = True
        
        # Third row: More sectors
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("NIFTY METAL", key="idx_niftymetal", use_container_width=True,
                        type="primary" if st.session_state.selected_index == "NIFTY METAL" else "secondary"):
                st.session_state.selected_index = "NIFTY METAL"
                st.session_state.tips_refresh = True
        with col2:
            if st.button("NIFTY ENERGY", key="idx_niftyenergy", use_container_width=True,
                        type="primary" if st.session_state.selected_index == "NIFTY ENERGY" else "secondary"):
                st.session_state.selected_index = "NIFTY ENERGY"
                st.session_state.tips_refresh = True
        with col3:
            if st.button("🔄 Refresh", key="refresh_index_tips", use_container_width=True, help="Refresh tips with current prices"):
                st.session_state.tips_refresh = True
        
        # Fourth row: Full Market Scan (prominent button)
        if st.button("🌐 FULL MARKET SCAN (500+ Stocks)", key="idx_fullmarket", use_container_width=True,
                    type="primary" if st.session_state.selected_index == "FULL MARKET" else "secondary",
                    help="Scan entire market - stocks above ₹20"):
            st.session_state.selected_index = "FULL MARKET"
            st.session_state.tips_refresh = True
        
        if st.session_state.selected_index == "FULL MARKET":
            st.caption("⏳ Scanning 500+ stocks across all sectors (Price > ₹20). This may take a minute...")
        
        st.markdown("---")
        
        # Show selected index and last update time
        col_idx, col_time = st.columns([2, 1])
        with col_idx:
            st.markdown(f"**Analyzing: {st.session_state.selected_index}**")
        with col_time:
            if "tips_timestamp" in st.session_state:
                age_mins = (datetime.now() - st.session_state.tips_timestamp).seconds // 60
                age_secs = (datetime.now() - st.session_state.tips_timestamp).seconds % 60
                st.caption(f"Updated: {age_mins}m {age_secs}s ago")
        
        # Cache tips in session state - refresh on demand or every 5 minutes
        tips_age = 0
        if "tips_timestamp" in st.session_state:
            tips_age = (datetime.now() - st.session_state.tips_timestamp).seconds
        
        should_refresh = (
            "trading_tips" not in st.session_state or 
            st.session_state.get("tips_refresh", False) or
            tips_age > 300  # Auto-refresh every 5 minutes
        )
        
        if should_refresh:
            # Different spinner message for full market scan
            if st.session_state.selected_index == "FULL MARKET":
                spinner_msg = "🌐 Scanning 500+ stocks across entire market (Price > ₹20)..."
            else:
                spinner_msg = f"Analyzing {st.session_state.selected_index} stocks..."
            
            with st.spinner(spinner_msg):
                st.session_state.trading_tips = get_quick_tips(
                    index_name=st.session_state.selected_index,
                    num_tips=4 if st.session_state.selected_index == "FULL MARKET" else 2  # More tips for full scan
                )
                st.session_state.tips_timestamp = datetime.now()
                st.session_state.tips_refresh = False
        
        tips = st.session_state.trading_tips
        
        # === TIME CONTEXT DISPLAY ===
        # Show market timing information
        time_context = tips.get("time_context", {})
        market_phase = tips.get("market_phase", "UNKNOWN")
        time_warning = tips.get("time_warning")
        mins_to_squareoff = tips.get("mins_to_squareoff", 0)
        can_trade = tips.get("can_trade", True)
        
        # Time status bar
        if market_phase in ["PRIME", "AFTERNOON"]:
            time_color = "#22c55e"  # Green - good trading time
            time_icon = "🟢"
        elif market_phase in ["OPENING"]:
            time_color = "#f59e0b"  # Yellow - opening volatility
            time_icon = "🟡"
        elif market_phase in ["AFTERNOON_LATE", "LATE"]:
            time_color = "#f97316"  # Orange - getting late
            time_icon = "🟠"
        elif market_phase in ["CLOSING", "SQUARE_OFF"]:
            time_color = "#ef4444"  # Red - close/square off
            time_icon = "🔴"
        else:
            time_color = "#64748b"  # Gray - pre-market or other
            time_icon = "⚪"
        
        # Display time bar
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, {time_color}20 0%, {time_color}10 100%); 
                    padding: 8px 12px; border-radius: 8px; margin-bottom: 10px; 
                    border-left: 4px solid {time_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: {time_color}; font-weight: bold;">{time_icon} {market_phase.replace('_', ' ')}</span>
                <span style="color: #64748b; font-size: 0.85em;">⏱️ {mins_to_squareoff}m to square-off (3:15 PM)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show warning if applicable
        if time_warning:
            st.warning(time_warning)
        
        # Show if trading is disabled
        if not can_trade:
            st.error("⛔ No new positions - Market closing soon. Square off all intraday positions!")
        
        # Show info about what's being analyzed
        stocks_count = tips.get("stocks_analyzed", 0)
        if st.session_state.selected_index == "FULL MARKET":
            st.caption(f"🌐 Scanned {stocks_count} stocks from entire market (Price > ₹20). Showing top volatile picks.")
        else:
            st.caption(f"💡 Analyzing {stocks_count} stocks. Click any index/sector above to switch.")
        
        # Show error if any
        if tips.get("status") == "error":
            st.error(f"Error fetching tips: {tips.get('error', 'Unknown error')}")
            st.info("This could be due to market being closed or network issues. Try refreshing.")
        
        if tips["status"] == "success":
            # Run backtests if not cached
            if "backtest_results" not in st.session_state:
                st.session_state.backtest_results = {}
            
            # LONG Tips
            st.markdown("#### 🟢 Best for LONG")
            if tips.get("long_tips"):
                for tip in tips["long_tips"]:
                    try:
                        # Get values with safe defaults
                        symbol = str(tip.get('symbol', 'N/A'))
                        ltp = float(tip.get('ltp', 0))
                        change_pct = float(tip.get('change_pct', 0))
                        reason = str(tip.get('reason', 'Analysis'))
                        entry = float(tip.get('entry', ltp))
                        stoploss = float(tip.get('stoploss', ltp * 0.993))
                        target1 = float(tip.get('target1', ltp * 1.01))
                        scalp_sl = float(tip.get('scalp_sl', ltp * 0.998))
                        scalp_target = float(tip.get('scalp_target', ltp * 1.003))
                        
                        # SUPERTREND
                        supertrend = str(tip.get('supertrend', 'N/A'))
                        st_crossover = tip.get('supertrend_crossover', False)
                        st_value = float(tip.get('supertrend_value', ltp))
                        
                        # VWAP
                        vwap = float(tip.get('vwap', ltp))
                        vwap_signal = str(tip.get('vwap_signal', 'N/A'))
                        
                        # Conviction & Profit
                        conviction = int(tip.get('conviction_pct', 50))
                        scalp_profit = float(tip.get('scalp_profit_pct', 0.3))
                        swing_profit = float(tip.get('swing_profit_pct', 1.0))
                        
                        # VOLATILITY
                        vol_rank = tip.get('volatility_rank', 'LOW')
                        vol_score = int(tip.get('volatility_score', 0))
                        atr_pct = float(tip.get('atr_pct', 0))
                        
                        # Volatility color
                        if vol_rank == "HIGH":
                            vol_color = "#ef4444"
                            vol_icon = "🔥"
                        elif vol_rank == "MEDIUM":
                            vol_color = "#f59e0b"
                            vol_icon = "⚡"
                        else:
                            vol_color = "#64748b"
                            vol_icon = "💤"
                        
                        # Conviction color
                        if conviction >= 80:
                            conv_color = "#22c55e"
                            conv_icon = "🔥"
                        elif conviction >= 65:
                            conv_color = "#84cc16"
                            conv_icon = "✅"
                        else:
                            conv_color = "#f59e0b"
                            conv_icon = "⚠️"
                        
                        # Supertrend badge
                        if supertrend == "BULLISH":
                            st_badge = "🟢 ST+" if not st_crossover else "🔥 ST BUY!"
                        else:
                            st_badge = f"⚠️ ST-"
                        
                        # VWAP badge
                        if vwap_signal == "BULLISH":
                            vwap_badge = "🟢 >VWAP"
                        elif vwap_signal == "BEARISH":
                            vwap_badge = "🔴 <VWAP"
                        else:
                            vwap_badge = "🟡 =VWAP"
                        
                        # Display with Conviction, Profit & Volatility
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #166534 0%, #14532d 100%); 
                                    padding: 12px; border-radius: 10px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 1.1em; font-weight: bold; color: white;">📈 {symbol}</span>
                                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                                    <span style="background: {vol_color}33; color: {vol_color}; padding: 3px 8px; border-radius: 15px; font-size: 0.8em; font-weight: bold;">{vol_icon} Vol {vol_score}</span>
                                    <span style="background: {conv_color}33; color: {conv_color}; padding: 3px 8px; border-radius: 15px; font-size: 0.8em; font-weight: bold;">{conv_icon} {conviction}%</span>
                                    <span style="background: #3b82f633; color: #60a5fa; padding: 3px 8px; border-radius: 15px; font-size: 0.8em; font-weight: bold;">💰 +{swing_profit:.1f}%</span>
                                </div>
                            </div>
                            <div style="color: #86efac; font-size: 0.9em; margin-bottom: 6px;">
                                ₹{ltp:,.2f} ({change_pct:+.2f}%) | {st_badge} | {vwap_badge}
                            </div>
                            <div style="color: #9ca3af; font-size: 0.75em;">{reason} | ATR: {atr_pct:.2f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**⚡ Scalp** → +{scalp_profit:.2f}%")
                            st.caption(f"Entry: ₹{entry:,.2f} | SL: ₹{scalp_sl:,.2f} | Target: ₹{scalp_target:,.2f}")
                        with col2:
                            st.markdown(f"**🎯 Swing** → +{swing_profit:.2f}%")
                            st.caption(f"Entry: ₹{entry:,.2f} | SL: ₹{stoploss:,.2f} | Target: ₹{target1:,.2f}")
                        st.markdown("---")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.info("No strong LONG signals right now")
            
            st.markdown("")
            
            # SHORT Tips
            st.markdown("#### 🔴 Best for SHORT")
            if tips.get("short_tips"):
                for tip in tips["short_tips"]:
                    try:
                        # Get values with safe defaults
                        symbol = str(tip.get('symbol', 'N/A'))
                        ltp = float(tip.get('ltp', 0))
                        change_pct = float(tip.get('change_pct', 0))
                        reason = str(tip.get('reason', 'Analysis'))
                        entry = float(tip.get('entry', ltp))
                        stoploss = float(tip.get('stoploss', ltp * 1.007))
                        target1 = float(tip.get('target1', ltp * 0.99))
                        scalp_sl = float(tip.get('scalp_sl', ltp * 1.002))
                        scalp_target = float(tip.get('scalp_target', ltp * 0.997))
                        
                        # SUPERTREND
                        supertrend = str(tip.get('supertrend', 'N/A'))
                        st_crossover = tip.get('supertrend_crossover', False)
                        st_value = float(tip.get('supertrend_value', ltp))
                        
                        # VWAP
                        vwap = float(tip.get('vwap', ltp))
                        vwap_signal = str(tip.get('vwap_signal', 'N/A'))
                        
                        # Conviction & Profit
                        conviction = int(tip.get('conviction_pct', 50))
                        scalp_profit = float(tip.get('scalp_profit_pct', 0.3))
                        swing_profit = float(tip.get('swing_profit_pct', 1.0))
                        
                        # VOLATILITY
                        vol_rank = tip.get('volatility_rank', 'LOW')
                        vol_score = int(tip.get('volatility_score', 0))
                        atr_pct = float(tip.get('atr_pct', 0))
                        
                        # Volatility color
                        if vol_rank == "HIGH":
                            vol_color = "#ef4444"
                            vol_icon = "🔥"
                        elif vol_rank == "MEDIUM":
                            vol_color = "#f59e0b"
                            vol_icon = "⚡"
                        else:
                            vol_color = "#64748b"
                            vol_icon = "💤"
                        
                        # Conviction color
                        if conviction >= 80:
                            conv_color = "#22c55e"
                            conv_icon = "🔥"
                        elif conviction >= 65:
                            conv_color = "#84cc16"
                            conv_icon = "✅"
                        else:
                            conv_color = "#f59e0b"
                            conv_icon = "⚠️"
                        
                        # Supertrend badge
                        if supertrend == "BEARISH":
                            st_badge = "🔴 ST-" if not st_crossover else "🔥 ST SELL!"
                        else:
                            st_badge = f"⚠️ ST+"
                        
                        # VWAP badge
                        if vwap_signal == "BEARISH":
                            vwap_badge = "🔴 <VWAP"
                        elif vwap_signal == "BULLISH":
                            vwap_badge = "🟢 >VWAP"
                        else:
                            vwap_badge = "🟡 =VWAP"
                        
                        # Display with Conviction, Profit & Volatility
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #991b1b 0%, #7f1d1d 100%); 
                                    padding: 12px; border-radius: 10px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 1.1em; font-weight: bold; color: white;">📉 {symbol}</span>
                                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                                    <span style="background: {vol_color}33; color: {vol_color}; padding: 3px 8px; border-radius: 15px; font-size: 0.8em; font-weight: bold;">{vol_icon} Vol {vol_score}</span>
                                    <span style="background: {conv_color}33; color: {conv_color}; padding: 3px 8px; border-radius: 15px; font-size: 0.8em; font-weight: bold;">{conv_icon} {conviction}%</span>
                                    <span style="background: #3b82f633; color: #60a5fa; padding: 3px 8px; border-radius: 15px; font-size: 0.8em; font-weight: bold;">💰 +{swing_profit:.1f}%</span>
                                </div>
                            </div>
                            <div style="color: #fca5a5; font-size: 0.9em; margin-bottom: 6px;">
                                ₹{ltp:,.2f} ({change_pct:+.2f}%) | {st_badge} | {vwap_badge}
                            </div>
                            <div style="color: #9ca3af; font-size: 0.75em;">{reason} | ATR: {atr_pct:.2f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**⚡ Scalp** → +{scalp_profit:.2f}%")
                            st.caption(f"Entry: ₹{entry:,.2f} | SL: ₹{scalp_sl:,.2f} | Target: ₹{scalp_target:,.2f}")
                        with col2:
                            st.markdown(f"**🎯 Swing** → +{swing_profit:.2f}%")
                            st.caption(f"Entry: ₹{entry:,.2f} | SL: ₹{stoploss:,.2f} | Target: ₹{target1:,.2f}")
                        st.markdown("---")
                    except Exception as e:
                        st.warning(f"Error displaying tip: {e}")
            else:
                st.info("No strong SHORT signals right now")
            
            st.caption(f"🕐 Updated: {tips['timestamp'][11:19]}")
            
            if st.button("🔄 Refresh Tips", key="refresh_tips_main", use_container_width=True):
                st.session_state.tips_refresh = True
                st.rerun()
        else:
            st.error(f"Analysis failed: {tips.get('error', 'Unknown error')}")
            if st.button("🔄 Retry", key="retry_tips"):
                st.session_state.tips_refresh = True
                st.rerun()
        
        if st.button("🔄 Refresh All", key="refresh_dashboard", use_container_width=True):
            st.session_state.tips_refresh = True
            st.session_state.big_move_refresh = True
            st.rerun()
    
    with right_col:
        # Intraday Breakout Alert - Loads after Tips
        st.subheader("🚀 Breakout Alert")
        st.caption("Stocks coiling for big intraday moves")
        
        # Cache big move data
        if "big_move_data" not in st.session_state or st.session_state.get("big_move_refresh", False):
            with st.spinner("Scanning..."):
                st.session_state.big_move_data = detect_big_move_stocks(
                    index_name=st.session_state.get("selected_index", "NIFTY 50"),
                    num_stocks=5
                )
                st.session_state.big_move_refresh = False
        
        big_move_data = st.session_state.big_move_data
        
        # Show time context for breakout alerts
        ba_time_context = big_move_data.get("time_context", {})
        ba_mins_to_squareoff = big_move_data.get("mins_to_squareoff", 0)
        ba_time_warning = big_move_data.get("time_warning")
        ba_can_trade = big_move_data.get("can_trade", True)
        
        if ba_time_warning:
            st.warning(f"⏰ {ba_time_warning}")
        
        if not ba_can_trade:
            st.error("⛔ Market closed - No new breakout trades")
        
        if big_move_data.get("status") == "success" and big_move_data.get("big_move_stocks"):
            for stock in big_move_data["big_move_stocks"]:
                try:
                    symbol = stock["symbol"]
                    ltp = stock["ltp"]
                    change_pct = stock["change_pct"]
                    score = stock["breakout_score"]
                    direction = stock["direction"]
                    volume_ratio = stock["volume_ratio"]
                    signals = stock["signal_text"]
                    
                    # Get trading levels
                    entry = stock.get("entry", ltp)
                    stoploss = stock.get("stoploss", ltp * 0.99)
                    target1 = stock.get("target1", ltp * 1.02)
                    profit_pct = stock.get("profit_pct", 1.5)
                    risk_reward = stock.get("risk_reward", 1.5)
                    time_note = stock.get("time_note")  # Time warning if late in day
                    mins_left = stock.get("mins_to_squareoff", 0)
                    
                    # VOLATILITY
                    vol_label = stock.get("volatility_label", "")
                    vol_rank = stock.get("volatility_rank", "LOW")
                    vol_score_val = stock.get("volatility_score", 0)
                    
                    # Volatility color
                    if vol_rank == "HIGH":
                        vol_color = "#ef4444"
                    elif vol_rank == "MEDIUM":
                        vol_color = "#f59e0b"
                    else:
                        vol_color = "#64748b"
                    
                    # Direction colors
                    dir_color = "#22c55e" if direction == "BULLISH" else "#ef4444"
                    dir_icon = "🟢 LONG" if direction == "BULLISH" else "🔴 SHORT"
                    
                    # Score badge
                    if score >= 80:
                        score_badge = "🔥🔥🔥"
                    elif score >= 60:
                        score_badge = "🔥🔥"
                    elif score >= 45:
                        score_badge = "🔥"
                    else:
                        score_badge = "⚡"
                    
                    change_color = "#4ade80" if change_pct >= 0 else "#f87171"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                                padding: 12px; border-radius: 10px; margin-bottom: 10px; 
                                border-left: 4px solid {dir_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                            <span style="font-weight: bold; color: white; font-size: 1.1em;">{symbol}</span>
                            <div style="display: flex; gap: 4px; align-items: center;">
                                <span style="background: {vol_color}33; color: {vol_color}; padding: 2px 6px; border-radius: 10px; font-size: 0.7em;">{vol_label}</span>
                                <span style="background: {dir_color}33; color: {dir_color}; padding: 2px 8px; border-radius: 10px; font-size: 0.75em;">{dir_icon}</span>
                                <span style="color: #fbbf24; font-size: 0.85em;">{score_badge}</span>
                            </div>
                        </div>
                        <div style="color: {change_color}; font-size: 0.9em; margin: 5px 0;">₹{ltp:,.2f} ({change_pct:+.1f}%)</div>
                        <div style="display: flex; justify-content: space-between; background: #0f172a; padding: 8px; border-radius: 6px; margin: 5px 0;">
                            <div style="text-align: center;">
                                <div style="color: #64748b; font-size: 0.65em;">ENTRY</div>
                                <div style="color: white; font-size: 0.85em;">₹{entry:,.0f}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="color: #64748b; font-size: 0.65em;">SL</div>
                                <div style="color: #ef4444; font-size: 0.85em;">₹{stoploss:,.0f}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="color: #64748b; font-size: 0.65em;">TARGET</div>
                                <div style="color: #22c55e; font-size: 0.85em;">₹{target1:,.0f}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="color: #64748b; font-size: 0.65em;">PROFIT</div>
                                <div style="color: #3b82f6; font-size: 0.85em; font-weight: bold;">+{profit_pct:.1f}%</div>
                            </div>
                        </div>
                        <div style="color: #64748b; font-size: 0.7em;">{signals} | RR: {risk_reward:.1f}</div>
                        {"<div style='color: #f97316; font-size: 0.7em; margin-top: 4px;'>" + time_note + "</div>" if time_note else ""}
                    </div>
                    """, unsafe_allow_html=True)
                except:
                    pass
            
            if st.button("🔄 Refresh", key="refresh_breakout", use_container_width=True):
                st.session_state.big_move_refresh = True
                st.rerun()
            st.caption(f"Found {big_move_data.get('total_candidates', 0)} candidates from {big_move_data.get('stocks_with_data', 0)} stocks")
        else:
            # Show debug info
            if big_move_data.get("status") == "error":
                st.error(f"Error: {big_move_data.get('error', 'Unknown')}")
            else:
                st.warning("No breakouts detected")
                st.caption(f"Index: {st.session_state.get('selected_index', 'NIFTY 50')}")
                analyzed = big_move_data.get('stocks_analyzed', 0)
                with_data = big_move_data.get('stocks_with_data', 0)
                candidates = big_move_data.get('total_candidates', 0)
                st.caption(f"Scanned: {analyzed} | With data: {with_data} | Passed: {candidates}")
                if with_data == 0:
                    st.info("⚠️ No stock data available. Market may be closed or network issue.")
            if st.button("🔄 Scan Again", key="scan_breakout", use_container_width=True):
                st.session_state.big_move_refresh = True
                st.rerun()


def show_intraday_strategy(state):
    """Multi-Timeframe DayTrade Strategy with VWAP, Supertrend, Bollinger Bands"""
    st.title("⚡ DayTrade Strategy")
    st.markdown("**Multi-Timeframe Confirmation** using VWAP, Supertrend & Bollinger Bands on 5m and 10m charts")
    
    # Strategy explanation
    with st.expander("📖 Strategy Explained", expanded=False):
        st.markdown("""
        **Core Multi-Timeframe Indicators:**
        
        | Indicator | 5-Minute | 10-Minute | Purpose |
        |-----------|----------|-----------|---------|
        | **VWAP** | Entry timing | Trend bias | Price vs Volume-weighted average |
        | **Supertrend** | Entry signal | Trend confirmation | Dynamic support/resistance |
        | **Bollinger Bands** | Overbought/Oversold | Volatility squeeze | Mean reversion + breakout |
        
        ---
        
        **🆕 Advanced Predictive Indicators:**
        
        | Indicator | Signal | Purpose |
        |-----------|--------|---------|
        | **ADX** | Trend weakening | When ADX > 25 but falling, trend is fading - prepare for reversal |
        | **ROC (Rate of Change)** | Momentum divergence | Price making highs but ROC falling = bearish divergence |
        | **BB Squeeze** | Breakout coming | Bands narrowing = volatility compression, big move incoming |
        | **BB Walk & Curl** | Reversal warning | Price stops touching outer band & curls = reversal starting |
        | **VWAP Distance** | Rubber band effect | Price at 2nd/3rd StdDev from VWAP = overextended, will snap back |
        
        ---
        
        **Signal Requirements:**
        - Minimum **4 confirmations** across indicators
        - Advanced signals can ADD or SUBTRACT confirmations
        - Warnings shown when risk factors detected
        
        **Confidence Levels:**
        - 🔥🔥🔥 VERY HIGH (8+ confirmations)
        - 🔥🔥 HIGH (7 confirmations)  
        - 🔥 GOOD (6 confirmations)
        - ⚡ MODERATE (4-5 confirmations)
        """)
    
    # Index selector
    st.markdown("**Select Index/Sector:**")
    
    if "intraday_index" not in st.session_state:
        st.session_state.intraday_index = "NIFTY 50"
    
    # Row 1
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("NIFTY 50", key="itd_nifty50", use_container_width=True,
                    type="primary" if st.session_state.intraday_index == "NIFTY 50" else "secondary"):
            st.session_state.intraday_index = "NIFTY 50"
            st.session_state.intraday_refresh = True
    with col2:
        if st.button("NIFTY BANK", key="itd_niftybank", use_container_width=True,
                    type="primary" if st.session_state.intraday_index == "NIFTY BANK" else "secondary"):
            st.session_state.intraday_index = "NIFTY BANK"
            st.session_state.intraday_refresh = True
    with col3:
        if st.button("NIFTY IT", key="itd_niftyit", use_container_width=True,
                    type="primary" if st.session_state.intraday_index == "NIFTY IT" else "secondary"):
            st.session_state.intraday_index = "NIFTY IT"
            st.session_state.intraday_refresh = True
    with col4:
        if st.button("NIFTY AUTO", key="itd_niftyauto", use_container_width=True,
                    type="primary" if st.session_state.intraday_index == "NIFTY AUTO" else "secondary"):
            st.session_state.intraday_index = "NIFTY AUTO"
            st.session_state.intraday_refresh = True
    
    # Row 2
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("NIFTY PHARMA", key="itd_niftypharma", use_container_width=True,
                    type="primary" if st.session_state.intraday_index == "NIFTY PHARMA" else "secondary"):
            st.session_state.intraday_index = "NIFTY PHARMA"
            st.session_state.intraday_refresh = True
    with col2:
        if st.button("NIFTY METAL", key="itd_niftymetal", use_container_width=True,
                    type="primary" if st.session_state.intraday_index == "NIFTY METAL" else "secondary"):
            st.session_state.intraday_index = "NIFTY METAL"
            st.session_state.intraday_refresh = True
    with col3:
        if st.button("NIFTY ENERGY", key="itd_niftyenergy", use_container_width=True,
                    type="primary" if st.session_state.intraday_index == "NIFTY ENERGY" else "secondary"):
            st.session_state.intraday_index = "NIFTY ENERGY"
            st.session_state.intraday_refresh = True
    with col4:
        if st.button("🔄 Refresh", key="itd_refresh", use_container_width=True):
            st.session_state.intraday_refresh = True
    
    # Full Market
    if st.button("🌐 FULL MARKET (500+ Stocks)", key="itd_fullmarket", use_container_width=True,
                type="primary" if st.session_state.intraday_index == "FULL MARKET" else "secondary"):
        st.session_state.intraday_index = "FULL MARKET"
        st.session_state.intraday_refresh = True
    
    st.markdown("---")
    
    # Fetch data
    if "intraday_data" not in st.session_state or st.session_state.get("intraday_refresh", False):
        if st.session_state.intraday_index == "FULL MARKET":
            spinner_msg = "🌐 Scanning 500+ stocks with multi-timeframe analysis..."
        else:
            spinner_msg = f"⚡ Analyzing {st.session_state.intraday_index} on 5m & 10m timeframes..."
        
        with st.spinner(spinner_msg):
            st.session_state.intraday_data = get_multi_timeframe_signals(
                index_name=st.session_state.intraday_index,
                num_stocks=6 if st.session_state.intraday_index == "FULL MARKET" else 4
            )
            st.session_state.intraday_refresh = False
    
    data = st.session_state.intraday_data
    
    if data.get("status") == "success":
        # Time context
        market_phase = data.get("market_phase", "UNKNOWN")
        mins_to_squareoff = data.get("mins_to_squareoff", 0)
        
        # Time bar
        if market_phase in ["PRIME", "AFTERNOON"]:
            time_color = "#22c55e"
            time_icon = "🟢"
        elif market_phase in ["OPENING"]:
            time_color = "#f59e0b"
            time_icon = "🟡"
        elif market_phase in ["LATE", "CLOSING"]:
            time_color = "#ef4444"
            time_icon = "🔴"
        else:
            time_color = "#64748b"
            time_icon = "⚪"
        
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, {time_color}20 0%, {time_color}10 100%); 
                    padding: 10px 15px; border-radius: 10px; margin-bottom: 15px; 
                    border-left: 4px solid {time_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="color: {time_color}; font-weight: bold; font-size: 1.1em;">
                        {time_icon} {market_phase.replace('_', ' ')}
                    </span>
                    <span style="color: #64748b; margin-left: 15px;">
                        ⏱️ {mins_to_squareoff}m to square-off
                    </span>
                </div>
                <div style="color: #94a3b8; font-size: 0.85em;">
                    Analyzing: {st.session_state.intraday_index} | {data.get('stocks_analyzed', 0)} stocks | 
                    Generated: {data.get('generated_at', '')}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Stats bar
        st.markdown(f"""
        <div style="display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">
            <div style="background: #16532d; padding: 8px 15px; border-radius: 8px;">
                <span style="color: #86efac;">🟢 LONG Signals:</span>
                <span style="color: white; font-weight: bold; margin-left: 5px;">{data.get('total_long', 0)}</span>
            </div>
            <div style="background: #7f1d1d; padding: 8px 15px; border-radius: 8px;">
                <span style="color: #fca5a5;">🔴 SHORT Signals:</span>
                <span style="color: white; font-weight: bold; margin-left: 5px;">{data.get('total_short', 0)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Two columns for signals
        long_col, short_col = st.columns(2)
        
        with long_col:
            st.markdown("### 🟢 LONG Signals")
            st.caption("Multi-timeframe confirmed BUY setups")
            
            long_signals = data.get("long_signals", [])
            
            if long_signals:
                for sig in long_signals:
                    try:
                        symbol = sig["symbol"]
                        ltp = sig["ltp"]
                        change_pct = sig["change_pct"]
                        confidence_pct = sig.get("confidence_pct", 60)
                        reasons = sig.get("reason_text", "")
                        warnings = sig.get("warning_text", "")
                        
                        entry = sig.get("entry", ltp)
                        stoploss = sig.get("stoploss", ltp * 0.99)
                        target1 = sig.get("target1", ltp * 1.01)
                        target2 = sig.get("target2", ltp * 1.02)
                        
                        # Get indicator signals
                        vwap_5m = sig.get("vwap_5m_signal", "N/A")
                        st_5m = sig.get("st_5m_signal", "N/A")
                        bb_5m = sig.get("bb_5m_signal", "N/A")
                        vwap_10m = sig.get("vwap_10m_signal", "N/A")
                        st_10m = sig.get("st_10m_signal", "N/A")
                        bb_10m = sig.get("bb_10m_signal", "N/A")
                        
                        # Get advanced indicators
                        adx = sig.get("adx", 0)
                        adx_strength = sig.get("adx_strength", "N/A")
                        roc = sig.get("roc", 0)
                        roc_signal = sig.get("roc_signal", "N/A")
                        bb_squeeze = sig.get("bb_squeeze", False)
                        bb_curling = sig.get("bb_curling_up", False)
                        vwap_overext = sig.get("vwap_overextended_down", False)
                        roc_div = sig.get("roc_bullish_div", False)
                        
                        # Get profit potential
                        profit_potential = sig.get("profit_potential", 0)
                        target_status = sig.get("target_status", "🚀 ACTIVE")
                        
                        # Display card using native Streamlit
                        with st.container():
                            st.markdown(f"**📈 {symbol}** | ₹{ltp:,.2f} | {change_pct:+.2f}% | 🔥 {confidence_pct}%")
                            st.markdown(f"**💰 Profit Potential: {profit_potential:+.2f}%** | {target_status}")
                            
                            # Show reasons
                            if reasons:
                                st.caption(f"✅ {reasons}")
                            
                            # Show warnings if any
                            if warnings:
                                st.warning(warnings)
                            
                            # Indicator table using columns
                            col1, col2, col3 = st.columns(3)
                            col1.write("**Indicator**")
                            col2.write("**5-Min**")
                            col3.write("**10-Min**")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.write("VWAP")
                            col2.write("✅" if vwap_5m == "BULLISH" else "❌" if vwap_5m == "BEARISH" else "➖")
                            col3.write("✅" if vwap_10m == "BULLISH" else "❌" if vwap_10m == "BEARISH" else "➖")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.write("Supertrend")
                            col2.write("✅" if st_5m == "BULLISH" else "❌" if st_5m == "BEARISH" else "➖")
                            col3.write("✅" if st_10m == "BULLISH" else "❌" if st_10m == "BEARISH" else "➖")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.write("Bollinger")
                            col2.write("✅" if bb_5m in ["BULLISH", "OVERSOLD"] else "❌" if bb_5m in ["BEARISH", "OVERBOUGHT"] else "➖")
                            col3.write("✅" if bb_10m in ["BULLISH", "OVERSOLD"] else "❌" if bb_10m in ["BEARISH", "OVERBOUGHT"] else "➖")
                            
                            # Advanced indicators row
                            st.markdown("**Advanced:**")
                            adv1, adv2, adv3, adv4 = st.columns(4)
                            
                            # ADX
                            adx_icon = "🟢" if adx >= 25 else "🟡" if adx >= 20 else "🔴"
                            adv1.metric("ADX", f"{adx:.0f}", adx_strength[:4] if len(adx_strength) > 4 else adx_strength)
                            
                            # ROC
                            roc_icon = "✅" if roc_signal == "BULLISH" else "❌" if roc_signal == "BEARISH" else "➖"
                            adv2.metric("ROC", f"{roc:+.1f}%", roc_icon)
                            
                            # BB Status
                            bb_status = "🎯 Squeeze" if bb_squeeze else "↗️ Curl" if bb_curling else "➖"
                            adv3.write(f"**BB:** {bb_status}")
                            
                            # Special signals
                            special = []
                            if vwap_overext:
                                special.append("🎯 VWAP Snap")
                            if roc_div:
                                special.append("🔥 Divergence")
                            if bb_squeeze:
                                special.append("💥 Breakout")
                            adv4.write(" ".join(special) if special else "➖")
                            
                            st.caption(f"📋 BUY: Entry ₹{entry:,.0f} | SL ₹{stoploss:,.0f} | T1 ₹{target1:,.0f} | T2 ₹{target2:,.0f}")
                            st.markdown("---")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.info("No LONG signals with sufficient confirmation")
        
        with short_col:
            st.markdown("### 🔴 SHORT Signals")
            st.caption("Multi-timeframe confirmed SELL setups")
            
            short_signals = data.get("short_signals", [])
            
            if short_signals:
                for sig in short_signals:
                    try:
                        symbol = sig["symbol"]
                        ltp = sig["ltp"]
                        change_pct = sig["change_pct"]
                        confidence_pct = sig.get("confidence_pct", 60)
                        reasons = sig.get("reason_text", "")
                        warnings = sig.get("warning_text", "")
                        
                        entry = sig.get("entry", ltp)
                        stoploss = sig.get("stoploss", ltp * 1.01)
                        target1 = sig.get("target1", ltp * 0.99)
                        target2 = sig.get("target2", ltp * 0.98)
                        
                        # Get indicator signals
                        vwap_5m = sig.get("vwap_5m_signal", "N/A")
                        st_5m = sig.get("st_5m_signal", "N/A")
                        bb_5m = sig.get("bb_5m_signal", "N/A")
                        vwap_10m = sig.get("vwap_10m_signal", "N/A")
                        st_10m = sig.get("st_10m_signal", "N/A")
                        bb_10m = sig.get("bb_10m_signal", "N/A")
                        
                        # Get advanced indicators
                        adx = sig.get("adx", 0)
                        adx_strength = sig.get("adx_strength", "N/A")
                        roc = sig.get("roc", 0)
                        roc_signal = sig.get("roc_signal", "N/A")
                        bb_squeeze = sig.get("bb_squeeze", False)
                        bb_curling = sig.get("bb_curling_down", False)
                        vwap_overext = sig.get("vwap_overextended_up", False)
                        roc_div = sig.get("roc_bearish_div", False)
                        
                        # Get profit potential
                        profit_potential = sig.get("profit_potential", 0)
                        target_status = sig.get("target_status", "🚀 ACTIVE")
                        
                        # Display card using native Streamlit
                        with st.container():
                            st.markdown(f"**📉 {symbol}** | ₹{ltp:,.2f} | {change_pct:+.2f}% | 🔥 {confidence_pct}%")
                            st.markdown(f"**💰 Profit Potential: {profit_potential:+.2f}%** | {target_status}")
                            
                            # Show reasons
                            if reasons:
                                st.caption(f"✅ {reasons}")
                            
                            # Show warnings if any
                            if warnings:
                                st.warning(warnings)
                            
                            # Indicator table using columns (for SHORT, bearish is good)
                            col1, col2, col3 = st.columns(3)
                            col1.write("**Indicator**")
                            col2.write("**5-Min**")
                            col3.write("**10-Min**")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.write("VWAP")
                            col2.write("✅" if vwap_5m == "BEARISH" else "❌" if vwap_5m == "BULLISH" else "➖")
                            col3.write("✅" if vwap_10m == "BEARISH" else "❌" if vwap_10m == "BULLISH" else "➖")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.write("Supertrend")
                            col2.write("✅" if st_5m == "BEARISH" else "❌" if st_5m == "BULLISH" else "➖")
                            col3.write("✅" if st_10m == "BEARISH" else "❌" if st_10m == "BULLISH" else "➖")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.write("Bollinger")
                            col2.write("✅" if bb_5m in ["BEARISH", "OVERBOUGHT"] else "❌" if bb_5m in ["BULLISH", "OVERSOLD"] else "➖")
                            col3.write("✅" if bb_10m in ["BEARISH", "OVERBOUGHT"] else "❌" if bb_10m in ["BULLISH", "OVERSOLD"] else "➖")
                            
                            # Advanced indicators row
                            st.markdown("**Advanced:**")
                            adv1, adv2, adv3, adv4 = st.columns(4)
                            
                            # ADX
                            adx_icon = "🟢" if adx >= 25 else "🟡" if adx >= 20 else "🔴"
                            adv1.metric("ADX", f"{adx:.0f}", adx_strength[:4] if len(adx_strength) > 4 else adx_strength)
                            
                            # ROC
                            roc_icon = "✅" if roc_signal == "BEARISH" else "❌" if roc_signal == "BULLISH" else "➖"
                            adv2.metric("ROC", f"{roc:+.1f}%", roc_icon)
                            
                            # BB Status
                            bb_status = "🎯 Squeeze" if bb_squeeze else "↘️ Curl" if bb_curling else "➖"
                            adv3.write(f"**BB:** {bb_status}")
                            
                            # Special signals
                            special = []
                            if vwap_overext:
                                special.append("🎯 VWAP Snap")
                            if roc_div:
                                special.append("🔥 Divergence")
                            if bb_squeeze:
                                special.append("💥 Breakout")
                            adv4.write(" ".join(special) if special else "➖")
                            
                            st.caption(f"📋 SELL: Entry ₹{entry:,.0f} | SL ₹{stoploss:,.0f} | T1 ₹{target1:,.0f} | T2 ₹{target2:,.0f}")
                            st.markdown("---")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.info("No SHORT signals with sufficient confirmation")
        
        # Refresh button
        st.markdown("---")
        if st.button("🔄 Refresh Signals", key="refresh_intraday_main", use_container_width=True):
            st.session_state.intraday_refresh = True
            st.rerun()
    else:
        st.error(f"Error: {data.get('error', 'Unknown error')}")
        if st.button("🔄 Try Again", key="retry_intraday", use_container_width=True):
            st.session_state.intraday_refresh = True
            st.rerun()


def show_tomorrow_outlook(state):
    """Tomorrow's Intraday - Stocks good for day trading tomorrow"""
    st.title("🌅 Tomorrow's Intraday")
    st.markdown("**Stocks good for INTRADAY trading tomorrow.** Exit same day by 3:15 PM. Best analyzed after 3 PM.")
    
    # Index selector for Tomorrow's Outlook
    st.markdown("**Select Index/Sector to Scan:**")
    
    # Initialize session state for tomorrow index
    if "tomorrow_index" not in st.session_state:
        st.session_state.tomorrow_index = "NIFTY 50"
    
    # Index selection in rows
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("NIFTY 50", key="tmrw_nifty50", use_container_width=True,
                    type="primary" if st.session_state.tomorrow_index == "NIFTY 50" else "secondary"):
            st.session_state.tomorrow_index = "NIFTY 50"
            st.session_state.tomorrow_refresh = True
            st.rerun()
    with col2:
        if st.button("NIFTY 100", key="tmrw_nifty100", use_container_width=True,
                    type="primary" if st.session_state.tomorrow_index == "NIFTY 100" else "secondary"):
            st.session_state.tomorrow_index = "NIFTY 100"
            st.session_state.tomorrow_refresh = True
            st.rerun()
    with col3:
        if st.button("NIFTY BANK", key="tmrw_niftybank", use_container_width=True,
                    type="primary" if st.session_state.tomorrow_index == "NIFTY BANK" else "secondary"):
            st.session_state.tomorrow_index = "NIFTY BANK"
            st.session_state.tomorrow_refresh = True
            st.rerun()
    with col4:
        if st.button("NIFTY IT", key="tmrw_niftyit", use_container_width=True,
                    type="primary" if st.session_state.tomorrow_index == "NIFTY IT" else "secondary"):
            st.session_state.tomorrow_index = "NIFTY IT"
            st.session_state.tomorrow_refresh = True
            st.rerun()
    
    # Second row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("NIFTY AUTO", key="tmrw_niftyauto", use_container_width=True,
                    type="primary" if st.session_state.tomorrow_index == "NIFTY AUTO" else "secondary"):
            st.session_state.tomorrow_index = "NIFTY AUTO"
            st.session_state.tomorrow_refresh = True
            st.rerun()
    with col2:
        if st.button("NIFTY PHARMA", key="tmrw_niftypharma", use_container_width=True,
                    type="primary" if st.session_state.tomorrow_index == "NIFTY PHARMA" else "secondary"):
            st.session_state.tomorrow_index = "NIFTY PHARMA"
            st.session_state.tomorrow_refresh = True
            st.rerun()
    with col3:
        if st.button("NIFTY METAL", key="tmrw_niftymetal", use_container_width=True,
                    type="primary" if st.session_state.tomorrow_index == "NIFTY METAL" else "secondary"):
            st.session_state.tomorrow_index = "NIFTY METAL"
            st.session_state.tomorrow_refresh = True
            st.rerun()
    with col4:
        if st.button("NIFTY ENERGY", key="tmrw_niftyenergy", use_container_width=True,
                    type="primary" if st.session_state.tomorrow_index == "NIFTY ENERGY" else "secondary"):
            st.session_state.tomorrow_index = "NIFTY ENERGY"
            st.session_state.tomorrow_refresh = True
            st.rerun()
    
    # Full Market Scan
    if st.button("🌐 FULL MARKET SCAN (500+ Stocks)", key="tmrw_fullmarket", use_container_width=True,
                type="primary" if st.session_state.tomorrow_index == "FULL MARKET" else "secondary"):
        st.session_state.tomorrow_index = "FULL MARKET"
        st.session_state.tomorrow_refresh = True
        st.rerun()
    
    st.markdown("---")
    
    # Show selected index
    st.markdown(f"**Analyzing: {st.session_state.tomorrow_index}**")
    
    # Cache tomorrow's outlook data - always refresh if index changed
    cache_key = f"tomorrow_outlook_{st.session_state.tomorrow_index}"
    if cache_key not in st.session_state or st.session_state.get("tomorrow_refresh", False):
        if st.session_state.tomorrow_index == "FULL MARKET":
            spinner_msg = "🌐 Scanning 500+ stocks for tomorrow's intraday..."
        else:
            spinner_msg = f"Analyzing {st.session_state.tomorrow_index} for tomorrow's intraday..."
        
        with st.spinner(spinner_msg):
            st.session_state[cache_key] = get_tomorrow_outlook(
                index_name=st.session_state.tomorrow_index,
                num_stocks=6 if st.session_state.tomorrow_index == "FULL MARKET" else 4
            )
            st.session_state.tomorrow_refresh = False
    
    outlook_data = st.session_state[cache_key]
    
    if outlook_data.get("status") == "success":
        # Market Bias Header
        market_bias = outlook_data.get("market_bias", "NEUTRAL")
        bias_color = "#22c55e" if market_bias == "BULLISH" else "#ef4444" if market_bias == "BEARISH" else "#f59e0b"
        bias_icon = "📈" if market_bias == "BULLISH" else "📉" if market_bias == "BEARISH" else "➡️"
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {bias_color}20 0%, #1f293710 100%); 
                    padding: 15px; border-radius: 12px; margin-bottom: 20px; 
                    border-left: 5px solid {bias_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="color: {bias_color}; font-weight: bold; font-size: 1.3em;">
                        {bias_icon} {market_bias} Outlook
                    </span>
                    <span style="color: #9ca3af; font-size: 0.9em; margin-left: 15px;">
                        for {outlook_data.get('for_date', 'Tomorrow')}
                    </span>
                </div>
                <span style="color: #64748b; font-size: 0.85em;">
                    Generated at {outlook_data.get('generated_at', '')}
                </span>
            </div>
            <div style="color: #94a3b8; font-size: 0.9em; margin-top: 8px;">
                {outlook_data.get('market_note', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Stats bar
        st.markdown(f"""
        <div style="display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap;">
            <div style="background: #1e293b; padding: 10px 20px; border-radius: 8px;">
                <span style="color: #64748b;">Stocks Analyzed:</span>
                <span style="color: white; font-weight: bold; margin-left: 5px;">{outlook_data.get('stocks_analyzed', 0)}</span>
            </div>
            <div style="background: #16532d; padding: 10px 20px; border-radius: 8px;">
                <span style="color: #86efac;">Long Setups:</span>
                <span style="color: white; font-weight: bold; margin-left: 5px;">{outlook_data.get('total_long', 0)}</span>
            </div>
            <div style="background: #7f1d1d; padding: 10px 20px; border-radius: 8px;">
                <span style="color: #fca5a5;">Short Setups:</span>
                <span style="color: white; font-weight: bold; margin-left: 5px;">{outlook_data.get('total_short', 0)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Two columns for long and short setups
        bull_col, bear_col = st.columns(2)
        
        with bull_col:
            st.markdown("### 🟢 LONG Tomorrow")
            st.caption("BUY these tomorrow - exit same day")
            long_setups = outlook_data.get("long_setups", [])
            
            if long_setups:
                for setup in long_setups:
                    try:
                        symbol = setup["symbol"]
                        ltp = setup["ltp"]
                        change_pct = setup["change_pct"]
                        score = setup["score"]
                        signals = setup.get("signal_text", "")
                        plan = setup.get("tomorrow_plan", {})
                        atr_pct = setup.get("atr_pct", 1.5)
                        close_pos = setup.get("close_position", 50)
                        
                        vwap_entry = plan.get("vwap_entry", ltp)
                        orb_entry = plan.get("orb_entry", ltp * 1.005)
                        stoploss = plan.get("stoploss", ltp * 0.98)
                        target1 = plan.get("target1", ltp * 1.01)
                        reward_pct = plan.get("reward_pct", 1.0)
                        strategy = plan.get("strategy", "Trend")
                        
                        # Score badge
                        if score >= 60:
                            score_badge = "🔥🔥"
                        elif score >= 45:
                            score_badge = "🔥"
                        else:
                            score_badge = "⚡"
                        
                        change_color = "#4ade80" if change_pct >= 0 else "#f87171"
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                                    padding: 15px; border-radius: 12px; margin-bottom: 12px; 
                                    border-left: 4px solid #22c55e;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: bold; color: white; font-size: 1.2em;">{symbol}</span>
                                <span style="color: #fbbf24; font-size: 0.9em;">{score_badge} {score}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                                <span style="color: {change_color}; font-size: 0.9em;">₹{ltp:,.2f} ({change_pct:+.1f}%)</span>
                                <span style="color: #60a5fa; font-size: 0.8em;">ATR: {atr_pct:.1f}%</span>
                            </div>
                            <div style="color: #94a3b8; font-size: 0.8em; margin: 8px 0;">{signals}</div>
                            <div style="background: #0f172a; padding: 10px; border-radius: 8px; margin-top: 10px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                    <span style="color: #22c55e; font-size: 0.85em; font-weight: bold;">📋 {strategy}</span>
                                    <span style="color: #64748b; font-size: 0.75em;">Close: {close_pos:.0f}%</span>
                                </div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.8em;">
                                    <div>
                                        <span style="color: #64748b;">Entry:</span>
                                        <span style="color: white; font-weight: bold;"> ₹{vwap_entry:,.0f}</span>
                                    </div>
                                    <div>
                                        <span style="color: #64748b;">ORB:</span>
                                        <span style="color: #60a5fa; font-weight: bold;"> ₹{orb_entry:,.0f}</span>
                                    </div>
                                    <div>
                                        <span style="color: #64748b;">SL:</span>
                                        <span style="color: #ef4444; font-weight: bold;"> ₹{stoploss:,.0f}</span>
                                    </div>
                                    <div>
                                        <span style="color: #64748b;">TGT:</span>
                                        <span style="color: #22c55e; font-weight: bold;"> ₹{target1:,.0f}</span>
                                    </div>
                                </div>
                                <div style="color: #3b82f6; font-size: 0.85em; margin-top: 8px; text-align: right; font-weight: bold;">
                                    💰 Potential: +{reward_pct:.1f}%
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    except:
                        pass
            else:
                st.info(f"No LONG setups found. Analyzed {outlook_data.get('stocks_analyzed', 0)} stocks.")
        
        with bear_col:
            st.markdown("### 🔴 SHORT Tomorrow")
            st.caption("SELL these tomorrow - exit same day")
            short_setups = outlook_data.get("short_setups", [])
            
            if short_setups:
                for setup in short_setups:
                    try:
                        symbol = setup["symbol"]
                        ltp = setup["ltp"]
                        change_pct = setup["change_pct"]
                        score = setup["score"]
                        signals = setup.get("signal_text", "")
                        plan = setup.get("tomorrow_plan", {})
                        atr_pct = setup.get("atr_pct", 1.5)
                        close_pos = setup.get("close_position", 50)
                        
                        vwap_entry = plan.get("vwap_entry", ltp)
                        orb_entry = plan.get("orb_entry", ltp * 0.995)
                        stoploss = plan.get("stoploss", ltp * 1.02)
                        target1 = plan.get("target1", ltp * 0.99)
                        reward_pct = plan.get("reward_pct", 1.0)
                        strategy = plan.get("strategy", "Trend")
                        
                        # Score badge
                        if score >= 60:
                            score_badge = "🔥🔥"
                        elif score >= 45:
                            score_badge = "🔥"
                        else:
                            score_badge = "⚡"
                        
                        change_color = "#4ade80" if change_pct >= 0 else "#f87171"
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                                    padding: 15px; border-radius: 12px; margin-bottom: 12px; 
                                    border-left: 4px solid #ef4444;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: bold; color: white; font-size: 1.2em;">{symbol}</span>
                                <span style="color: #fbbf24; font-size: 0.9em;">{score_badge} {score}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                                <span style="color: {change_color}; font-size: 0.9em;">₹{ltp:,.2f} ({change_pct:+.1f}%)</span>
                                <span style="color: #60a5fa; font-size: 0.8em;">ATR: {atr_pct:.1f}%</span>
                            </div>
                            <div style="color: #94a3b8; font-size: 0.8em; margin: 8px 0;">{signals}</div>
                            <div style="background: #0f172a; padding: 10px; border-radius: 8px; margin-top: 10px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                    <span style="color: #ef4444; font-size: 0.85em; font-weight: bold;">📋 {strategy}</span>
                                    <span style="color: #64748b; font-size: 0.75em;">Close: {close_pos:.0f}%</span>
                                </div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.8em;">
                                    <div>
                                        <span style="color: #64748b;">Entry:</span>
                                        <span style="color: white; font-weight: bold;"> ₹{vwap_entry:,.0f}</span>
                                    </div>
                                    <div>
                                        <span style="color: #64748b;">ORB:</span>
                                        <span style="color: #60a5fa; font-weight: bold;"> ₹{orb_entry:,.0f}</span>
                                    </div>
                                    <div>
                                        <span style="color: #64748b;">SL:</span>
                                        <span style="color: #ef4444; font-weight: bold;"> ₹{stoploss:,.0f}</span>
                                    </div>
                                    <div>
                                        <span style="color: #64748b;">TGT:</span>
                                        <span style="color: #22c55e; font-weight: bold;"> ₹{target1:,.0f}</span>
                                    </div>
                                </div>
                                <div style="color: #3b82f6; font-size: 0.85em; margin-top: 8px; text-align: right; font-weight: bold;">
                                    💰 Potential: +{reward_pct:.1f}%
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    except:
                        pass
            else:
                st.info(f"No SHORT setups found. Try refreshing or check after 3 PM.")
        
        # Refresh button
        st.markdown("---")
        if st.button("🔄 Refresh Tomorrow's Intraday", key="refresh_tomorrow_main", use_container_width=True):
            # Clear all tomorrow outlook caches
            keys_to_delete = [k for k in st.session_state.keys() if k.startswith("tomorrow_outlook")]
            for k in keys_to_delete:
                del st.session_state[k]
            st.session_state.tomorrow_refresh = True
            st.rerun()
    else:
        st.error(f"Error loading data: {outlook_data.get('error', 'Unknown error')}. Make sure market data is available.")
        if st.button("🔄 Try Again", key="retry_tomorrow_main", use_container_width=True):
            # Clear all tomorrow outlook caches
            keys_to_delete = [k for k in st.session_state.keys() if k.startswith("tomorrow_outlook")]
            for k in keys_to_delete:
                del st.session_state[k]
            st.session_state.tomorrow_refresh = True
            st.rerun()


def show_long_term(state):
    """Long Term Investment Picks - Multi-timeframe analysis"""
    st.title("📈 Long Term Investment")
    st.markdown("Find the best stocks for long-term wealth creation based on your investment horizon")
    
    # Initialize session state
    if "long_term_index" not in st.session_state:
        st.session_state.long_term_index = "NIFTY 50"
    if "long_term_period" not in st.session_state:
        st.session_state.long_term_period = "6 Months"
    
    # === CONFIGURATION SECTION ===
    st.markdown("### ⚙️ Configure Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Index Selection
        st.markdown("**Select Index/Sector:**")
        
        # Row 1 - Main indices
        idx_col1, idx_col2, idx_col3, idx_col4 = st.columns(4)
        with idx_col1:
            if st.button("NIFTY 50", key="lt_nifty50", use_container_width=True,
                        type="primary" if st.session_state.long_term_index == "NIFTY 50" else "secondary"):
                st.session_state.long_term_index = "NIFTY 50"
        with idx_col2:
            if st.button("NIFTY 100", key="lt_nifty100", use_container_width=True,
                        type="primary" if st.session_state.long_term_index == "NIFTY 100" else "secondary"):
                st.session_state.long_term_index = "NIFTY 100"
        with idx_col3:
            if st.button("NIFTY BANK", key="lt_niftybank", use_container_width=True,
                        type="primary" if st.session_state.long_term_index == "NIFTY BANK" else "secondary"):
                st.session_state.long_term_index = "NIFTY BANK"
        with idx_col4:
            if st.button("NIFTY IT", key="lt_niftyit", use_container_width=True,
                        type="primary" if st.session_state.long_term_index == "NIFTY IT" else "secondary"):
                st.session_state.long_term_index = "NIFTY IT"
        
        # Row 2 - Sector indices
        idx_col1, idx_col2, idx_col3, idx_col4 = st.columns(4)
        with idx_col1:
            if st.button("NIFTY AUTO", key="lt_niftyauto", use_container_width=True,
                        type="primary" if st.session_state.long_term_index == "NIFTY AUTO" else "secondary"):
                st.session_state.long_term_index = "NIFTY AUTO"
        with idx_col2:
            if st.button("NIFTY PHARMA", key="lt_niftypharma", use_container_width=True,
                        type="primary" if st.session_state.long_term_index == "NIFTY PHARMA" else "secondary"):
                st.session_state.long_term_index = "NIFTY PHARMA"
        with idx_col3:
            if st.button("NIFTY METAL", key="lt_niftymetal", use_container_width=True,
                        type="primary" if st.session_state.long_term_index == "NIFTY METAL" else "secondary"):
                st.session_state.long_term_index = "NIFTY METAL"
        with idx_col4:
            if st.button("NIFTY ENERGY", key="lt_niftyenergy", use_container_width=True,
                        type="primary" if st.session_state.long_term_index == "NIFTY ENERGY" else "secondary"):
                st.session_state.long_term_index = "NIFTY ENERGY"
        
        # Full Market Scan
        if st.button("🌐 FULL MARKET (500+ Stocks)", key="lt_fullmarket", use_container_width=True,
                    type="primary" if st.session_state.long_term_index == "FULL MARKET" else "secondary"):
            st.session_state.long_term_index = "FULL MARKET"
    
    with col2:
        # Period Selection with Dropdown
        st.markdown("**Investment Horizon:**")
        period_options = ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years", "5 Years"]
        selected_period = st.selectbox(
            "Select Period",
            period_options,
            index=period_options.index(st.session_state.long_term_period),
            key="lt_period_select",
            label_visibility="collapsed"
        )
        st.session_state.long_term_period = selected_period
        
        # Period descriptions
        period_desc = {
            "1 Month": "📅 Short-term swing trades",
            "3 Months": "📆 Medium-term positions",
            "6 Months": "📈 Investment grade picks",
            "1 Year": "💰 Long-term wealth building",
            "2 Years": "🏦 Serious investment",
            "5 Years": "💎 Wealth creation"
        }
        st.caption(period_desc.get(selected_period, ""))
    
    # Submit Button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        submit_clicked = st.button(
            f"🔍 Analyze {st.session_state.long_term_index} for {st.session_state.long_term_period}",
            key="lt_submit",
            use_container_width=True,
            type="primary"
        )
    
    if submit_clicked:
        st.session_state.long_term_refresh = True
    
    # === RESULTS SECTION ===
    if "long_term_data" not in st.session_state or st.session_state.get("long_term_refresh", False):
        if st.session_state.get("long_term_refresh", False) or "long_term_data" not in st.session_state:
            if st.session_state.long_term_index == "FULL MARKET":
                spinner_msg = f"🌐 Scanning 500+ stocks for {st.session_state.long_term_period} investment..."
            else:
                spinner_msg = f"📊 Analyzing {st.session_state.long_term_index} for {st.session_state.long_term_period}..."
            
            with st.spinner(spinner_msg):
                st.session_state.long_term_data = get_long_term_picks(
                    index_name=st.session_state.long_term_index,
                    period=st.session_state.long_term_period,
                    num_stocks=10 if st.session_state.long_term_index == "FULL MARKET" else 6
                )
                st.session_state.long_term_refresh = False
    
    # Display results if available
    if "long_term_data" in st.session_state:
        data = st.session_state.long_term_data
        
        if data.get("status") == "success":
            # Market Sentiment Header
            sentiment = data.get("market_sentiment", "NEUTRAL")
            if "BULLISH" in sentiment:
                sent_color = "#22c55e"
                sent_icon = "📈"
            elif "BEARISH" in sentiment:
                sent_color = "#ef4444"
                sent_icon = "📉"
            else:
                sent_color = "#f59e0b"
                sent_icon = "➡️"
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {sent_color}20 0%, #1f293710 100%); 
                        padding: 15px; border-radius: 12px; margin: 20px 0; 
                        border-left: 5px solid {sent_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span style="color: {sent_color}; font-weight: bold; font-size: 1.3em;">
                            {sent_icon} {sentiment}
                        </span>
                        <span style="color: #9ca3af; font-size: 0.9em; margin-left: 15px;">
                            for {data.get('period', '')} ({data.get('horizon', '')})
                        </span>
                    </div>
                    <span style="color: #64748b; font-size: 0.85em;">
                        Generated: {data.get('generated_at', '')}
                    </span>
                </div>
                <div style="color: #94a3b8; font-size: 0.9em; margin-top: 8px;">
                    {data.get('sentiment_note', '')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Stats bar
            st.markdown(f"""
            <div style="display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap;">
                <div style="background: #1e293b; padding: 10px 20px; border-radius: 8px;">
                    <span style="color: #64748b;">Stocks Analyzed:</span>
                    <span style="color: white; font-weight: bold; margin-left: 5px;">{data.get('stocks_analyzed', 0)}</span>
                </div>
                <div style="background: #1e293b; padding: 10px 20px; border-radius: 8px;">
                    <span style="color: #64748b;">Index:</span>
                    <span style="color: #60a5fa; font-weight: bold; margin-left: 5px;">{data.get('index', '')}</span>
                </div>
                <div style="background: #16532d; padding: 10px 20px; border-radius: 8px;">
                    <span style="color: #86efac;">Buy Picks:</span>
                    <span style="color: white; font-weight: bold; margin-left: 5px;">{data.get('total_buys', 0)}</span>
                </div>
                <div style="background: #7f1d1d; padding: 10px 20px; border-radius: 8px;">
                    <span style="color: #fca5a5;">Avoid/Sell:</span>
                    <span style="color: white; font-weight: bold; margin-left: 5px;">{data.get('total_sells', 0)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Two columns for buy and sell picks
            buy_col, sell_col = st.columns(2)
            
            with buy_col:
                st.markdown("### 🟢 Best BUY Picks")
                st.caption(f"Top stocks to invest for {data.get('period', '')}")
                buy_picks = data.get("buy_picks", [])
                
                if buy_picks:
                    for pick in buy_picks:
                        try:
                            symbol = pick["symbol"]
                            ltp = pick["ltp"]
                            period_return = pick["period_return"]
                            score = pick["score"]
                            signals = pick.get("signal_text", "")
                            
                            entry = pick.get("entry", ltp)
                            stoploss = pick.get("stoploss", ltp * 0.9)
                            target1 = pick.get("target1", ltp * 1.2)
                            potential = pick.get("potential_return", 15)
                            risk_pct = pick.get("risk_pct", 10)
                            
                            # Score badge
                            if score >= 70:
                                score_badge = "🔥🔥🔥"
                            elif score >= 55:
                                score_badge = "🔥🔥"
                            elif score >= 40:
                                score_badge = "🔥"
                            else:
                                score_badge = "⚡"
                            
                            return_color = "#4ade80" if period_return >= 0 else "#f87171"
                            
                            # Golden cross badge
                            gc_badge = "🌟" if pick.get("golden_cross") else ""
                            acc_badge = "📊" if pick.get("accumulation") else ""
                            above_200 = "📈" if pick.get("above_200_sma") else ""
                            badges = f"{gc_badge}{acc_badge}{above_200}".strip()
                            
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                                        padding: 15px; border-radius: 12px; margin-bottom: 12px; 
                                        border-left: 4px solid #22c55e;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: bold; color: white; font-size: 1.2em;">{symbol} {badges}</span>
                                    <span style="color: #fbbf24; font-size: 0.9em;">{score_badge} {score}</span>
                                </div>
                                <div style="color: white; font-size: 1.1em; margin: 5px 0;">₹{ltp:,.2f}</div>
                                <div style="display: flex; gap: 15px; margin: 8px 0;">
                                    <div style="background: #374151; padding: 5px 10px; border-radius: 6px;">
                                        <span style="color: #9ca3af; font-size: 0.75em;">Past {data.get('period', '')}:</span>
                                        <span style="color: {return_color}; font-size: 0.85em; font-weight: bold;"> {period_return:+.1f}%</span>
                                    </div>
                                    <div style="background: #164e63; padding: 5px 10px; border-radius: 6px;">
                                        <span style="color: #9ca3af; font-size: 0.75em;">Expected Gain:</span>
                                        <span style="color: #22d3ee; font-size: 0.85em; font-weight: bold;"> +{potential:.1f}%</span>
                                    </div>
                                </div>
                                <div style="color: #94a3b8; font-size: 0.8em; margin: 8px 0;">{signals}</div>
                                <div style="background: #0f172a; padding: 10px; border-radius: 8px; margin-top: 10px;">
                                    <div style="color: #22c55e; font-size: 0.85em; font-weight: bold; margin-bottom: 8px;">
                                        📋 Investment Plan: BUY & HOLD
                                    </div>
                                    <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
                                        <div>
                                            <span style="color: #64748b;">Entry:</span>
                                            <span style="color: white; font-weight: bold;"> ₹{entry:,.0f}</span>
                                        </div>
                                        <div>
                                            <span style="color: #64748b;">SL:</span>
                                            <span style="color: #ef4444; font-weight: bold;"> ₹{stoploss:,.0f}</span>
                                        </div>
                                        <div>
                                            <span style="color: #64748b;">Target:</span>
                                            <span style="color: #22c55e; font-weight: bold;"> ₹{target1:,.0f}</span>
                                        </div>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.85em;">
                                        <span style="color: #ef4444;">Risk: -{risk_pct:.1f}%</span>
                                        <span style="color: #22c55e; font-weight: bold;">Reward: +{potential:.1f}%</span>
                                        <span style="color: #60a5fa;">R:R = 1:{potential/risk_pct:.1f}</span>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        except:
                            pass
                else:
                    st.info("No strong buy picks found for this period")
            
            with sell_col:
                st.markdown("### 🔴 AVOID / SELL")
                st.caption("Stocks to avoid or exit from portfolio")
                sell_picks = data.get("sell_picks", [])
                
                if sell_picks:
                    for pick in sell_picks:
                        try:
                            symbol = pick["symbol"]
                            ltp = pick["ltp"]
                            period_return = pick["period_return"]
                            score = pick["score"]
                            signals = pick.get("signal_text", "")
                            warning = pick.get("warning", "Consider avoiding")
                            
                            support1 = pick.get("support1", ltp * 0.9)
                            support2 = pick.get("support2", ltp * 0.8)
                            downside = pick.get("potential_downside", 10)
                            
                            # Calculate potential further fall
                            fall_to_support1 = ((ltp - support1) / ltp) * 100
                            fall_to_support2 = ((ltp - support2) / ltp) * 100
                            
                            # Score badge
                            if score >= 70:
                                score_badge = "⚠️⚠️⚠️"
                            elif score >= 55:
                                score_badge = "⚠️⚠️"
                            elif score >= 40:
                                score_badge = "⚠️"
                            else:
                                score_badge = "❓"
                            
                            return_color = "#4ade80" if period_return >= 0 else "#f87171"
                            
                            # Warning badges
                            death_cross = "☠️" if not pick.get("golden_cross") and pick.get("above_200_sma") == False else ""
                            below_200 = "📉" if not pick.get("above_200_sma") else ""
                            badges = f"{death_cross}{below_200}".strip()
                            
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                                        padding: 15px; border-radius: 12px; margin-bottom: 12px; 
                                        border-left: 4px solid #ef4444;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: bold; color: white; font-size: 1.2em;">{symbol} {badges}</span>
                                    <span style="color: #ef4444; font-size: 0.9em;">{score_badge} {score}</span>
                                </div>
                                <div style="color: white; font-size: 1.1em; margin: 5px 0;">₹{ltp:,.2f}</div>
                                <div style="display: flex; gap: 15px; margin: 8px 0;">
                                    <div style="background: #374151; padding: 5px 10px; border-radius: 6px;">
                                        <span style="color: #9ca3af; font-size: 0.75em;">Past {data.get('period', '')}:</span>
                                        <span style="color: {return_color}; font-size: 0.85em; font-weight: bold;"> {period_return:+.1f}%</span>
                                    </div>
                                    <div style="background: #7f1d1d; padding: 5px 10px; border-radius: 6px;">
                                        <span style="color: #9ca3af; font-size: 0.75em;">Can Fall:</span>
                                        <span style="color: #fca5a5; font-size: 0.85em; font-weight: bold;"> -{fall_to_support1:.1f}%</span>
                                    </div>
                                </div>
                                <div style="color: #94a3b8; font-size: 0.8em; margin: 8px 0;">{signals}</div>
                                <div style="background: #0f172a; padding: 10px; border-radius: 8px; margin-top: 10px;">
                                    <div style="color: #ef4444; font-size: 0.85em; font-weight: bold; margin-bottom: 8px;">
                                        ⚠️ {warning}
                                    </div>
                                    <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
                                        <div>
                                            <span style="color: #64748b;">Support 1:</span>
                                            <span style="color: #f59e0b; font-weight: bold;"> ₹{support1:,.0f}</span>
                                            <span style="color: #9ca3af; font-size: 0.75em;"> (-{fall_to_support1:.0f}%)</span>
                                        </div>
                                        <div>
                                            <span style="color: #64748b;">Support 2:</span>
                                            <span style="color: #ef4444; font-weight: bold;"> ₹{support2:,.0f}</span>
                                            <span style="color: #9ca3af; font-size: 0.75em;"> (-{fall_to_support2:.0f}%)</span>
                                        </div>
                                    </div>
                                    <div style="color: #f59e0b; font-size: 0.85em; margin-top: 8px; text-align: center;">
                                        📉 Already {downside:.1f}% below 52-Week High
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        except:
                            pass
                else:
                    st.info("No stocks to avoid found")
            
            # Refresh button
            st.markdown("---")
            if st.button("🔄 Re-analyze", key="refresh_long_term", use_container_width=True):
                st.session_state.long_term_refresh = True
                st.rerun()
        else:
            st.error(f"Error: {data.get('error', 'Unknown error')}")
            if st.button("🔄 Try Again", key="retry_long_term", use_container_width=True):
                st.session_state.long_term_refresh = True
                st.rerun()
    else:
        # Show initial prompt
        st.info("👆 Select an index and investment period above, then click **Analyze** to see the best long-term picks!")


def show_stock_analyzer(state):
    st.title("🔍 Stock Analyzer")
    st.markdown("Enter any NSE stock symbol to get instant intraday analysis with buy/sell signals and targets")
    
    # Popular stocks for quick selection
    popular_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", 
                      "TATAMOTORS", "ITC", "BHARTIARTL", "WIPRO", "AXISBANK", "KOTAKBANK"]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Text input for custom stock
        stock_input = st.text_input(
            "Enter Stock Symbol (NSE)", 
            placeholder="e.g., RELIANCE, TCS, INFY",
            help="Enter NSE stock symbol without .NS suffix"
        ).upper().strip()
    
    with col2:
        # Quick select dropdown
        quick_select = st.selectbox("Or Quick Select", [""] + popular_stocks)
    
    # Use quick select if text input is empty
    symbol = stock_input if stock_input else quick_select
    
    if symbol:
        with st.spinner(f"Analyzing {symbol}..."):
            # Analyze the stock
            result = analyze_stock(symbol)
            
            if result is None:
                st.error(f"❌ Could not analyze {symbol}. Please check the symbol name.")
                st.info("Make sure you're using NSE symbol (e.g., RELIANCE, not RELIANCE.NS)")
            else:
                # Display analysis results
                st.markdown("---")
                
                # Time context warnings
                time_warning = result.get("time_warning")
                can_trade = result.get("can_trade", True)
                mins_to_squareoff = result.get("mins_to_squareoff", 0)
                
                if time_warning:
                    st.warning(f"⏰ {time_warning}")
                if not can_trade:
                    st.error("⛔ Market closing - No new intraday positions! Square off all positions before 3:15 PM")
                
                # Header with signal
                signal = result.get("signal", "NEUTRAL")
                signal_color = "#4ade80" if signal == "LONG" else "#f87171" if signal == "SHORT" else "#fbbf24"
                signal_icon = "📈 BUY" if signal == "LONG" else "📉 SELL" if signal == "SHORT" else "⏸️ WAIT"
                signal_bg = "#166534" if signal == "LONG" else "#991b1b" if signal == "SHORT" else "#92400e"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {signal_bg} 0%, #1f2937 100%); 
                            padding: 20px; border-radius: 15px; margin-bottom: 20px;
                            border: 2px solid {signal_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 2em; font-weight: bold; color: white;">
                                {symbol}
                            </span>
                            <span style="color: #9ca3af; font-size: 1.2em; margin-left: 15px;">
                                NSE
                            </span>
                        </div>
                        <div style="background: {signal_color}; padding: 10px 25px; border-radius: 25px;">
                            <span style="color: {'white' if signal != 'NEUTRAL' else 'black'}; font-weight: bold; font-size: 1.3em;">
                                {signal_icon}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Price info
                col1, col2, col3, col4 = st.columns(4)
                
                change_pct = result.get("change_pct", 0)
                change_color = "green" if change_pct >= 0 else "red"
                
                with col1:
                    st.metric("Current Price", f"₹{result['ltp']:,.2f}", f"{change_pct:+.2f}%")
                with col2:
                    st.metric("Day High", f"₹{result.get('today_high', 0):,.2f}")
                with col3:
                    st.metric("Day Low", f"₹{result.get('today_low', 0):,.2f}")
                with col4:
                    st.metric("Prev Close", f"₹{result.get('prev_close', 0):,.2f}")
                
                st.markdown("---")
                
                # Gap Analysis
                gap_type = result.get("gap_type", "NO_GAP")
                gap_pct = result.get("gap_pct", 0)
                
                if gap_type != "NO_GAP":
                    gap_color = "#4ade80" if gap_type == "GAP_UP" else "#f87171"
                    gap_icon = "⬆️" if gap_type == "GAP_UP" else "⬇️"
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 10px 15px; border-radius: 8px; 
                                display: inline-block; margin-bottom: 15px;">
                        <span style="color: {gap_color}; font-weight: bold;">
                            {gap_icon} {gap_type.replace('_', ' ')}: {gap_pct:+.2f}%
                        </span>
                        <span style="color: #9ca3af; margin-left: 10px;">
                            ({result.get('gap_status', '')})
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # SUPERTREND Indicator Section
                st_signal = result.get("supertrend", "NEUTRAL")
                st_value = result.get("supertrend_value", result['ltp'])
                st_crossover = result.get("supertrend_crossover", False)
                st_distance = result.get("supertrend_distance", 0)
                
                if st_signal == "BULLISH":
                    st_color = "#22c55e"
                    st_bg = "#166534"
                    st_icon = "🟢"
                    st_label = "BULLISH" if not st_crossover else "🔥 BUY SIGNAL!"
                elif st_signal == "BEARISH":
                    st_color = "#ef4444"
                    st_bg = "#991b1b"
                    st_icon = "🔴"
                    st_label = "BEARISH" if not st_crossover else "🔥 SELL SIGNAL!"
                else:
                    st_color = "#f59e0b"
                    st_bg = "#92400e"
                    st_icon = "🟡"
                    st_label = "NEUTRAL"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {st_bg} 0%, #1f2937 100%); 
                            padding: 15px 20px; border-radius: 10px; margin: 15px 0; border: 1px solid {st_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="color: #9ca3af; font-size: 0.85em;">📊 SUPERTREND INDICATOR</span>
                            <div style="font-size: 1.4em; font-weight: bold; color: {st_color}; margin-top: 5px;">
                                {st_icon} {st_label}
                            </div>
                        </div>
                        <div style="text-align: center;">
                            <div style="color: #9ca3af; font-size: 0.75em;">ST VALUE</div>
                            <div style="color: white; font-size: 1.2em; font-weight: bold;">₹{st_value:,.2f}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="color: #9ca3af; font-size: 0.75em;">DISTANCE</div>
                            <div style="color: {st_color}; font-size: 1.1em; font-weight: bold;">{st_distance:+.2f}%</div>
                        </div>
                        <div style="background: rgba(0,0,0,0.3); padding: 10px 15px; border-radius: 8px;">
                            <div style="color: #9ca3af; font-size: 0.7em;">TREND STATUS</div>
                            <div style="color: white; font-size: 0.9em;">
                                {"Price ABOVE Supertrend" if st_signal == "BULLISH" else "Price BELOW Supertrend" if st_signal == "BEARISH" else "No clear trend"}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Trading Levels - The main feature!
                st.subheader("🎯 Trading Levels")
                
                if signal == "LONG":
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #166534 0%, #1f2937 100%); 
                                padding: 20px; border-radius: 12px; border: 1px solid #4ade80;">
                        <h4 style="color: #4ade80; margin-bottom: 15px;">📈 BUY Setup</h4>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.8em; margin-bottom: 5px;">ENTRY</div>
                                <div style="color: #60a5fa; font-size: 1.4em; font-weight: bold;">₹{result['entry']:,.2f}</div>
                            </div>
                            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.8em; margin-bottom: 5px;">STOP LOSS</div>
                                <div style="color: #f87171; font-size: 1.4em; font-weight: bold;">₹{result['stoploss']:,.2f}</div>
                            </div>
                            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.8em; margin-bottom: 5px;">TARGET 1</div>
                                <div style="color: #4ade80; font-size: 1.4em; font-weight: bold;">₹{result['target1']:,.2f}</div>
                            </div>
                            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.8em; margin-bottom: 5px;">TARGET 2</div>
                                <div style="color: #22c55e; font-size: 1.4em; font-weight: bold;">₹{result['target2']:,.2f}</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; color: #9ca3af; font-size: 0.9em;">
                            Risk: ₹{abs(result['entry'] - result['stoploss']):,.2f} | 
                            Reward: ₹{abs(result['target1'] - result['entry']):,.2f} | 
                            R:R = 1:{result['risk_reward']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                elif signal == "SHORT":
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #991b1b 0%, #1f2937 100%); 
                                padding: 20px; border-radius: 12px; border: 1px solid #f87171;">
                        <h4 style="color: #f87171; margin-bottom: 15px;">📉 SELL Setup</h4>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.8em; margin-bottom: 5px;">ENTRY</div>
                                <div style="color: #60a5fa; font-size: 1.4em; font-weight: bold;">₹{result['entry']:,.2f}</div>
                            </div>
                            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.8em; margin-bottom: 5px;">STOP LOSS</div>
                                <div style="color: #f87171; font-size: 1.4em; font-weight: bold;">₹{result['stoploss']:,.2f}</div>
                            </div>
                            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.8em; margin-bottom: 5px;">TARGET 1</div>
                                <div style="color: #4ade80; font-size: 1.4em; font-weight: bold;">₹{result['target1']:,.2f}</div>
                            </div>
                            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; text-align: center;">
                                <div style="color: #9ca3af; font-size: 0.8em; margin-bottom: 5px;">TARGET 2</div>
                                <div style="color: #22c55e; font-size: 1.4em; font-weight: bold;">₹{result['target2']:,.2f}</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; color: #9ca3af; font-size: 0.9em;">
                            Risk: ₹{abs(result['stoploss'] - result['entry']):,.2f} | 
                            Reward: ₹{abs(result['entry'] - result['target1']):,.2f} | 
                            R:R = 1:{result['risk_reward']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("⏸️ No clear trading signal. Wait for better setup.")
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 15px; border-radius: 10px;">
                        <p style="color: #9ca3af;">Current levels for reference:</p>
                        <p style="color: white;">Entry: ₹{result['entry']:,.2f} | SL: ₹{result['stoploss']:,.2f} | Target: ₹{result['target1']:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Technical Indicators
                st.subheader("📊 Technical Indicators")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    rsi = result.get("rsi", 50)
                    rsi_color = "#4ade80" if rsi < 30 else "#f87171" if rsi > 70 else "#fbbf24"
                    rsi_status = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">RSI (14)</div>
                        <div style="color: {rsi_color}; font-size: 1.8em; font-weight: bold;">{rsi:.1f}</div>
                        <div style="color: {rsi_color}; font-size: 0.85em;">{rsi_status}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    momentum = result.get("momentum", 0)
                    mom_color = "#4ade80" if momentum > 0 else "#f87171"
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">Momentum (5D)</div>
                        <div style="color: {mom_color}; font-size: 1.8em; font-weight: bold;">{momentum:+.2f}%</div>
                        <div style="color: {mom_color}; font-size: 0.85em;">{'Bullish' if momentum > 0 else 'Bearish'}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    vol_ratio = result.get("volume_ratio", 1)
                    vol_color = "#4ade80" if vol_ratio > 1.2 else "#9ca3af"
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">Volume Ratio</div>
                        <div style="color: {vol_color}; font-size: 1.8em; font-weight: bold;">{vol_ratio:.2f}x</div>
                        <div style="color: {vol_color}; font-size: 0.85em;">{'High' if vol_ratio > 1.2 else 'Normal'}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Moving Averages
                st.markdown("")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    sma5 = result.get("sma_5", 0)
                    above_sma5 = result['ltp'] > sma5
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 10px; border-radius: 8px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">5-Day MA</div>
                        <div style="color: white; font-size: 1.2em;">₹{sma5:,.2f}</div>
                        <div style="color: {'#4ade80' if above_sma5 else '#f87171'}; font-size: 0.8em;">
                            {'Price Above ✓' if above_sma5 else 'Price Below ✗'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    sma20 = result.get("sma_20", 0)
                    above_sma20 = result['ltp'] > sma20
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 10px; border-radius: 8px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">20-Day MA</div>
                        <div style="color: white; font-size: 1.2em;">₹{sma20:,.2f}</div>
                        <div style="color: {'#4ade80' if above_sma20 else '#f87171'}; font-size: 0.8em;">
                            {'Price Above ✓' if above_sma20 else 'Price Below ✗'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    support = result.get("support", 0)
                    resistance = result.get("resistance", 0)
                    st.markdown(f"""
                    <div style="background: #1f2937; padding: 10px; border-radius: 8px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 0.8em;">Support / Resistance</div>
                        <div style="color: #4ade80; font-size: 1em;">S: ₹{support:,.2f}</div>
                        <div style="color: #f87171; font-size: 1em;">R: ₹{resistance:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Analysis Reason
                st.subheader("💡 Analysis")
                st.info(f"**Signal Reason:** {result.get('reason', 'N/A')}")
                
                # Strength indicator
                strength = result.get("strength", 0)
                st.markdown(f"""
                <div style="margin-top: 10px;">
                    <span style="color: #9ca3af;">Signal Strength: </span>
                    <span style="color: #fbbf24; font-size: 1.2em;">{'⭐' * strength}{'☆' * (5 - strength)}</span>
                    <span style="color: #9ca3af;"> ({strength}/5)</span>
                </div>
                """, unsafe_allow_html=True)
    
    else:
        # Show instructions when no symbol entered
        st.info("👆 Enter a stock symbol above or select from quick options to analyze")
        
        st.markdown("### 📝 How to Use")
        st.markdown("""
        1. **Enter Stock Symbol** - Type any NSE stock symbol (e.g., RELIANCE, TCS, INFY)
        2. **Get Instant Analysis** - See buy/sell signal based on technical indicators
        3. **Trading Levels** - Get entry, stop-loss, and target prices
        4. **Technical Indicators** - View RSI, momentum, volume, and moving averages
        """)
        
        st.markdown("### 🎯 Signals Explained")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="background: #166534; padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.5em; color: #4ade80;">📈 BUY</div>
                <div style="color: #9ca3af; font-size: 0.9em; margin-top: 5px;">
                    Bullish setup detected<br>
                    Go LONG
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="background: #991b1b; padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.5em; color: #f87171;">📉 SELL</div>
                <div style="color: #9ca3af; font-size: 0.9em; margin-top: 5px;">
                    Bearish setup detected<br>
                    Go SHORT
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="background: #92400e; padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.5em; color: #fbbf24;">⏸️ WAIT</div>
                <div style="color: #9ca3af; font-size: 0.9em; margin-top: 5px;">
                    No clear signal<br>
                    Stay on sidelines
                </div>
            </div>
            """, unsafe_allow_html=True)


def show_settings(state):
    st.title("⚙️ Settings")
    
    import yaml
    
    # Check if system is running
    running, _ = is_trading_running()
    if running:
        st.warning("⚠️ Stop the trading system before changing settings")
    
    # Editable settings
    st.subheader("📝 Edit Configuration")
    
    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 Trading")
            
            capital = st.number_input(
                "Capital (₹)",
                min_value=10000,
                max_value=10000000,
                value=state.config.get('trading', {}).get('capital', 100000),
                step=10000
            )
        
        with col2:
            st.markdown("### 🛡️ Risk Management")
            
            max_position_pct = st.slider(
                "Max Position Size (%)",
                min_value=1,
                max_value=50,
                value=state.config.get('risk', {}).get('max_position_pct', 10)
            )
            
            max_daily_loss_pct = st.slider(
                "Max Daily Loss (%)",
                min_value=1,
                max_value=10,
                value=state.config.get('risk', {}).get('max_daily_loss_pct', 2)
            )
            
            max_open_positions = st.number_input(
                "Max Open Positions",
                min_value=1,
                max_value=10,
                value=state.config.get('risk', {}).get('max_open_positions', 3)
            )
            
            mandatory_stoploss = st.checkbox(
                "Mandatory Stop-Loss",
                value=state.config.get('risk', {}).get('mandatory_stoploss', True)
            )
            
            default_sl_pct = st.slider(
                "Default Stop-Loss (%)",
                min_value=0.5,
                max_value=5.0,
                value=float(state.config.get('risk', {}).get('default_stoploss_pct', 1.5)),
                step=0.5
            )
            
            default_target_pct = st.slider(
                "Default Target (%)",
                min_value=1.0,
                max_value=10.0,
                value=float(state.config.get('risk', {}).get('default_target_pct', 3.0)),
                step=0.5
            )
        
        submitted = st.form_submit_button("💾 Save Settings", type="primary", disabled=running)
        
        if submitted and not running:
            # Load current config
            config_path = Path("config/settings.yaml")
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            # Update values
            config["trading"]["capital"] = capital
            config["risk"]["max_position_pct"] = max_position_pct
            config["risk"]["max_daily_loss_pct"] = max_daily_loss_pct
            config["risk"]["max_open_positions"] = max_open_positions
            config["risk"]["mandatory_stoploss"] = mandatory_stoploss
            config["risk"]["default_stoploss_pct"] = default_sl_pct
            config["risk"]["default_target_pct"] = default_target_pct
            
            # Save
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            
            st.success("✅ Settings saved!")
            st.rerun()
    
    st.markdown("---")
    
    # API Credentials Status
    st.subheader("🔑 API Credentials")
    
    credentials = get_credentials()
    
    cred_status = []
    for key, value in credentials.items():
        if key != "environment":
            status = "✅" if value else "❌"
            cred_status.append({"Credential": key.replace("_", " ").title(), "Status": status})
    
    st.dataframe(pd.DataFrame(cred_status), use_container_width=True, hide_index=True)
    
    if not all(v for k, v in credentials.items() if k != "environment"):
        st.warning("⚠️ Some credentials are missing. Edit `config/.env` file.")
    else:
        st.success("✅ All credentials configured")
    
    st.markdown("---")
    
    # Watchlist
    st.subheader("👀 Watchlist")
    
    equity = state.instruments.get("equity", [])
    df = pd.DataFrame(equity)
    edited_df = st.data_editor(df, use_container_width=True, hide_index=True, disabled=running)
    
    st.caption("💡 To add/remove symbols, edit `config/instruments.yaml`")


def show_logs():
    st.title("📜 System Logs")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-refresh (every 5s)", key="logs_auto_refresh", value=False)
    with col2:
        if st.button("🔄 Refresh Now", key="refresh_logs"):
            st.rerun()
    
    if auto_refresh:
        time.sleep(5)
        st.rerun()
    
    # Tabs for different log types
    tab1, tab2, tab3 = st.tabs(["📊 Trading Logs", "🖥️ Live Output", "⚠️ Error Logs"])
    
    with tab1:
        logs = load_general_logs(100)
        if logs:
            # Filter options
            filter_text = st.text_input("Filter logs", "")
            
            filtered_logs = [l for l in logs if filter_text.lower() in l.lower()] if filter_text else logs
            
            # Display as code block
            st.code("\n".join(filtered_logs[-50:]), language="log")
        else:
            st.info("No logs yet. Start the trading system to generate logs.")
    
    with tab2:
        # Show live trading output
        output_log = Path("logs/trading_output.log")
        if output_log.exists():
            with open(output_log, "r") as f:
                output = f.readlines()[-100:]
            st.code("\n".join(output), language="log")
        else:
            st.info("No live output yet. Start the trading system.")
    
    with tab3:
        error_log = Path("logs/errors.log")
        if error_log.exists():
            with open(error_log, "r") as f:
                errors = f.readlines()[-30:]
            if errors:
                st.code("\n".join(errors), language="log")
            else:
                st.success("No errors logged! 🎉")
        else:
            st.success("No errors logged! 🎉")


if __name__ == "__main__":
    main()
