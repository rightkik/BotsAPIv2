# BotsAPIv2 — Claude Project Instructions

## Project Overview
BotsAPIv2 เป็น SET Signal Monitor สำหรับหุ้นไทย — สแกนสัญญาณ EMA crossover + ADX filter บน 27 หุ้น SET ทุก 5 นาที และส่งแจ้งเตือนผ่าน Telegram

โปรเจกต์ fork มาจาก BNbotsAPI (Binance crypto bot) ซึ่งยังอยู่ครบใน repo นี้ แต่ทิศทางหลักตอนนี้คือ SET Signal Monitor

---

## My Background
- เคยเทรดบน MetaTrader 4 ผ่าน XM (Forex/CFD) หยุดไปประมาณ 5-6 ปีแล้ว
- Python ระดับกลาง — เรียนรู้ผ่านโปรเจกต์นี้ (เริ่มจาก Sessions 1-9)
- เข้าใจ concept การเทรด (MA, RSI, signal, Supply/Demand, SL/TP)
- ตลาดเป้าหมายปัจจุบัน: หุ้นไทย SET (ข้อมูลจาก yfinance .BK)

---

## Current Goals (ณ Session 10)
1. SET Signal Monitor ที่เสถียรและแจ้งเตือน Telegram ได้ถูกต้อง
2. Dashboard แสดงสัญญาณ 27 หุ้นแบบ real-time
3. Phase 2: เชื่อมต่อ Settrade API สำหรับ realtime price
4. ไม่มีแผน fully-automated order สำหรับตลาด SET — แจ้งเตือน แล้วตัดสินใจเอง

---

## Tech Stack
- **Language**: Python 3.10+
- **Editor**: VS Code
- **Data**: yfinance (Yahoo Finance, SET .BK symbols)
- **Dashboard**: Streamlit + Plotly
- **Alert**: Telegram Bot API
- **Indicators**: คำนวณเองใน bot/indicator.py (EMA, ADX, RSI, ATR, Supply/Demand)
- **Version Control**: Git → github.com/rightkik/BNbotsAPI

---

## Coding Guidelines

### ภาษา
- อธิบาย code เป็นภาษาไทย ทั้ง comment และคำอธิบาย
- ชื่อ function / variable เป็นภาษาอังกฤษ

### Code style
- ห้าม hardcode ค่าใดๆ — ดึงจาก config.py เสมอ
- function เล็ก มีชื่อชัดเจน
- comment อธิบาย WHY ไม่ใช่ WHAT

### Safety rules
- ห้ามใส่ Telegram token หรือ API key ในโค้ดโดยตรง — ใช้ .env เสมอ
- ห้าม commit .env จริง
- SET Monitor เป็น notification-only — ไม่ส่ง order อัตโนมัติ

---

## File Structure (ปัจจุบัน)
```
BotsAPIv2/
├── .env                    # keys (ห้าม commit)
├── .env.example            # template
├── config.py               # ตั้งค่าทั้งหมด
├── monitor.py              # SET signal monitor loop (entry point)
├── main.py                 # Binance bot (ระงับไว้ก่อน)
├── run_monitor.bat
├── run_dashboard.bat
├── notifier/
│   └── telegram.py         # Telegram alerts
├── data/
│   ├── fetcher.py          # yfinance OHLCV
│   ├── cache/signals.json  # latest signals (dashboard อ่าน)
│   └── logs/alerts.csv
├── bot/
│   ├── indicator.py        # indicators (ใช้ร่วม SET + Binance)
│   ├── strategy.py         # signal logic (ใช้ร่วม SET + Binance)
│   ├── risk.py             # risk management (Binance)
│   ├── trader.py           # ccxt order execution (Binance)
│   └── logger.py           # logging (Binance)
├── backtest/
│   └── backtest.py         # Binance backtest engine
└── dashboard/
    └── app.py              # Streamlit dashboard (SET Monitor)
```

---

## Key Config Values
```python
WATCHLIST        = [27 SET stocks]
TIMEFRAME        = "1d"          # daily
HISTORY_PERIOD   = "6mo"
EMA_FAST / SLOW  = 20 / 50
ADX_THRESHOLD    = 25
MONITOR_INTERVAL = 300           # 5 นาที
ALERT_COOLDOWN_SEC = 14400       # 4 ชั่วโมง
SIGNAL_CACHE     = "data/cache/signals.json"
```

---

## How to Run
```bash
python monitor.py                  # รัน SET signal loop
streamlit run dashboard/app.py     # เปิด dashboard
python main.py --dry-run           # ทดสอบ Binance bot logic
python backtest/backtest.py --days 90
```

---

## Questions to Ask Claude
เมื่อติดปัญหา ให้ถามแบบนี้:
- "อธิบาย [function นี้] ให้เข้าใจก่อน แล้วค่อยเขียนโค้ด"
- "มีวิธีอื่นทำแบบนี้ไหม แบบไหนดีกว่าสำหรับหุ้นไทย"
- "โค้ดนี้มีความเสี่ยงหรือ edge case อะไรบ้าง"

---

## ประวัติโปรเจกต์
ดู `dev_log.txt` — บันทึกทุก session ตั้งแต่ Session 1 (Binance bot setup) ถึง Session 10 (SET Monitor pivot)
