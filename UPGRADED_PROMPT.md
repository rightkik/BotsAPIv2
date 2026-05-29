# 🚀 UPGRADED Strategy Prompt for Claude Code
# รวม + ปรับปรุงจาก TradingView concept + Python bot spec
# เอาไฟล์นี้วางใน root project แล้วใช้ prompt ด้านล่างสั่ง Claude Code

> **[COMPLETED — Session 5–9]** Spec นี้ถูก implement ครบแล้วใน bot/ ทุกไฟล์
> bot/indicator.py, bot/strategy.py, bot/risk.py, bot/trader.py, bot/logger.py, backtest/backtest.py
> ปัจจุบันโปรเจกต์ pivot สู่ SET Signal Monitor — ดู README.md และ PHASE_GUIDES.md

---

## สิ่งที่ Upgrade จากแผนเดิม

| หัวข้อ | แผนเดิม | Upgraded |
|---|---|---|
| Signal | MA5/MA20 Crossover | EMA20/EMA50 + ADX filter |
| Volatility | ไม่มี | ATR-based SL/TP |
| Trailing Stop | ไม่มี | Breakeven auto-move |
| Kill Switch | Max drawdown 10% | Daily loss 5% kill 24hr |
| Zones | ไม่มี | Supply/Demand Zone detection |
| Multi-TF | ไม่มี | H1 confirm + M15 entry |
| Dashboard | Basic | Professional dark/gold theme |

---

## PROMPT — วางใน Claude Code ได้เลย

