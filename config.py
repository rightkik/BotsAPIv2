# ===================================================
# config.py — ค่าตั้งต้นทั้งหมดของ Bot
#
# ห้ามใส่ API Key ในไฟล์นี้ — ดึงจาก .env เสมอ
# ===================================================

# Exchange & Pair
SYMBOL          = "BTC/USDT"
TIMEFRAME_MAIN  = "15m"      # timeframe หลักสำหรับ signal
TIMEFRAME_ENTRY = "5m"       # timeframe รองสำหรับยืนยัน entry
TIMEFRAME_HTF   = "1h"       # Higher TF filter — BUY ได้เฉพาะตอน 1h Bullish
USE_TESTNET     = True

# EMA Settings
EMA_FAST        = 20
EMA_SLOW        = 50

# ADX Settings
ADX_PERIOD      = 14
ADX_THRESHOLD   = 25         # ต้องมากกว่านี้ถึงจะเทรด

# RSI Settings
RSI_PERIOD      = 14
RSI_OB          = 70         # Overbought — กรอง Long
RSI_OS          = 30         # Oversold — กรอง Short

# ATR Settings
ATR_PERIOD      = 14
ATR_SL_MULT     = 1.5        # SL = 1.5 × ATR
ATR_TP_MULT     = 3.0        # TP = 3.0 × ATR (RR 1:2)

# Supply/Demand Zone
PIVOT_LENGTH    = 5          # ความไวในการหา pivot point
ZONE_BUFFER     = 0.001      # buffer 0.1% รอบ zone

# Risk Management
RISK_PER_TRADE       = 0.01  # เสี่ยงได้ 1% ต่อ trade
BREAKEVEN_RR         = 1.0   # ย้าย SL → entry เมื่อกำไร 1:1
MAX_DAILY_LOSS_PCT   = 0.05  # kill switch เมื่อขาดทุน 5%/วัน
MAX_OPEN_TRADES      = 1     # เปิดพร้อมกันสูงสุด 1 position
COOLDOWN_BARS        = 3     # รอ 3 แท่งหลังปิด trade

# File Paths
LOG_FILE        = "data/logs/trades.csv"
SIGNAL_LOG      = "data/logs/signals.csv"
STATE_FILE      = "data/logs/state.json"
STATE_HISTORY   = "data/logs/state.jsonl"
POSITION_FILE   = "data/logs/position.json"

# Dashboard
DASHBOARD_REFRESH_SEC = 30   # refresh ทุก 30 วินาที

# Backtest
BACKTEST_DAYS        = 90
BACKTEST_COMMISSION  = 0.001  # 0.1% ต่อ trade (Binance standard)
BACKTEST_DIR         = "backtest/results"

# Multi-symbol trading
SYMBOLS          = ["BTC/USDT", "ETH/USDT"]
MONITOR_INTERVAL = 60
