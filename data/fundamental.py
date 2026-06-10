import pandas as pd
import streamlit as st
import yfinance as yf

from .fetcher import to_yf


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def get_fundamentals(symbol: str) -> dict:
    if symbol == "SET":
        return {}
    try:
        ticker = yf.Ticker(to_yf(symbol))
        info = ticker.info or {}
        return info
    except Exception:
        return {}


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
