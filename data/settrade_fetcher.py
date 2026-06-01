"""
data/settrade_fetcher.py — ดึง OHLCV จาก Settrade Open API (real-time mode)

ต้องตั้งค่าใน .env:
  SETTRADE_APP_ID, SETTRADE_APP_SECRET, SETTRADE_APP_CODE, SETTRADE_BROKER_ID

Sandbox: ตั้ง BROKER_ID=SANDBOX, APP_CODE=SANDBOX → ใช้ UAT environment อัตโนมัติ

API interval ที่ใช้ได้:
  "1m","5m","15m","30m","60m" = intraday | "1d" = รายวัน | "1w" = รายสัปดาห์
  Response format: dict คอลัมน์ขนาน {time:[], open:[], high:[], low:[], close:[], volume:[]}
"""

from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

import config

BKK = ZoneInfo("Asia/Bangkok")

# SET index ไม่มีใน Settrade — ข้ามในโหมด real-time
_SKIP_SYMBOLS = {"SET"}

# module-level cache — login ครั้งเดียวต่อ process
_cached_investor = None


def has_credentials() -> bool:
    """ตรวจว่า Settrade credentials ครบพอ login ได้"""
    return all([
        config.SETTRADE_APP_ID,
        config.SETTRADE_APP_SECRET,
        config.SETTRADE_APP_CODE,
        config.SETTRADE_BROKER_ID,
    ])


def _make_investor():
    """คืน Investor ที่ login แล้ว — ใช้ instance เดิมถ้ามีอยู่แล้ว"""
    global _cached_investor
    if not has_credentials():
        raise ValueError("Settrade credentials ไม่ครบ — ตั้งค่าใน .env ก่อน")
    if _cached_investor is None:
        from settrade_v2 import Investor
        _cached_investor = Investor(
            app_id=config.SETTRADE_APP_ID,
            app_secret=config.SETTRADE_APP_SECRET,
            app_code=config.SETTRADE_APP_CODE,
            broker_id=config.SETTRADE_BROKER_ID,
        )
    return _cached_investor


def _parse_candlestick(raw: dict) -> Optional[pd.DataFrame]:
    """
    แปลง response จาก get_candlestick → DataFrame
    Settrade API คืน columnar dict: {time:[], open:[], high:[], low:[], close:[], volume:[]}
    """
    if not isinstance(raw, dict):
        return None

    times = raw.get("time")
    if not isinstance(times, list) or not times:
        return None

    needed = ["open", "high", "low", "close", "volume"]
    if any(k not in raw for k in needed):
        return None

    df = pd.DataFrame({k: raw[k] for k in ["open", "high", "low", "close", "volume"]})

    # แปลง timestamp → DatetimeIndex Asia/Bangkok
    sample = times[0]
    if isinstance(sample, (int, float)):
        df.index = pd.to_datetime(times, unit="ms", utc=True).dt.tz_convert(BKK)
    else:
        df.index = pd.to_datetime(times).dt.tz_localize(BKK, nonexistent="shift_forward")

    df = df[needed].astype(float)
    df["volume"] = df["volume"].fillna(0.0)
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df if len(df) > 0 else None


def fetch_one_st(
    symbol: str,
    interval: str = None,
    limit: int = None,
) -> Optional[pd.DataFrame]:
    """
    ดึง OHLCV 1 symbol จาก Settrade
    คืน DataFrame format เดียวกับ yfinance fetcher หรือ None ถ้าล้มเหลว
    """
    if symbol in _SKIP_SYMBOLS:
        return None

    interval = interval or config.REALTIME_INTERVAL
    limit    = limit    or config.REALTIME_LIMIT

    try:
        investor = _make_investor()
        market   = investor.MarketData()
        raw      = market.get_candlestick(symbol=symbol, interval=interval, limit=limit)
        return _parse_candlestick(raw)
    except Exception:
        return None


def fetch_all_st(
    symbols: list = None,
    interval: str = None,
    limit: int = None,
) -> dict:
    """
    Batch fetch OHLCV ทุก symbol จาก Settrade
    คืน dict {symbol: DataFrame} — format เดียวกับ yfinance fetch_all()
    SET index ถูกข้ามในโหมดนี้ (ไม่มีใน Settrade)
    """
    symbols  = symbols  or [s for s in config.WATCHLIST if s not in _SKIP_SYMBOLS]
    interval = interval or config.REALTIME_INTERVAL
    limit    = limit    or config.REALTIME_LIMIT

    try:
        investor = _make_investor()
        market   = investor.MarketData()
    except Exception:
        return {}

    result = {}
    for symbol in symbols:
        try:
            raw = market.get_candlestick(symbol=symbol, interval=interval, limit=limit)
            df  = _parse_candlestick(raw)
            if df is not None and len(df) >= config.EMA_SLOW + 10:
                result[symbol] = df
        except Exception:
            continue

    return result


def get_quote(symbol: str) -> Optional[dict]:
    """ดึงราคา real-time 1 symbol — คืน dict หรือ None ถ้าล้มเหลว"""
    if symbol in _SKIP_SYMBOLS:
        return None
    try:
        market = _make_investor().MarketData()
        return market.get_quote_symbol(symbol)
    except Exception:
        return None


def fetch_quotes_all(symbols: list = None) -> dict:
    """
    Batch fetch real-time quote ทุก symbol — login ครั้งเดียว
    คืน dict {symbol: {"price": float, "price_chg_pct": float}}
    symbol ที่ดึงไม่ได้หรือ last=None จะไม่อยู่ใน dict (ให้ caller ใช้ yfinance แทน)
    """
    symbols = symbols or [s for s in config.WATCHLIST if s not in _SKIP_SYMBOLS]
    try:
        market = _make_investor().MarketData()
    except Exception:
        return {}

    result = {}
    for symbol in symbols:
        try:
            q = market.get_quote_symbol(symbol)
            last = q.get("last") if q else None
            pct  = q.get("percentChange") if q else None
            if last is not None:
                result[symbol] = {
                    "price":         float(last),
                    "price_chg_pct": float(pct) if pct is not None else 0.0,
                }
        except Exception:
            continue
    return result
