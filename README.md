# BotsAPIv2 — SET Signal Monitor

> สแกนสัญญาณหุ้นไทย (SET) 27 ตัว แจ้งเตือนผ่าน Telegram อัตโนมัติ
> พัฒนาต่อจาก BNbotsAPI (Binance bot) — เปลี่ยน direction สู่ตลาดหุ้นไทย

---

## ภาพรวม

| รายการ | รายละเอียด |
|---|---|
| ตลาด | SET (หุ้นไทย) — ข้อมูลจาก Yahoo Finance (.BK) |
| Timeframe | Daily (1d) |
| Watchlist | 27 หุ้น (PTT, KBANK, BDMS, PTTEP, OR, LH, ...) |
| Signal | EMA20/EMA50 Crossover + ADX filter + Supply/Demand zones |
| Alert | Telegram Bot — BUY/SELL/ใกล้ zone |
| Dashboard | Streamlit — กราฟ + indicators ครบ |

---

## โครงสร้าง Project

```
BotsAPIv2/
├── .env                    # API keys (ห้าม commit!)
├── .env.example            # template
├── config.py               # ตั้งค่าทั้งหมด
├── monitor.py              # SET signal monitor loop
├── run_monitor.bat         # double-click รัน monitor
├── run_dashboard.bat       # double-click รัน dashboard
│
├── notifier/               # การแจ้งเตือน
│   └── telegram.py         # Telegram alert (BUY/SELL/approaching zone)
│
├── data/
│   ├── fetcher.py          # yfinance OHLCV (SET .BK symbols)
│   ├── cache/
│   │   └── signals.json    # latest signal ทุก symbol
│   └── logs/
│       └── alerts.csv      # Telegram alert history
│
├── bot/                    # Core logic (ใช้ร่วมกับ Binance bot เดิม)
│   ├── indicator.py        # EMA, ADX, RSI, ATR, Supply/Demand zones
│   └── strategy.py         # Signal logic
│
├── dashboard/
│   └── app.py              # Streamlit dashboard
│
└── backtest/               # Binance backtest engine (สำรองไว้)
    └── backtest.py
```

---

## Setup

### 1. ติดตั้ง Libraries

```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า .env

```bash
cp .env.example .env
# แก้ไข .env ใส่ค่าต่อไปนี้
```

```env
# Telegram Bot (สำหรับ alert)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Settrade (Phase 2 — ยังไม่ใช้)
# SETTRADE_APP_ID=
# SETTRADE_APP_SECRET=
```

> สร้าง Telegram bot ได้จาก [@BotFather](https://t.me/BotFather)

### 3. รัน Monitor

```bash
python monitor.py
```

หรือ double-click `run_monitor.bat`

### 4. รัน Dashboard

```bash
streamlit run dashboard/app.py
```

หรือ double-click `run_dashboard.bat` แล้วเปิด `http://localhost:8501`

---

## วิธีทำงาน

```
[ทุก 5 นาที]
      ↓
ดึง OHLCV 27 หุ้น (yfinance daily)
      ↓
คำนวณ EMA20/50, ADX, RSI, ATR, Supply/Demand zones
      ↓
ตรวจ signal ทุก symbol
      ↓
    BUY/SELL?          ใกล้ zone?
       ↓                   ↓
  Telegram alert     Telegram warning
       ↓
  บันทึก cache → data/cache/signals.json
       ↓
  Dashboard อ่าน cache แสดงผล real-time
```

---

## กลยุทธ์ที่ใช้

```
สัญญาณ BUY  — EMA20 ตัด EMA50 ขึ้น (Golden Cross) + ADX > 25
สัญญาณ SELL — EMA20 ตัด EMA50 ลง  (Death Cross)  + ADX > 25
```

กรอง False Signal ด้วย:
- ADX > 25 (มีเทรนด์พอ)
- Supply/Demand Zone awareness
- RSI filter (ไม่ Overbought/Oversold สุดขั้ว)

---

## Watchlist (27 หุ้น SET)

```
3BBIF  CPAXT  OSP    PTT    KBANK  WHA    TU     PTTEP
BDMS   HANN   TOP    IVL    TASCO  STGT   TISCO  LH
OR     RATCH  PACO   EGCO   SCC    ORI    HANA   BAM
BANPU  RCL    KKP
```

---

## Telegram Alert ตัวอย่าง

```
🟢 PTT — ซื้อ (BUY)
ราคา: 35.50 บาท
ความแรง: STRONG
เหตุผล: EMA Golden Cross + ADX=31.2
เวลา: 29/05 10:15

⚠️ ใกล้แนวรับ (Demand)
KBANK ราคา 142.00 บาท
เวลา: 29/05 09:30
```

---

## config.py — ค่าสำคัญ

```python
WATCHLIST        = [...]       # 27 หุ้น SET
TIMEFRAME        = "1d"        # daily
HISTORY_PERIOD   = "6mo"       # ย้อนหลัง 6 เดือน
EMA_FAST         = 20
EMA_SLOW         = 50
ADX_THRESHOLD    = 25
MONITOR_INTERVAL = 300         # เช็คทุก 5 นาที (วินาที)
ALERT_COOLDOWN_SEC = 14400     # ส่ง alert ซ้ำได้ทุก 4 ชั่วโมง
```

---

## กฎความปลอดภัย

| ห้ามทำ | ให้ทำ |
|---|---|
| ใส่ Telegram Token ในโค้ด | ใช้ .env เสมอ |
| Commit ไฟล์ .env | ใส่ .env ใน .gitignore |
| ส่ง order โดยอัตโนมัติโดยไม่ตรวจสอบ | monitor แจ้งเตือน, ตัดสินใจเองเสมอ |

---

## Libraries ที่ใช้

```
yfinance>=0.2.36      # ดึง OHLCV หุ้นไทย (Yahoo Finance .BK)
pandas>=2.2.0         # จัดการข้อมูล
numpy                 # คำนวณตัวเลข
streamlit>=1.32.0     # dashboard
plotly>=5.18.0        # กราฟแท่งเทียน
requests              # Telegram API
python-dotenv         # โหลด .env
```

---

## Roadmap

- [x] data/fetcher.py — yfinance batch download SET stocks
- [x] bot/indicator.py — EMA, ADX, RSI, ATR, Supply/Demand zones
- [x] bot/strategy.py — signal logic พร้อม ADX filter
- [x] monitor.py — background loop + Telegram alerts
- [x] dashboard/app.py — Streamlit SET Signal Monitor
- [x] run_*.bat launchers
- [ ] Settrade API — realtime price (Phase 2)
- [ ] Weekly HTF filter (TIMEFRAME_HTF = "1wk")
- [ ] Volume + RSI confirmation filter
- [ ] Dashboard grid view — BUY/SELL/HOLD ทุกหุ้นในหน้าเดียว
- [ ] Line OA / LINE Notify integration

---

> หมายเหตุ: Binance bot (Sessions 1-9) ยังอยู่ใน main.py / backtest/ สามารถรันได้ตามปกติ
> ดู dev_log.txt สำหรับประวัติการพัฒนาทั้งหมด
