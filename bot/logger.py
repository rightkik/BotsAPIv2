# ===================================================
# bot/logger.py — บันทึก Log ทุกประเภท (Upgraded)
#
# ไฟล์นี้มีหน้าที่:
#   log_trade()    — บันทึก trade ลง CSV (ข้อมูลละเอียดขึ้น)
#   log_signal()   — บันทึกทุก signal ที่เกิด
#   log_state()    — snapshot state ทุก loop → JSONL
#   print_status() — แสดงสถานะแบบ box UI ใน terminal
# ===================================================

import csv
import json
import os
import sys
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config

# columns สำหรับ trades.csv
TRADE_FIELDS = [
    'timestamp', 'symbol', 'direction', 'entry', 'exit',
    'sl', 'tp2', 'quantity', 'pnl_usdt', 'pnl_pct',
    'result', 'atr', 'adx', 'rsi', 'signal_strength',
]

# columns สำหรับ signals.csv
SIGNAL_FIELDS = [
    'timestamp', 'symbol', 'action', 'strength', 'reason',
    'price', 'ema_fast', 'ema_slow', 'adx', 'rsi', 'atr',
    'near_demand', 'near_supply', 'bos', 'choch',
]


def log_trade(trade_data: dict) -> None:
    """
    บันทึก 1 trade (round-trip) ลงไฟล์ CSV

    เรียกหลังปิด position — ต้องมีทั้ง entry และ exit price

    trade_data keys ที่สำคัญ:
        symbol, direction, entry, exit, sl, tp2,
        quantity, pnl_usdt, pnl_pct, result (WIN/LOSS/BE),
        atr, adx, rsi, signal_strength
    """
    log_file = config.LOG_FILE
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_exists = os.path.exists(log_file)

    row = {
        'timestamp':      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol':         trade_data.get('symbol', config.SYMBOL),
        'direction':      trade_data.get('direction', 'long'),
        'entry':          round(trade_data.get('entry', 0), 2),
        'exit':           round(trade_data.get('exit', 0), 2),
        'sl':             round(trade_data.get('sl', 0), 2),
        'tp2':            round(trade_data.get('tp2', 0), 2),
        'quantity':       trade_data.get('quantity', 0),
        'pnl_usdt':       round(trade_data.get('pnl_usdt', 0), 4),
        'pnl_pct':        round(trade_data.get('pnl_pct', 0) * 100, 3),
        'result':         trade_data.get('result', 'UNKNOWN'),
        'atr':            round(trade_data.get('atr', 0), 2),
        'adx':            round(trade_data.get('adx', 0), 2),
        'rsi':            round(trade_data.get('rsi', 0), 2),
        'signal_strength': trade_data.get('signal_strength', 'NORMAL'),
    }

    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    sign = "+" if row['pnl_usdt'] >= 0 else ""
    result_icon = {"WIN": "✅", "LOSS": "❌", "BE": "⚖️"}.get(row['result'], "•")
    print(f"[TRADE] {result_icon} {row['direction'].upper()} {row['symbol']}"
          f"  {row['entry']:,.2f} → {row['exit']:,.2f}"
          f"  PnL: {sign}{row['pnl_usdt']:.2f} USDT ({sign}{row['pnl_pct']:.2f}%)")


def log_signal(signal: dict, indicators: dict, price: float) -> None:
    """
    บันทึกทุก signal ที่เกิด (รวม HOLD) ลง signals.csv

    ช่วยวิเคราะห์ย้อนหลังว่า signal เกิดบ่อยแค่ไหน
    และเงื่อนไขไหนที่ผ่าน/ไม่ผ่านบ่อย
    """
    log_file = config.SIGNAL_LOG
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_exists = os.path.exists(log_file)

    row = {
        'timestamp':  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol':     config.SYMBOL,
        'action':     signal.get('action', 'HOLD'),
        'strength':   signal.get('strength', 'WEAK'),
        'reason':     signal.get('reason', ''),
        'price':      round(price, 2),
        'ema_fast':   round(indicators.get('ema_fast', 0), 2),
        'ema_slow':   round(indicators.get('ema_slow', 0), 2),
        'adx':        round(indicators.get('adx', 0), 2),
        'rsi':        round(indicators.get('rsi', 0), 2),
        'atr':        round(indicators.get('atr', 0), 2),
        'near_demand': signal.get('near_demand', False),
        'near_supply': signal.get('near_supply', False),
        'bos':         signal.get('bos', ''),
        'choch':       signal.get('choch', False),
    }

    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SIGNAL_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def log_state(state: dict) -> None:
    """
    บันทึก state snapshot ทุก loop ลง JSONL (append)

    JSONL = JSON Lines — แต่ละบรรทัดคือ JSON object 1 ชุด
    ใช้ดู history ของ bot ย้อนหลังได้ละเอียด
    """
    log_file = config.STATE_HISTORY
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    snapshot = dict(state)
    snapshot['_logged_at'] = datetime.now().isoformat()

    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"❌ log_state ล้มเหลว: {e}")


