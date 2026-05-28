# ===================================================
# bot/monitor.py — Live Terminal Monitor
#
# แสดงราคา, MA, RSI และ trend ของทุก symbol
# พร้อม countdown อัปเดตอัตโนมัติทุก N วินาที
#
# วิธีใช้: เรียกผ่าน main.py หรือ import run_monitor()
# หยุด: Ctrl+C
# ===================================================

import os
import sys
import time
from datetime import datetime
from typing import Optional

from binance.client import Client

from bot.client import get_price
from bot.data import get_ohlcv, calculate_ma, calculate_rsi

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

WIDTH = 58


def _get_trend(df, short: int, long: int) -> tuple[str, str]:
    """
    ตรวจสอบ trend และสัญญาณ crossover จาก MA สองเส้น

    เปรียบเทียบ MA เส้นสั้นกับยาวใน 2 แท่งล่าสุด:
    - ถ้าเพิ่งตัดขึ้น = Golden Cross (BUY signal)
    - ถ้าเพิ่งตัดลง  = Death Cross  (SELL signal)
    - ถ้าเส้นสั้น > ยาว = Bullish trend
    - ถ้าเส้นสั้น < ยาว = Bearish trend

    Returns:
        (trend_label, signal_label)
    """
    ma_s_now  = df[f'ma{short}'].iloc[-1]
    ma_l_now  = df[f'ma{long}'].iloc[-1]
    ma_s_prev = df[f'ma{short}'].iloc[-2]
    ma_l_prev = df[f'ma{long}'].iloc[-2]

    crossed_up   = ma_s_prev <= ma_l_prev and ma_s_now > ma_l_now
    crossed_down = ma_s_prev >= ma_l_prev and ma_s_now < ma_l_now

    if crossed_up:
        return "GOLDEN CROSS", "** BUY SIGNAL **"
    elif crossed_down:
        return "DEATH CROSS", "** SELL SIGNAL **"
    elif ma_s_now > ma_l_now:
        return "Bullish", "Hold / Watch"
    else:
        return "Bearish", "Hold / Watch"


def _rsi_label(rsi: float) -> str:
    """แปลงค่า RSI เป็น label พร้อม indicator"""
    if rsi >= 70:
        return f"{rsi:.1f}  [Overbought]"
    elif rsi <= 30:
        return f"{rsi:.1f}  [Oversold]"
    else:
        return f"{rsi:.1f}  [Normal]"


def _fetch_symbol_data(client: Client, symbol: str, interval: str,
                       ma_short: int, ma_long: int) -> Optional[dict]:
    """
    ดึงและประมวลผลข้อมูลทั้งหมดของ 1 symbol

    Returns:
        dict ที่มี price, ma_short, ma_long, rsi, trend, signal
        หรือ None ถ้า symbol ไม่มีในเซิร์ฟเวอร์นี้
    """
    price = get_price(client, symbol)
    if price is None:
        return None

    # ดึง OHLCV 3 วัน — suppress print เพื่อไม่รบกวน live display
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        df = get_ohlcv(client, symbol=symbol, interval=interval, days=3)
        if df is None or len(df) < ma_long + 2:
            return {"price": price, "error": "not enough data for indicators"}
        df = calculate_ma(df, short=ma_short, long=ma_long)
        df = calculate_rsi(df, period=14)

    trend, signal = _get_trend(df, ma_short, ma_long)

    return {
        "price":    price,
        "ma_short": df[f'ma{ma_short}'].iloc[-1],
        "ma_long":  df[f'ma{ma_long}'].iloc[-1],
        "rsi":      df['rsi'].iloc[-1],
        "trend":    trend,
        "signal":   signal,
    }


def _print_header(mode: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    print("=" * WIDTH)
    print(f"  BINANCE MONITOR  |  {mode}")
    print(f"  Updated: {now}")
    print("=" * WIDTH)


def _print_symbol_block(symbol: str, data: Optional[dict],
                        ma_short: int, ma_long: int) -> None:
    """แสดงข้อมูล 1 symbol"""
    print(f"\n  [{symbol}]")
    if data is None:
        print(f"    Price  : N/A  (not available on this server)")
        return

    if "error" in data:
        print(f"    Price  : ${data['price']:,.2f}")
        print(f"    Note   : {data['error']}")
        return

    # MA trend arrow
    arrow = "^" if data['ma_short'] > data['ma_long'] else "v"

    print(f"    Price  : ${data['price']:>12,.2f}")
    print(f"    MA{ma_short:<3}  : ${data['ma_short']:>12,.2f}")
    print(f"    MA{ma_long:<3}  : ${data['ma_long']:>12,.2f}  {arrow} {data['trend']}")
    print(f"    RSI14  : {_rsi_label(data['rsi'])}")
    print(f"    Signal : {data['signal']}")


def run_monitor(client: Client, symbols: list[str], interval: str = "1h",
                ma_short: int = 5, ma_long: int = 20,
                refresh_seconds: int = 60, mode_label: str = "Testnet") -> None:
    """
    วนลูป live monitoring — อัปเดตทุก refresh_seconds วินาที

    ทุกรอบ:
      1. Clear screen
      2. แสดง header + ข้อมูลทุก symbol
      3. countdown N วินาที แล้ววนซ้ำ

    หยุดด้วย Ctrl+C

    Args:
        client:          Binance Client
        symbols:         list ของ symbol เช่น ["BTCUSDT", "XAUUSDT"]
        interval:        timeframe สำหรับ OHLCV
        ma_short:        MA เส้นสั้น
        ma_long:         MA เส้นยาว
        refresh_seconds: ความถี่อัปเดต
        mode_label:      แสดงบน header ("Testnet" หรือ "LIVE")
    """
    print(f"\nStarting live monitor — {len(symbols)} symbol(s), refresh every {refresh_seconds}s")
    print("Press Ctrl+C to stop\n")
    time.sleep(1)

    while True:
        # --- ดึงข้อมูลทุก symbol (ก่อน clear เพื่อไม่ให้หน้าจอกระพริบ) ---
        results = {}
        for sym in symbols:
            results[sym] = _fetch_symbol_data(client, sym, interval, ma_short, ma_long)

        # --- แสดงผล ---
        os.system('cls' if os.name == 'nt' else 'clear')
        _print_header(mode_label)

        for sym in symbols:
            _print_symbol_block(sym, results[sym], ma_short, ma_long)

        print(f"\n{'-' * WIDTH}")

        # --- countdown ---
        try:
            for remaining in range(refresh_seconds, 0, -1):
                print(f"\r  Next update in {remaining:>3}s  |  Ctrl+C to stop", end='', flush=True)
                time.sleep(1)
            print()  # ขึ้นบรรทัดใหม่ก่อน loop ถัดไป

        except KeyboardInterrupt:
            print("\n\nMonitor stopped.")
            break
