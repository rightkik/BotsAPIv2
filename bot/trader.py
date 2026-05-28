# ===================================================
# bot/trader.py — ส่งคำสั่งซื้อขายด้วย ccxt
#
# ไฟล์นี้มีหน้าที่:
#   create_exchange()           — สร้าง ccxt exchange object
#   get_balance()               — ดูยอดเงิน
#   place_market_order()        — ส่ง market order พร้อม retry
#   execute_signal()            — ประมวลผล signal และส่ง order
#   check_and_update_trailing() — ตรวจ SL/TP และ breakeven ทุก loop
#
# ใช้ ccxt แทน python-binance เพื่อ flexibility มากขึ้น
# ===================================================

import sys
import os
import time
import json
from datetime import datetime
from typing import Optional

import ccxt
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

import config
from bot.risk import (
    calculate_position_size,
    calculate_atr_sl_tp,
    check_sl_tp,
    should_move_to_breakeven,
    check_daily_kill_switch,
)


# ===================================================
# Exchange Setup
# ===================================================

def create_exchange(testnet: bool = None) -> ccxt.binance:
    """
    สร้าง ccxt.binance exchange object

    โหลด API key จาก .env เสมอ — ห้าม hardcode
    testnet=True → เชื่อมต่อ testnet.binance.vision
    testnet=False → เชื่อมต่อ Binance จริง (ระวัง!)
    """
    if testnet is None:
        testnet = config.USE_TESTNET

    exchange = ccxt.binance({
        'apiKey':  os.getenv('BINANCE_API_KEY', ''),
        'secret':  os.getenv('BINANCE_SECRET_KEY', ''),
        'options': {
            'defaultType': 'spot',
        },
        'enableRateLimit': True,  # ป้องกัน rate limit อัตโนมัติ
    })

    if testnet:
        exchange.set_sandbox_mode(True)

    return exchange


# ===================================================
# Balance
# ===================================================

def get_balance(exchange: ccxt.binance, currency: str = "USDT") -> float:
    """
    ดูยอดเงินคงเหลือใน spot wallet

    คืน 0.0 ถ้า API key ไม่มีสิทธิ์ Read หรือเกิด error
    (Testnet มักมีปัญหา 401 กับบาง permission)
    """
    try:
        balance = exchange.fetch_balance()
        return float(balance.get(currency, {}).get('free', 0.0))
    except ccxt.AuthenticationError:
        # Testnet API key ไม่มี Read permission — ไม่แสดง error รบกวน
        return 0.0
    except ccxt.NetworkError as e:
        print(f"❌ Network error ดู balance: {e}")
        return 0.0
    except Exception as e:
        print(f"❌ ดู balance ไม่ได้: {e}")
        return 0.0


# ===================================================
# Order Placement
# ===================================================