def print_status(
    state: dict,
    price: float,
    signal: dict,
    indicators: dict
) -> None:
    """
    แสดงสถานะ bot แบบ box UI ใน terminal

    ┌─────────────────────────────────────────┐
    │  🤖 BINANCE BOT  │  BTC/USDT  │  1H    │
    ├─────────────────────────────────────────┤
    │  💰 ราคา: $67,420.50                    │
    │  📊 สัญญาณ: 🟢 BUY (STRONG)            │
    │  📈 EMA20: $67,100 │ EMA50: $66,800    │
    │  📉 ADX: 32.5  RSI: 58.3  ATR: $420   │
    ├─────────────────────────────────────────┤
    │  📍 Position: LONG @ $67,200           │
    │  🛑 SL: $66,570  🎯 TP2: $68,460      │
    │  💵 PnL วันนี้: +$2.30 (+2.3%)        │
    └─────────────────────────────────────────┘
    """
    now    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    width  = 47
    line   = "─" * width

    # Signal icon
    action  = signal.get('action', 'HOLD')
    strength = signal.get('strength', '')
    sig_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(action, "⚪")

    # Indicators
    ema_fast = indicators.get('ema_fast', 0)
    ema_slow = indicators.get('ema_slow', 0)
    adx      = indicators.get('adx', 0)
    rsi      = indicators.get('rsi', 0)
    atr      = indicators.get('atr', 0)

    # Bot status
    if not state.get('bot_active', True):
        bot_status = "⛔ Kill Switch"
    elif state.get('cooldown_bars', 0) > 0:
        bot_status = f"⏸ Cooldown ({state['cooldown_bars']} bars)"
    else:
        bot_status = "✅ Active"

    print(f"\n┌{line}┐")
    print(f"│  🤖 BINANCE BOT  │  {config.SYMBOL:<10}│  {config.TIMEFRAME_MAIN:<4}  │")
    print(f"│  {now}  │  {bot_status:<14}│")
    print(f"├{line}┤")
    print(f"│  💰 ราคา    : ${price:>12,.2f}                  │")
    print(f"│  📊 สัญญาณ  : {sig_icon} {action} ({strength})             │")
    print(f"│  📈 EMA{config.EMA_FAST:<3}  : ${ema_fast:>10,.2f}                    │")
    print(f"│  📈 EMA{config.EMA_SLOW:<3}  : ${ema_slow:>10,.2f}                    │")
    print(f"│  📉 ADX     : {adx:>6.1f}   RSI: {rsi:>5.1f}   ATR: ${atr:>6,.0f} │")

    if state.get('in_position'):
        entry    = state.get('entry_price', 0)
        qty      = state.get('quantity', 0)
        sl       = state.get('stop_loss') or 0
        tp2      = state.get('tp2') or 0
        pnl      = (price - entry) * qty
        pnl_pct  = (price - entry) / entry * 100 if entry > 0 else 0
        be_mark  = " [BE]" if state.get('breakeven_moved') else ""
        sign     = "+" if pnl >= 0 else ""

        print(f"├{line}┤")
        print(f"│  📍 Position: LONG @ ${entry:>10,.2f}{be_mark:<8}     │")
        print(f"│  🛑 SL      : ${sl:>10,.2f}                       │")
        print(f"│  🎯 TP2     : ${tp2:>10,.2f}                       │")
        print(f"│  💵 Float PnL: {sign}{pnl:>8,.2f} USDT  ({sign}{pnl_pct:.2f}%)     │")
    else:
        print(f"├{line}┤")
        print(f"│  📍 Position: ไม่มี position เปิดอยู่              │")

    # Daily PnL
    daily_pnl     = state.get('daily_pnl_usdt', 0.0)
    daily_pnl_pct = state.get('daily_pnl_pct', 0.0) * 100
    d_sign        = "+" if daily_pnl >= 0 else ""
    reason        = signal.get('reason', '')[:30]

    print(f"│  💵 PnL วันนี้: {d_sign}{daily_pnl:>7,.2f} USDT ({d_sign}{daily_pnl_pct:.2f}%)   │")
    print(f"│  📝 {reason:<43}│")
    print(f"└{line}┘")


def print_summary(log_file: str = None) -> None:
    """แสดงสรุปผลการเทรดจาก CSV"""
    if log_file is None:
        log_file = config.LOG_FILE

    if not os.path.exists(log_file):
        print("  ยังไม่มี trade ที่บันทึก")
        return

    with open(log_file, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("  ยังไม่มี trade ที่บันทึก")
        return

    wins   = [r for r in rows if r.get('result') == 'WIN']
    losses = [r for r in rows if r.get('result') == 'LOSS']
    bes    = [r for r in rows if r.get('result') == 'BE']
    total_pnl = sum(float(r.get('pnl_usdt', 0)) for r in rows)

    print(f"\n{'─'*40}")
    print(f"  Trade Summary")
    print(f"{'─'*40}")
    print(f"  Total trades : {len(rows)}")
    print(f"  WIN  : {len(wins)}   LOSS: {len(losses)}   BE: {len(bes)}")
    if rows:
        win_rate = len(wins) / len(rows) * 100
        print(f"  Win Rate     : {win_rate:.1f}%")
    sign = "+" if total_pnl >= 0 else ""
    print(f"  Total PnL    : {sign}{total_pnl:.2f} USDT")
    if rows:
        print(f"  Last trade   : {rows[-1].get('timestamp', '')}  "
              f"{rows[-1].get('direction', '').upper()} @ "
              f"${float(rows[-1].get('entry', 0)):,.2f}")
    print(f"{'─'*40}")
