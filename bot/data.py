# ===================================================
# bot/data.py — ดึงข้อมูลราคาและคำนวณ Indicators
#
# ไฟล์นี้มีหน้าที่ 4 อย่าง:
#   1. get_ohlcv()      — ดึงข้อมูลแท่งเทียน OHLCV จาก Binance
#   2. calculate_ma()   — คำนวณ Moving Average เส้นสั้นและยาว
#   3. calculate_rsi()  — คำนวณ RSI 14 (momentum indicator)
#   4. plot_chart()     — วาดกราฟราคาพร้อม MA และ RSI แล้วบันทึกไฟล์
#
# OHLCV = Open, High, Low, Close, Volume (ข้อมูลพื้นฐานแท่งเทียน)
# ===================================================

import os
import sys
from typing import Optional

import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from binance.client import Client
from binance.exceptions import BinanceAPIException

# แก้ปัญหา Windows terminal ไม่แสดงภาษาไทย
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def get_ohlcv(
    client: Client,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    days: int = 30
) -> Optional[pd.DataFrame]:
    """
    ดึงข้อมูลแท่งเทียน OHLCV ย้อนหลัง N วัน

    เรียก get_historical_klines() จาก Binance แล้วแปลงเป็น DataFrame
    แต่ละแถว = 1 แท่งเทียน มี Open, High, Low, Close, Volume

    Args:
        client:   Binance Client
        symbol:   คู่เหรียญ เช่น "BTCUSDT"
        interval: ความถี่แท่งเทียน เช่น "1h", "4h", "1d"
        days:     จำนวนวันย้อนหลัง

    Returns:
        DataFrame: ข้อมูล OHLCV พร้อม index เป็น datetime
                   หรือ None ถ้าดึงไม่ได้
    """
    try:
        print(f"📥 ดึงข้อมูล {symbol} {interval} ย้อนหลัง {days} วัน...")

        # ดึงข้อมูลจาก Binance — แต่ละ kline คือ list 12 ค่า
        raw = client.get_historical_klines(
            symbol,
            interval,
            f"{days} day ago UTC"
        )

        if not raw:
            print("❌ ไม่มีข้อมูลจาก Binance")
            return None

        # แปลงเป็น DataFrame — เลือกแค่ 6 คอลัมน์ที่ใช้จริง
        df = pd.DataFrame(raw, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])

        # แปลงประเภทข้อมูล — Binance ส่งมาเป็น string ทั้งหมด
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # ตั้ง time เป็น index เพื่อใช้กับ matplotlib ได้สะดวก
        df.set_index('time', inplace=True)

        # เก็บเฉพาะคอลัมน์ที่จำเป็น
        df = df[['open', 'high', 'low', 'close', 'volume']]

        print(f"✅ ได้ข้อมูล {len(df)} แท่งเทียน "
              f"({df.index[0].strftime('%Y-%m-%d')} ถึง {df.index[-1].strftime('%Y-%m-%d')})")
        return df

    except BinanceAPIException as e:
        if "Invalid symbol" in str(e.message):
            return None  # symbol ไม่มีใน server นี้ — handle โดย caller
        print(f"❌ Binance API Error {e.status_code}: {e.message}")
        return None
    except Exception as e:
        print(f"❌ ดึงข้อมูลไม่ได้: {e}")
        return None


