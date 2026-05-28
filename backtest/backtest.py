# ===================================================
# backtest/backtest.py — Backtesting Engine
#
# รันกลยุทธ์เดียวกับ main.py บนข้อมูลย้อนหลัง
# ดึงข้อมูลจาก Binance LIVE (ไม่ต้อง API key)
#
# วิธีรัน:
#   py backtest/backtest.py
#   py backtest/backtest.py --days 30
#   py backtest/backtest.py --symbol BTC/USDT --timeframe 4h
#
# ผลลัพธ์:
#   - Win Rate, PnL, Drawdown, Sharpe
#   - Equity curve PNG
#   - Trades CSV
# ===================================================

import sys
import os
import argparse
import csv
from datetime import datetime, date

import ccxt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # ไม่แสดงหน้าต่าง — บันทึกไฟล์อย่างเดียว
import matplotlib.pyplot as plt

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# เพิ่ม project root เข้า path เพื่อ import config และ bot
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from bot.indicator import add_all_indicators
from bot.strategy  import detect_ema_crossover, check_adx_filter
from bot.risk      import calculate_atr_sl_tp, calculate_position_size


# ===================================================
# Data Fetching — ใช้ LIVE Binance (public, ไม่ต้อง API key)
# ===================================================

def fetch_historical_data(
    symbol: str,
    timeframe: str,
    days: int
) -> pd.DataFrame:
    """
    ดึงข้อมูล OHLCV ย้อนหลัง N วัน จาก Binance LIVE (ไม่ต้อง key)

    ต้องใช้ข้อมูลจริงจาก live — Testnet มีข้อมูลสังเคราะห์ที่ไม่ใช่ราคาจริง
    ไม่มี API key = ดึงได้แค่ public historical data
    """
    print(f"📥 ดึงข้อมูล LIVE {symbol} {timeframe} ย้อนหลัง {days} วัน...")

    # instance แยกต่างหากสำหรับ backtest — ไม่ใช้ testnet
    exchange = ccxt.binance({'enableRateLimit': True})

    tf_seconds = {
        "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "4h": 14400, "1d": 86400
    }
    period    = tf_seconds.get(timeframe, 3600)
    limit_per = 1000  # Binance max per request
    total_bars = int(days * 86400 / period)

    all_bars = []
    since    = exchange.milliseconds() - days * 24 * 60 * 60 * 1000

    while len(all_bars) < total_bars:
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit_per)
        except Exception as e:
            print(f"❌ ดึงข้อมูลไม่ได้: {e}")
            break

        if not bars:
            break

        all_bars.extend(bars)
        since = bars[-1][0] + 1  # ต่อจากแท่งสุดท้าย

        # ป้องกัน infinite loop
        if len(bars) < limit_per:
            break

    if not all_bars:
        print("❌ ไม่มีข้อมูล")
        sys.exit(1)

    df = pd.DataFrame(all_bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms', utc=True)
    df.set_index('time', inplace=True)
    df = df[~df.index.duplicated(keep='first')]  # ลบ duplicate
    df = df.sort_index()

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    print(f"✅ ได้ {len(df)} แท่ง  ({df.index[0].date()} ถึง {df.index[-1].date()})")
    return df


# ===================================================
# Backtest Engine
# ===================================================

def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 10000.0,
    commission_pct: float = None
) -> dict:
    """
    จำลองการเทรดทุกแท่ง bar-by-bar

    เงื่อนไข:
    - เปิด position เมื่อ EMA Golden Cross + ADX ผ่าน + RSI < RSI_OB
    - ปิด position เมื่อ SL/TP โดน หรือ Death Cross
    - commission 0.1% ต่อ order (ซื้อ 1 + ขาย 1 = 0.2% รอบ)
    - ไม่ใช้ leverage
    """
    if commission_pct is None:
        commission_pct = config.BACKTEST_COMMISSION

    df = add_all_indicators(df.copy())

    capital   = initial_capital
    equity    = [capital]
    trades    = []
    in_pos    = False
    entry_px  = 0.0
    sl        = 0.0
    tp1 = tp2 = tp3 = 0.0
    qty       = 0.0
    entry_i   = 0
    be_moved  = False

    print(f"\n🔄 Backtest เริ่มต้น: ${initial_capital:,.0f}  commission: {commission_pct*100:.2f}%")

    for i in range(config.EMA_SLOW + 5, len(df) - 1):
        row  = df.iloc[i]
        prev = df.iloc[i - 1]
        candle_high = row['high']
        candle_low  = row['low']

        if in_pos:
            # ตรวจ SL/TP ภายในแท่ง (ใช้ high/low ของแท่ง)

            # ย้าย SL → breakeven เมื่อราคาถึง TP1
            if not be_moved and candle_high >= tp1:
                sl       = entry_px
                be_moved = True

            # ตรวจ SL โดน
            if candle_low <= sl:
                exit_px = sl
                pnl     = (exit_px - entry_px) * qty - commission_pct * exit_px * qty
                result  = "WIN" if pnl > 0 else ("BE" if abs(pnl) < 1 else "LOSS")
                capital += pnl
                trades.append(_make_trade(df.index[entry_i], df.index[i], entry_px, exit_px,
                                          qty, pnl, pnl / (entry_px * qty), result, row))
                in_pos = False
                equity.append(capital)
                continue

            # ตรวจ TP2 โดน
            if candle_high >= tp2:
                exit_px = tp2
                pnl     = (exit_px - entry_px) * qty - commission_pct * exit_px * qty
                capital += pnl
                trades.append(_make_trade(df.index[entry_i], df.index[i], entry_px, exit_px,
                                          qty, pnl, pnl / (entry_px * qty), "WIN", row))
                in_pos = False
                equity.append(capital)
                continue

            # ตรวจ Death Cross → ปิด position
            prev_ema_fast = df['ema_fast'].iloc[i - 1]
            prev_ema_slow = df['ema_slow'].iloc[i - 1]
            curr_ema_fast = row['ema_fast']
            curr_ema_slow = row['ema_slow']
            prev2_ema_fast = df['ema_fast'].iloc[i - 2]
            prev2_ema_slow = df['ema_slow'].iloc[i - 2]

            death = prev2_ema_fast >= prev2_ema_slow and prev_ema_fast < prev_ema_slow
            if death:
                exit_px = row['close']
                pnl     = (exit_px - entry_px) * qty - commission_pct * exit_px * qty
                result  = "WIN" if pnl > 0 else "LOSS"
                capital += pnl
                trades.append(_make_trade(df.index[entry_i], df.index[i], entry_px, exit_px,
                                          qty, pnl, pnl / (entry_px * qty), result, row))
                in_pos = False
                equity.append(capital)
            else:
                equity.append(capital)

        else:
            # ตรวจ Golden Cross + ADX + RSI
            prev2_ema_fast = df['ema_fast'].iloc[i - 2] if i >= 2 else 0
            prev2_ema_slow = df['ema_slow'].iloc[i - 2] if i >= 2 else 0
            prev_ema_fast  = df['ema_fast'].iloc[i - 1]
            prev_ema_slow  = df['ema_slow'].iloc[i - 1]

            golden = prev2_ema_fast <= prev2_ema_slow and prev_ema_fast > prev_ema_slow
            adx_ok = float(prev['adx']) > config.ADX_THRESHOLD if not pd.isna(prev['adx']) else False
            rsi_ok = float(prev['rsi']) < config.RSI_OB if not pd.isna(prev['rsi']) else False

            if golden and adx_ok and rsi_ok:
                entry_px = row['open']  # เปิดที่ราคา open ของแท่งถัดไป
                atr      = float(prev['atr'])
                levels   = calculate_atr_sl_tp(entry_px, atr, "long")
                sl   = levels["sl"]
                tp1  = levels["tp1"]
                tp2  = levels["tp2"]
                tp3  = levels["tp3"]
                qty  = calculate_position_size(capital, entry_px, sl)

                if qty > 0:
                    commission = commission_pct * entry_px * qty
                    capital   -= commission  # หัก commission ตอน buy
                    in_pos     = True
                    entry_i    = i
                    be_moved   = False

            equity.append(capital)

    # ปิด position ที่ค้างอยู่ตอนจบ backtest
    if in_pos:
        exit_px = df['close'].iloc[-1]
        pnl     = (exit_px - entry_px) * qty - commission_pct * exit_px * qty
        result  = "WIN" if pnl > 0 else "LOSS"
        capital += pnl
        trades.append(_make_trade(df.index[entry_i], df.index[-1], entry_px, exit_px,
                                  qty, pnl, pnl / (entry_px * qty), result, df.iloc[-1]))
        equity.append(capital)

    return {
        "trades":         trades,
        "equity":         equity,
        "initial_capital": initial_capital,
        "final_capital":   capital,
        "df":             df,
    }


