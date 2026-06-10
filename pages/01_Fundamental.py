import os
import sys
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config
from data.fundamental import get_dividend_history, get_fundamentals

# ── Page Config ───────────────────────────────────────
st.set_page_config(
    page_title="Fundamental — SET",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .stApp { background-color: #0D1117; color: #E6EDF3; }
  .stApp header { background-color: #0D1117; }
  h1,h2,h3 { color: #58A6FF !important; }
  hr { border-color: #21262D !important; margin: 0.4rem 0 !important; }
  .block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
  }
  header[data-testid="stHeader"] { background-color: #0D1117 !important; }
  .stSelectbox label { color: #8B949E !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────
st.markdown(
    "<span style='color:#58A6FF;font-size:1.5rem;font-weight:700'>📊 Fundamental Data</span>",
    unsafe_allow_html=True,
)

stocks = [s for s in config.WATCHLIST if s != "SET"]

col_sym, col_btn, _ = st.columns([2, 1, 5])
with col_sym:
    symbol = st.selectbox("เลือกหุ้น", stocks, label_visibility="collapsed")
with col_btn:
    if st.button("🔄 รีเฟรช"):
        get_fundamentals.clear()
        get_dividend_history.clear()
        st.rerun()

st.markdown("---")

# ── Load Data ─────────────────────────────────────────
with st.spinner(f"กำลังโหลด {symbol}..."):
    info = get_fundamentals(symbol)
    divs = get_dividend_history(symbol)

if not info:
    st.warning(f"ไม่พบข้อมูล fundamental สำหรับ {symbol}")
    st.stop()

# ── Helpers ───────────────────────────────────────────
def _fmt(val, fmt_str="{:,.2f}", fallback="—"):
    if val is None:
        return fallback
    try:
        f = float(val)
        if f != f:  # NaN
            return fallback
        return fmt_str.format(f)
    except Exception:
        return str(val)

def _row(label, value):
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"padding:6px 0;border-bottom:1px solid #21262D'>"
        f"<span style='color:#8B949E;font-size:0.88rem'>{label}</span>"
        f"<span style='color:#E6EDF3;font-size:0.88rem;font-weight:600'>{value}</span>"
        f"</div>"
    )

def _card(title, rows_html):
    return (
        f"<div style='background:#161B22;border:1px solid #30363D;"
        f"border-radius:8px;padding:14px 16px;margin-bottom:12px'>"
        f"<div style='color:#58A6FF;font-size:0.95rem;font-weight:700;margin-bottom:8px'>{title}</div>"
        f"{rows_html}</div>"
    )

# ── Company Overview ──────────────────────────────────
sector    = info.get("sector", "—") or "—"
industry  = info.get("industry", "—") or "—"
summary   = info.get("longBusinessSummary", "")
market_cap = info.get("marketCap")
mc_str = f"{market_cap/1e9:,.2f} พันล้านบาท" if market_cap else "—"

mrq_ts = info.get("mostRecentQuarter")
freshness = datetime.fromtimestamp(mrq_ts).strftime("%d %b %Y") if mrq_ts else "ไม่ทราบ"

col1, col2 = st.columns([3, 2])

with col1:
    rows = (
        _row("Sector", sector)
        + _row("Industry", industry)
        + _row("Market Cap", mc_str)
        + _row("ข้อมูล ณ", freshness)
    )
    st.markdown(_card("🏢 Company Overview", rows), unsafe_allow_html=True)
    if summary:
        with st.expander("รายละเอียดบริษัท"):
            snippet = summary[:800] + ("…" if len(summary) > 800 else "")
            st.markdown(
                f"<p style='color:#8B949E;font-size:0.82rem;line-height:1.6'>{snippet}</p>",
                unsafe_allow_html=True,
            )

with col2:
    pe  = info.get("trailingPE")
    fpe = info.get("forwardPE")
    eps = info.get("trailingEps")
    pb  = info.get("priceToBook")

    rows = (
        _row("P/E (Trailing)", _fmt(pe))
        + _row("P/E (Forward)", _fmt(fpe))
        + _row("EPS (Trailing)", _fmt(eps, "{:,.2f} ฿"))
        + _row("P/B", _fmt(pb))
    )
    st.markdown(_card("📐 Financial Ratios", rows), unsafe_allow_html=True)

st.markdown("---")

# ── Revenue & Profitability ───────────────────────────
rev    = info.get("totalRevenue")
margin = info.get("profitMargins")
roe    = info.get("returnOnEquity")
de     = info.get("debtToEquity")
cr     = info.get("currentRatio")
rev_ps = info.get("revenuePerShare")

rev_str    = f"{rev/1e9:,.2f} พันล้านบาท" if rev else "—"
margin_str = f"{margin*100:,.2f}%" if margin else "—"
roe_str    = f"{roe*100:,.2f}%" if roe else "—"

col3, col4 = st.columns(2)
with col3:
    rows = (
        _row("Total Revenue", rev_str)
        + _row("Revenue/Share", _fmt(rev_ps, "{:,.2f} ฿"))
        + _row("Profit Margin", margin_str)
    )
    st.markdown(_card("📈 Revenue & Profitability", rows), unsafe_allow_html=True)

with col4:
    rows = (
        _row("Return on Equity (ROE)", roe_str)
        + _row("Debt / Equity", _fmt(de, "{:,.2f}x"))
        + _row("Current Ratio", _fmt(cr, "{:,.2f}x"))
    )
    st.markdown(_card("⚖️ Balance Sheet", rows), unsafe_allow_html=True)

st.markdown("---")

# ── Dividends ─────────────────────────────────────────
div_yield  = info.get("dividendYield")
div_rate   = info.get("dividendRate")
payout     = info.get("payoutRatio")
ex_date_ts = info.get("exDividendDate")

dy_str = f"{div_yield:,.2f}%" if div_yield else "—"
dr_str = _fmt(div_rate, "{:,.2f} ฿/หุ้น")
po_str = f"{payout*100:,.2f}%" if payout else "—"
ex_str = datetime.fromtimestamp(ex_date_ts).strftime("%d %b %Y") if ex_date_ts else "—"

col5, _ = st.columns([2, 2])
with col5:
    rows = (
        _row("Dividend Yield", dy_str)
        + _row("Dividend Rate", dr_str)
        + _row("Payout Ratio", po_str)
        + _row("Ex-Dividend Date", ex_str)
    )
    st.markdown(_card("💰 Dividends", rows), unsafe_allow_html=True)

# ── Dividend History Chart ─────────────────────────────
if not divs.empty:
    fig = go.Figure(go.Bar(
        x=divs["date"].dt.strftime("%Y-%m-%d"),
        y=divs["dividend"],
        marker_color="#58A6FF",
        text=[f"{v:.2f}" for v in divs["dividend"]],
        textposition="outside",
        textfont=dict(color="#E6EDF3", size=10),
    ))
    fig.update_layout(
        paper_bgcolor="#0D1117",
        plot_bgcolor="#161B22",
        font=dict(color="#E6EDF3"),
        title=dict(
            text=f"{symbol} — Dividend History (5 ปีล่าสุด)",
            font=dict(color="#58A6FF", size=13),
        ),
        xaxis=dict(gridcolor="#1C2128", title=""),
        yaxis=dict(gridcolor="#1C2128", title="บาท/หุ้น"),
        margin=dict(t=40, b=40, l=40, r=10),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Disclaimer ────────────────────────────────────────
st.markdown(
    "<p style='color:#8B949E;font-size:0.75rem;text-align:center;margin-top:12px'>"
    "⚠️ ข้อมูลจาก Yahoo Finance อาจล่าช้า 1-4 สัปดาห์ — "
    "ใช้ประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำการลงทุน</p>",
    unsafe_allow_html=True,
)
