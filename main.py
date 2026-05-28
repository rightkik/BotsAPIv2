# ===================================================
# main.py — จุดเริ่มต้นของ Binance Trading Bot (Upgraded)
#
# วิธีรัน:
#   py main.py --test     — ทดสอบ connection + แสดง balance
#   py main.py --dry-run  — รัน logic ครบ แต่ไม่ส่ง order จริง
#   py main.py --verbose  — รัน bot พร้อม log ละเอียด
#   py main.py            — รัน bot จริงบน Testnet
# ===================================================

import sys
import os
import time
import contextlib
import io as _io
from datetime import datetime, timezone

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import config
from bot.trader   import create_exchange, get_balance, execute_signal, check_and_update_trailing
from bot.trader   import load_state, reset_daily_stats
from bot.data     import get_ohlcv_ccxt
from bot.indicator import add_all_indicators
from bot.strategy  import get_signal, get_trend_label
from bot.risk      import check_daily_kill_switch, check_resume_time, should_stop_bot
from bot.logger    import log_signal, log_state, print_status, print_summary


# ===================================================
# Connection Test
# ===================================================

def run_test(exchange) -> None:
    """ทดสอบ connection + แสดง balance + ราคาปัจจุบัน"""
    print("=" * 55)
    print("   Binance Bot — Connection Test")
    print("=" * 55)

    # ทดสอบ public endpoint (ไม่ต้องใช้ API key)
    print("\n[1/3] ทดสอบการเชื่อมต่อ (public)...")
    try:
        ticker = exchange.fetch_ticker(config.SYMBOL)
        price  = ticker['last']
        chg24h = ticker.get('percentage', 0) or 0
        sign   = "+" if chg24h >= 0 else ""
        print(f"✅ เชื่อมต่อสำเร็จ! {config.SYMBOL} = ${price:,.2f}  ({sign}{chg24h:.2f}% 24hr)")
    except Exception as e:
        print(f"❌ เชื่อมต่อไม่ได้: {e}")
        sys.exit(1)

    # ทดสอบ private endpoint (ต้องใช้ API key)
    print("\n[2/3] ทดสอบ API key (private)...")
    balance = get_balance(exchange, "USDT")
    if balance > 0:
        print(f"✅ USDT balance: ${balance:,.2f}")
    else:
        print("⚠️  Balance = 0 หรือ API key ไม่มีสิทธิ์ Read")
        print("   (Testnet ต้องการ key จาก testnet.binance.vision)")

    # ทดสอบดึง OHLCV
    print(f"\n[3/3] ทดสอบดึง OHLCV {config.TIMEFRAME_MAIN}...")
    df = get_ohlcv_ccxt(exchange, config.SYMBOL, config.TIMEFRAME_MAIN, limit=60)
    if df is not None:
        print(f"✅ ได้ {len(df)} แท่ง  ({df.index[0].strftime('%Y-%m-%d')} ถึง {df.index[-1].strftime('%Y-%m-%d')})")
        df = add_all_indicators(df)
        last = df.iloc[-2]  # แท่งปิดล่าสุด
        print(f"   EMA{config.EMA_FAST}: ${last['ema_fast']:,.2f}  |  "
              f"EMA{config.EMA_SLOW}: ${last['ema_slow']:,.2f}  |  "
              f"ADX: {last['adx']:.1f}  |  RSI: {last['rsi']:.1f}  |  ATR: ${last['atr']:,.0f}")
    else:
        print("❌ ดึง OHLCV ไม่ได้")

    print("\n" + "=" * 55)
    print("  Test สำเร็จ — พร้อมรัน bot")
    print("  py main.py --dry-run  → ทดสอบ logic")
    print("  py main.py            → รัน bot จริง")
    print("=" * 55)


# ===================================================
# Sync to Candle Close
# ===================================================