```
อ่านไฟล์เหล่านี้ก่อนทุกครั้ง:
- README.md
- STRATEGY_LOGIC.md
- config.py (ถ้ามีแล้ว)

แล้วสร้าง/อัปเดตไฟล์ต่อไปนี้ทั้งหมดในโปรเจกต์

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 config.py — ค่าตั้งต้นทั้งหมด
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สร้าง config.py ที่มีค่าเหล่านี้:

# Exchange & Pair
SYMBOL          = "BTC/USDT"
TIMEFRAME_MAIN  = "1h"       # timeframe หลักสำหรับ signal
TIMEFRAME_ENTRY = "15m"      # timeframe รองสำหรับ entry
USE_TESTNET     = True

# EMA Settings
EMA_FAST        = 20
EMA_SLOW        = 50

# ADX Settings
ADX_PERIOD      = 14
ADX_THRESHOLD   = 25         # ต้องมากกว่านี้ถึงจะเทรด

# RSI Settings
RSI_PERIOD      = 14
RSI_OB          = 70         # Overbought (กรอง Long)
RSI_OS          = 30         # Oversold (กรอง Short)

# ATR Settings
ATR_PERIOD      = 14
ATR_SL_MULT     = 1.5        # SL = 1.5 x ATR
ATR_TP_MULT     = 3.0        # TP = 3.0 x ATR (RR 1:2)

# Supply/Demand Zone
PIVOT_LENGTH    = 5          # ความไวในการหา pivot point
ZONE_BUFFER     = 0.001      # buffer 0.1% รอบ zone

# Risk Management
RISK_PER_TRADE       = 0.01  # เสี่ยงได้ 1% ต่อ trade
BREAKEVEN_RR         = 1.0   # ย้าย SL → entry เมื่อกำไร 1:1
MAX_DAILY_LOSS_PCT   = 0.05  # kill switch เมื่อขาดทุน 5%/วัน
MAX_OPEN_TRADES      = 1     # เปิดพร้อมกันสูงสุด 1 position
COOLDOWN_BARS        = 3     # รอ 3 แท่งหลังปิด trade

# Dashboard
DASHBOARD_REFRESH_SEC = 30   # refresh ทุก 30 วินาที

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 bot/indicator.py — คำนวณ indicators ทั้งหมด
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สร้างฟังก์ชันต่อไปนี้:

def calculate_ema(df, period) → Series
  # Exponential Moving Average — ไวกว่า MA ปกติ ตอบสนองราคาล่าสุดมากกว่า

def calculate_adx(df, period=14) → DataFrame ที่มี columns: adx, di_plus, di_minus
  # Average Directional Index — วัดความแรงของเทรนด์ (ไม่ได้บอกทิศทาง)
  # ADX > 25 = มีเทรนด์ชัดเจน, ADX < 20 = ตลาด sideways
  # คำนวณจาก: True Range → Directional Movement → Smoothed → ADX

def calculate_rsi(df, period=14) → Series

def calculate_atr(df, period=14) → Series
  # Average True Range — วัดความผันผวนของตลาด
  # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))

def calculate_volume_delta(df) → Series
  # ประมาณ Buy/Sell pressure จาก candle body
  # candle ขึ้น → volume เป็น buy, candle ลง → volume เป็น sell

def find_supply_demand_zones(df, pivot_length=5) → dict
  # หา Supply Zone (แนวต้าน) และ Demand Zone (แนวรับ)
  # Supply = pivot high + บริเวณรอบๆ (high ± buffer)
  # Demand = pivot low + บริเวณรอบๆ (low ± buffer)
  # คืน: {"supply": [(price_high, price_low), ...], "demand": [(price_high, price_low), ...]}

def detect_market_structure(df) → dict
  # ตรวจ Break of Structure (BoS) และ Change of Character (CHoCH)
  # BoS = ราคาทำลาย High/Low เดิมในทิศเดิม (เทรนด์ต่อ)
  # CHoCH = ราคาทำลาย High/Low ในทิศตรงข้าม (เทรนด์เปลี่ยน)
  # คืน: {"bos": "bullish"/"bearish"/None, "choch": True/False}

def add_all_indicators(df) → DataFrame
  # รวมทุก indicator เข้า df แล้วคืนกลับ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 bot/strategy.py — Signal Logic
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สร้างฟังก์ชันต่อไปนี้:

def detect_ema_crossover(df) → "golden" / "death" / None
  # golden = EMA20 ตัด EMA50 ขึ้น (2 แท่งก่อนหน้า EMA20 < EMA50)
  # death  = EMA20 ตัด EMA50 ลง

def check_adx_filter(df) → bool
  # True ถ้า ADX > ADX_THRESHOLD (มีเทรนด์พอจะเทรด)

def check_near_zone(price, zones, zone_type, buffer) → bool
  # True ถ้าราคาอยู่ใกล้ Supply หรือ Demand Zone ตาม buffer ที่กำหนด

def get_signal(df, state) → dict
  # คืน signal object:
  # {
  #   "action": "BUY" / "SELL" / "HOLD",
  #   "reason": "อธิบายเหตุผลภาษาไทย",
  #   "strength": "STRONG" / "NORMAL" / "WEAK",
  #   "near_demand": bool,
  #   "near_supply": bool,
  #   "bos": str,
  #   "choch": bool
  # }
  #
  # เงื่อนไข BUY (ต้องผ่านทุกข้อ):
  #   ✓ EMA Golden Cross
  #   ✓ ADX > 25
  #   ✓ RSI < 70 (ไม่ overbought)
  #   ✓ ไม่มี position เปิดอยู่
  #   ✓ ไม่อยู่ใน cooldown
  #   ✓ bot_active = True
  #   + STRONG ถ้า: ราคาอยู่ใกล้ Demand Zone หรือ CHoCH เป็น bullish
  #
  # เงื่อนไข SELL (ต้องผ่านทุกข้อ):
  #   ✓ EMA Death Cross
  #   ✓ ADX > 25
  #   ✓ RSI > 30 (ไม่ oversold)
  #   ✓ ไม่มี position เปิดอยู่
  #   ✓ ไม่อยู่ใน cooldown
  #   ✓ bot_active = True
  #   + STRONG ถ้า: ราคาอยู่ใกล้ Supply Zone หรือ CHoCH เป็น bearish

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 bot/risk.py — Risk Management
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สร้างฟังก์ชันต่อไปนี้:

def calculate_position_size(balance, entry_price, stop_loss_price, risk_pct) → float
  # คำนวณขนาด position ให้เสียได้แค่ risk_pct ถ้า SL โดน
  # quantity = (balance × risk_pct) / abs(entry_price - stop_loss_price)

def calculate_atr_sl_tp(entry_price, atr, direction, sl_mult, tp_mult) → dict
  # คืน: {"sl": float, "tp1": float, "tp2": float, "tp3": float}
  # direction = "long" หรือ "short"
  # SL   = entry ± (sl_mult × ATR)       → 1.5 ATR
  # TP1  = entry ± (sl_mult × ATR)       → 1:1 RR (จุด breakeven)
  # TP2  = entry ± (tp_mult × ATR)       → 1:2 RR (TP หลัก)
  # TP3  = entry ± (tp_mult × 1.5 × ATR) → 1:3 RR (TP สูงสุด)

def check_sl_tp(current_price, state) → "STOP_LOSS" / "TP1" / "TP2" / "TP3" / "BREAKEVEN" / None
  # ตรวจว่าราคาถึง level ไหนแล้ว

def should_move_to_breakeven(current_price, state) → bool
  # True ถ้าราคาถึง TP1 (1:1 RR) แล้ว SL ยังไม่ได้ย้าย
  # เมื่อ True → ย้าย SL ไปที่ entry_price (breakeven)

def check_daily_kill_switch(state) → bool
  # True ถ้าขาดทุนรวมวันนี้เกิน MAX_DAILY_LOSS_PCT
  # ถ้า True: ตั้ง state["bot_active"] = False, state["resume_time"] = ตอนนี้ + 24hr

def check_resume_time(state) → bool
  # True ถ้าครบ 24hr แล้ว สามารถ resume บอทได้

def should_stop_bot(state) → bool
  # รวมทุกเงื่อนไขหยุด:
  # - daily kill switch โดน
  # - consecutive losses เกิน MAX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 bot/trader.py — ส่งคำสั่ง
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ใช้ library: ccxt (ไม่ใช่ python-binance)

def create_exchange(testnet=True) → ccxt.binance object
  # โหลด API key จาก .env
  # ถ้า testnet=True ให้ set sandbox mode

def get_balance(exchange, currency="USDT") → float

def place_market_order(exchange, symbol, side, quantity) → dict
  # side = "buy" หรือ "sell"
  # มี retry 3 ครั้งถ้า network error
  # มี rate limit handler

def execute_signal(exchange, signal, df, state) → state
  # ถ้า BUY:
  #   1. get_balance
  #   2. คำนวณ ATR SL/TP
  #   3. คำนวณ position size
  #   4. place_market_order("buy")
  #   5. อัปเดต state ทั้งหมด
  # ถ้า SELL (close long):
  #   1. place_market_order("sell")
  #   2. คำนวณ PnL
  #   3. อัปเดต daily_pnl, consecutive_losses
  #   4. เช็ค kill switch
  #   5. เริ่ม cooldown
  # ถ้า BREAKEVEN:
  #   อัปเดต state["stop_loss"] = state["entry_price"]

def check_and_update_trailing(exchange, current_price, state) → state
  # เรียกทุก loop เพื่อเช็ค breakeven และ SL/TP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 bot/logger.py — บันทึก Log
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def log_trade(trade_data) → None
  # บันทึกลง data/logs/trades.csv
  # columns: timestamp, symbol, direction, entry, exit, sl, tp,
  #          quantity, pnl_usdt, pnl_pct, result(WIN/LOSS/BE),
  #          atr, adx, rsi, signal_strength

def log_signal(signal, indicators, price) → None
  # บันทึกทุก signal ที่เกิด (รวม HOLD) ลง data/logs/signals.csv

def log_state(state) → None
  # บันทึก state snapshot ทุก loop ลง data/logs/state.jsonl

def print_status(state, price, signal, indicators) → None
  # แสดงใน terminal แบบ real-time สวยงาม:
  #
  # ┌─────────────────────────────────────────┐
  # │  🤖 BINANCE BOT  │  BTC/USDT  │  1H    │
  # ├─────────────────────────────────────────┤
  # │  💰 ราคา: $67,420.50                    │
  # │  📊 สัญญาณ: 🟢 BUY (STRONG)            │
  # │  📈 EMA20: $67,100 │ EMA50: $66,800    │
  # │  📉 ADX: 32.5  RSI: 58.3  ATR: $420   │
  # ├─────────────────────────────────────────┤
  # │  📍 Position: LONG @ $67,200           │
  # │  🛑 SL: $66,570  🎯 TP2: $68,460      │
  # │  💵 PnL วันนี้: +$2.30 (+2.3%)        │
  # └─────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 main.py — จุดเริ่มต้นหลัก
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สร้าง main.py ที่:

1. รับ arguments:
   --test     → ทดสอบ connection อย่างเดียว
   --dry-run  → รันครบทุก logic แต่ไม่ส่ง order จริง
   --verbose  → แสดง log ละเอียด

2. Main loop ทำงานดังนี้:

   a. เช็ค resume_time → ถ้า kill switch หายแล้ว resume บอท
   b. ดึง OHLCV ทั้ง TIMEFRAME_MAIN และ TIMEFRAME_ENTRY
   c. add_all_indicators() ทั้ง 2 timeframe
   d. check_and_update_trailing() → เช็ค breakeven ก่อนเสมอ
   e. check_and_update_trailing() → เช็ค SL/TP hit
   f. should_stop_bot() → ถ้า True หยุด loop แจ้งเตือน
   g. get_signal() จาก TIMEFRAME_MAIN
   h. ถ้า signal STRONG บน H1 → ยืนยันด้วย M15 (same direction)
   i. execute_signal() → ส่งหรือไม่ส่ง order
   j. print_status() + log ทุกอย่าง
   k. sync_to_candle_close() → รอให้ครบแท่ง H1 แล้ว loop ใหม่

3. sync_to_candle_close(timeframe) → None
   # คำนวณเวลาที่แท่งถัดไปจะปิด แล้ว sleep จนถึงเวลานั้น
   # ดีกว่า sleep(3600) เพราะ sync กับ Binance candle จริงๆ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 backtest/backtest.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สร้าง backtest ที่:
- รับ --days (default 90), --symbol, --timeframe
- ดึงข้อมูลจาก Binance จริง (ไม่ต้อง API key สำหรับ historical data)
- รัน strategy เดียวกับ main.py ทุก bar
- จำลอง SL/TP/Breakeven ครบถ้วน
- แสดงผล:
  * Win Rate (W/L/BE)
  * Total PnL (USDT และ %)
  * Max Drawdown
  * Sharpe Ratio (ถ้าทำได้)
  * จำนวน trade ทั้งหมด
  * ค่า commission รวม (0.1% ต่อ trade)
  * Best/Worst trade
- บันทึกกราฟ equity curve → backtest/results/equity_YYYYMMDD.png
- บันทึก CSV → backtest/results/trades_YYYYMMDD.csv

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 dashboard/app.py — Streamlit Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สร้าง Streamlit dashboard ธีม dark gold เหมือน Binance:
  พื้นหลัง: #0B0E11
  accent:   #F0B90B (เหลืองทอง Binance)
  ข้อความ:  #EAECEF

Row 1 — Header Metrics (4 คอลัมน์)
  💰 ราคาปัจจุบัน + % เปลี่ยนแปลง 24hr
  📊 สัญญาณ: BUY🟢 / SELL🔴 / HOLD⚪ + strength
  💵 PnL วันนี้ (USDT + %) สีเขียว/แดง
  🤖 สถานะบอท: Active / Kill Switch / Cooldown

Row 2 — Indicators Bar (5 คอลัมน์)
  EMA20 vs EMA50 (Cross หรือไม่)
  ADX + ทิศทาง (Trending/Sideways)
  RSI + โซน (OB/OS/Normal)
  ATR (ความผันผวน)
  Volume Delta (Buy% vs Sell%)

Row 3 — Chart
  กราฟแท่งเทียน BTC/USDT พร้อม:
  - เส้น EMA20 (สีฟ้า) EMA50 (สีส้ม)
  - กรอบ Supply Zone (สีแดงโปร่งแสง)
  - กรอบ Demand Zone (สีเขียวโปร่งแสง)
  - จุด BUY (▲) SELL (▼) บนกราฟ
  - เส้น SL (แดงประ) TP1/TP2/TP3 (เขียวประ)
  - RSI subplot ด้านล่าง (เส้น 70/30)

Row 4 — Trade Info (ถ้ามี position)
  Entry Price | SL | TP1 | TP2 | TP3
  Current PnL | RR Ratio | ATR distance

Row 5 — Trade History Table
  20 trades ล่าสุดจาก CSV
  columns: เวลา, ทิศทาง, Entry, Exit, SL, PnL, ผล
  สีแถว: เขียว=WIN, แดง=LOSS, เทา=BREAKEVEN

Auto-refresh ทุก DASHBOARD_REFRESH_SEC วินาที

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ข้อกำหนดสำคัญทุกไฟล์:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. comment ภาษาไทยทุก function — อธิบายว่าทำอะไรและทำไม
2. ทุก Binance API call มี try/except + retry 3 ครั้ง
3. handle RateLimitExceeded จาก ccxt ด้วย exponential backoff
4. handle NetworkError และ Timeout แยกกัน
5. ห้าม hardcode ค่าใดๆ ดึงจาก config.py เสมอ
6. ทุก order ที่ส่ง log ก่อนส่งและหลังส่งเสมอ
7. ใช้ ccxt ไม่ใช่ python-binance
8. เมื่อเขียนเสร็จทุกไฟล์ สรุปวิธีทดสอบแต่ละไฟล์ว่ารันยังไง

```

---

## หลังได้โค้ดแล้ว — ลำดับการทดสอบ

```
1. python main.py --test
   → ตรวจ connection + แสดง balance

2. python main.py --dry-run
   → รัน logic ครบ แต่ไม่ส่ง order

3. python backtest/backtest.py --days 30
   → ดู win rate + equity curve

4. python main.py
   → รัน bot จริงบน Testnet

5. streamlit run dashboard/app.py
   → เปิด dashboard ดูแบบ real-time
```

---

## ข้อควรระวัง

- ccxt ต้องติดตั้งเพิ่ม: `pip install ccxt`
- อัปเดต requirements.txt เพิ่ม `ccxt==4.3.0`
- ADX คำนวณยากกว่า MA ธรรมดา ถ้า Claude Code มีปัญหาให้บอกให้ใช้ `pandas-ta` แทน: `pip install pandas-ta`
