# 🤖 Binance Trading Bot — Claude Project Instructions

## Project Overview
This project builds an automated Binance trading bot with a dashboard using Python. The goal is to learn Python through building real trading tools — starting from data fetching, to strategy logic, backtesting, and live monitoring.

---

## My Background
- Previously traded on MetaTrader 4 via XM (Forex/CFD), stopped ~5-6 years ago
- Beginner in Python — learning through this project
- Familiar with basic trading concepts (MA, RSI, signals, Buy/Sell)
- Target market: Crypto via Binance (starting with BTC/USDT)

---

## Goals
1. Learn Python fundamentals through practical trading code
2. Build a working Binance trading bot (starting on Testnet)
3. Build a monitoring dashboard to visualize bot activity
4. Understand backtesting before risking real money
5. Eventually run the bot live with small capital ($10–$50 to start)

---

## Tech Stack
- **Language**: Python 3.11+
- **Editor**: VS Code
- **Key Libraries**: python-binance, pandas, numpy, matplotlib, flask or streamlit (dashboard)
- **Exchange**: Binance (Testnet first → Live later)
- **Version Control**: Git

---

## Project Phases

### Phase 1 — Setup & Connection (Week 1)
- Install Python, VS Code, libraries
- Connect to Binance API (read-only first)
- Fetch and display live prices

### Phase 2 — Data & Indicators (Week 2)
- Pull OHLCV historical data
- Calculate indicators: MA, RSI, Bollinger Bands
- Visualize with matplotlib

### Phase 3 — Bot Logic & Testnet (Week 3)
- Write signal logic (MA crossover to start)
- Paper trade on Binance Testnet
- Log all bot decisions to CSV

### Phase 4 — Backtesting (Week 4)
- Backtest strategy on 30–90 days of data
- Calculate PnL, win rate, drawdown
- Iterate on strategy

### Phase 5 — Dashboard (Month 2)
- Build monitoring dashboard (Streamlit)
- Show: live price, bot signals, open positions, PnL
- Add alerts (email or Line Notify)

### Phase 6 — Live Trading (Month 3+)
- Move from Testnet to live with small capital
- Add risk management: stop-loss, position sizing
- Monitor and tune strategy

---

## Coding Guidelines for Claude

### Always explain code in Thai
เพราะกำลังเรียนรู้ Python ไปพร้อมกัน ให้อธิบายทุก function และ logic เป็นภาษาไทย

### Code style
- ใส่ comment ภาษาไทยทุก block สำคัญ
- แยก config ออกจาก logic (ใช้ config.py หรือ .env)
- ทำ function เล็กๆ ชื่อชัดเจน อย่าเขียนยาวในที่เดียว
- ทุก function ให้มี docstring สั้นๆ

### Safety rules (สำคัญมาก)
- ห้ามใส่ API Key ในโค้ดโดยตรง — ใช้ .env เสมอ
- ห้ามเปิด Withdrawal permission บน API Key
- เริ่มบน Testnet เสมอ ก่อน go live
- มี stop-loss ทุกครั้งก่อนใช้เงินจริง

### File structure ให้ยึดตามนี้
```
binance-bot/
├── .env                  # API keys (ไม่ commit)
├── .gitignore
├── config.py             # ตั้งค่ากลยุทธ์
├── main.py               # จุดเริ่มต้นรัน bot
├── bot/
│   ├── client.py         # เชื่อมต่อ Binance
│   ├── strategy.py       # logic สัญญาณซื้อขาย
│   ├── trader.py         # ส่งคำสั่งซื้อขาย
│   └── logger.py         # บันทึก log
├── backtest/
│   ├── backtest.py       # รัน backtest
│   └── results/          # ผล backtest
├── dashboard/
│   └── app.py            # Streamlit dashboard
├── data/
│   └── logs/             # trade logs CSV
└── tests/
    └── test_strategy.py  # unit tests
```

---

## Strategy Starting Point
เริ่มด้วย MA Crossover ก่อน (ง่ายที่สุด เข้าใจง่าย)
- **BUY** เมื่อ MA5 ตัด MA20 ขึ้น (Golden Cross)
- **SELL** เมื่อ MA5 ตัด MA20 ลง (Death Cross)
- Pair: BTC/USDT
- Timeframe: 1 ชั่วโมง

---

## Questions to Ask Claude
เมื่อติดปัญหา ให้ถามแบบนี้เพื่อให้ได้คำตอบที่ดีที่สุด:
- "อธิบาย [function นี้] ให้เข้าใจก่อน แล้วค่อยเขียนโค้ด"
- "มีวิธีอื่นทำแบบนี้ไหม แบบไหนดีกว่า"
- "โค้ดนี้มีความเสี่ยงอะไรบ้าง"
- "เขียน test สำหรับ function นี้ให้ด้วย"
