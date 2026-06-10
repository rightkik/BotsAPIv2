"""
scripts/fetch_fundamentals.py
รัน: python scripts/fetch_fundamentals.py
บันทึก fundamental data ทุก symbol → data/cache/fundamentals.json
(GitHub Actions รันทุกวันทำการ 8:00 น. BKK)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

WATCHLIST_PATH = os.path.join(ROOT, "data", "watchlist.json")
OUT_PATH = os.path.join(ROOT, "data", "cache", "fundamentals.json")

FIELDS = [
    "shortName", "sector", "industry", "longBusinessSummary", "marketCap",
    "mostRecentQuarter", "trailingPE", "forwardPE", "trailingEps", "priceToBook",
    "totalRevenue", "revenuePerShare", "profitMargins", "returnOnEquity",
    "debtToEquity", "currentRatio", "dividendYield", "dividendRate",
    "payoutRatio", "exDividendDate",
]


def load_watchlist() -> list[str]:
    try:
        with open(WATCHLIST_PATH, encoding="utf-8") as f:
            wl = json.load(f)
        return sorted(wl) if wl else []
    except Exception:
        return []


def to_yf(symbol: str) -> str:
    return "^SET.BK" if symbol == "SET" else f"{symbol}.BK"


def fetch_symbol(symbol: str) -> dict | None:
    for attempt in range(3):
        try:
            info = yf.Ticker(to_yf(symbol)).info or {}
            if len(info) >= 5:
                return {k: info.get(k) for k in FIELDS}
        except Exception as e:
            print(f"  attempt {attempt+1} failed: {e}")
        time.sleep(2 ** attempt)
    return None


def main():
    watchlist = load_watchlist()
    if not watchlist:
        print("ERROR: watchlist empty")
        sys.exit(1)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    data: dict = {
        "_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    ok, fail = 0, 0

    for symbol in watchlist:
        if symbol == "SET":
            continue
        print(f"  {symbol}...", end=" ", flush=True)
        result = fetch_symbol(symbol)
        if result:
            data[symbol] = result
            print("OK")
            ok += 1
        else:
            print("FAIL")
            fail += 1
        time.sleep(1)  # ป้องกัน rate-limit

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nSaved {ok} symbols ({fail} failed) -> {OUT_PATH}")
    print(f"Updated: {data['_updated']}")


if __name__ == "__main__":
    main()
