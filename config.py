import json
import os
from dotenv import load_dotenv

load_dotenv()

# ── Watchlist — โหลดจาก data/watchlist.json (แก้ได้ผ่าน dashboard) ──
_WATCHLIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "watchlist.json")

_DEFAULT_WATCHLIST = [
    "AE",    "BAM",   "BANPU", "BDMS",  "CPAXT", "EGCO",  "HANA",
    "HANN",  "KBANK", "KKP",   "LH",    "OR",    "ORI",   "PACO",
    "PTTEP", "RATCH", "SCC",   "SCB",   "SCGD",  "SET",   "STGT",
    "TASCO", "TISCO", "TOP",   "TTA",   "TU",    "WHA",
]

def _load_watchlist() -> list:
    try:
        with open(_WATCHLIST_PATH, encoding="utf-8") as f:
            wl = json.load(f)
        return sorted(wl) if wl else _DEFAULT_WATCHLIST
    except (FileNotFoundError, json.JSONDecodeError):
        return _DEFAULT_WATCHLIST

WATCHLIST = _load_watchlist()

# ── Indicator Settings ─────────────────────────────────
EMA_FAST        = 20
EMA_SLOW        = 50
ADX_PERIOD      = 14
ADX_THRESHOLD   = 25
RSI_PERIOD      = 14
RSI_OB          = 70
RSI_OS          = 30
RSI_BULL        = 50
RSI_BEAR        = 50
ATR_PERIOD      = 14
ATR_SL_MULT     = 1.5
ATR_TP_MULT     = 3.0
PIVOT_LENGTH    = 5
VOL_AVG_PERIOD  = 20
ZONE_BUFFER     = 0.002

# ── Data Settings ──────────────────────────────────────
TIMEFRAME       = "1d"
TIMEFRAME_HTF   = "1wk"
HISTORY_PERIOD  = "6mo"
HTF_PERIOD      = "2y"

# ── Monitor & Alert ────────────────────────────────────
MONITOR_INTERVAL    = 300
ALERT_COOLDOWN_SEC  = 14400

# ── Dashboard ──────────────────────────────────────────
DASHBOARD_REFRESH_SEC = 300
DASHBOARD_COLS        = 4

# ── File Paths ─────────────────────────────────────────
SIGNAL_CACHE    = "data/cache/signals.json"
ALERT_LOG       = "data/logs/alerts.csv"
WATCHLIST_PATH  = _WATCHLIST_PATH

# ── Telegram ───────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Settrade (Phase 2 — realtime price feed) ───────────
SETTRADE_APP_ID     = os.getenv("SETTRADE_APP_ID", "")
SETTRADE_APP_SECRET = os.getenv("SETTRADE_APP_SECRET", "")
SETTRADE_APP_CODE   = os.getenv("SETTRADE_APP_CODE", "")
SETTRADE_BROKER_ID  = os.getenv("SETTRADE_BROKER_ID", "")

# ── Real-time mode settings ────────────────────────────
REALTIME_INTERVAL    = "5"
REALTIME_LIMIT       = 300
REALTIME_REFRESH_SEC = 60

# ── GitHub (สำหรับ commit watchlist จาก dashboard) ────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "rightkik/BotsAPIv2")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "master")
