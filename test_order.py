# ===================================================
# test_order.py — ทดสอบ BUY + SELL บน Testnet
# รัน: python test_order.py
# ===================================================

import sys
import time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from bot.trader import create_exchange, get_balance, place_market_order
from bot.logger import log_trade

TEST_SYMBOL   = "BTC/USDT"
TEST_QUANTITY = 0.001          # ~$73 ที่ราคาปัจจุบัน

def main():
    print("=" * 50)
    print("  Testnet Order Test — BUY then SELL")
    print("=" * 50)

    exchange = create_exchange(testnet=True)

    # 1. ดู balance ก่อน
    balance = get_balance(exchange, "USDT")
    print(f"\n[1] USDT Balance: ${balance:,.2f}")

    # 2. ดูราคาปัจจุบัน
    ticker = exchange.fetch_ticker(TEST_SYMBOL)
    price  = ticker['last']
    print(f"[2] {TEST_SYMBOL} Price: ${price:,.2f}")
    print(f"    Order value: ~${price * TEST_QUANTITY:,.2f}")

    # 3. BUY
    print(f"\n[3] Placing MARKET BUY {TEST_QUANTITY} {TEST_SYMBOL}...")
    buy = place_market_order(exchange, TEST_SYMBOL, "buy", TEST_QUANTITY, dry_run=False)
    if buy is None:
        print("❌ BUY failed — หยุด")
        return
    print(f"    Order ID : {buy['id']}")
    print(f"    Fill price: ${buy['price']:,.2f}")
    print(f"    Cost      : ${buy['cost']:,.2f}")

    # 4. รอ 2 วินาที
    print("\n    รอ 2 วินาที...")
    time.sleep(2)

    # 5. SELL
    print(f"\n[4] Placing MARKET SELL {TEST_QUANTITY} {TEST_SYMBOL}...")
    sell = place_market_order(exchange, TEST_SYMBOL, "sell", TEST_QUANTITY, dry_run=False)
    if sell is None:
        print("❌ SELL failed")
        return
    print(f"    Order ID : {sell['id']}")
    print(f"    Fill price: ${sell['price']:,.2f}")

    # 6. สรุป + log
    pnl     = (sell['price'] - buy['price']) * TEST_QUANTITY
    pnl_pct = pnl / (buy['price'] * TEST_QUANTITY)
    result  = "WIN" if pnl > 0 else ("BE" if pnl == 0 else "LOSS")

    print(f"\n[5] Result:")
    print(f"    BUY  @ ${buy['price']:,.2f}")
    print(f"    SELL @ ${sell['price']:,.2f}")
    print(f"    PnL  : {'+'if pnl>=0 else ''}{pnl:.4f} USDT  ({result})")

    log_trade({
        "symbol":          TEST_SYMBOL,
        "direction":       "long",
        "entry":           buy['price'],
        "exit":            sell['price'],
        "sl":              buy['price'] * 0.98,
        "tp2":             buy['price'] * 1.06,
        "quantity":        TEST_QUANTITY,
        "pnl_usdt":        pnl,
        "pnl_pct":         pnl_pct,
        "result":          result,
        "atr":             0,
        "adx":             0,
        "rsi":             0,
        "signal_strength": "TEST",
    })
    print(f"    บันทึก trade ลง trades.csv แล้ว")
    print(f"\n✅ Order test สำเร็จ — API ใช้งานได้ปกติ")

    balance_after = get_balance(exchange, "USDT")
    print(f"    USDT Balance after: ${balance_after:,.2f}")
    print("=" * 50)

if __name__ == "__main__":
    main()
