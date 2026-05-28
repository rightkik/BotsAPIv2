# ===================================================
# bot/client.py — ตัวเชื่อมต่อ Binance API
#
# ไฟล์นี้มีหน้าที่ 3 อย่าง:
#   1. get_client()      — สร้าง Binance Client จาก .env
#   2. test_connection() — ทดสอบว่า API ตอบสนองหรือเปล่า
#   3. get_btc_price()   — ดึงราคา BTC/USDT ล่าสุด
#
# กฎเหล็ก: API Key อยู่ใน .env เท่านั้น — ห้ามใส่ในโค้ด!
# ===================================================

import os
import sys
from typing import Optional
from dotenv import load_dotenv

# แก้ปัญหา Windows terminal ไม่แสดงภาษาไทยและ emoji
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from binance.client import Client
from binance.exceptions import BinanceAPIException

# โหลดค่าจากไฟล์ .env เข้าสู่ os.environ ทันทีที่ import ไฟล์นี้
load_dotenv()


def get_client() -> Client:
    """
    สร้าง Binance Client พร้อมใช้งาน

    ขั้นตอน:
      1. อ่าน API Key และ Secret จาก .env
      2. ตรวจสอบว่า Key ถูกกรอกแล้ว (ไม่ใช่ค่า placeholder)
      3. สร้าง Client แบบ Testnet หรือ Live ตาม BINANCE_TESTNET

    Returns:
        Client: Binance client ที่พร้อมเรียก API

    Raises:
        SystemExit: ถ้าไม่มี Key หรือสร้าง Client ไม่สำเร็จ
    """
    # อ่านค่าจาก environment
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_SECRET_KEY", "")
    is_testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    # ตรวจสอบว่า Key มีค่าหรือยัง
    if not api_key or not api_secret:
        print("❌ ข้อผิดพลาด: ไม่พบ BINANCE_API_KEY หรือ BINANCE_SECRET_KEY ในไฟล์ .env")
        print("   วิธีแก้: คัดลอก .env.example เป็น .env แล้วใส่ key จริง")
        raise SystemExit(1)

    # ตรวจสอบว่าไม่ใช่ค่า placeholder จาก .env.example
    if api_key == "your_api_key_here" or api_secret == "your_secret_key_here":
        print("❌ ข้อผิดพลาด: ยังไม่ได้เปลี่ยน API Key ในไฟล์ .env")
        print("   วิธีแก้: แทนที่ 'your_api_key_here' ด้วย key จริงจาก Binance Testnet")
        raise SystemExit(1)

    # แสดงโหมดที่กำลังจะเชื่อมต่อ
    mode_label = "Testnet (เงินปลอม — ปลอดภัย)" if is_testnet else "🔴 LIVE (เงินจริง!)"
    print(f"🔌 กำลังเชื่อมต่อ Binance {mode_label}...")

    try:
        # testnet=True จะเปลี่ยน endpoint ไปที่ testnet.binance.vision อัตโนมัติ
        client = Client(api_key, api_secret, testnet=is_testnet)
        return client

    except Exception as e:
        print(f"❌ ข้อผิดพลาด: สร้าง Client ไม่สำเร็จ — {e}")
        raise SystemExit(1)


def test_connection(client: Client) -> bool:
    """
    ทดสอบการเชื่อมต่อกับ Binance API

    ส่ง ping ไปยัง server และดึงเวลาเพื่อยืนยัน
    ถ้า API ตอบกลับ = เชื่อมต่อสำเร็จ

    Args:
        client: Binance Client ที่ได้จาก get_client()

    Returns:
        bool: True = เชื่อมต่อสำเร็จ, False = ล้มเหลว
    """
    try:
        # ping() จะ raise exception ถ้า server ไม่ตอบ
        client.ping()

        # get_server_time() ยืนยันว่า API key ถูกต้องและ server ทำงานปกติ
        server_time = client.get_server_time()
        print(f"✅ เชื่อมต่อสำเร็จ! Server time: {server_time['serverTime']}")
        return True

    except BinanceAPIException as e:
        # จัดการ error code ที่พบบ่อย
        print(f"❌ Binance API Error {e.status_code}: {e.message}")
        if e.status_code == -2014:
            print("   สาเหตุ: API Key รูปแบบไม่ถูกต้อง — ตรวจสอบ BINANCE_API_KEY ใน .env")
        elif e.status_code == -2015:
            print("   สาเหตุ: API Key ไม่ถูกต้องหรือถูกปิดใช้งาน — สร้าง key ใหม่")
        elif e.status_code == -1021:
            print("   สาเหตุ: เวลาเครื่องไม่ตรงเซิร์ฟเวอร์ — ลองซิงค์เวลา Windows")
        return False

    except Exception as e:
        print(f"❌ เชื่อมต่อไม่ได้: {e}")
        print("   ตรวจสอบ: อินเทอร์เน็ต / ปิด VPN ถ้าใช้อยู่ / Firewall")
        return False


def get_price(client: Client, symbol: str) -> Optional[float]:
    """
    ดึงราคาปัจจุบันของ symbol ใดก็ได้จาก Binance

    Args:
        client: Binance Client
        symbol: เช่น "BTCUSDT", "XAUUSDT", "ETHUSDT"

    Returns:
        float: ราคาล่าสุด หรือ None ถ้าดึงไม่ได้ (symbol ไม่มีใน exchange)
    """
    try:
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    except BinanceAPIException as e:
        # symbol ไม่มีใน exchange นี้ (เช่น XAUUSDT ไม่มีใน Testnet) — ไม่ต้อง print
        if "Invalid symbol" in str(e.message):
            return None
        print(f"❌ ดึงราคา {symbol} ไม่ได้: {e.status_code} — {e.message}")
        return None

    except Exception as e:
        print(f"❌ ดึงราคา {symbol} ไม่ได้: {e}")
        return None


def get_btc_price(client: Client) -> Optional[float]:
    """ดึงราคา BTC/USDT — wrapper ของ get_price() สำหรับ backward compatibility"""
    return get_price(client, "BTCUSDT")
