# ===================================================
# bot/risk.py — Risk Management ทั้งหมด
#
# ไฟล์นี้มีหน้าที่:
#   calculate_position_size() — คำนวณขนาด position ตาม % risk
#   calculate_atr_sl_tp()     — กำหนด SL/TP จาก ATR
#   check_sl_tp()             — ตรวจว่าราคาถึง level ไหน
#   should_move_to_breakeven()— ตรวจว่าควรย้าย SL ไป breakeven
#   check_daily_kill_switch() — ตรวจ daily loss limit
#   check_resume_time()       — ตรวจว่า kill switch หายแล้วหรือยัง
#   should_stop_bot()         — รวมทุกเงื่อนไขหยุด
# ===================================================

import sys
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config


def calculate_position_size(
    balance: float,
    entry_price: float,
    stop_loss_price: float,
    risk_pct: float = None
) -> float:
    """
    คำนวณขนาด position ให้เสียได้แค่ risk_pct ถ้า SL โดน

    สูตร: quantity = (balance × risk_pct) / |entry - SL|
    เช่น: balance=10000, risk=1%, entry=67000, SL=66000
          → quantity = 100 / 1000 = 0.1 BTC

    ต้องมี SL ก่อนเสมอ — ห้ามคำนวณ size โดยไม่รู้ SL
    """
    if risk_pct is None:
        risk_pct = config.RISK_PER_TRADE

    risk_amount = balance * risk_pct
    sl_distance = abs(entry_price - stop_loss_price)

    if sl_distance <= 0:
        return 0.0

    quantity = risk_amount / sl_distance
    # ปัดให้เป็น 3 ตำแหน่ง (ขั้นต่ำ BTC บน Binance)
    return round(quantity, 3)


def calculate_atr_sl_tp(
    entry_price: float,
    atr: float,
    direction: str,
    sl_mult: float = None,
    tp_mult: float = None
) -> dict:
    """
    คำนวณ SL และ TP targets จาก ATR

    direction = "long"  → SL อยู่ด้านล่าง, TP อยู่ด้านบน
    direction = "short" → SL อยู่ด้านบน,  TP อยู่ด้านล่าง

    คืน:
        sl  = entry ± (sl_mult × ATR)        → 1.5 ATR
        tp1 = entry ± (sl_mult × ATR)        → 1:1 RR (จุด breakeven)
        tp2 = entry ± (tp_mult × ATR)        → 1:2 RR (TP หลัก)
        tp3 = entry ± (tp_mult × 1.5 × ATR)  → 1:3 RR (TP สูงสุด)
    """
    if sl_mult is None:
        sl_mult = config.ATR_SL_MULT
    if tp_mult is None:
        tp_mult = config.ATR_TP_MULT

    sl_dist  = sl_mult * atr
    tp2_dist = tp_mult * atr
    tp3_dist = tp_mult * 1.5 * atr

    if direction == "long":
        return {
            "sl":  entry_price - sl_dist,
            "tp1": entry_price + sl_dist,    # 1:1 RR
            "tp2": entry_price + tp2_dist,   # 1:2 RR
            "tp3": entry_price + tp3_dist,   # 1:3 RR
        }
    else:  # short
        return {
            "sl":  entry_price + sl_dist,
            "tp1": entry_price - sl_dist,
            "tp2": entry_price - tp2_dist,
            "tp3": entry_price - tp3_dist,
        }


def check_sl_tp(current_price: float, state: dict) -> str | None:
    """
    ตรวจว่าราคาถึง level ไหนแล้ว

    ตรวจตามลำดับ: SL → TP1 → TP2 → TP3
    คืน string ของ level ที่ถึง หรือ None ถ้ายังไม่ถึงไหน
    """
    if not state.get("in_position"):
        return None

    direction = state.get("direction", "long")
    sl  = state.get("stop_loss")
    tp1 = state.get("tp1")
    tp2 = state.get("tp2")
    tp3 = state.get("tp3")

    if direction == "long":
        if sl  is not None and current_price <= sl:
            return "STOP_LOSS"
        if tp3 is not None and current_price >= tp3:
            return "TP3"
        if tp2 is not None and current_price >= tp2:
            return "TP2"
        if tp1 is not None and current_price >= tp1:
            return "TP1"
    else:  # short
        if sl  is not None and current_price >= sl:
            return "STOP_LOSS"
        if tp3 is not None and current_price <= tp3:
            return "TP3"
        if tp2 is not None and current_price <= tp2:
            return "TP2"
        if tp1 is not None and current_price <= tp1:
            return "TP1"

    return None


def should_move_to_breakeven(current_price: float, state: dict) -> bool:
    """
    ตรวจว่าควรย้าย SL ไปที่ entry (breakeven) หรือยัง

    เงื่อนไข:
    - มี position เปิดอยู่
    - ราคาถึง TP1 แล้ว (1:1 RR)
    - SL ยังอยู่ต่ำกว่า entry (ยังไม่ได้ย้าย)
    """
    if not state.get("in_position"):
        return False
    if state.get("breakeven_moved"):
        return False

    direction    = state.get("direction", "long")
    entry_price  = state.get("entry_price", 0)
    tp1          = state.get("tp1")

    if tp1 is None:
        return False

    if direction == "long":
        return current_price >= tp1
    else:
        return current_price <= tp1


def check_daily_kill_switch(state: dict) -> bool:
    """
    ตรวจ daily loss limit — ถ้าขาดทุนเกิน MAX_DAILY_LOSS_PCT ต่อวัน
    หยุดบอทและตั้ง resume_time = 24 ชั่วโมงข้างหน้า

    คืน True ถ้าเพิ่งโดน kill switch (ต้องหยุด)
    """
    daily_pnl_pct = state.get("daily_pnl_pct", 0.0)

    # ตรวจเฉพาะเมื่อยังไม่โดน kill switch
    if state.get("bot_active", True) and daily_pnl_pct <= -config.MAX_DAILY_LOSS_PCT:
        state["bot_active"]   = False
        state["resume_time"]  = (datetime.now() + timedelta(hours=24)).isoformat()
        print(f"\n⛔ KILL SWITCH: ขาดทุน {daily_pnl_pct*100:.2f}% วันนี้ — หยุดบอท 24 ชั่วโมง")
        print(f"   Resume at: {state['resume_time']}")
        return True

    return False


def check_resume_time(state: dict) -> bool:
    """
    ตรวจว่าครบ 24hr แล้วหรือยัง — ถ้าครบ resume บอทได้

    คืน True ถ้าบอท inactive แต่ถึงเวลา resume แล้ว
    """
    if state.get("bot_active", True):
        return False

    resume_str = state.get("resume_time")
    if not resume_str:
        return False

    try:
        resume_time = datetime.fromisoformat(resume_str)
        if datetime.now() >= resume_time:
            state["bot_active"]  = True
            state["resume_time"] = None
            print("✅ Kill switch หมดเวลา — บอทกลับมาทำงานแล้ว")
            return True
    except Exception:
        pass

    return False


def should_stop_bot(state: dict) -> bool:
    """
    รวมทุกเงื่อนไขที่ทำให้บอทต้องหยุด

    - bot_active = False (kill switch โดน และยังไม่ครบ 24hr)
    """
    if not state.get("bot_active", True):
        resume_str = state.get("resume_time", "")
        if resume_str:
            try:
                resume_time = datetime.fromisoformat(resume_str)
                remaining = (resume_time - datetime.now()).total_seconds()
                if remaining > 0:
                    print(f"  ⛔ Bot inactive — resume ใน {remaining/3600:.1f} ชั่วโมง")
                    return True
            except Exception:
                pass
        return True

    return False
