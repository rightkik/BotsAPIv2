"""
data/settrade_fetcher.py — ดึง OHLCV จาก Settrade Open API (real-time mode)

ต้องตั้งค่าใน .env:
  SETTRADE_APP_ID, SETTRADE_APP_SECRET, SETTRADE_APP_CODE, SETTRADE_BROKER_ID

Sandbox: ตั้ง SETTRADE_BROKER_ID=SANDBOX → ใช้ UAT environment อัตโนมัติ

API:
  get_candlestick(symbol, interval, limit)
    interval: "1","5","15","30","60" = นาที | "D" = รายวัน | "W" = รายสัปดาห์
  get_quote_symbol(symbol)
    ราคา bid/offer/last แบบ real-time
"""

from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

import config

BKK = ZoneInfo("Asia/Bangkok")

# SET index ไม่มีใน Settrade — ข้ามในโหมด real-time
_SKIP_SYMBOLS = {"SET"}


def has_credentials() -> bool:
    """ตรวจว่า Settrade credentials ครบพอ login ได้"""
    return all([
        config.SETTRADE_APP_ID,
        config.SETTRADE_APP_SECRET,
        config.SETTRADE_APP_CODE,
        config.SETTRADE_BROKER_ID,
    ])


def _make_investor():
    """สร้าง Investor จาก credentials ใน .env (login ตอนสร้าง)"""
    from settrade_v2 import Investor

    if not has_credentials():
        raise ValueError("Settrade credentials ไม่ครบ — ตั้งค่าใน .env ก่อน")

    return Investor(
        app_id=config.SETTRADE_APP_ID,
        app_secret=config.SETTRADE_APP_SECRET,
        app_code=config.SETTRADE_APP_CODE,
        broker_id=config.SETTRADE_BROKER_ID,
    )


def _parse_candlestick(raw: dict) -> Optional[pd.DataFrame]:
    """
    แปลง response dict จาก get_candlestick → DataFrame
    รองรับ format ที่ Settrade API คืนมา 2 แบบ:
      - key "candlesticks" หรือ "data" → list of candle dicts
      - candle field names: time/datetime + open/o, high/h, low/l, close/c, volume/v
    """
    # หา list ของแท่งเทียน
    candles = None
    for key in ("candlesticks", "data", "result"):
        if key in raw and isinstance(raw[key], list):
            candles = raw[key]
            break
    if candles is None and isinstance(raw, list):
        candles = raw
    if not candles:
        return None

    df = pd.DataFrame(candles)

    # normalize column names
    rename = {
        "datetime": "time",
        "o": "open",  "h": "high",  "l": "low",
        "c": "close", "v": "volume",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    if "time" not in df.columns:
        return None

    # แปลง timestamp → DatetimeIndex Asia/Bangkok
    sample = df["time"].iloc[0]
    if isinstance(sample, (int, float)):
        # Unix ms
        df.index = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert(BKK)
    else:
        df.index = pd.to_datetime(df["time"]).dt.tz_localize(BKK, nonexistent="shift_forward")

    df = df.drop(columns=["time"])

    needed = ["open", "high", "low", "close", "volume"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        return None

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
    """
    ดึงราคา real-time ล่าสุด 1 symbol
    คืน dict จาก API หรือ None ถ้าล้มเหลว
    ใช้สำหรับแสดงราคาปัจจุบันในหน้า dashboard
    """
    if symbol in _SKIP_SYMBOLS:
        return None

    try:
        investor = _make_investor()
        market   = investor.MarketData()
        return market.get_quote_symbol(symbol)
    except Exception:
        return None
