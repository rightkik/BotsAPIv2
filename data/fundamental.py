import json
import os
import time

import pandas as pd
import streamlit as st
import yfinance as yf

from .fetcher import to_yf

_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "cache", "fundamentals.json",
)


@st.cache_data(ttl=300, show_spinner=False)
def _load_cache_file() -> dict:
    """โหลด fundamentals.json ที่ GitHub Actions commit ไว้ (cache 5 นาที)"""
    try:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_cache_updated() -> str:
    """คืนวันที่อัปเดตล่าสุด หรือ '' ถ้าไม่มี cache"""
    return _load_cache_file().get("_updated", "")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def get_fundamentals(symbol: str) -> dict:
    """คืน fundamental dict — อ่านจาก cache file ก่อน, fallback live"""
    if symbol == "SET":
        return {}

    cache = _load_cache_file()
    if symbol in cache:
        return cache[symbol]

    # fallback: live fetch (อาจ rate-limit บน cloud)
    last_exc: Exception = RuntimeError("unknown error")
    for attempt in range(3):
        if attempt > 0:
            time.sleep(2 ** attempt)
        try:
            info = yf.Ticker(to_yf(symbol)).info or {}
            if len(info) >= 5:
                return info
            last_exc = ValueError(f"Yahoo Finance คืนข้อมูลไม่ครบสำหรับ {symbol}")
        except Exception as e:
            last_exc = e
    raise last_exc


@st.cache_data(ttl=3600, show_spinner=False)
def get_price_history(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """OHLCV ย้อนหลัง พร้อมคอลัมน์ change และ change_pct (vs close วันก่อน)"""
    if symbol == "SET":
        period = "6mo"
    try:
        import yfinance as yf
        df = yf.download(to_yf(symbol), period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c.lower() if isinstance(c, str) else c[0].lower()
                      for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        df["change"]     = df["close"].diff()
        df["change_pct"] = df["close"].pct_change() * 100
        df = df.dropna(subset=["change"]).sort_index(ascending=False)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def get_dividend_history(symbol: str) -> pd.DataFrame:
    if symbol == "SET":
        return pd.DataFrame()
    try:
        ticker = yf.Ticker(to_yf(symbol))
        divs = ticker.dividends
        if divs is None or divs.empty:
            return pd.DataFrame()
        divs = divs.reset_index()
        divs.columns = ["date", "dividend"]
        cutoff = pd.Timestamp.now(tz=divs["date"].dt.tz) - pd.DateOffset(years=5)
        divs = divs[divs["date"] >= cutoff].copy()
        return divs
    except Exception:
        return pd.DataFrame()