def place_market_order(
    exchange: ccxt.binance,
    symbol: str,
    side: str,
    quantity: float,
    dry_run: bool = False
) -> Optional[dict]:
    """
    ส่ง Market Order พร้อม retry 3 ครั้ง

    side = "buy" หรือ "sell"
    dry_run = True → แสดง log แต่ไม่ส่ง order จริง

    retry logic:
    - NetworkError: retry ทันที (max 3 ครั้ง)
    - RateLimitExceeded: exponential backoff (2s, 4s, 8s)
    - Other: raise ทันที

    คืน:
        dict: { id, price, amount, cost, timestamp }
        None: ถ้าล้มเหลวทุก retry
    """
    max_retries = 3
    delay       = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  Placing MARKET {side.upper()}: {quantity} {symbol}"
                  + (" [DRY RUN]" if dry_run else ""))

            if dry_run:
                # ดึงราคาตลาดเพื่อ simulate
                ticker = exchange.fetch_ticker(symbol)
                sim_price = ticker['last']
                return {
                    "id":        "DRY_RUN",
                    "price":     sim_price,
                    "amount":    quantity,
                    "cost":      sim_price * quantity,
                    "timestamp": datetime.now().isoformat(),
                }

            order = exchange.create_market_order(symbol, side, quantity)
            fill_price = float(order.get('average') or order.get('price') or 0)
            print(f"  ✅ {side.upper()} filled: {quantity} {symbol} @ ${fill_price:,.2f}"
                  f"  (id: {order.get('id', '')})")
            return {
                "id":        str(order.get('id', '')),
                "price":     fill_price,
                "amount":    float(order.get('amount', quantity)),
                "cost":      float(order.get('cost', fill_price * quantity)),
                "timestamp": datetime.now().isoformat(),
            }

        except ccxt.RateLimitExceeded:
            print(f"  ⚠️  Rate limit (attempt {attempt}/{max_retries}) — รอ {delay:.0f}s")
            time.sleep(delay)
            delay *= 2  # exponential backoff

        except ccxt.NetworkError as e:
            print(f"  ⚠️  Network error (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(delay)

        except ccxt.InsufficientFunds as e:
            print(f"  ❌ {side.upper()} failed: เงินไม่พอ — {e}")
            return None

        except ccxt.BaseError as e:
            print(f"  ❌ {side.upper()} failed: {e}")
            return None

    print(f"  ❌ {side.upper()} ล้มเหลวทุก {max_retries} ครั้ง")
    return None


# ===================================================
# Signal Execution
# ===================================================

def execute_signal(
    exchange: ccxt.binance,
    signal: dict,
    df,
    state: dict,
    dry_run: bool = False
) -> dict:
    """
    ประมวลผล signal และส่ง order ถ้าเงื่อนไขครบ

    BUY flow:
      1. get_balance
      2. คำนวณ ATR SL/TP
      3. คำนวณ position size ตาม risk %
      4. place_market_order("buy")
      5. อัปเดต state

    SELL (close long) flow:
      1. place_market_order("sell")
      2. คำนวณ PnL
      3. อัปเดต daily_pnl, consecutive_losses
      4. เช็ค kill switch
      5. เริ่ม cooldown

    คืน state ที่อัปเดตแล้ว
    """
    action = signal.get("action", "HOLD")

    if action == "BUY":
        balance = get_balance(exchange, "USDT")
        if balance <= 0:
            # Testnet balance ดึงไม่ได้ — ใช้ค่าสมมติเพื่อทดสอบ
            balance = 10000.0
            print(f"  ⚠️  ใช้ balance สมมติ ${balance:,.0f} (testnet permission)")

        atr_val = float(df['atr'].iloc[-2])
        price   = float(df['close'].iloc[-2])

        # คำนวณ SL ก่อน แล้วค่อยคำนวณ size
        levels   = calculate_atr_sl_tp(price, atr_val, "long")
        quantity = calculate_position_size(balance, price, levels["sl"])

        if quantity <= 0:
            print(f"  ⚠️  Position size = 0 — ข้าม BUY")
            return state

        result = place_market_order(exchange, config.SYMBOL, "buy", quantity, dry_run)
        if result is None:
            return state

        fill_price = result["price"]
        levels     = calculate_atr_sl_tp(fill_price, atr_val, "long")

        state.update({
            "in_position":     True,
            "direction":       "long",
            "entry_price":     fill_price,
            "quantity":        result["amount"],
            "entry_time":      result["timestamp"],
            "order_id":        result["id"],
            "stop_loss":       levels["sl"],
            "tp1":             levels["tp1"],
            "tp2":             levels["tp2"],
            "tp3":             levels["tp3"],
            "atr_at_entry":    atr_val,
            "breakeven_moved": False,
        })
        _save_state(state)

    elif action == "SELL" or (action == "CLOSE" and state.get("in_position")):
        if not state.get("in_position"):
            return state

        quantity = state.get("quantity", 0)
        result   = place_market_order(exchange, config.SYMBOL, "sell", quantity, dry_run)
        if result is None:
            return state

        fill_price  = result["price"]
        entry_price = state.get("entry_price", fill_price)
        pnl         = (fill_price - entry_price) * quantity

        # อัปเดต daily stats
        balance      = get_balance(exchange, "USDT") or 10000.0
        pnl_pct      = pnl / (entry_price * quantity)
        daily_pnl    = state.get("daily_pnl_usdt", 0.0) + pnl
        daily_pnl_pct = state.get("daily_pnl_pct", 0.0) + pnl_pct

        # นับ consecutive losses
        cons_losses = state.get("consecutive_losses", 0)
        if pnl < 0:
            cons_losses += 1
        else:
            cons_losses = 0

        state.update({
            "in_position":        False,
            "direction":          None,
            "entry_price":        0.0,
            "quantity":           0.0,
            "stop_loss":          None,
            "tp1":                None,
            "tp2":                None,
            "tp3":                None,
            "breakeven_moved":    False,
            "last_pnl":           pnl,
            "daily_pnl_usdt":     daily_pnl,
            "daily_pnl_pct":      daily_pnl_pct,
            "consecutive_losses": cons_losses,
            "cooldown_bars":      config.COOLDOWN_BARS,
        })

        check_daily_kill_switch(state)
        _save_state(state)

    return state


def check_and_update_trailing(
    exchange: ccxt.binance,
    current_price: float,
    state: dict,
    dry_run: bool = False
) -> dict:
    """
    เรียกทุก loop เพื่อตรวจ breakeven และ SL/TP hit

    ตรวจตามลำดับ:
    1. Should move to breakeven? → อัปเดต stop_loss
    2. SL/TP hit?                → ปิด position
    """
    if not state.get("in_position"):
        # ลด cooldown counter ทุก loop
        if state.get("cooldown_bars", 0) > 0:
            state["cooldown_bars"] -= 1
        return state

    # ตรวจ breakeven ก่อน
    if should_move_to_breakeven(current_price, state):
        old_sl = state.get("stop_loss")
        state["stop_loss"]       = state["entry_price"]
        state["breakeven_moved"] = True
        print(f"  📍 ย้าย SL → Breakeven @ ${state['entry_price']:,.2f}"
              f"  (เดิม: ${old_sl:,.2f})")
        _save_state(state)

    # ตรวจ SL/TP hit
    hit = check_sl_tp(current_price, state)
    if hit:
        print(f"\n  EXIT: {hit} hit @ ${current_price:,.2f}")
        close_signal = {"action": "CLOSE", "reason": hit, "strength": "NORMAL"}
        state = execute_signal(exchange, close_signal, None, state, dry_run)
        # log จาก execute_signal แล้ว

    return state


# ===================================================
# State Persistence
# ===================================================

def load_state(state_file: str = None) -> dict:
    """โหลด bot state จาก JSON file"""
    if state_file is None:
        state_file = config.STATE_FILE

    default = {
        "in_position":        False,
        "direction":          None,
        "entry_price":        0.0,
        "quantity":           0.0,
        "entry_time":         "",
        "order_id":           "",
        "stop_loss":          None,
        "tp1":                None,
        "tp2":                None,
        "tp3":                None,
        "atr_at_entry":       0.0,
        "breakeven_moved":    False,
        "bot_active":         True,
        "resume_time":        None,
        "daily_pnl_usdt":     0.0,
        "daily_pnl_pct":      0.0,
        "daily_reset_date":   datetime.now().strftime('%Y-%m-%d'),
        "consecutive_losses": 0,
        "cooldown_bars":      0,
        "last_pnl":           0.0,
    }

    if not os.path.exists(state_file):
        return default

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # merge กับ default เพื่อรองรับ field ใหม่ที่อาจยังไม่มี
        default.update(data)
        return default
    except Exception:
        return default


def _save_state(state: dict, state_file: str = None) -> None:
    """บันทึก state ลงไฟล์ JSON (overwrite ทุกครั้ง)"""
    if state_file is None:
        state_file = config.STATE_FILE

    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ บันทึก state ไม่ได้: {e}")


def reset_daily_stats(state: dict) -> dict:
    """
    รีเซ็ต daily PnL ทุกวันใหม่

    เรียกตอนต้น loop ทุกครั้ง — ตรวจวันที่เปลี่ยนหรือเปล่า
    """
    today = datetime.now().strftime('%Y-%m-%d')
    if state.get("daily_reset_date") != today:
        state["daily_pnl_usdt"]   = 0.0
        state["daily_pnl_pct"]    = 0.0
        state["daily_reset_date"] = today
        # resume บอทเมื่อวันใหม่ (ถ้า kill switch จาก 24hr ผ่านไปแล้ว)
        if not state.get("bot_active") and not state.get("resume_time"):
            state["bot_active"] = True
    return state
