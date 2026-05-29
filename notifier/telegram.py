import csv
import os
from datetime import datetime

import requests

import config


def send(text: str) -> bool:
    """ส่งข้อความ HTML ไปยัง Telegram"""
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return r.ok
    except Exception:
        return False


def alert_signal(symbol: str, action: str, price: float, reason: str, strength: str) -> bool:
    """ส่ง alert เมื่อมีสัญญาณ BUY หรือ SELL"""
    icon  = "🟢" if action == "BUY" else "🔴"
    label = "ซื้อ (BUY)" if action == "BUY" else "ขาย (SELL)"
    now   = datetime.now().strftime("%d/%m %H:%M")

    text = (
        f"{icon} <b>{symbol} — {label}</b>\n"
        f"ราคา: <b>{price:,.2f} บาท</b>\n"
        f"ความแรง: {strength}\n"
        f"เหตุผล: {reason}\n"
        f"เวลา: {now}"
    )
    ok = send(text)
    _log(symbol, action, price, strength)
    return ok


def alert_approaching(symbol: str, side: str, price: float) -> bool:
    """ส่ง alert เมื่อราคาใกล้ถึง zone"""
    icon  = "⚠️ ใกล้แนวรับ (Demand)" if side == "demand" else "⚠️ ใกล้แนวต้าน (Supply)"
    now   = datetime.now().strftime("%d/%m %H:%M")
    text  = (
        f"{icon}\n"
        f"<b>{symbol}</b> ราคา {price:,.2f} บาท\n"
        f"เวลา: {now}"
    )
    return send(text)


def _log(symbol: str, action: str, price: float, strength: str):
    os.makedirs(os.path.dirname(config.ALERT_LOG), exist_ok=True)
    with open(config.ALERT_LOG, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([datetime.now().isoformat(), symbol, action, price, strength])
