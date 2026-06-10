import time

import pandas as pd
import streamlit as st
import yfinance as yf

from .fetcher import to_yf


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def get_fundamentals(symbol: str) -> dict:
    """คืน yfinance .info dict — raise Exception เมื่อ fail (ไม่ cache ผล error)"""
    if symbol == "SET":
        return {}
    last_exc: Exception = RuntimeError("unknown error")
    for attempt in range(3):
        if attempt > 0:
            time.sleep(2 ** attempt)  # 2s, 4s
        try:
            info = yf.Ticker(to_yf(symbol)).info or {}
            if len(info) >= 5:
                return info
            last_exc = ValueError(f"Yahoo Finance คืนข้อมูลไม่ครบสำหรับ {symbol}")
        except Exception as e:
            last_exc = e
    raise last_exc


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
