import warnings
from typing import Optional
import pandas as pd
import yfinance as yf

import config

warnings.filterwarnings("ignore")


def to_yf(symbol: str) -> str:
    if symbol == "SET":
        return "^SET.BK"
    return f"{symbol}.BK"


def fetch_all(
    symbols: list[str] = None,
    period: str = None,
    interval: str = None,
) -> dict[str, pd.DataFrame]:
    """
    Batch download OHLCV สำหรับทุก symbol ใน watchlist
    คืน dict {symbol: DataFrame} — symbol ที่ดึงไม่ได้จะไม่อยู่ใน dict
    """
    symbols  = symbols  or config.WATCHLIST
    period   = period   or config.HISTORY_PERIOD
    interval = interval or config.TIMEFRAME

    tickers = [to_yf(s) for s in symbols]

    raw = yf.download(
        tickers,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
        group_by="ticker",
    )

    result: dict[str, pd.DataFrame] = {}

    for sym, yf_sym in zip(symbols, tickers):
        try:
            # multi-ticker download → MultiIndex columns (ticker, field)
            if isinstance(raw.columns, pd.MultiIndex):
                df = raw[yf_sym].copy()
            else:
                df = raw.copy()

            df = df.dropna(how="all")
            if df.empty or len(df) < 60:
                continue

            df.columns = [c.lower() for c in df.columns]
            df = df[["open", "high", "low", "close", "volume"]].astype(float)

            # ตั้ง timezone เป็น Bangkok
            if df.index.tz is None:
                df.index = df.index.tz_localize("Asia/Bangkok", nonexistent="shift_forward")
            else:
                df.index = df.index.tz_convert("Asia/Bangkok")

            result[sym] = df

        except Exception:
            continue

    return result


def fetch_one(
    symbol: str,
    period: str = None,
    interval: str = None,
) -> Optional[pd.DataFrame]:
    """ดึง OHLCV สำหรับ symbol เดียว"""
    period   = period   or config.HISTORY_PERIOD
    interval = interval or config.TIMEFRAME

    try:
        df = yf.download(
            to_yf(symbol),
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        if df.empty:
            return None

        df = df.dropna(how="all")
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].astype(float)

        if df.index.tz is None:
            df.index = df.index.tz_localize("Asia/Bangkok", nonexistent="shift_forward")
        else:
            df.index = df.index.tz_convert("Asia/Bangkok")

        return df

    except Exception:
        return None