def sync_to_candle_close(timeframe: str) -> None:
    """
    รอให้ครบแท่งเทียน แล้วค่อย loop ใหม่

    ดีกว่า sleep(3600) เพราะซิงค์กับเวลาปิดแท่งจริงของ Binance
    เช่น timeframe "1h": แท่งปิดตอน xx:00:00 UTC ทุกชั่วโมง
    """
    tf_seconds = {
        "1m": 60, "3m": 180, "5m": 300, "15m": 900,
        "30m": 1800, "1h": 3600, "2h": 7200, "4h": 14400,
        "6h": 21600, "12h": 43200, "1d": 86400,
    }
    period = tf_seconds.get(timeframe, 3600)

    now_ts      = int(datetime.now(timezone.utc).timestamp())
    next_close  = ((now_ts // period) + 1) * period
    wait_secs   = next_close - now_ts

    # เพิ่ม buffer 5 วินาทีเพื่อให้แท่งปิดแน่นอนก่อนดึงข้อมูล
    wait_secs += 5

    print(f"\n  ⏱ รอแท่ง {timeframe} ถัดไป: {wait_secs}s  "
          f"(ปิดตอน {datetime.fromtimestamp(next_close, tz=timezone.utc).strftime('%H:%M:%S')} UTC)")

    try:
        for remaining in range(wait_secs, 0, -1):
            print(f"\r  Next candle in {remaining:>5}s  |  Ctrl+C to stop", end='', flush=True)
            time.sleep(1)
        print()
    except KeyboardInterrupt:
        raise


# ===================================================
# Main Bot Loop
# ===================================================

def run_bot(exchange, dry_run: bool = False, verbose: bool = False) -> None:
    """
    Main trading loop — ทำงานจนกว่าจะ Ctrl+C

    ทุกรอบ:
      1. รีเซ็ต daily stats ถ้าเป็นวันใหม่
      2. เช็ค resume_time (kill switch หายหรือยัง)
      3. ดึง OHLCV ทั้ง MAIN และ ENTRY timeframe
      4. add_all_indicators ทั้งสอง
      5. check_and_update_trailing (SL/TP/breakeven)
      6. should_stop_bot — ถ้าต้องหยุด แสดงเวลา resume
      7. get_signal จาก MAIN TF
      8. ถ้า STRONG → ยืนยันด้วย ENTRY TF
      9. execute_signal
      10. log + print_status
      11. sync_to_candle_close
    """
    mode_label = "DRY RUN" if dry_run else ("TESTNET" if config.USE_TESTNET else "** LIVE **")

    print(f"\n{'=' * 55}")
    print(f"  TRADING BOT STARTED  |  {mode_label}")
    print(f"  Symbols   : {', '.join(config.SYMBOLS)}")
    print(f"  Strategy  : EMA{config.EMA_FAST}/EMA{config.EMA_SLOW} + ADX{config.ADX_THRESHOLD} + HTF({config.TIMEFRAME_HTF})")
    print(f"  SL/TP     : {config.ATR_SL_MULT}x ATR / {config.ATR_TP_MULT}x ATR")
    print(f"  Risk/Trade: {config.RISK_PER_TRADE*100:.0f}%  |  Kill Switch: {config.MAX_DAILY_LOSS_PCT*100:.0f}%/day")
    print(f"  Press Ctrl+C to stop")
    print(f"{'=' * 55}\n")

    # โหลด state แยกต่อ symbol
    states     = {sym: load_state(sym) for sym in config.SYMBOLS}
    loop_count = 0

    while True:
        loop_count += 1
        print(f"\n{'=' * 55}")
        print(f"  Loop #{loop_count}  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 55}")

        for sym in config.SYMBOLS:
            print(f"\n--- {sym} ---")
            state = states[sym]

            # --- 1. รีเซ็ต daily stats ---
            state = reset_daily_stats(state)

            # --- 2. เช็ค kill switch resume ---
            check_resume_time(state)

            # --- 3. ดึงข้อมูล OHLCV ---
            df_main = get_ohlcv_ccxt(exchange, sym, config.TIMEFRAME_MAIN, limit=200)
            if df_main is None:
                print(f"❌ ดึงข้อมูล {sym} MAIN TF ไม่ได้ — ข้ามรอบนี้")
                states[sym] = state
                continue

            df_entry = get_ohlcv_ccxt(exchange, sym, config.TIMEFRAME_ENTRY, limit=100)
            if df_entry is None:
                df_entry = df_main.copy()

            df_htf = get_ohlcv_ccxt(exchange, sym, config.TIMEFRAME_HTF, limit=100)

            # --- 4. คำนวณ indicators ---
            df_main  = add_all_indicators(df_main)
            df_entry = add_all_indicators(df_entry)
            if df_htf is not None:
                df_htf = add_all_indicators(df_htf)

            last      = df_main.iloc[-2]
            price     = float(df_main['close'].iloc[-1])
            indicators = {
                'ema_fast': float(last['ema_fast']),
                'ema_slow': float(last['ema_slow']),
                'adx':      float(last['adx']),
                'rsi':      float(last['rsi']),
                'atr':      float(last['atr']),
            }

            # --- 5. ตรวจ trailing SL/TP/breakeven ก่อนเสมอ ---
            state = check_and_update_trailing(exchange, price, state, dry_run, symbol=sym)

            # --- 6. เช็คว่าควรหยุดหรือเปล่า ---
            if should_stop_bot(state):
                _show_wait_and_resume(state)
                states[sym] = state
                continue

            # --- 7. Signal จาก MAIN TF (+ HTF filter) ---
            signal = get_signal(df_main, state, df_htf)

            # --- 8. Multi-TF Confirmation ---
            if signal['action'] in ("BUY", "SELL") and signal['strength'] == "STRONG":
                entry_signal = get_signal(df_entry, {"in_position": False, "bot_active": True, "cooldown_bars": 0})
                if entry_signal['action'] != signal['action']:
                    if verbose:
                        print(f"  ⚠️  Multi-TF ไม่ confirm: MAIN={signal['action']}, "
                              f"ENTRY={entry_signal['action']} — ลด strength เป็น NORMAL")
                    signal['strength'] = "NORMAL"
                    signal['reason']  += " (ENTRY TF ไม่ confirm)"

            # --- 9. Execute Signal ---
            if signal['action'] in ("BUY", "SELL"):
                state = execute_signal(exchange, signal, df_main, state, dry_run, symbol=sym)

            # --- 10. Log + Print Status ---
            print_status(state, price, signal, indicators, symbol=sym)
            log_signal(signal, indicators, price)
            log_state(state)

            if verbose:
                print(f"\n  Reason: {signal['reason']}")
                trend = get_trend_label(df_main)
                print(f"  Trend:  {trend}")

            states[sym] = state

        # --- 11. รอแท่งถัดไป (sync ครั้งเดียวสำหรับทุก symbol) ---
        try:
            print(f"\n  Trade log: {config.LOG_FILE}")
            sync_to_candle_close(config.TIMEFRAME_MAIN)
        except KeyboardInterrupt:
            print(f"\n\nBot stopped after {loop_count} loop(s).")
            print_summary()
            break


def _show_wait_and_resume(state: dict) -> None:
    """แสดงเวลา resume แล้วรอ 5 นาทีก่อน loop ใหม่"""
    resume_str = state.get("resume_time", "")
    if resume_str:
        try:
            rt = datetime.fromisoformat(resume_str)
            remaining = (rt - datetime.now()).total_seconds()
            print(f"  ⛔ Kill Switch active — resume ใน {remaining/3600:.1f}h ({rt.strftime('%H:%M:%S')})")
        except Exception:
            pass
    time.sleep(300)  # รอ 5 นาทีแล้ว loop ใหม่เช็ค resume


# ===================================================
# Entry Point
# ===================================================

def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv
    test    = "--test"    in sys.argv

    exchange = create_exchange(testnet=config.USE_TESTNET)

    if test:
        run_test(exchange)
        return

    if dry_run:
        print("🔶 DRY RUN mode — ไม่ส่ง order จริง")

    run_bot(exchange, dry_run=dry_run, verbose=verbose)


if __name__ == "__main__":
    main()
