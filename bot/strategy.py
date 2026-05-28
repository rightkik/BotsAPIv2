# ===================================================
# bot/strategy.py — Signal Logic (Upgraded)
#
# กลยุทธ์ใหม่: EMA Crossover + ADX Filter + Zone Awareness
#
# get_signal()         — คืน signal dict พร้อม reason และ strength
# detect_ema_crossover() — ตรวจ Golden/Death Cross
# check_adx_filter()   — กรองสัญญาณตาม ADX
# check_near_zone()    — ตรวจว่าราคาอยู่ใกล้ zone ไหม
# get_trend_label()    — คืน label สำหรับแสดงผล (Bullish/Bearish)
# ===================================================

import sys
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config
from bot.indicator import find_supply_demand_zones, detect_market_structure


def detect_ema_crossover(df: pd.DataFrame) -> str | None:
    """
    ตรวจ EMA Crossover จากแท่งปิดล่าสุด

    Golden Cross = EMA_FAST ตัด EMA_SLOW ขึ้น → สัญญาณ BUY
    Death Cross  = EMA_FAST ตัด EMA_SLOW ลง  → สัญญาณ SELL

    ใช้ iloc[-2] (แท่งปิดล่าสุด) และ iloc[-3] (แท่งก่อนหน้า)
    ไม่ใช้ iloc[-1] เพราะอาจเป็นแท่งที่ยังไม่ปิด
    """
    df_clean = df[['ema_fast', 'ema_slow']].dropna()
    if len(df_clean) < 3:
        return None

    prev = df_clean.iloc[-3]  # แท่งก่อนหน้า
    last = df_clean.iloc[-2]  # แท่งปิดล่าสุด

    golden = prev['ema_fast'] <= prev['ema_slow'] and last['ema_fast'] > last['ema_slow']
    death  = prev['ema_fast'] >= prev['ema_slow'] and last['ema_fast'] < last['ema_slow']

    if golden:
        return "golden"
    elif death:
        return "death"
    return None


def check_adx_filter(df: pd.DataFrame) -> bool:
    """
    กรองสัญญาณด้วย ADX — ต้องมีเทรนด์พอจะเทรด

    ADX > ADX_THRESHOLD = มีเทรนด์ชัดเจน → ผ่านกรอง
    ADX < ADX_THRESHOLD = ตลาด sideways → ไม่เทรด
    """
    df_clean = df[['adx']].dropna()
    if len(df_clean) < 1:
        return False
    adx = df_clean['adx'].iloc[-2] if len(df_clean) >= 2 else df_clean['adx'].iloc[-1]
    return float(adx) > config.ADX_THRESHOLD


def check_near_zone(
    price: float,
    zones: list[tuple],
    buffer: float = None
) -> bool:
    """
    ตรวจว่าราคาปัจจุบันอยู่ใกล้ zone หรือไม่

    zones = [(price_high, price_low), ...]  (จาก find_supply_demand_zones)
    buffer = % ที่ยืดออกทั้งสองด้าน (default: config.ZONE_BUFFER)
    """
    if buffer is None:
        buffer = config.ZONE_BUFFER

    for zone_high, zone_low in zones:
        zone_upper = zone_high * (1 + buffer)
        zone_lower = zone_low  * (1 - buffer)
        if zone_lower <= price <= zone_upper:
            return True
    return False


