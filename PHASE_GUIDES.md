# Phase Guides — BotsAPIv2

---

## ✅ Phase 1–6 — Binance Bot (Sessions 1–9, เสร็จแล้ว)

Binance crypto bot พัฒนาเสร็จครบ — EMA20/50 + ADX + ATR SL/TP + Supply/Demand zones + Multi-symbol (BTC/ETH) + HTF filter + Streamlit dashboard + Backtest engine

ดูรายละเอียดทั้งหมดใน `dev_log.txt` Sessions 1–9

**สรุปผล Backtest (90 วัน Bearish market):**
- 15m + HTF filter: 10 trades, Win Rate 20%, PnL -6.55%
- หมายเหตุ: ทุก configuration ขาดทุนในช่วง Bearish 90 วัน — ระบบทำงานถูกต้อง แค่ตลาดไม่เอื้อ

**เหตุที่หยุดพัฒนาต่อ:** win rate ต่ำในตลาด crypto Bearish → pivot สู่หุ้นไทย SET

---

## ✅ Phase SET-1 — SET Signal Monitor MVP (Session 10)

### สิ่งที่สร้าง
- [x] `data/fetcher.py` — yfinance batch OHLCV สำหรับ SET .BK symbols
- [x] `monitor.py` — background loop ทุก 5 นาที, Telegram alert
- [x] `notifier/telegram.py` — BUY/SELL/approaching zone alerts
- [x] `dashboard/app.py` — Streamlit SET Signal Monitor (rewrite)
- [x] `run_monitor.bat` / `run_dashboard.bat` — launchers
- [x] config.py rewrite — 27-stock watchlist, daily TF, Telegram settings

### Watchlist (27 หุ้น)
```
3BBIF  CPAXT  OSP    PTT    KBANK  WHA    TU     PTTEP
BDMS   HANN   TOP    IVL    TASCO  STGT   TISCO  LH
OR     RATCH  PACO   EGCO   SCC    ORI    HANA   BAM
BANPU  RCL    KKP
```

---

## ⏳ Phase SET-2 — Signal Quality + Settrade (ถัดไป)

### เป้าหมาย
ลด false signal และเพิ่ม realtime price จาก Settrade

### Checklist
- [ ] Volume filter — กรอง signal ที่ volume ต่ำกว่า average (breakout ต้องมี volume สูง)
- [ ] RSI confirmation — BUY ต้องการ RSI > 40, SELL ต้องการ RSI < 60 (กรอง sideways)
- [ ] Weekly HTF filter — BUY ได้เฉพาะตอน weekly EMA20 > EMA50
      (config.TIMEFRAME_HTF = "1wk" เตรียมไว้แล้ว)
- [ ] Settrade API integration
      - realtime price แทน yfinance (delayed ~15 min)
      - ดู order book + last trade
      - env vars: SETTRADE_APP_ID, APP_SECRET, USERNAME, PASSWORD, BROKER_ID

### คำถามที่ควรถาม Claude
- "อธิบาย Settrade Open API authentication flow ก่อนเขียนโค้ด"
- "Volume filter ควรใช้ threshold เท่าไหร่สำหรับหุ้น SET ที่ volume ต่ำกว่า crypto"

---

## ⏳ Phase SET-3 — Dashboard Upgrade

### Checklist
- [ ] Grid view — แสดงทุก 27 หุ้นในหน้าเดียว (signal card per symbol)
      BUY=เขียว, SELL=แดง, HOLD=เทา + ราคา + % เปลี่ยนแปลง
- [ ] Alert history table — แสดง alert ล่าสุดจาก alerts.csv
- [ ] Sector grouping — จัดหุ้นตามกลุ่ม (พลังงาน, ธนาคาร, สุขภาพ)
- [ ] Market heatmap — visualize ว่า sector ไหนแข็งแกร่ง/อ่อนแอ

---

## ⏳ Phase SET-4 — Notification Expansion

### Checklist
- [ ] LINE OA / Line Notify integration
- [ ] Daily summary — สรุปสัญญาณทั้งหมดของวัน ส่งตอนตลาดปิด (16:30 BKK)
- [ ] Morning scan — ส่ง watchlist สัญญาณตอนเปิดตลาด (09:30 BKK)
- [ ] Alert log dashboard — ดูประวัติ alert ย้อนหลังได้ใน Streamlit

---

## เงื่อนไขก่อนพิจารณา Phase SET-5 (Paper Trading)
- [ ] ระบบ monitor รันต่อเนื่องได้ 2 สัปดาห์โดยไม่ crash
- [ ] Signal quality ดีขึ้นหลัง Volume/RSI/HTF filter
- [ ] ติดตาม signal ด้วยมือ 20 trades ก่อน — เทียบว่าตลาดจริงไปทิศเดียวกับ signal ไหม
- [ ] Win rate จาก manual tracking > 50%
