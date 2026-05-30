# ===================================================
# bot/indicator.py — คำนวณ Technical Indicators ทั้งหมด
#
# ใช้ library: ta (Technical Analysis library)
# ไม่มีการเรียก API — รับ DataFrame เข้าแล้วคืน DataFrame/Series
# ===================================================

import sys
import numpy as np
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """
    คำนวณ Exponential Moving Average
    ไวกว่า SMA ปกติ — ให้น้ำหนักกับแท่งล่าสุดมากกว่า
    """
    return df['close'].ewm(span=period, adjust=False).mean()


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    คำนวณ Average Directional Index (ADX)

    ADX วัดความแรงของเทรนด์ (ไม่บอกทิศทาง)
    ADX > 25 = มีเทรนด์ชัดเจน พร้อมเทรด
    ADX < 20 = ตลาด sideways ควรหลีกเลี่ยง

    คืน DataFrame ที่มี columns: adx, di_plus, di_minus
    """
    high  = df['high']
    low   = df['low']
    close = df['close']

    # True Range = ช่วงกว้างที่สุดของแท่งนี้รวม gap จากแท่งก่อน
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Directional Movement
    up_move   = high - high.shift(1)
    down_move = low.shift(1) - low

    dm_plus  = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    dm_minus = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    dm_plus_s  = pd.Series(dm_plus,  index=df.index)
    dm_minus_s = pd.Series(dm_minus, index=df.index)

    # Wilder Smoothing (เหมือน EWM แต่ใช้ alpha = 1/period)
    alpha   = 1.0 / period
    atr_s   = tr.ewm(alpha=alpha, adjust=False).mean()
    di_plus  = 100 * dm_plus_s.ewm(alpha=alpha, adjust=False).mean() / atr_s
    di_minus = 100 * dm_minus_s.ewm(alpha=alpha, adjust=False).mean() / atr_s

    # DX → ADX
    dx  = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx = dx.ewm(alpha=alpha, adjust=False).mean()

    result = pd.DataFrame({
        'adx':      adx,
        'di_plus':  di_plus,
        'di_minus': di_minus,
    }, index=df.index)
    return result


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    คำนวณ RSI (Relative Strength Index)
    RSI > 70 = overbought (อาจจะลง)
    RSI < 30 = oversold  (อาจจะขึ้น)
    """
    delta = df['close'].diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    คำนวณ Average True Range (ATR)
    วัดความผันผวนของตลาด — ใช้กำหนดระยะ SL/TP
    ATR สูง = ตลาดผันผวนมาก ควรเพิ่ม buffer
    """
    prev_close = df['close'].shift(1)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - prev_close).abs(),
        (df['low']  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean()


def calculate_volume_delta(df: pd.DataFrame) -> pd.Series:
    """
    ประมาณแรงซื้อ/ขาย (Buy/Sell Pressure) จาก candle body

    แท่งเขียว (close > open) → volume นับเป็น buy pressure
    แท่งแดง (close < open)   → volume นับเป็น sell pressure

    คืน % ของ buy volume เทียบกับ total ทั้งแท่ง
    ค่า > 50 = แรงซื้อเยอะกว่า, < 50 = แรงขายเยอะกว่า
    """
    buy_vol  = df['volume'].where(df['close'] >= df['open'], 0.0)
    sell_vol = df['volume'].where(df['close'] < df['open'], 0.0)
    total    = (buy_vol + sell_vol).replace(0, np.nan)
    return (buy_vol / total * 100).fillna(50.0)


def find_supply_demand_zones(
    df: pd.DataFrame,
    pivot_length: int = 5
) -> dict:
    """
    หา Supply Zone (แนวต้าน) และ Demand Zone (แนวรับ)

    Supply Zone = บริเวณที่ราคาเคย pivot high → แรงขายสูง
    Demand Zone = บริเวณที่ราคาเคย pivot low  → แรงซื้อสูง

    คืน: {
        "supply": [(high, low), ...],  — โซนต้าน (ราคาสูง, ราคาต่ำของโซน)
        "demand": [(high, low), ...]   — โซนรับ
    }
    """
    supply_zones = []
    demand_zones = []
    buf = config.ZONE_BUFFER

    n = len(df)
    for i in range(pivot_length, n - pivot_length):
        high_window = df['high'].iloc[i - pivot_length: i + pivot_length + 1]
        low_window  = df['low'].iloc[i - pivot_length: i + pivot_length + 1]

        # Pivot High = high ณ จุดนี้สูงกว่าทุกแท่งในหน้าต่าง
        if df['high'].iloc[i] == high_window.max():
            ph = df['high'].iloc[i]
            supply_zones.append((ph * (1 + buf), ph * (1 - buf)))

        # Pivot Low = low ณ จุดนี้ต่ำกว่าทุกแท่งในหน้าต่าง
        if df['low'].iloc[i] == low_window.min():
            pl = df['low'].iloc[i]
            demand_zones.append((pl * (1 + buf), pl * (1 - buf)))

    # เก็บแค่ 5 โซนล่าสุด (ใกล้ราคาปัจจุบันที่สุด)
    return {
        "supply": supply_zones[-5:],
        "demand": demand_zones[-5:],
    }


def detect_market_structure(df: pd.DataFrame) -> dict:
    """
    ตรวจ Break of Structure (BoS) และ Change of Character (CHoCH)

    BoS  = ราคาทำลาย swing high/low เดิมในทิศเดิม → เทรนด์ดำเนินต่อ
    CHoCH = ราคาทำลายในทิศตรงข้าม → สัญญาณเปลี่ยนเทรนด์

    คืน: {
        "bos":   "bullish" / "bearish" / None,
        "choch": True / False
    }
    """
    if len(df) < 10:
        return {"bos": None, "choch": False}

    recent = df.tail(20)

    swing_high = recent['high'].rolling(5).max().iloc[-2]  # swing high ก่อนล่าสุด
    swing_low  = recent['low'].rolling(5).min().iloc[-2]   # swing low  ก่อนล่าสุด
    current_close = recent['close'].iloc[-1]
    prev_close    = recent['close'].iloc[-2]

    bos   = None
    choch = False

    # BoS Bullish = ทะลุ swing high ขึ้น
    if current_close > swing_high and prev_close <= swing_high:
        bos = "bullish"

    # BoS Bearish = ทะลุ swing low ลง
    elif current_close < swing_low and prev_close >= swing_low:
        bos = "bearish"

    # CHoCH = มีแนวโน้มเดิม แต่ราคาทำลายกลับทิศ
    ema_fast = recent['close'].ewm(span=config.EMA_FAST, adjust=False).mean()
    if ema_fast.iloc[-1] > ema_fast.iloc[-5]:  # เทรนด์ขึ้น
        if bos == "bearish":
            choch = True
    elif ema_fast.iloc[-1] < ema_fast.iloc[-5]:  # เทรนด์ลง
        if bos == "bullish":
            choch = True

    return {"bos": bos, "choch": choch}


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    เพิ่ม indicator ทั้งหมดเข้า DataFrame แล้วคืนกลับ

    columns ที่เพิ่ม:
      ema_fast, ema_slow     — EMA lines
      adx, di_plus, di_minus — trend strength
      rsi                    — momentum
      atr                    — volatility
      vol_delta              — buy/sell pressure
    """
    df = df.copy()

    # EMA
    df['ema_fast'] = calculate_ema(df, config.EMA_FAST)
    df['ema_slow'] = calculate_ema(df, config.EMA_SLOW)

    # ADX
    adx_df = calculate_adx(df, config.ADX_PERIOD)
    df['adx']      = adx_df['adx']
    df['di_plus']  = adx_df['di_plus']
    df['di_minus'] = adx_df['di_minus']

    # RSI
    df['rsi'] = calculate_rsi(df, config.RSI_PERIOD)

    # ATR
    df['atr'] = calculate_atr(df, config.ATR_PERIOD)

    # Volume Delta
    df['vol_delta'] = calculate_volume_delta(df)

    # Volume Moving Average — ใช้กรองสัญญาณที่ปริมาณซื้อขายต่ำเกินไป
    df['vol_ma'] = df['volume'].rolling(config.VOL_AVG_PERIOD).mean()

    return df
