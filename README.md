# 🤖 Binance Trading Bot + Dashboard

> Python trading bot สำหรับ Binance พร้อม monitoring dashboard  
> สร้างขึ้นเพื่อเรียนรู้ Python และ Algorithmic Trading ไปพร้อมกัน

---

## 📁 โครงสร้าง Project

```
binance-bot/
├── .env                      # 🔑 API Keys (ห้าม commit!)
├── .env.example              # ตัวอย่าง .env
├── .gitignore
├── requirements.txt          # Python libraries
├── config.py                 # ตั้งค่ากลยุทธ์และค่าต่างๆ
├── main.py                   # จุดเริ่มต้น — รัน bot ที่นี่
│
├── bot/                      # 🧠 ตัว Bot หลัก
│   ├── __init__.py
│   ├── client.py             # เชื่อมต่อ Binance API
│   ├── strategy.py           # logic สัญญาณซื้อขาย
│   ├── trader.py             # ส่งคำสั่งซื้อขาย
│   └── logger.py             # บันทึก log การเทรด
│
├── backtest/                 # 📊 ทดสอบกลยุทธ์กับข้อมูลเก่า
│   ├── backtest.py
│   └── results/
│
├── dashboard/                # 📺 หน้าจอ Monitoring
│   └── app.py                # Streamlit app
│
├── data/
│   └── logs/                 # ไฟล์ CSV บันทึกการเทรด
│
└── tests/                    # 🧪 Unit tests
    └── test_strategy.py
```

---

## 🚀 วิธีเริ่มต้น (Setup)

### 1. Clone / เปิด Project ใน VS Code
```bash
mkdir binance-bot && cd binance-bot
code .
```

### 2. สร้าง Virtual Environment
```python
# สร้าง environment แยกสำหรับ project นี้
python -m venv venv

# เปิดใช้งาน (Windows)
venv\Scripts\activate

# เปิดใช้งาน (Mac/Linux)
source venv/bin/activate
```

### 3. ติดตั้ง Libraries
```bash
pip install -r requirements.txt
```

### 4. ตั้งค่า API Key
```bash
# คัดลอกไฟล์ตัวอย่าง
cp .env.example .env

# แก้ไข .env ใส่ key ของคุณ
# ใช้ Testnet key ก่อนเสมอ!
```

### 5. ทดสอบการเชื่อมต่อ
```bash
python main.py --test
```

---

## ⚙️ การตั้งค่า (.env)

```env
# ===== TESTNET (ใช้ก่อน! ปลอดภัย) =====
BINANCE_TESTNET=true
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_SECRET_KEY=your_testnet_secret_key_here

# ===== LIVE (เปิดเมื่อพร้อมจริงๆ) =====
# BINANCE_TESTNET=false
# BINANCE_API_KEY=your_live_api_key_here
# BINANCE_SECRET_KEY=your_live_secret_key_here
```

> 🔑 สมัคร Testnet ได้ที่: https://testnet.binance.vision

---

## ⚙️ การตั้งค่ากลยุทธ์ (config.py)

```python
# config.py — แก้ค่าเหล่านี้เพื่อปรับกลยุทธ์

SYMBOL     = "BTCUSDT"        # คู่เหรียญที่เทรด
INTERVAL   = "1h"             # timeframe: 1m, 5m, 15m, 1h, 4h, 1d
QUANTITY   = 0.001            # จำนวน BTC ต่อ order

# MA Crossover Strategy
MA_SHORT   = 5                # MA เส้นสั้น
MA_LONG    = 20               # MA เส้นยาว

# Risk Management
STOP_LOSS  = 0.02             # stop loss 2%
TAKE_PROFIT = 0.04            # take profit 4%
MAX_TRADES = 1                # จำนวน position สูงสุดที่เปิดพร้อมกัน
```

---

## 🧠 กลยุทธ์ที่ใช้: MA Crossover

```
สัญญาณ BUY  🟢 — MA5 ตัด MA20 ขึ้น (Golden Cross)
สัญญาณ SELL 🔴 — MA5 ตัด MA20 ลง  (Death Cross)
```

### ภาพรวมการทำงาน
```
[ทุก 1 ชั่วโมง]
      ↓
ดึงราคาล่าสุด
      ↓
คำนวณ MA5 และ MA20
      ↓
เกิด Crossover ไหม?
   ↙         ↘
ใช่           ไม่
  ↓
ส่งคำสั่ง Buy/Sell
  ↓
บันทึก Log
```

---

## 📊 รัน Dashboard

```bash
# เปิด Streamlit dashboard
streamlit run dashboard/app.py
```

เปิด browser ไปที่ `http://localhost:8501`

Dashboard จะแสดง:
- 📈 กราฟราคา BTC แบบ real-time
- 🟢🔴 สัญญาณล่าสุด
- 💰 Portfolio และ PnL
- 📋 ประวัติการเทรด

---

## 📊 รัน Backtest

```bash
# ทดสอบกลยุทธ์กับข้อมูล 30 วันที่ผ่านมา
python backtest/backtest.py --days 30

# ทดสอบ 90 วัน
python backtest/backtest.py --days 90
```

ผลที่จะได้:
- Win Rate (%)
- Total PnL
- Max Drawdown
- Sharpe Ratio

---

## ▶️ รัน Bot

```bash
# รัน bot (Testnet)
python main.py

# รัน bot พร้อม log แบบละเอียด
python main.py --verbose
```

---

## 🛡️ กฎความปลอดภัย

| ❌ ห้ามทำ | ✅ ให้ทำ |
|---|---|
| ใส่ API Key ในโค้ดตรงๆ | ใช้ .env เสมอ |
| เปิด Withdrawal permission | เปิดแค่ Read + Trade |
| รัน Live ก่อน Backtest | Testnet → Backtest → Live |
| ไม่มี Stop Loss | ตั้ง Stop Loss ทุกครั้ง |
| Commit ไฟล์ .env | ใส่ .env ใน .gitignore |

---

## 📦 Libraries ที่ใช้

```txt
# requirements.txt
python-binance==1.0.19    # เชื่อมต่อ Binance API
pandas==2.1.0             # จัดการข้อมูลตาราง
numpy==1.24.0             # คำนวณตัวเลข
matplotlib==3.7.0         # วาดกราฟ
streamlit==1.28.0         # Dashboard
python-dotenv==1.0.0      # โหลด .env
schedule==1.2.0           # ตั้งเวลารัน bot
requests==2.31.0          # HTTP requests
```

---

## 📚 แหล่งเรียนรู้เพิ่มเติม

| หัวข้อ | แหล่ง |
|---|---|
| Binance API Docs | https://binance-docs.github.io/apidocs |
| Testnet | https://testnet.binance.vision |
| Python-Binance Docs | https://python-binance.readthedocs.io |
| Pandas Tutorial | https://pandas.pydata.org/docs/getting_started |
| Streamlit Docs | https://docs.streamlit.io |

---

## 🗺️ Roadmap

- [x] Setup project structure
- [ ] เชื่อมต่อ Binance Testnet
- [ ] ดึงราคาและคำนวณ MA
- [ ] เขียน signal logic
- [ ] รัน bot บน Testnet
- [ ] Backtest 30 วัน
- [ ] สร้าง Dashboard
- [ ] เพิ่ม Stop Loss / Take Profit
- [ ] Go Live ด้วยทุน $10–$50

---

> 💡 **เคล็ดลับ**: อ่าน log ทุกวัน เรียนรู้จากทุก trade ที่บอทตัดสินใจ — ถูกหรือผิดก็มีประโยชน์ทั้งนั้น
