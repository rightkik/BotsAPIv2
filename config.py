import os
from dotenv import load_dotenv

load_dotenv()

# ── Watchlist หุ้นไทย SET ──────────────────────────────
WATCHLIST = [
    "AE",    "BAM",   "BANPU", "BDMS",  "CPAXT", "EGCO",  "HANA",
    "HANN",  "KBANK", "KKP",   "LH",    "OR",    "ORI",   "PACO",
    "PTTEP", "RATCH", "SCC",   "SCB",   "SCGD",  "SET",   "STGT",
    "TASCO", "TISCO", "TOP",   "TTA",   "TU",    "WHA",
]

# ── Indicator Settings ─────────────────────────────────
EMA_FAST        = 20
EMA_SLOW        = 50
ADX_PERIOD      = 14
ADX_THRESHOLD   = 25
RSI_PERIOD      = 14
RSI_OB          = 70
RSI_OS          = 30
RSI_BULL        = 50    # BUY ต้องการ RSI > ค่านี้ (momentum ยืนยัน)
RSI_BEAR        = 50    # SELL ต้องการ RSI < ค่านี้
ATR_PERIOD      = 14
ATR_SL_MULT     = 1.5
ATR_TP_MULT     = 3.0
PIVOT_LENGTH    = 5
VOL_AVG_PERIOD  = 20    # period สำหรับ volume moving average
ZONE_BUFFER     = 0.002     # 0.2% รอบ zone (หุ้นไทยมีกระดาน ticksize ชัดเจน)

# ── Data Settings ──────────────────────────────────────
TIMEFRAME       = "1d"      # daily — เหมาะกับ SET ไทย
TIMEFRAME_HTF   = "1wk"     # weekly สำหรับ HTF filter
HISTORY_PERIOD  = "6mo"     # ย้อนหลัง 6 เดือน (~120 วัน พอสำหรับ EMA50)
HTF_PERIOD      = "2y"      # 2 ปี (~104 weekly bars พอสำหรับ EMA50 weekly)

# ── Monitor & Alert ────────────────────────────────────
MONITOR_INTERVAL    = 300       # เช็คทุก 5 นาที (วินาที)
ALERT_COOLDOWN_SEC  = 14400     # ส่ง alert ซ้ำได้ทุก 4 ชั่วโมง

# ── Dashboard ──────────────────────────────────────────
DASHBOARD_REFRESH_SEC = 300     # auto-refresh ทุก 5 นาที
DASHBOARD_COLS        = 4       # card ต่อแถว

# ── File Paths ─────────────────────────────────────────
SIGNAL_CACHE    = "data/cache/signals.json"
ALERT_LOG       = "data/logs/alerts.csv"

# ── Telegram ───────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Settrade (Phase 2 — realtime price feed) ───────────
SETTRADE_APP_ID     = os.getenv("SETTRADE_APP_ID", "")
SETTRADE_APP_SECRET = os.getenv("SETTRADE_APP_SECRET", "")
SETTRADE_APP_CODE   = os.getenv("SETTRADE_APP_CODE", "")
SETTRADE_BROKER_ID  = os.getenv("SETTRADE_BROKER_ID", "")

# ── Real-time mode settings ────────────────────────────
REALTIME_INTERVAL   = "5"     # แท่ง 5 นาที (รองรับ: "1","5","15","30","60","D","W")
REALTIME_LIMIT      = 300     # 300 แท่ง ≈ 5 วันทำการ (พอสำหรับ EMA50)
REALTIME_REFRESH_SEC = 60     # dashboard refresh ทุก 1 นาทีใน real-time mode
