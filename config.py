import os
from dotenv import load_dotenv

load_dotenv()

# ── Watchlist หุ้นไทย SET ──────────────────────────────
WATCHLIST = [
    "3BBIF", "CPAXT", "OSP",   "PTT",   "KBANK", "WHA",  "TU",   "PTTEP",
    "BDMS",  "HANN",  "TOP",   "IVL",   "TASCO",
    "STGT",  "TISCO", "LH",    "OR",    "RATCH", "PACO", "EGCO", "SCC",
    "ORI",   "HANA",  "BAM",   "BANPU", "RCL",   "KKP",
]

# ── Indicator Settings ─────────────────────────────────
EMA_FAST        = 20
EMA_SLOW        = 50
ADX_PERIOD      = 14
ADX_THRESHOLD   = 25
RSI_PERIOD      = 14
RSI_OB          = 70
RSI_OS          = 30
ATR_PERIOD      = 14
ATR_SL_MULT     = 1.5
ATR_TP_MULT     = 3.0
PIVOT_LENGTH    = 5
ZONE_BUFFER     = 0.002     # 0.2% รอบ zone (หุ้นไทยมีกระดาน ticksize ชัดเจน)

# ── Data Settings ──────────────────────────────────────
TIMEFRAME       = "1d"      # daily — เหมาะกับ SET ไทย
TIMEFRAME_HTF   = "1wk"     # weekly สำหรับ HTF filter (ยังไม่ใช้)
HISTORY_PERIOD  = "6mo"     # ย้อนหลัง 6 เดือน (~120 วัน พอสำหรับ EMA50)

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

# ── Settrade (สำหรับ realtime price — Phase 2) ─────────
SETTRADE_APP_ID     = os.getenv("SETTRADE_APP_ID", "")
SETTRADE_APP_SECRET = os.getenv("SETTRADE_APP_SECRET", "")
SETTRADE_USERNAME   = os.getenv("SETTRADE_USERNAME", "")
SETTRADE_PASSWORD   = os.getenv("SETTRADE_PASSWORD", "")
SETTRADE_BROKER_ID  = os.getenv("SETTRADE_BROKER_ID", "")
