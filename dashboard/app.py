"""
dashboard/app.py — SET Signal Monitor Dashboard

รัน: streamlit run dashboard/app.py
"""

import base64
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from bot.indicator import add_all_indicators, find_supply_demand_zones
from bot.strategy  import get_signal
from data.fetcher  import fetch_all
from data.settrade_fetcher import fetch_all_st, has_credentials

# ══════════════════════════════════════════════════════
# GitHub API
# ══════════════════════════════════════════════════════

def commit_watchlist(watchlist: list) -> tuple[bool, str]:
    """Commit data/watchlist.json ขึ้น GitHub — trigger Streamlit Cloud redeploy"""
    token  = config.GITHUB_TOKEN
    repo   = config.GITHUB_REPO
    branch = config.GITHUB_BRANCH

    if not token:
        return False, "ไม่พบ GITHUB_TOKEN — ตั้งค่าใน Streamlit Secrets ก่อน"

    api_url = f"https://api.github.com/repos/{repo}/contents/data/watchlist.json"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    r = requests.get(api_url, headers=headers, params={"ref": branch}, timeout=10)
    sha = r.json().get("sha") if r.status_code == 200 else None

    content = json.dumps(sorted(watchlist), ensure_ascii=False, indent=2)
    payload = {
        "message": f"update watchlist ({len(watchlist)} stocks)",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(api_url, headers=headers, json=payload, timeout=10)
    if r.status_code in (200, 201):
        return True, f"บันทึกแล้ว ({len(watchlist)} ตัว) — Streamlit Cloud กำลัง redeploy ~2 นาที"
    return False, f"GitHub error {r.status_code}: {r.json().get('message', '')}"


# ══════════════════════════════════════════════════════
# Page Config
# ══════════════════════════════════════════════════════

st.set_page_config(
    page_title="SET Signal Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════

DUMMY_STATE = {"in_position": False, "bot_active": True, "cooldown_bars": 0}
BKK = ZoneInfo("Asia/Bangkok")

SIG_COLOR  = {"BUY": "#238636", "SELL": "#DA3633", "HOLD": "#21262D"}
SIG_TEXT   = {"BUY": "#3FB950", "SELL": "#F85149", "HOLD": "#8B949E"}
SIG_BORDER = {"BUY": "#3FB950", "SELL": "#F85149", "HOLD": "#30363D"}

# ══════════════════════════════════════════════════════
# Session State
# ══════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════
# Data Loading
# ══════════════════════════════════════════════════════

def _build_results(ohlcv_map: dict, watchlist: list, htf_map: dict = None) -> dict:
    """คำนวณ indicators + signal จาก ohlcv_map ที่รับมา"""
    results = {}
    for symbol in watchlist:
        df = ohlcv_map.get(symbol)
        if df is None or len(df) < config.EMA_SLOW + 10:
            results[symbol] = {"symbol": symbol, "error": "ข้อมูลไม่พอ"}
            continue
        try:
            df2 = add_all_indicators(df)

            df_htf = None
            if htf_map:
                df_raw_htf = htf_map.get(symbol)
                if df_raw_htf is not None and len(df_raw_htf) >= config.EMA_SLOW + 5:
                    df_htf = add_all_indicators(df_raw_htf)

            sig  = get_signal(df2, DUMMY_STATE, df_htf=df_htf)
            last = df2.iloc[-2]
            prev = df2.iloc[-3]
            price = float(df["close"].iloc[-1])
            chg   = (float(last["close"]) - float(prev["close"])) / float(prev["close"]) * 100
            atr   = float(last["atr"])

            # คำนวณแนวรับ/แนวต้านจาก Supply/Demand zones
            zones = find_supply_demand_zones(df2, config.PIVOT_LENGTH)
            demand_mids = sorted([(h + l) / 2 for h, l in zones["demand"]], reverse=True)
            supply_mids = sorted([(h + l) / 2 for h, l in zones["supply"]])
            support    = next((m for m in demand_mids if m <= price * 1.02), demand_mids[0]  if demand_mids else None)
            resistance = next((m for m in supply_mids if m >= price * 0.98), supply_mids[-1] if supply_mids else None)

            # ราคาแนะนำตาม signal
            sig_act = sig["action"]
            if sig_act == "BUY":
                suggest_entry = price
                suggest_sl    = price - atr * config.ATR_SL_MULT
                suggest_tp    = price + atr * 2.0
            elif sig_act == "SELL":
                suggest_entry = price
                suggest_sl    = price + atr * config.ATR_SL_MULT
                suggest_tp    = price - atr * 2.0
            else:
                suggest_entry = support
                suggest_sl    = support * (1 - 0.03) if support else None
                suggest_tp    = resistance

            def _fmt(v):
                return round(v, 2) if v is not None else None

            results[symbol] = {
                "symbol":        symbol,
                "price":         price,
                "price_chg_pct": round(chg, 2),
                "ema_fast":      float(last["ema_fast"]),
                "ema_slow":      float(last["ema_slow"]),
                "adx":           float(last["adx"]),
                "rsi":           float(last["rsi"]),
                "atr":           atr,
                "signal":        sig["action"],
                "strength":      sig["strength"],
                "reason":        sig["reason"],
                "near_demand":   sig["near_demand"],
                "near_supply":   sig["near_supply"],
                "support":       _fmt(support),
                "resistance":    _fmt(resistance),
                "suggest_entry": _fmt(suggest_entry),
                "suggest_sl":    _fmt(suggest_sl),
                "suggest_tp":    _fmt(suggest_tp),
                "_df":           df2,
            }
        except Exception as e:
            results[symbol] = {"symbol": symbol, "error": str(e)}
    return results


@st.cache_data(ttl=config.DASHBOARD_REFRESH_SEC)
def load_signals_daily():
    """Daily mode — ดึงข้อมูลจาก yfinance (cache 5 นาที)"""
    ohlcv_map = fetch_all()
    htf_map   = fetch_all(interval=config.TIMEFRAME_HTF, period=config.HTF_PERIOD)
    return _build_results(ohlcv_map, list(config.WATCHLIST), htf_map=htf_map)


@st.cache_data(ttl=config.REALTIME_REFRESH_SEC)
def load_signals_realtime():
    """Real-time mode — ดึงข้อมูลจาก Settrade (cache 1 นาที, ข้าม SET index)"""
    watchlist = [s for s in config.WATCHLIST if s != "SET"]
    return _build_results(fetch_all_st(), watchlist)


def is_market_open() -> bool:
    now = datetime.now(tz=BKK)
    if now.weekday() >= 5:
        return False
    t = now.hour * 60 + now.minute
    return (9*60 <= t <= 12*60+30) or (14*60 <= t <= 16*60+30)


# ══════════════════════════════════════════════════════
# Card Renderer
# ══════════════════════════════════════════════════════

def render_card(data: dict):
    """แสดงข้อมูลหุ้น 1 ตัว รวม name header ที่ top"""
    symbol = data.get("symbol", "")

    if "error" in data:
        st.markdown(f"""
        <div style="background:#161B22;border:1px solid #30363D;border-radius:8px 8px 0 0;
                    padding:10px 12px;margin:0;min-height:144px">
          <div style="font-weight:700;color:#58A6FF;font-size:0.88rem;margin-bottom:6px">{symbol}</div>
          <span style="color:#F85149;font-size:0.75rem">{data['error']}</span>
        </div>""", unsafe_allow_html=True)
        return

    sig    = data["signal"]
    chg    = data["price_chg_pct"]
    rsi    = data["rsi"]
    adx    = data["adx"]
    near_d = data["near_demand"]
    near_s = data["near_supply"]
    sup    = data.get("support")
    res    = data.get("resistance")
    s_tp   = data.get("suggest_tp")
    s_sl   = data.get("suggest_sl")

    # ── Name header styling ────────────────────────────
    if near_d:
        name_bg     = "#1A3020"
        name_color  = "#3FB950"
        name_border = "#3FB950"
        near_badge  = "<span style='font-size:0.65rem;opacity:0.9'>▲ ใกล้รับ</span>"
    elif near_s:
        name_bg     = "#301A1A"
        name_color  = "#F85149"
        name_border = "#F85149"
        near_badge  = "<span style='font-size:0.65rem;opacity:0.9'>▼ ใกล้ต้าน</span>"
    else:
        name_bg     = "#1C2128"
        name_color  = "#58A6FF"
        name_border = "#30363D"
        near_badge  = ""

    strength_badge = ""
    if sig != "HOLD" and data["strength"] == "STRONG":
        strength_badge = "<span style='font-size:0.65rem;color:#E3B341'>★ STRONG&nbsp;</span>"

    near_tag = ""
    if near_d and sig == "HOLD":
        near_tag = "<span style='font-size:0.65rem;color:#3FB950'>▲ ใกล้แนวรับ</span>"
    elif near_s and sig == "HOLD":
        near_tag = "<span style='font-size:0.65rem;color:#F85149'>▼ ใกล้แนวต้าน</span>"

    chg_color = "#3FB950" if chg >= 0 else "#F85149"
    chg_sign  = "+" if chg >= 0 else ""
    rsi_color = "#F85149" if rsi > 70 else ("#3FB950" if rsi < 30 else "#8B949E")
    adx_color = "#3FB950" if adx > config.ADX_THRESHOLD else "#E3B341"
    bg_color  = "#1A2332" if sig == "BUY" else ("#2A1A1A" if sig == "SELL" else "#161B22")

    # แถวแนวรับ/แนวต้าน
    sup_str = f"{sup:,.2f}" if sup else "-"
    res_str = f"{res:,.2f}" if res else "-"
    zone_row = (
        f"<div style='font-size:0.69rem;display:flex;gap:10px;margin-top:4px'>"
        f"<span>รับ: <span style='color:#3FB950;font-weight:600'>{sup_str}</span></span>"
        f"<span>ต้าน: <span style='color:#F85149;font-weight:600'>{res_str}</span></span>"
        f"</div>"
    )

    # แถวราคาแนะนำ
    if sig == "BUY" and s_tp and s_sl:
        price_row = (
            f"<div style='font-size:0.67rem;margin-top:3px'>"
            f"<span style='color:#E3B341'>เป้า: <b>{s_tp:,.2f}</b></span>"
            f"&nbsp;&nbsp;<span style='color:#F85149'>SL: {s_sl:,.2f}</span>"
            f"</div>"
        )
    elif sig == "SELL" and s_tp and s_sl:
        price_row = (
            f"<div style='font-size:0.67rem;margin-top:3px'>"
            f"<span style='color:#E3B341'>เป้า: <b>{s_tp:,.2f}</b></span>"
            f"&nbsp;&nbsp;<span style='color:#3FB950'>SL: {s_sl:,.2f}</span>"
            f"</div>"
        )
    elif near_d and sig == "HOLD" and s_tp:
        price_row = (
            f"<div style='font-size:0.67rem;margin-top:3px;color:#8B949E'>"
            f"{strength_badge}{near_tag}"
            f"&nbsp;<span style='color:#E3B341'>เป้า: {s_tp:,.2f}</span>"
            f"</div>"
        )
    else:
        price_row = (
            f"<div style='font-size:0.67rem;margin-top:3px;color:#8B949E'>"
            f"{strength_badge}{near_tag}&nbsp;"
            f"</div>"
        )

    st.markdown(f"""
    <div style="margin:0">
      <div style="background:{name_bg};border:1px solid {name_border};
                  border-radius:8px 8px 0 0;border-bottom:none;
                  padding:5px 10px;display:flex;justify-content:space-between;
                  align-items:center;min-height:34px">
        <span style="color:{name_color};font-weight:700;font-size:0.88rem">{symbol}</span>
        <span style="color:{name_color}">{near_badge}</span>
      </div>
      <div style="background:{bg_color};border:1px solid {SIG_BORDER[sig]};
                  border-top:1px solid {name_border};
                  border-radius:0;padding:10px 12px;min-height:110px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="background:{SIG_COLOR[sig]};color:{SIG_TEXT[sig]};
                       padding:2px 7px;border-radius:4px;font-size:0.78rem;font-weight:700">{sig}</span>
          <span style="font-size:1.05rem;color:#E6EDF3;font-weight:600">
            {data['price']:,.2f}
            <span style="font-size:0.76rem;color:{chg_color}">&nbsp;{chg_sign}{chg:.2f}%</span>
          </span>
        </div>
        <div style="font-size:0.71rem;display:flex;gap:10px;margin-top:5px">
          <span>RSI: <span style="color:{rsi_color};font-weight:600">{rsi:.0f}</span></span>
          <span>ADX: <span style="color:{adx_color};font-weight:600">{adx:.0f}</span></span>
        </div>
        {zone_row}
        {price_row}
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

    fig.add_trace(go.Candlestick(
        x=df_chart.index,
        open=df_chart["open"], high=df_chart["high"],
        low=df_chart["low"],   close=df_chart["close"],
        name=symbol,
        increasing_line_color="#3FB950", increasing_fillcolor="#3FB950",
        decreasing_line_color="#F85149", decreasing_fillcolor="#F85149",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart["ema_fast"],
        name=f"EMA{config.EMA_FAST}", line=dict(color="#58A6FF", width=1.5),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart["ema_slow"],
        name=f"EMA{config.EMA_SLOW}", line=dict(color="#E3B341", width=1.5),
    ), row=1, col=1)

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

    fig.add_trace(go.Scatter(
        x=df_chart.index, y=df_chart["adx"],
        name="ADX", line=dict(color="#8B949E", width=1.2),
    ), row=2, col=1)
    fig.add_hline(y=config.ADX_THRESHOLD, row=2, col=1,
                  line=dict(color="#E3B341", dash="dash", width=0.8))

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
# Card click callback
# ══════════════════════════════════════════════════════

def _select(sym: str):
    """callback เมื่อคลิกปุ่มชื่อหุ้น — อัปเดต session state ก่อน rerender"""
    st.session_state.selected = sym


# ══════════════════════════════════════════════════════
# Main Layout
# ══════════════════════════════════════════════════════

def main():
    st.markdown("""
<style>
  .stApp { background-color: #0D1117; color: #E6EDF3; }
  .stApp header { background-color: #0D1117; }
  h1,h2,h3 { color: #58A6FF !important; }
  hr { border-color: #21262D !important; margin: 0.4rem 0 !important; }
  .block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 0 !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
  }
  header[data-testid="stHeader"] { background-color: #0D1117 !important; }
  .stSelectbox label { color: #8B949E !important; }
  [data-testid="stMetricValue"] { font-size:1.3rem !important; }
  [data-testid="stMetricLabel"] { font-size:0.75rem !important; color:#8B949E !important; }
  /* ปุ่ม "ดูกราฟ" ใต้แต่ละ card */
  div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button {
    background: #161B22 !important;
    border: 1px solid #30363D !important;
    border-top: none !important;
    color: #8B949E !important;
    font-size: 0.75rem !important;
    padding: 3px 0 !important;
    border-radius: 0 0 8px 8px !important;
    margin: 0 !important;
    width: 100% !important;
  }
  div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button:hover {
    background: #21262D !important;
    color: #58A6FF !important;
    border-color: #58A6FF !important;
    border-top: none !important;
  }
</style>
""", unsafe_allow_html=True)

    if "selected" not in st.session_state:
        st.session_state.selected = "SET"
    if "data_mode" not in st.session_state:
        st.session_state.data_mode = "daily"
    if "edit_wl" not in st.session_state:
        st.session_state.edit_wl = list(config.WATCHLIST)

    # ── Sidebar: Watchlist Manager ──────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ จัดการ Watchlist")
        st.caption(f"ปัจจุบัน {len(st.session_state.edit_wl)} ตัว")
        st.divider()

        to_del = None
        for sym in st.session_state.edit_wl:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{sym}**")
            if c2.button("✕", key=f"del_{sym}", help=f"ลบ {sym}"):
                to_del = sym
        if to_del:
            st.session_state.edit_wl.remove(to_del)
            st.rerun()

        st.divider()
        new_sym = st.text_input("เพิ่มหุ้น", placeholder="เช่น PTT", label_visibility="collapsed").strip().upper()
        if st.button("+ เพิ่ม", use_container_width=True) and new_sym:
            if new_sym not in st.session_state.edit_wl:
                st.session_state.edit_wl.append(new_sym)
                st.session_state.edit_wl.sort()
                st.rerun()
            else:
                st.warning(f"{new_sym} มีอยู่แล้ว")

        st.divider()
        token_ok = bool(config.GITHUB_TOKEN)
        if not token_ok:
            st.warning("⚠️ ไม่พบ GITHUB_TOKEN ใน Secrets")
        if st.button("💾 บันทึกขึ้น GitHub", type="primary", use_container_width=True, disabled=not token_ok):
            with st.spinner("กำลัง commit..."):
                ok, msg = commit_watchlist(st.session_state.edit_wl)
            if ok:
                st.success(msg)
                st.info("หลัง redeploy ~2 นาที กด Refresh หรือ reload หน้า")
            else:
                st.error(msg)

        if st.button("↺ รีเซ็ต", use_container_width=True, help="คืนค่าเป็น watchlist ปัจจุบัน"):
            st.session_state.edit_wl = list(config.WATCHLIST)
            st.rerun()

    market_open  = is_market_open()
    market_label = "🟢 ตลาดเปิด" if market_open else "🔴 ตลาดปิด"
    now_str      = datetime.now(tz=BKK).strftime("%d/%m/%Y %H:%M")

    # ── Header ─────────────────────────────────────────
    h1, h2, h3, h4, h5 = st.columns([2.8, 1, 1, 1, 1.5])
    with h1:
        tf_label = f"{config.REALTIME_INTERVAL}m" \
                   if st.session_state.data_mode == "realtime" else "Daily"
        st.markdown(
            "<span style='color:#58A6FF;font-size:1.5rem;font-weight:700'>📈 SET Signal Monitor</span>"
            f"&nbsp;&nbsp;<span style='color:#8B949E;font-size:0.85rem'>{tf_label} TF — {now_str}</span>",
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            f"<div style='text-align:center;padding-top:6px'>{market_label}</div>",
            unsafe_allow_html=True,
        )
    with h3:
        # mode toggle
        mode_choice = st.selectbox(
            "mode",
            options=["📊 Daily", "⚡ Real-time"],
            index=0 if st.session_state.data_mode == "daily" else 1,
            label_visibility="collapsed",
        )
        new_mode = "realtime" if "Real-time" in mode_choice else "daily"
        if new_mode != st.session_state.data_mode:
            st.session_state.data_mode = new_mode
            st.cache_data.clear()
            st.rerun()
    with h4:
        filter_opt = st.selectbox(
            "filter", ["ทั้งหมด", "BUY", "SELL", "ใกล้ Zone"],
            label_visibility="collapsed",
        )
    with h5:
        # selectbox sync กับ session_state.selected
        all_syms = list(config.WATCHLIST)
        cur_idx  = all_syms.index(st.session_state.selected) \
                   if st.session_state.selected in all_syms else 0
        chosen = st.selectbox(
            "เลือกหุ้น", options=all_syms, index=cur_idx,
            label_visibility="collapsed",
        )
        if chosen != st.session_state.selected:
            st.session_state.selected = chosen

    st.divider()

    # ── Load data ───────────────────────────────────────
    is_realtime = st.session_state.data_mode == "realtime"

    if is_realtime and not has_credentials():
        st.warning(
            "⚡ **Real-time mode** ต้องการ Settrade credentials — "
            "ตั้งค่าใน `.env` ก่อน ([ดูวิธีสมัคร](https://developer.settrade.com)) "
            "| แสดงข้อมูล Daily (yfinance) แทนชั่วคราว",
            icon="🔑",
        )
        is_realtime = False  # fallback to daily

    with st.spinner("กำลังดึงข้อมูล..."):
        all_data = load_signals_realtime() if is_realtime else load_signals_daily()

    # ── Summary bar ─────────────────────────────────────
    buy_list  = [s for s, d in all_data.items() if d.get("signal") == "BUY"]
    sell_list = [s for s, d in all_data.items() if d.get("signal") == "SELL"]
    near_list = [s for s, d in all_data.items()
                 if d.get("near_demand") or d.get("near_supply")]
    hold_cnt  = sum(1 for d in all_data.values() if d.get("signal") == "HOLD")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🟢 BUY",  len(buy_list),
              ", ".join(buy_list[:3]) + ("…" if len(buy_list) > 3 else "") or "-")
    m2.metric("🔴 SELL", len(sell_list),
              ", ".join(sell_list[:3]) + ("…" if len(sell_list) > 3 else "") or "-")
    m3.metric("⚪ HOLD", hold_cnt)
    m4.metric("⚠️ ใกล้ Zone", len(near_list), ", ".join(near_list[:3]) or "-")

    st.divider()

    # ══════════════════════════════════════════════════
    # รายละเอียด + กราฟ  (อยู่เหนือ grid)
    # ══════════════════════════════════════════════════
    selected = st.session_state.selected
    st.markdown(f"### รายละเอียด — {selected}")

    data = all_data.get(selected, {})
    if "error" not in data and "_df" in data:
        df  = data["_df"]
        sig = data["signal"]

        ic1, ic2, ic3, ic4, ic5 = st.columns(5)
        ema_bull  = data["ema_fast"] > data["ema_slow"]
        ema_color = "#3FB950" if ema_bull else "#F85149"
        ema_label = "Bullish ↑" if ema_bull else "Bearish ↓"
        with ic1:
            st.markdown(f"""
            <div style="padding:4px 0 0 0">
              <div style="color:#8B949E;font-size:0.78rem;margin-bottom:2px">EMA{config.EMA_FAST}/{config.EMA_SLOW}</div>
              <div style="color:{ema_color};font-size:1.35rem;font-weight:700;line-height:1.2">{ema_label}</div>
              <div style="color:#8B949E;font-size:0.75rem;margin-top:2px">
                ↑ {data['ema_fast']:.2f} / {data['ema_slow']:.2f}
              </div>
            </div>""", unsafe_allow_html=True)
        ic2.metric("ADX", f"{data['adx']:.1f}",
                   "Trending" if data["adx"] > config.ADX_THRESHOLD else "Sideways")
        ic3.metric("RSI", f"{data['rsi']:.1f}",
                   "Overbought" if data["rsi"] > config.RSI_OB else
                   ("Oversold" if data["rsi"] < config.RSI_OS else "Normal"))
        ic4.metric("ATR", f"{data['atr']:.2f}")
        ic5.metric("Signal", sig,
                   data["strength"] if sig != "HOLD" else data["reason"][:30])

        fig = build_chart(df, selected)
        st.plotly_chart(fig, use_container_width=True)

        if sig != "HOLD":
            color = "#238636" if sig == "BUY" else "#DA3633"
            st.markdown(
                f"<div style='background:{color};padding:8px 14px;border-radius:6px;"
                f"color:#fff;font-size:0.9rem'>"
                f"<b>{sig}</b> — {data['reason']}</div>",
                unsafe_allow_html=True,
            )
    else:
        err_msg = data.get("error", "ไม่มีข้อมูล") if data else "กำลังโหลด..."
        st.warning(f"{selected}: {err_msg}")

    st.divider()

    # ══════════════════════════════════════════════════
    # Stock Grid
    # ══════════════════════════════════════════════════

    if filter_opt == "BUY":
        display = [s for s in config.WATCHLIST if all_data.get(s, {}).get("signal") == "BUY"]
    elif filter_opt == "SELL":
        display = [s for s in config.WATCHLIST if all_data.get(s, {}).get("signal") == "SELL"]
    elif filter_opt == "ใกล้ Zone":
        display = [s for s in config.WATCHLIST
                   if all_data.get(s, {}).get("near_demand") or all_data.get(s, {}).get("near_supply")]
    else:
        display = list(config.WATCHLIST)

    if not display:
        st.info(f"ไม่มีหุ้นที่ตรงกับ filter '{filter_opt}' ขณะนี้")
    else:
        cols = st.columns(config.DASHBOARD_COLS)
        for i, symbol in enumerate(display):
            card_data = all_data.get(symbol, {"symbol": symbol, "error": "ไม่มีข้อมูล"})
            with cols[i % config.DASHBOARD_COLS]:
                render_card(card_data)
                st.button(
                    "📈 กราฟ",
                    key=f"sel_{symbol}",
                    use_container_width=True,
                    on_click=_select,
                    args=(symbol,),
                )

    # ── Footer ──────────────────────────────────────────
    st.divider()
    fl, fr = st.columns([3, 1])
    with fl:
        refresh_min = config.REALTIME_REFRESH_SEC // 60 \
                      if st.session_state.data_mode == "realtime" \
                      else config.DASHBOARD_REFRESH_SEC // 60
        mode_tag = "⚡ Real-time (Settrade)" if st.session_state.data_mode == "realtime" \
                   else "📊 Daily (yfinance)"
        st.caption(f"อัพเดทล่าสุด: {now_str} | {mode_tag} | Auto-refresh ทุก {refresh_min} นาที")
    with fr:
        if st.button("🔄 Refresh ตอนนี้", key="refresh_btn"):
            st.cache_data.clear()
            st.rerun()

    refresh_sec = config.REALTIME_REFRESH_SEC \
                  if st.session_state.data_mode == "realtime" \
                  else config.DASHBOARD_REFRESH_SEC
    st.markdown(
        f"<meta http-equiv='refresh' content='{refresh_sec}'>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
