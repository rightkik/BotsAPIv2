# ===================================================
# dashboard/app.py — Streamlit Dashboard (Binance Dark/Gold Theme)
#
# วิธีรัน:
#   streamlit run dashboard/app.py
#
# Theme: พื้นหลัง #0B0E11  |  Accent #F0B90B  |  Text #EAECEF
# Auto-refresh ทุก DASHBOARD_REFRESH_SEC วินาที
# ===================================================

import sys
import os
import csv
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from bot.trader    import create_exchange, get_balance
from bot.data      import get_ohlcv_ccxt
from bot.indicator import add_all_indicators, find_supply_demand_zones
from bot.strategy  import get_signal, get_trend_label

# ===================================================
# Page Setup
# ===================================================

st.set_page_config(
    page_title="Binance Bot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject CSS — Binance dark/gold theme
st.markdown("""
<style>
  /* พื้นหลัง */
  .stApp { background-color: #0B0E11; color: #EAECEF; }
  .stApp header { background-color: #0B0E11; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background-color: #1E2329;
    border: 1px solid #2B3139;
    border-radius: 8px;
    padding: 16px;
  }
  [data-testid="metric-container"] label { color: #848E9C !important; font-size: 0.8rem; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #EAECEF !important;
    font-size: 1.4rem;
    font-weight: 600;
  }
  [data-testid="stMetricDelta"] { font-size: 0.85rem; }

  /* DataFrames */
  .dataframe { background-color: #1E2329 !important; color: #EAECEF !important; }

  /* Headers */
  h1, h2, h3 { color: #F0B90B !important; }

  /* Sidebar */
  .css-1d391kg { background-color: #161A1E; }

  /* Divider */
  hr { border-color: #2B3139; }
</style>
""", unsafe_allow_html=True)

# ===================================================
# Helpers
# ===================================================

@st.cache_data(ttl=config.DASHBOARD_REFRESH_SEC)
def load_ohlcv():
    """ดึง OHLCV และคำนวณ indicators (cache TTL = refresh interval)"""
    try:
        exchange = create_exchange(testnet=config.USE_TESTNET)
        df = get_ohlcv_ccxt(exchange, config.SYMBOL, config.TIMEFRAME_MAIN, limit=200)
        if df is not None:
            df = add_all_indicators(df)
        return df, exchange
    except Exception as e:
        return None, None


def load_state() -> dict:
    """โหลด bot state จากไฟล์ JSON"""
    default = {
        "in_position": False, "bot_active": True,
        "daily_pnl_usdt": 0.0, "daily_pnl_pct": 0.0,
        "cooldown_bars": 0, "resume_time": None,
    }
    if not os.path.exists(config.STATE_FILE):
        return default
    try:
        with open(config.STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        default.update(data)
        return default
    except Exception:
        return default


def load_trades(limit: int = 20) -> pd.DataFrame:
    """โหลด N trades ล่าสุดจาก CSV"""
    if not os.path.exists(config.LOG_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_csv(config.LOG_FILE, encoding='utf-8')
        return df.tail(limit).iloc[::-1]  # ล่าสุดก่อน
    except Exception:
        return pd.DataFrame()


def get_bot_status_label(state: dict) -> tuple[str, str]:
    """คืน (label, color) สำหรับสถานะบอท"""
    if not state.get("bot_active", True):
        return "⛔ Kill Switch", "#F6465D"
    if state.get("cooldown_bars", 0) > 0:
        n = state["cooldown_bars"]
        return f"⏸ Cooldown ({n})", "#F0B90B"
    return "✅ Active", "#0ECB81"


# ===================================================
# Chart Builder
# ===================================================

def build_chart(df: pd.DataFrame, state: dict) -> go.Figure:
    """สร้างกราฟแท่งเทียน + EMA + Zones + SL/TP"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.04,
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name=config.SYMBOL,
        increasing_line_color='#0ECB81',
        decreasing_line_color='#F6465D',
        increasing_fillcolor='#0ECB81',
        decreasing_fillcolor='#F6465D',
    ), row=1, col=1)

    # EMA lines
    fig.add_trace(go.Scatter(
        x=df.index, y=df['ema_fast'],
        name=f'EMA{config.EMA_FAST}',
        line=dict(color='#36BFFA', width=1.5),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['ema_slow'],
        name=f'EMA{config.EMA_SLOW}',
        line=dict(color='#F0B90B', width=1.5),
    ), row=1, col=1)

    # Supply / Demand Zones (แค่ 50 แท่งล่าสุด เพื่อลด noise)
    zones = find_supply_demand_zones(df.tail(100), config.PIVOT_LENGTH)
    for z_high, z_low in zones["supply"][-3:]:
        fig.add_hrect(
            y0=z_low, y1=z_high, row=1, col=1,
            fillcolor='rgba(246, 70, 93, 0.10)',
            line=dict(color='#F6465D', width=0.5),
            annotation_text="Supply", annotation_font_color='#F6465D',
            annotation_position="right",
        )
    for z_high, z_low in zones["demand"][-3:]:
        fig.add_hrect(
            y0=z_low, y1=z_high, row=1, col=1,
            fillcolor='rgba(14, 203, 129, 0.10)',
            line=dict(color='#0ECB81', width=0.5),
            annotation_text="Demand", annotation_font_color='#0ECB81',
            annotation_position="right",
        )

    # SL / TP lines ถ้ามี position
    if state.get("in_position"):
        sl  = state.get("stop_loss")
        tp2 = state.get("tp2")
        tp1 = state.get("tp1")
        tp3 = state.get("tp3")
        entry = state.get("entry_price")

        for level, color, label in [
            (entry, '#F0B90B', 'Entry'),
            (sl,   '#F6465D', 'SL'),
            (tp1,  '#A8FF78', 'TP1'),
            (tp2,  '#0ECB81', 'TP2'),
            (tp3,  '#0ECB81', 'TP3'),
        ]:
            if level:
                fig.add_hline(
                    y=level, row=1, col=1,
                    line=dict(color=color, dash='dash', width=1),
                    annotation_text=f"{label}: ${level:,.0f}",
                    annotation_font_color=color,
                    annotation_position="left",
                )

    # RSI subplot
    fig.add_trace(go.Scatter(
        x=df.index, y=df['rsi'],
        name='RSI', line=dict(color='#9B59B6', width=1.3),
    ), row=2, col=1)
    fig.add_hline(y=70, row=2, col=1, line=dict(color='#F6465D', dash='dash', width=0.8))
    fig.add_hline(y=30, row=2, col=1, line=dict(color='#0ECB81', dash='dash', width=0.8))
    fig.add_hline(y=50, row=2, col=1, line=dict(color='#4A4A4A', dash='dot', width=0.5))

    # Layout
    fig.update_layout(
        paper_bgcolor='#0B0E11',
        plot_bgcolor='#131722',
        font=dict(color='#EAECEF'),
        xaxis_rangeslider_visible=False,
        legend=dict(bgcolor='#1E2329', bordercolor='#2B3139', font_color='#EAECEF'),
        margin=dict(t=20, b=10),
        height=550,
    )
    fig.update_yaxes(gridcolor='#1E2329', zerolinecolor='#1E2329')
    fig.update_xaxes(gridcolor='#1E2329', rangeslider_visible=False)

    return fig


# ===================================================
# Dashboard Layout
# ===================================================

def main():
    # Header
    st.markdown(
        f"<h1 style='color:#F0B90B;margin-bottom:0'>🤖 Binance Bot Dashboard</h1>"
        f"<p style='color:#848E9C;margin-top:4px'>"
        f"{config.SYMBOL} — {config.TIMEFRAME_MAIN} — "
        f"{'TESTNET' if config.USE_TESTNET else '🔴 LIVE'}"
        f"</p>",
        unsafe_allow_html=True
    )

    st.divider()

    # โหลดข้อมูล
    df, exchange = load_ohlcv()
    state        = load_state()
    trades_df    = load_trades(20)

    if df is None or len(df) < config.EMA_SLOW + 5:
        st.error("❌ ดึงข้อมูลไม่ได้ — ตรวจ internet หรือ .env")
        return

    # ค่า indicator ปัจจุบัน
    last         = df.iloc[-2]
    price        = float(df['close'].iloc[-1])
    ema_fast     = float(last['ema_fast'])
    ema_slow     = float(last['ema_slow'])
    adx          = float(last['adx'])
    rsi          = float(last['rsi'])
    atr          = float(last['atr'])
    vol_delta    = float(last['vol_delta'])

    # Signal
    dummy_state  = {"in_position": False, "bot_active": True, "cooldown_bars": 0}
    signal       = get_signal(df, state)
    trend_label  = get_trend_label(df)

    # Price change 24h (ถ้า df มีข้อมูลพอ)
    if len(df) >= 24:
        price_24h_ago = float(df['close'].iloc[-25])
        chg_24h       = (price - price_24h_ago) / price_24h_ago * 100
    else:
        chg_24h       = 0.0

    # Bot status
    bot_label, bot_color = get_bot_status_label(state)

    # ──────────────────────────────────────────────────
    # Row 1: Header Metrics
    # ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        sign = "+" if chg_24h >= 0 else ""
        st.metric(
            "💰 ราคา",
            f"${price:,.2f}",
            f"{sign}{chg_24h:.2f}% (24h)",
            delta_color="normal",
        )

    with c2:
        action   = signal.get("action", "HOLD")
        strength = signal.get("strength", "")
        sig_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(action, "⚪")
        st.metric("📊 สัญญาณ", f"{sig_icon} {action}", strength)

    with c3:
        d_pnl      = state.get("daily_pnl_usdt", 0.0)
        d_pnl_pct  = state.get("daily_pnl_pct", 0.0) * 100
        d_sign     = "+" if d_pnl >= 0 else ""
        st.metric("💵 PnL วันนี้", f"${d_pnl:+.2f}", f"{d_sign}{d_pnl_pct:.2f}%")

    with c4:
        st.metric("🤖 สถานะบอท", bot_label, "")

    st.divider()

    # ──────────────────────────────────────────────────
    # Row 2: Indicators Bar
    # ──────────────────────────────────────────────────
    i1, i2, i3, i4, i5 = st.columns(5)

    ema_cross = "↑ Bullish" if ema_fast > ema_slow else "↓ Bearish"
    ema_color = "#0ECB81" if ema_fast > ema_slow else "#F6465D"

    adx_label = "Trending" if adx > config.ADX_THRESHOLD else "Sideways"
    adx_color = "#0ECB81" if adx > config.ADX_THRESHOLD else "#F0B90B"

    rsi_label = "OB" if rsi > config.RSI_OB else ("OS" if rsi < config.RSI_OS else "Normal")
    rsi_color = "#F6465D" if rsi > config.RSI_OB else ("#0ECB81" if rsi < config.RSI_OS else "#EAECEF")

    with i1:
        st.markdown(
            f"**EMA{config.EMA_FAST}/{config.EMA_SLOW}**<br>"
            f"<span style='color:{ema_color}'>{ema_cross}</span><br>"
            f"<span style='color:#848E9C;font-size:0.8rem'>"
            f"Fast: ${ema_fast:,.0f}<br>Slow: ${ema_slow:,.0f}</span>",
            unsafe_allow_html=True
        )
    with i2:
        st.markdown(
            f"**ADX**<br>"
            f"<span style='color:{adx_color}'>{adx:.1f} ({adx_label})</span><br>"
            f"<span style='color:#848E9C;font-size:0.8rem'>+DI: {last['di_plus']:.1f}  -DI: {last['di_minus']:.1f}</span>",
            unsafe_allow_html=True
        )
    with i3:
        st.markdown(
            f"**RSI {config.RSI_PERIOD}**<br>"
            f"<span style='color:{rsi_color}'>{rsi:.1f} ({rsi_label})</span><br>"
            f"<span style='color:#848E9C;font-size:0.8rem'>OB: {config.RSI_OB} / OS: {config.RSI_OS}</span>",
            unsafe_allow_html=True
        )
    with i4:
        st.markdown(
            f"**ATR {config.ATR_PERIOD}**<br>"
            f"<span style='color:#F0B90B'>${atr:,.0f}</span><br>"
            f"<span style='color:#848E9C;font-size:0.8rem'>SL: ${atr*config.ATR_SL_MULT:,.0f}  TP: ${atr*config.ATR_TP_MULT:,.0f}</span>",
            unsafe_allow_html=True
        )
    with i5:
        buy_pct  = vol_delta
        sell_pct = 100 - vol_delta
        vd_color = "#0ECB81" if buy_pct > 50 else "#F6465D"
        st.markdown(
            f"**Volume Delta**<br>"
            f"<span style='color:{vd_color}'>Buy {buy_pct:.0f}%</span>  Sell {sell_pct:.0f}%<br>"
            f"<span style='color:#848E9C;font-size:0.8rem'>{trend_label}</span>",
            unsafe_allow_html=True
        )

    st.divider()

    # ──────────────────────────────────────────────────
    # Row 3: Candlestick Chart
    # ──────────────────────────────────────────────────
    fig = build_chart(df.tail(100), state)  # แสดง 100 แท่งล่าสุด
    st.plotly_chart(fig, use_container_width=True)

    # ──────────────────────────────────────────────────
    # Row 4: Position Info (ถ้ามี)
    # ──────────────────────────────────────────────────
    if state.get("in_position"):
        st.markdown("### 📍 Position Info")
        entry = state.get("entry_price", 0)
        qty   = state.get("quantity", 0)
        sl    = state.get("stop_loss") or 0
        tp1   = state.get("tp1") or 0
        tp2   = state.get("tp2") or 0
        tp3   = state.get("tp3") or 0
        pnl   = (price - entry) * qty if entry > 0 else 0
        rr    = abs(price - entry) / abs(entry - sl) if (entry - sl) != 0 else 0

        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("Entry", f"${entry:,.2f}")
        p2.metric("Stop Loss", f"${sl:,.2f}", f"-{abs(entry-sl):,.0f}")
        p3.metric("TP1 (1:1)", f"${tp1:,.2f}")
        p4.metric("TP2 (Main)", f"${tp2:,.2f}")
        p5.metric("TP3 (Max)", f"${tp3:,.2f}")

        q1, q2, q3 = st.columns(3)
        pnl_sign = "+" if pnl >= 0 else ""
        q1.metric("Float PnL", f"{pnl_sign}${pnl:,.2f}", f"{pnl_sign}{pnl/(entry*qty)*100:.2f}%" if entry * qty > 0 else "")
        q2.metric("R:R Ratio", f"1:{rr:.2f}")
        q3.metric("ATR Distance", f"${abs(price-entry):,.0f}")

        st.divider()

    # ──────────────────────────────────────────────────
    # Row 5: Trade History
    # ──────────────────────────────────────────────────
    st.markdown("### 📋 Trade History (20 ล่าสุด)")

    if trades_df.empty:
        st.info("ยังไม่มีประวัติการเทรด")
    else:
        # ใส่สี row ตาม result
        def color_row(val):
            if val == "WIN":
                return "background-color: #0D2318; color: #0ECB81"
            elif val == "LOSS":
                return "background-color: #2A0D0D; color: #F6465D"
            else:
                return "background-color: #1E2329; color: #848E9C"

        styled = trades_df.style.applymap(
            color_row, subset=['result'] if 'result' in trades_df.columns else []
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

    # ──────────────────────────────────────────────────
    # Footer + Auto-refresh
    # ──────────────────────────────────────────────────
    st.divider()
    col_l, col_r = st.columns([3, 1])
    with col_l:
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  "
                   f"Auto-refresh every {config.DASHBOARD_REFRESH_SEC}s")
    with col_r:
        if st.button("🔄 Refresh Now"):
            st.cache_data.clear()
            st.rerun()

    # Auto-refresh ด้วย meta tag
    st.markdown(
        f"<meta http-equiv='refresh' content='{config.DASHBOARD_REFRESH_SEC}'>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