def get_ohlcv_ccxt(
    exchange: ccxt.Exchange,
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    limit: int = 200,
) -> Optional[pd.DataFrame]:
    """
    ดึงข้อมูล OHLCV ด้วย ccxt

    ใช้กับ main bot loop (upgraded)
    exchange = ccxt.binance object จาก create_exchange()
    limit    = จำนวนแท่งเทียนล่าสุด (200 แท่งพอสำหรับ EMA50 + buffer)

    คืน DataFrame ที่มี index เป็น datetime UTC
    """
    try:
        raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not raw:
            return None

        df = pd.DataFrame(raw, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='ms', utc=True)
        df.set_index('time', inplace=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df

    except ccxt.NetworkError as e:
        print(f"❌ Network error ดึง OHLCV {symbol}: {e}")
        return None
    except ccxt.BaseError as e:
        print(f"❌ ccxt error ดึง OHLCV {symbol}: {e}")
        return None
    except Exception as e:
        print(f"❌ ดึง OHLCV ไม่ได้: {e}")
        return None


def calculate_ma(df: pd.DataFrame, short: int = 5, long: int = 20) -> pd.DataFrame:
    """
    คำนวณ Moving Average 2 เส้นและเพิ่มเข้า DataFrame

    MA = ค่าเฉลี่ยราคาปิด N แท่งที่ผ่านมา
    MA เส้นสั้น (fast) ตอบสนองไวต่อราคา
    MA เส้นยาว (slow) แสดงแนวโน้มหลัก

    ใช้สัญญาณ:
      Golden Cross: MA_short ตัด MA_long ขึ้น = BUY
      Death Cross:  MA_short ตัด MA_long ลง  = SELL

    Args:
        df:    DataFrame ที่มีคอลัมน์ 'close'
        short: จำนวนแท่งสำหรับ MA เส้นสั้น (default 5)
        long:  จำนวนแท่งสำหรับ MA เส้นยาว  (default 20)

    Returns:
        DataFrame: เพิ่มคอลัมน์ 'ma_short' และ 'ma_long'
    """
    # rolling(n).mean() = ค่าเฉลี่ยของ n แท่งที่ผ่านมา
    df[f'ma{short}'] = df['close'].rolling(window=short).mean()
    df[f'ma{long}'] = df['close'].rolling(window=long).mean()

    print(f"📊 MA{short} ล่าสุด: ${df[f'ma{short}'].iloc[-1]:,.2f}")
    print(f"📊 MA{long} ล่าสุด: ${df[f'ma{long}'].iloc[-1]:,.2f}")
    return df


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    คำนวณ RSI (Relative Strength Index) และเพิ่มเข้า DataFrame

    RSI วัดความแรงของแนวโน้มราคา ค่าอยู่ระหว่าง 0-100
      RSI > 70 = Overbought (ซื้อมากไป — อาจลง)
      RSI < 30 = Oversold   (ขายมากไป — อาจขึ้น)
      RSI ~ 50 = สมดุล

    สูตร: RSI = 100 - (100 / (1 + RS))
          RS  = ค่าเฉลี่ยวันที่ราคาขึ้น / ค่าเฉลี่ยวันที่ราคาลง

    Args:
        df:     DataFrame ที่มีคอลัมน์ 'close'
        period: จำนวนแท่งสำหรับคำนวณ (มาตรฐาน = 14)

    Returns:
        DataFrame: เพิ่มคอลัมน์ 'rsi'
    """
    # หาการเปลี่ยนแปลงราคาแต่ละแท่ง
    delta = df['close'].diff()

    # แยกวันที่ราคาขึ้น (gain) และลง (loss)
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # ค่าเฉลี่ยแบบ Exponential (ให้น้ำหนักข้อมูลล่าสุดมากกว่า)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    rsi_now = df['rsi'].iloc[-1]
    if rsi_now > 70:
        zone = "Overbought ⚠️"
    elif rsi_now < 30:
        zone = "Oversold ⚠️"
    else:
        zone = "ปกติ"
    print(f"📊 RSI{period} ล่าสุด: {rsi_now:.1f} ({zone})")
    return df


def plot_chart(df: pd.DataFrame, symbol: str = "BTCUSDT", save_dir: str = "data/logs") -> str:
    """
    วาดกราฟราคาพร้อมเส้น MA และ RSI แล้วบันทึกเป็นไฟล์ PNG

    Layout:
      - บนสุด (70%): กราฟราคา Close พร้อม MA5 และ MA20
      - ล่าง  (30%): RSI พร้อมเส้น Overbought/Oversold

    Args:
        df:       DataFrame ที่มี close, ma5, ma20, rsi
        symbol:   ชื่อคู่เหรียญสำหรับ title
        save_dir: โฟลเดอร์บันทึกไฟล์

    Returns:
        str: path ของไฟล์ที่บันทึก
    """
    # สร้างโฟลเดอร์ถ้ายังไม่มี
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{symbol}_chart.png")

    # กำหนดขนาดกราฟและแบ่ง subplot
    fig, (ax1, ax2) = plt.subplots(
        2, 1,
        figsize=(14, 8),
        gridspec_kw={'height_ratios': [7, 3]},
        sharex=True
    )
    fig.patch.set_facecolor('#1a1a2e')

    # --- subplot บน: ราคาและ MA ---
    ax1.set_facecolor('#16213e')
    ax1.plot(df.index, df['close'], color='#e0e0e0', linewidth=1.0, label='Close', alpha=0.9)

    # วาด MA เฉพาะที่มีค่า (ช่วงแรกจะเป็น NaN)
    ma_cols = [c for c in df.columns if c.startswith('ma')]
    colors = ['#f39c12', '#3498db', '#e74c3c', '#2ecc71']
    for i, col in enumerate(ma_cols):
        ax1.plot(df.index, df[col], color=colors[i % len(colors)],
                 linewidth=1.5, label=col.upper(), alpha=0.85)

    ax1.set_title(f'{symbol} — Price & Moving Average', color='white', fontsize=13, pad=10)
    ax1.set_ylabel('Price (USDT)', color='#aaaaaa')
    ax1.tick_params(colors='#aaaaaa')
    ax1.legend(loc='upper left', facecolor='#1a1a2e', labelcolor='white', fontsize=9)
    ax1.grid(color='#2a2a4a', linestyle='--', linewidth=0.5, alpha=0.7)
    for spine in ax1.spines.values():
        spine.set_edgecolor('#2a2a4a')

    # --- subplot ล่าง: RSI ---
    ax2.set_facecolor('#16213e')
    if 'rsi' in df.columns:
        ax2.plot(df.index, df['rsi'], color='#9b59b6', linewidth=1.3, label='RSI 14')
        ax2.axhline(70, color='#e74c3c', linestyle='--', linewidth=0.8, alpha=0.7, label='Overbought (70)')
        ax2.axhline(30, color='#2ecc71', linestyle='--', linewidth=0.8, alpha=0.7, label='Oversold (30)')
        ax2.axhline(50, color='#7f8c8d', linestyle=':', linewidth=0.6, alpha=0.5)
        ax2.fill_between(df.index, df['rsi'], 70,
                         where=(df['rsi'] >= 70), alpha=0.15, color='#e74c3c')
        ax2.fill_between(df.index, df['rsi'], 30,
                         where=(df['rsi'] <= 30), alpha=0.15, color='#2ecc71')
        ax2.set_ylim(0, 100)
        ax2.set_ylabel('RSI (14)', color='#aaaaaa')
        ax2.legend(loc='upper left', facecolor='#1a1a2e', labelcolor='white', fontsize=8)

    ax2.tick_params(colors='#aaaaaa')
    ax2.grid(color='#2a2a4a', linestyle='--', linewidth=0.5, alpha=0.7)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    for spine in ax2.spines.values():
        spine.set_edgecolor('#2a2a4a')

    plt.xticks(rotation=45, color='#aaaaaa')
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close()

    print(f"💾 บันทึกกราฟไว้ที่: {save_path}")
    return save_path