def get_signal(df: pd.DataFrame, state: dict) -> dict:
    """
    คืน signal object พร้อมเหตุผลและความแรง

    เงื่อนไข BUY (ต้องผ่านทุกข้อ):
      ✓ EMA Golden Cross (EMA20 ตัด EMA50 ขึ้น)
      ✓ ADX > ADX_THRESHOLD (มีเทรนด์)
      ✓ RSI < RSI_OB (ไม่ overbought)
      ✓ ไม่มี position เปิดอยู่
      ✓ ไม่อยู่ใน cooldown
      ✓ bot_active = True
      + STRONG ถ้าอยู่ใกล้ Demand Zone หรือมี CHoCH bullish

    เงื่อนไข SELL ใช้ตรงข้ามกัน
    """
    default = {
        "action":      "HOLD",
        "reason":      "ไม่มีสัญญาณ",
        "strength":    "WEAK",
        "near_demand": False,
        "near_supply": False,
        "bos":         None,
        "choch":       False,
    }

    # เช็คสถานะบอทก่อน
    if not state.get("bot_active", True):
        default["reason"] = "บอทถูกหยุดชั่วคราว (Kill Switch)"
        return default

    # เช็ค cooldown
    cooldown_remaining = state.get("cooldown_bars", 0)
    if cooldown_remaining > 0:
        default["reason"] = f"Cooldown {cooldown_remaining} แท่ง"
        return default

    # ถ้ามี position อยู่แล้ว — ไม่เปิดใหม่
    if state.get("in_position"):
        default["reason"] = "มี position อยู่แล้ว"
        return default

    df_clean = df[['ema_fast', 'ema_slow', 'adx', 'rsi']].dropna()
    if len(df_clean) < 3:
        default["reason"] = "ข้อมูลไม่พอ"
        return default

    # ดึงค่า indicator แท่งปิดล่าสุด (iloc[-2] เพราะ iloc[-1] อาจยังไม่ปิด)
    last_rsi = float(df_clean['rsi'].iloc[-2])

    crossover   = detect_ema_crossover(df)
    adx_ok      = check_adx_filter(df)

    # หา Supply/Demand zones
    zones       = find_supply_demand_zones(df, config.PIVOT_LENGTH)
    market      = detect_market_structure(df)
    price       = float(df['close'].iloc[-2])

    near_demand = check_near_zone(price, zones["demand"])
    near_supply = check_near_zone(price, zones["supply"])

    result = {
        "action":      "HOLD",
        "reason":      "",
        "strength":    "WEAK",
        "near_demand": near_demand,
        "near_supply": near_supply,
        "bos":         market["bos"],
        "choch":       market["choch"],
    }

    if crossover == "golden":
        if not adx_ok:
            result["reason"] = f"Golden Cross แต่ ADX ต่ำ (sideways)"
            return result
        if last_rsi >= config.RSI_OB:
            result["reason"] = f"Golden Cross แต่ RSI overbought ({last_rsi:.1f})"
            return result

        result["action"] = "BUY"
        result["reason"] = "EMA Golden Cross + ADX ผ่าน"

        # ยกระดับเป็น STRONG ถ้าเงื่อนไขเพิ่มเติมผ่าน
        strength_boosts = []
        if near_demand:
            strength_boosts.append("ใกล้ Demand Zone")
        if market["choch"] and market["bos"] == "bullish":
            strength_boosts.append("CHoCH Bullish")
        if market["bos"] == "bullish":
            strength_boosts.append("BoS Bullish")

        if len(strength_boosts) >= 1:
            result["strength"] = "STRONG"
            result["reason"] += " + " + " + ".join(strength_boosts)
        else:
            result["strength"] = "NORMAL"

    elif crossover == "death":
        if not adx_ok:
            result["reason"] = f"Death Cross แต่ ADX ต่ำ (sideways)"
            return result
        if last_rsi <= config.RSI_OS:
            result["reason"] = f"Death Cross แต่ RSI oversold ({last_rsi:.1f})"
            return result

        result["action"] = "SELL"
        result["reason"] = "EMA Death Cross + ADX ผ่าน"

        strength_boosts = []
        if near_supply:
            strength_boosts.append("ใกล้ Supply Zone")
        if market["choch"] and market["bos"] == "bearish":
            strength_boosts.append("CHoCH Bearish")
        if market["bos"] == "bearish":
            strength_boosts.append("BoS Bearish")

        if len(strength_boosts) >= 1:
            result["strength"] = "STRONG"
            result["reason"] += " + " + " + ".join(strength_boosts)
        else:
            result["strength"] = "NORMAL"

    else:
        result["reason"] = "ไม่มี EMA Crossover"

    return result


def get_trend_label(df: pd.DataFrame) -> str:
    """คืน label trend สำหรับแสดงผล: Bullish / Bearish / Sideways"""
    df_clean = df[['ema_fast', 'ema_slow', 'adx']].dropna()
    if len(df_clean) < 1:
        return "N/A"
    last = df_clean.iloc[-1]
    adx  = float(last['adx'])

    if adx < config.ADX_THRESHOLD:
        return "Sideways ~"
    return "Bullish ^" if last['ema_fast'] > last['ema_slow'] else "Bearish v"
