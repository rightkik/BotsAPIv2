"""
monitor.py — Background signal loop สำหรับ SET ไทย

รัน:  python monitor.py
หยุด: Ctrl+C

ทุก MONITOR_INTERVAL วินาที:
  1. ดึง OHLCV ทุกตัวจาก yfinance (batch)
  2. คำนวณ indicators + signal
  3. บันทึก cache → data/cache/signals.json
  4. ส่ง Telegram เมื่อมีสัญญาณ BUY/SELL ใหม่
"""

import json
import os
import sys
import time
from datetime import datetime

import config
from bot.indicator import add_all_indicators
from bot.strategy  import get_signal
from data.fetcher  import fetch_all
from notifier      import telegram

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DUMMY_STATE = {"in_position": False, "bot_active": True, "cooldown_bars": 0}

# ติดตาม alert ล่าสุดต่อ symbol เพื่อกัน spam
_last_alert: dict[str, datetime] = {}
_last_approach: dict[str, datetime] = {}


def _cooldown_ok(store: dict, symbol: str) -> bool:
    last = store.get(symbol)
    if last is None:
        return True
    return (datetime.now() - last).total_seconds() >= config.ALERT_COOLDOWN_SEC


def process(ohlcv_map: dict[str, object]) -> list[dict]:
    results = []
    for symbol in config.WATCHLIST:
        df = ohlcv_map.get(symbol)
        if df is None or len(df) < config.EMA_SLOW + 10:
            results.append({"symbol": symbol, "error": "ข้อมูลไม่พอ"})
            continue

        try:
            df    = add_all_indicators(df)
            sig   = get_signal(df, DUMMY_STATE)
            last  = df.iloc[-2]    # แท่งปิดล่าสุดที่สมบูรณ์
            prev  = df.iloc[-3]
            price = float(df["close"].iloc[-1])
            chg   = (float(last["close"]) - float(prev["close"])) / float(prev["close"]) * 100

            row = {
                "symbol":        symbol,
                "price":         price,
                "price_chg_pct": round(chg, 2),
                "ema_fast":      round(float(last["ema_fast"]), 2),
                "ema_slow":      round(float(last["ema_slow"]), 2),
                "adx":           round(float(last["adx"]), 1),
                "rsi":           round(float(last["rsi"]), 1),
                "atr":           round(float(last["atr"]), 2),
                "signal":        sig["action"],
                "strength":      sig["strength"],
                "reason":        sig["reason"],
                "near_demand":   sig["near_demand"],
                "near_supply":   sig["near_supply"],
                "updated":       datetime.now().isoformat(),
            }
            results.append(row)

            # ── Telegram alerts ────────────────────────────
            action = sig["action"]
            if action in ("BUY", "SELL") and _cooldown_ok(_last_alert, symbol):
                telegram.alert_signal(symbol, action, price, sig["reason"], sig["strength"])
                _last_alert[symbol] = datetime.now()

            elif action == "HOLD":
                if sig["near_demand"] and _cooldown_ok(_last_approach, symbol):
                    telegram.alert_approaching(symbol, "demand", price)
                    _last_approach[symbol] = datetime.now()
                elif sig["near_supply"] and _cooldown_ok(_last_approach, symbol):
                    telegram.alert_approaching(symbol, "supply", price)
                    _last_approach[symbol] = datetime.now()

        except Exception as e:
            results.append({"symbol": symbol, "error": str(e)})

    return results


def save_cache(results: list[dict]):
    os.makedirs(os.path.dirname(config.SIGNAL_CACHE), exist_ok=True)
    with open(config.SIGNAL_CACHE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def _print_summary(results: list[dict]):
    buy  = [r["symbol"] for r in results if r.get("signal") == "BUY"]
    sell = [r["symbol"] for r in results if r.get("signal") == "SELL"]
    near = [r["symbol"] for r in results if r.get("near_demand") or r.get("near_supply")]
    err  = [r["symbol"] for r in results if "error" in r]

    print(f"  BUY  ({len(buy)}): {', '.join(buy) or '-'}")
    print(f"  SELL ({len(sell)}): {', '.join(sell) or '-'}")
    print(f"  NEAR ({len(near)}): {', '.join(near) or '-'}")
    if err:
        print(f"  ERR  ({len(err)}): {', '.join(err)}")


def run():
    print(f"SET Signal Monitor")
    print(f"  หุ้น: {len(config.WATCHLIST)} ตัว")
    print(f"  อัพเดท: ทุก {config.MONITOR_INTERVAL // 60} นาที")
    print(f"  Telegram: {'OK' if config.TELEGRAM_TOKEN else 'ไม่ได้ตั้งค่า'}\n")

    while True:
        now = datetime.now()
        print(f"[{now.strftime('%H:%M:%S')}] กำลังดึงข้อมูล...")

        ohlcv_map = fetch_all()
        print(f"  ดึงได้ {len(ohlcv_map)}/{len(config.WATCHLIST)} ตัว")

        results = process(ohlcv_map)
        save_cache(results)
        _print_summary(results)

        print(f"  บันทึก cache แล้ว → {config.SIGNAL_CACHE}")
        print(f"  ถัดไป: {config.MONITOR_INTERVAL // 60} นาที\n")

        time.sleep(config.MONITOR_INTERVAL)


if __name__ == "__main__":
    run()
