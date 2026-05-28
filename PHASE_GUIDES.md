# 📋 Phase Guides — ขั้นตอนการพัฒนาทีละ Phase

---

## ✅ Phase 1 — Setup & Connection (Week 1)

### สิ่งที่จะได้เรียนรู้
- การติดตั้ง Python และ VS Code
- Virtual Environment คืออะไร ทำไมต้องใช้
- การใช้ pip ติดตั้ง library
- การใช้ .env เก็บ secret key อย่างปลอดภัย
- การเรียก Binance API ครั้งแรก

### Checklist
- [ ] ติดตั้ง Python 3.11+
- [ ] ติดตั้ง VS Code + Python Extension
- [ ] สร้าง Virtual Environment
- [ ] ติดตั้ง libraries จาก requirements.txt
- [ ] สมัคร Binance Testnet
- [ ] สร้าง API Key บน Testnet
- [ ] รัน test connection สำเร็จ
- [ ] ดึงราคา BTC/USDT แสดงบน terminal ได้

### คำถามที่ควรถาม Claude
- "อธิบาย virtual environment ว่าคืออะไร ทำไมต้องใช้"
- "ทำไมต้องเก็บ API Key ใน .env ไม่ใส่ในโค้ดตรงๆ"

---

## ✅ Phase 2 — Data & Indicators (Week 2)

### สิ่งที่จะได้เรียนรู้
- Pandas DataFrame คืออะไร
- OHLCV data คืออะไร (Open, High, Low, Close, Volume)
- วิธีคำนวณ Moving Average, RSI
- วาดกราฟด้วย matplotlib

### Checklist
- [ ] ดึงข้อมูล OHLCV ย้อนหลัง 30 วัน
- [ ] เก็บข้อมูลใน DataFrame
- [ ] คำนวณ MA5 และ MA20
- [ ] คำนวณ RSI 14
- [ ] วาดกราฟราคาพร้อมเส้น MA
- [ ] บันทึกกราฟเป็นไฟล์ภาพ

### คำถามที่ควรถาม Claude
- "อธิบาย DataFrame ใน pandas ให้เข้าใจก่อนเขียนโค้ด"
- "RSI คำนวณยังไง อธิบายหลักการก่อน"

---

## ✅ Phase 3 — Bot Logic & Testnet (Week 3)

### สิ่งที่จะได้เรียนรู้
- เขียน if/else สำหรับ trading signal
- ส่งคำสั่ง market order บน Testnet
- บันทึก log ลง CSV
- วนลูปทุก N นาที

### Checklist
- [ ] เขียน function ตรวจ MA Crossover
- [ ] ส่ง Buy order บน Testnet สำเร็จ
- [ ] ส่ง Sell order บน Testnet สำเร็จ
- [ ] บันทึกทุก trade ลง CSV
- [ ] บอทวนลูปได้โดยไม่ crash
- [ ] มี error handling เมื่อ API ล้มเหลว

### คำถามที่ควรถาม Claude
- "อธิบาย market order กับ limit order ต่างกันยังไง"
- "ทำ error handling ยังไงถ้า Binance API ไม่ตอบ"

---

## ✅ Phase 4 — Backtesting (Week 4)

### สิ่งที่จะได้เรียนรู้
- Backtesting คืออะไร ทำไมสำคัญ
- คำนวณ PnL (Profit and Loss)
- Win Rate, Drawdown คืออะไร
- ปรับค่า MA เพื่อหา parameter ที่ดีที่สุด

### Checklist
- [ ] รัน backtest บนข้อมูล 30 วันได้
- [ ] แสดงผล Win Rate
- [ ] แสดงผล Total PnL
- [ ] แสดงผล Max Drawdown
- [ ] ทดลองเปลี่ยน MA5/MA20 เป็นค่าอื่น
- [ ] บันทึกผล backtest เป็น CSV

### คำถามที่ควรถาม Claude
- "Max Drawdown คืออะไร สำคัญยังไงในการประเมินบอท"
- "ทำไม backtest ดีแต่ live ไม่ดี อธิบายปัญหา overfitting"

---

## ✅ Phase 5 — Dashboard (Month 2)

### สิ่งที่จะได้เรียนรู้
- Streamlit คืออะไร ทำงานยังไง
- แสดงกราฟ real-time บน web
- อ่านข้อมูลจาก CSV มาแสดงผล
- ส่งแจ้งเตือนผ่าน Line Notify

### Checklist
- [ ] รัน Streamlit app ได้
- [ ] แสดงราคา BTC แบบ auto-refresh
- [ ] แสดงกราฟพร้อมสัญญาณ Buy/Sell
- [ ] แสดงตารางประวัติการเทรด
- [ ] แสดง PnL ปัจจุบัน
- [ ] ส่ง Line Notify เมื่อเกิดสัญญาณ (optional)

### คำถามที่ควรถาม Claude
- "ทำ auto-refresh ใน Streamlit ทุก 60 วินาทียังไง"
- "สร้าง Line Notify bot แจ้งเตือนเมื่อบอทซื้อขายยังไง"

---

## ✅ Phase 6 — Live Trading (Month 3+)

### ก่อน Go Live — ต้องผ่านทุกข้อนี้
- [ ] Backtest ผ่านอย่างน้อย 90 วัน
- [ ] Win Rate > 50%
- [ ] Max Drawdown < 20%
- [ ] รัน Testnet ต่อเนื่องอย่างน้อย 2 สัปดาห์
- [ ] มี Stop Loss ทุก trade
- [ ] ทุนที่ใช้คือเงินที่ "ยอมเสียได้"
- [ ] เริ่มด้วยทุนไม่เกิน $50

### คำถามที่ควรถาม Claude
- "Position Sizing คืออะไร คำนวณยังไง"
- "ถ้าบอทขาดทุนติดต่อกัน 5 ครั้ง ควรทำอะไร"
