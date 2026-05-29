"""
dashboard/app.py — SET Signal Monitor Dashboard

รัน: streamlit run dashboard/app.py
"""

import json
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from bot.indicator import add_all_indicators, find_supply_demand_zones
from bot.strategy  import get_signal, get_trend_label
from data.fetcher  import fetch_all, fetch_one

# ══════════════════════════════════════════════════════
# Page Config
# ══════════════════════════════════════════════════════

st.set_page_config(
    page_title="SET Signal Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .stApp { background-color: #0D1117; color: #E6EDF3; }
  .stApp header { background-color: #0D1117; }
  h1,h2,h3 { color: #58A6FF !important; }
  hr { border-color: #21262D !important; margin: 0.4rem 0 !important; }
  .block-container { padding-top:0.8rem !important; padding-bottom:0 !important; }
  header[data-testid="stHeader"] { display:none !important; }
  .stSelectbox label { color: #8B949E !important; }
  [data-testid="stMetricValue"] { font-size:1.3rem !important; }
  [data-testid="stMetricLabel"] { font-size:0.75rem !important; color:#8B949E !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════

DUMMY_STATE = {"in_position": False, "bot_active": True, "cooldown_bars": 0}

SIG_COLOR = {
    "BUY":  "#238636",  # เขียวเข้ม
    "SELL": "#DA3633",  # แดงเข้ม
    "HOLD": "#21262D",  # เทาเข้ม
}
SIG_TEXT = {
    "BUY":  "#3FB950",
    "SELL": "#F85149",
    "HOLD": "#8B949E",
}
SIG_BORDER = {
    "BUY":  "#3FB950",
    "SELL": "#F85149",
    "HOLD": "#30363D",
}

# ══════════════════════════════════════════════════════
# Data Loading
# ══════════════════════════════════════════════════════

@st.cache_data(ttl=config.DASHBOARD_REFRESH_SEC)
def load_all_signals():
    """ดึงข้อมูล + คำนวณ signal ทุกตัว (cache TTL = refresh interval)"""
    ohlcv_map = fetch_all()
    results   = {}

    for symbol in config.WATCHLIST:
        df = ohlcv_map.get(symbol)
        if df is None or len(df) < config.EMA_SLOW + 10:
            results[symbol] = {"symbol": symbol, "error": "ข้อมูลไม่พอ"}
            continue
        try:
            df  = add_all_indicators(df)
            sig = get_signal(df, DUMMY_STATE)

            last  = df.iloc[-2]
            prev  = df.iloc[-3]
            price = float(df["close"].iloc[-1])
            chg   = (float(last["close"]) - float(prev["close"])) / float(prev["close"]) * 100

            results[symbol] = {
                "symbol":        symbol,
                "price":         price,
                "price_chg_pct": round(chg, 2),
                "ema_fast":      float(last["ema_fast"]),
                "ema_slow":      float(last["ema_slow"]),
                "adx":           float(last["adx"]),
                "rsi":           float(last["rsi"]),
                "atr":           float(last["atr"]),
                "signal":        sig["action"],
                "strength":      sig["strength"],
                "reason":        sig["reason"],
                "near_demand":   sig["near_demand"],
                "near_supply":   sig["near_supply"],
                "_df":           df,
            }
        except Exception as e:
            results[symbol] = {"symbol": symbol, "error": str(e)}

    return results


def is_market_open() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    h, m = now.hour, now.minute
    t = h * 60 + m
    return (9*60 <= t <= 12*60+30) or (14*60 <= t <= 16*60+30)


# ══════════════════════════════════════════════════════
# Card Renderer
# ══════════════════════════════════════════════════════

def render_card(data: dict):
    """แสดง card หุ้น 1 ตัว"""
    if "error" in data:
        st.markdown(f"""
        <div style="background:#161B22;border:1px solid #30363D;border-radius:8px;
                    padding:10px 12px;margin:3px 0;min-height:110px">
          <b style="color:#E6EDF3">{data['symbol']}</b>
          <br><span style="color:#F85149;font-size:0.75rem">{data['error']}</span>
        </div>""", unsafe_allow_html=True)
        return

    sig    = data["signal"]
    chg    = data["price_chg_pct"]
    rsi    = data["rsi"]
    adx    = data["adx"]
    near_d = data["near_demand"]
    near_s = data["near_supply"]

    # badge ความแรง
    strength_badge = ""
    if sig != "HOLD" and data["strength"] == "STRONG":
        strength_badge = "<span style='font-size:0.65rem;color:#E3B341'>★ STRONG</span> "

    # near zone indicator
    near_tag = ""
    if near_d and sig == "HOLD":
        near_tag = "<span style='font-size:0.65rem;color:#3FB950'>▲ ใกล้แนวรับ</span>"
    elif near_s and sig == "HOLD":
        near_tag = "<span style='font-size:0.65rem;color:#F85149'>▼ ใกล้แนวต้าน</span>"

    chg_color = "#3FB950" if chg >= 0 else "#F85149"
    chg_sign  = "+" if chg >= 0 else ""

    rsi_color = "#F85149" if rsi > 70 else ("#3FB950" if rsi < 30 else "#8B949E")
    adx_color = "#3FB950" if adx > config.ADX_THRESHOLD else "#E3B341"

    # border สีตาม signal
    border_color = SIG_BORDER[sig]
    bg_color     = "#1A2332" if sig == "BUY" else ("#2A1A1A" if sig == "SELL" else "#161B22")

    st.markdown(f"""
    <div style="background:{bg_color};border:1px solid {border_color};border-radius:8px;
                padding:10px 12px;margin:3px 0;min-height:115px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <b style="color:#E6EDF3;font-size:1rem">{data['symbol']}</b>
        <span style="background:{SIG_COLOR[sig]};color:{SIG_TEXT[sig]};
                     padding:2px 8px;border-radius:4px;font-size:0.8rem;font-weight:700">{sig}</span>
      </div>
      <div style="font-size:1.15rem;color:#E6EDF3;margin:3px 0;font-weight:600">
        {data['price']:,.2f}
        <span style="font-size:0.8rem;color:{chg_color};margin-left:6px">{chg_sign}{chg:.2f}%</span>
      </div>
      <div style="font-size:0.72rem;display:flex;gap:10px">
        <span>RSI: <span style="color:{rsi_color};font-weight:600">{rsi:.0f}</span></span>
        <span>ADX: <span style="color:{adx_color};font-weight:600">{adx:.0f}</span></span>
      </div>
      <div style="font-size:0.68rem;margin-top:3px;color:#8B949E">
        {strength_badge}{near_tag}
      </div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# Chart Builder
# ══════════════════════════════════════════════════════

def build_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    df_chart = df.tail(120)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.03,
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df_chart.index,
        open=df_chart["open"], high=df_chart["high"],
        low=df_chart["low"],   close=df_chart["close"],
        name=symbol,
        increasing_line_color="#3FB950", increasing_fillcolor="#3FB950",
        decreasing_line_color="#F85149", decreasing_fillcolor="#F85149",
    ), row=1, col=1)

    # EMA lines
    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart["ema_fast"],
        name=f"EMA{config.EMA_FAST}",
        line=dict(color="#58A6FF", width=1.5),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart["ema_slow"],
        name=f"EMA{config.EMA_SLOW}",
        line=dict(color="#E3B341", width=1.5),
    ), row=1, col=1)

    # Supply / Demand Zones
    zones = find_supply_demand_zones(df_chart, config.PIVOT_LENGTH)
    for z_high, z_low in zones["supply"][-3:]:
        fig.add_hrect(y0=z_low, y1=z_high, row=1, col=1,
                      fillcolor="rgba(248,81,73,0.10)",
                      line=dict(color="#F85149", width=0.5),
                      annotation_text="Supply", annotation_font_color="#F85149",
                      annotation_position="right")
    for z_high, z_low in zones["demand"][-3:]:
        fig.add_hrect(y0=z_low, y1=z_high, row=1, col=1,
                      fillcolor="rgba(63,185,80,0.10)",
                      line=dict(color="#3FB950", width=0.5),
                      annotation_text="Demand", annotation_font_color="#3FB950",
                      annotation_position="right")

    # ADX
    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart["adx"],
        name="ADX", line=dict(color="#8B949E", width=1.2),
    ), row=2, col=1)
    fig.add_hline(y=config.ADX_THRESHOLD, row=2, col=1,
                  line=dict(color="#E3B341", dash="dash", width=0.8))

    # RSI
    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart["rsi"],
        name="RSI", line=dict(color="#BC8CFF", width=1.2),
    ), row=3, col=1)
    fig.add_hline(y=70, row=3, col=1, line=dict(color="#F85149", dash="dash", width=0.8))
    fig.add_hline(y=30, row=3, col=1, line=dict(color="#3FB950", dash="dash", width=0.8))
    fig.add_hline(y=50, row=3, col=1, line=dict(color="#30363D", dash="dot", width=0.5))

    fig.update_layout(
        paper_bgcolor="#0D1117", plot_bgcolor="#161B22",
        font=dict(color="#E6EDF3"),
        xaxis_rangeslider_visible=False,
        legend=dict(bgcolor="#161B22", bordercolor="#30363D", font_color="#E6EDF3"),
        margin=dict(t=10, b=10),
        height=520,
        title=dict(text=f"{symbol} — Daily", font=dict(color="#58A6FF", size=14)),
    )
    fig.update_yaxes(gridcolor="#1C2128", zerolinecolor="#1C2128")
    fig.update_xaxes(gridcolor="#1C2128", rangeslider_visible=False)

    return fig


# ══════════════════════════════════════════════════════
# Main Layout
# ══════════════════════════════════════════════════════

def main():
    # ── Header ────────────────────────────────────────
    market_open  = is_market_open()
    market_label = "🟢 ตลาดเปิด" if market_open else "🔴 ตลาดปิด"
    now_str      = datetime.now().strftime("%d/%m/%Y %H:%M")

    h1, h2, h3 = st.columns([3, 1, 1])
    with h1:
        st.markdown(
            "<span style='color:#58A6FF;font-size:1.5rem;font-weight:700'>📈 SET Signal Monitor</span>"
            f"&nbsp;&nbsp;<span style='color:#8B949E;font-size:0.85rem'>Daily TF — {now_str}</span>",
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            f"<div style='text-align:center;padding-top:6px'>{market_label}</div>",
            unsafe_allow_html=True,
        )
    with h3:
        filter_opt = st.selectbox(
            "filter", ["ทั้งหมด", "BUY", "SELL", "ใกล้ Zone"],
            label_visibility="collapsed",
        )

    st.divider()

    # ── โหลดข้อมูล ─────────────────────────────────────
    with st.spinner("กำลังดึงข้อมูล..."):
        all_data = load_all_signals()

    # ── Summary Bar ────────────────────────────────────
    buy_list  = [s for s, d in all_data.items() if d.get("signal") == "BUY"]
    sell_list = [s for s, d in all_data.items() if d.get("signal") == "SELL"]
    near_list = [s for s, d in all_data.items()
                 if d.get("near_demand") or d.get("near_supply")]
    hold_cnt  = sum(1 for d in all_data.values() if d.get("signal") == "HOLD")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🟢 BUY",  len(buy_list),  f"{', '.join(buy_list[:3])}{'...' if len(buy_list) > 3 else ''}" or "-")
    m2.metric("🔴 SELL", len(sell_list), f"{', '.join(sell_list[:3])}{'...' if len(sell_list) > 3 else ''}" or "-")
    m3.metric("⚪ HOLD", hold_cnt)
    m4.metric("⚠️ ใกล้ Zone", len(near_list), ", ".join(near_list[:3]) or "-")

    st.divider()

    # ── Filter ─────────────────────────────────────────
    if filter_opt == "BUY":
        display = [s for s in config.WATCHLIST if all_data.get(s, {}).get("signal") == "BUY"]
    elif filter_opt == "SELL":
        display = [s for s in config.WATCHLIST if all_data.get(s, {}).get("signal") == "SELL"]
    elif filter_opt == "ใกล้ Zone":
        display = [s for s in config.WATCHLIST
                   if all_data.get(s, {}).get("near_demand") or all_data.get(s, {}).get("near_supply")]
    else:
        display = list(config.WATCHLIST)

    # ── Stock Grid ─────────────────────────────────────
    cols = st.columns(config.DASHBOARD_COLS)
    for i, symbol in enumerate(display):
        data = all_data.get(symbol, {"symbol": symbol, "error": "ไม่มีข้อมูล"})
        with cols[i % config.DASHBOARD_COLS]:
            render_card(data)

    st.divider()

    # ── Detail Chart ───────────────────────────────────
    st.markdown("### รายละเอียด")
    selected = st.selectbox(
        "เลือกหุ้น",
        options=list(config.WATCHLIST),
        index=0,
    )

    data = all_data.get(selected, {})
    if "error" not in data and "_df" in data:
        df  = data["_df"]
        sig = data["signal"]

        # Indicator row
        ic1, ic2, ic3, ic4, ic5 = st.columns(5)
        ema_bull = data["ema_fast"] > data["ema_slow"]
        ic1.metric(f"EMA{config.EMA_FAST}/{config.EMA_SLOW}",
                   "Bullish ↑" if ema_bull else "Bearish ↓",
                   f"{data['ema_fast']:.2f} / {data['ema_slow']:.2f}")
        ic2.metric("ADX", f"{data['adx']:.1f}",
                   "Trending" if data["adx"] > config.ADX_THRESHOLD else "Sideways")
        ic3.metric("RSI", f"{data['rsi']:.1f}",
                   "Overbought" if data["rsi"] > config.RSI_OB else
                   ("Oversold" if data["rsi"] < config.RSI_OS else "Normal"))
        ic4.metric("ATR", f"{data['atr']:.2f}")
        ic5.metric("Signal", f"{sig}",
                   data["strength"] if sig != "HOLD" else data["reason"][:30])

        # Chart
        fig = build_chart(df, selected)
        st.plotly_chart(fig, use_container_width=True)

        # Signal reason
        if sig != "HOLD":
            color = "#238636" if sig == "BUY" else "#DA3633"
            st.markdown(
                f"<div style='background:{color};padding:8px 14px;border-radius:6px;"
                f"color:#fff;font-size:0.9rem'>"
                f"<b>{sig}</b> — {data['reason']}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.warning(f"{selected}: {data.get('error', 'ไม่มีข้อมูล')}")

    # ── Footer ─────────────────────────────────────────
    st.divider()
    fl, fr = st.columns([3, 1])
    with fl:
        st.caption(f"อัพเดทล่าสุด: {now_str} | Auto-refresh ทุก {config.DASHBOARD_REFRESH_SEC // 60} นาที")
    with fr:
        if st.button("🔄 Refresh ตอนนี้"):
            st.cache_data.clear()
            st.rerun()

    st.markdown(
        f"<meta http-equiv='refresh' content='{config.DASHBOARD_REFRESH_SEC}'>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