def _make_trade(entry_time, exit_time, entry, exit_, qty, pnl, pnl_pct, result, row):
    return {
        "entry_time": entry_time,
        "exit_time":  exit_time,
        "entry":      round(entry, 2),
        "exit":       round(exit_, 2),
        "quantity":   round(qty, 4),
        "pnl_usdt":   round(pnl, 4),
        "pnl_pct":    round(pnl_pct * 100, 3),
        "result":     result,
        "adx":        round(float(row.get('adx', 0) or 0), 2),
        "rsi":        round(float(row.get('rsi', 0) or 0), 2),
        "atr":        round(float(row.get('atr', 0) or 0), 2),
    }


# ===================================================
# Stats Calculation
# ===================================================

def calculate_stats(results: dict) -> dict:
    """คำนวณ performance statistics จาก backtest results"""
    trades  = results["trades"]
    equity  = results["equity"]
    init_cap = results["initial_capital"]
    final_cap = results["final_capital"]

    if not trades:
        return {"error": "ไม่มี trade ใดเลย"}

    wins    = [t for t in trades if t["result"] == "WIN"]
    losses  = [t for t in trades if t["result"] == "LOSS"]
    bes     = [t for t in trades if t["result"] == "BE"]
    total_pnl = sum(t["pnl_usdt"] for t in trades)

    # Max Drawdown
    eq_arr  = np.array(equity)
    peak    = np.maximum.accumulate(eq_arr)
    dd      = (eq_arr - peak) / peak
    max_dd  = float(dd.min()) * 100

    # Sharpe Ratio (simplified, annualized)
    pnl_arr = np.array([t["pnl_usdt"] for t in trades])
    if len(pnl_arr) > 1 and pnl_arr.std() > 0:
        sharpe = (pnl_arr.mean() / pnl_arr.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Best / Worst trade
    best  = max(trades, key=lambda t: t["pnl_usdt"])
    worst = min(trades, key=lambda t: t["pnl_usdt"])

    return {
        "total_trades":   len(trades),
        "wins":           len(wins),
        "losses":         len(losses),
        "bes":            len(bes),
        "win_rate":       len(wins) / len(trades) * 100 if trades else 0,
        "total_pnl_usdt": round(total_pnl, 2),
        "total_pnl_pct":  round((final_cap - init_cap) / init_cap * 100, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio":   round(sharpe, 3),
        "best_trade":     best,
        "worst_trade":    worst,
        "initial_capital": init_cap,
        "final_capital":   round(final_cap, 2),
    }


def print_stats(stats: dict) -> None:
    """แสดงสรุปผล backtest ใน terminal"""
    if "error" in stats:
        print(f"❌ {stats['error']}")
        return

    sign = "+" if stats["total_pnl_usdt"] >= 0 else ""

    print(f"\n{'=' * 50}")
    print(f"  BACKTEST RESULTS")
    print(f"{'=' * 50}")
    print(f"  Initial Capital : ${stats['initial_capital']:>10,.2f}")
    print(f"  Final Capital   : ${stats['final_capital']:>10,.2f}")
    print(f"  Total PnL       : {sign}${stats['total_pnl_usdt']:>9,.2f}  ({sign}{stats['total_pnl_pct']:.2f}%)")
    print(f"  {'─' * 40}")
    print(f"  Total Trades    : {stats['total_trades']}")
    print(f"  WIN / LOSS / BE : {stats['wins']} / {stats['losses']} / {stats['bes']}")
    print(f"  Win Rate        : {stats['win_rate']:.1f}%")
    print(f"  Max Drawdown    : {stats['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe Ratio    : {stats['sharpe_ratio']:.3f}")
    print(f"  {'─' * 40}")
    best  = stats['best_trade']
    worst = stats['worst_trade']
    print(f"  Best Trade      : +${best['pnl_usdt']:,.2f}  @ {best['entry_time'].strftime('%Y-%m-%d')}")
    print(f"  Worst Trade     : ${worst['pnl_usdt']:,.2f}  @ {worst['entry_time'].strftime('%Y-%m-%d')}")
    print(f"{'=' * 50}")


# ===================================================
# Save Results
# ===================================================

def save_results(results: dict, stats: dict, symbol: str, timeframe: str) -> None:
    """บันทึก equity curve PNG และ trades CSV"""
    os.makedirs(config.BACKTEST_DIR, exist_ok=True)
    date_str = date.today().strftime('%Y%m%d')

    # Equity Curve
    eq_path = os.path.join(config.BACKTEST_DIR, f"equity_{date_str}.png")
    equity  = results["equity"]

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#16213e')
    ax.plot(equity, color='#F0B90B', linewidth=1.5, label='Equity')
    ax.axhline(results["initial_capital"], color='#7f8c8d', linestyle='--', linewidth=0.8, alpha=0.6)
    ax.set_title(f'Equity Curve — {symbol} {timeframe}  ({date_str})',
                 color='white', fontsize=12, pad=10)
    ax.set_ylabel('USDT', color='#aaaaaa')
    ax.set_xlabel('Bar #', color='#aaaaaa')
    ax.tick_params(colors='#aaaaaa')
    ax.legend(facecolor='#1a1a2e', labelcolor='white')
    ax.grid(color='#2a2a4a', linestyle='--', linewidth=0.5, alpha=0.5)
    for spine in ax.spines.values():
        spine.set_edgecolor('#2a2a4a')

    if stats.get("total_pnl_pct") is not None:
        sign = "+" if stats["total_pnl_pct"] >= 0 else ""
        ax.text(0.02, 0.95,
                f"PnL: {sign}{stats['total_pnl_pct']:.2f}%  |  Win: {stats['win_rate']:.0f}%  |  "
                f"DD: {stats['max_drawdown_pct']:.1f}%  |  Sharpe: {stats['sharpe_ratio']:.2f}",
                transform=ax.transAxes, color='#F0B90B', fontsize=9, va='top')

    plt.tight_layout()
    plt.savefig(eq_path, dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close()
    print(f"💾 Equity curve: {eq_path}")

    # Trades CSV
    trades_path = os.path.join(config.BACKTEST_DIR, f"trades_{date_str}.csv")
    fields = ['entry_time', 'exit_time', 'entry', 'exit', 'quantity',
              'pnl_usdt', 'pnl_pct', 'result', 'adx', 'rsi', 'atr']
    with open(trades_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for t in results["trades"]:
            writer.writerow({k: t.get(k, '') for k in fields})
    print(f"💾 Trades CSV: {trades_path}")


# ===================================================
# CLI Entry Point
# ===================================================

def main():
    parser = argparse.ArgumentParser(description="Backtest Trading Strategy")
    parser.add_argument('--days',      type=int,   default=config.BACKTEST_DAYS, help="จำนวนวันย้อนหลัง")
    parser.add_argument('--symbol',    type=str,   default=config.SYMBOL,        help="Symbol เช่น BTC/USDT")
    parser.add_argument('--timeframe', type=str,   default=config.TIMEFRAME_MAIN, help="Timeframe เช่น 1h, 4h")
    parser.add_argument('--capital',   type=float, default=10000.0,              help="เงินทุนเริ่มต้น USDT")
    args = parser.parse_args()

    print(f"\n{'=' * 50}")
    print(f"  BACKTEST ENGINE")
    print(f"  Symbol: {args.symbol}  TF: {args.timeframe}  Days: {args.days}")
    print(f"  Capital: ${args.capital:,.0f}")
    print(f"{'=' * 50}")

    df      = fetch_historical_data(args.symbol, args.timeframe, args.days)
    results = run_backtest(df, initial_capital=args.capital)
    stats   = calculate_stats(results)

    print_stats(stats)
    save_results(results, stats, args.symbol, args.timeframe)


if __name__ == "__main__":
    main()
