# HANDOFF — book-watch

อัปเดตล่าสุด: 2026-10-04 (จบ session ออกแบบ ยังไม่เริ่ม build)

## 1. เป้าหมาย

เฝ้าตลาดหนังสือไทยและหนังสือแปลไทยรายสัปดาห์ เพื่อเป็นวัตถุดิบเขียนบทความ Whale and Vibe ทุกเช้าวันจันทร์ระบบดึงรายการขายดี แนะนำ ออกใหม่ จากร้านและสำนักพิมพ์ไทย รวมเล่มเดียวกันจากหลายแหล่ง เรียงตามจำนวนแหล่งอิสระ แล้วส่งออก `latest.md`, `latest.json` และ ntfy

งานแบ่งเป็น 3 โปรเจกต์ย่อย ทำตามลำดับ

1. **Engine** (รีโปนี้): ออกแบบเสร็จ รอ build
2. Board บน Aquarium `/monitor/book-watch`: ยังไม่เริ่ม ต้องมี spec ของตัวเอง
3. ต่อ `latest.json` เข้า skill `wnv-publish`: ยังไม่เริ่ม ต้องมี spec ของตัวเอง

## 2. สถานะปัจจุบัน

- รีโปมีแค่เอกสาร 4 commit บน branch `main` ในเครื่อง: spec, plan และไฟล์นี้
- **ยังไม่มีโค้ด** ยังไม่มีรีโปบน GitHub ยังไม่มี secret
- Spec: Platoo อนุมัติแล้ว
- Plan: เขียนเสร็จ Platoo ยังไม่ได้ตอบว่าตรงกับที่ต้องการไหม และยังไม่ได้เลือกวิธี build
- โค้ดและ test ใน plan ยังไม่เคยถูกรัน ตรวจด้วยการไล่อ่านเท่านั้น

## 3. งานที่เสร็จแล้ว

- Appraise บทความ AIHOT: จริง ไม่ clone หยิบแค่ไอเดีย (บันทึกใน memory `reference_appraised_repos_202607.md`)
- Spike แหล่งข้อมูลไทย: ได้ 7 URL ที่ดึงด้วย HTTP ตรงๆ ได้จากเครื่องในไทย
- Spec และ plan 7 task พร้อมโค้ดและ test ครบทุกขั้น

## 4. การตัดสินใจและเหตุผล

| เรื่อง | ตัดสินใจ | เหตุผล |
|---|---|---|
| ผู้ใช้ผลลัพธ์ | วัตถุดิบบทความ WnV | Platoo เลือก |
| ตลาด | หนังสือไทยและแปลไทยเท่านั้น | Platoo ปรับจากแผนเดิมที่รวมต่างประเทศ |
| การคัด | กฎล้วน ไม่มี LLM รายสัปดาห์ | เริ่มถูกและนิ่ง เก็บตัวอย่างจริงไว้ทำ gold set ภายหลัง |
| โครง | รีโปใหม่ ก๊อปแนว watch-kb, Python stdlib ล้วน | แยกจากเรื่องน้ำท่วม พังไม่ลากกัน |
| รีโป public | ใช่ | Aquarium จะดึงไฟล์ raw ในโปรเจกต์ย่อย 2 |
| นายอินทร์, Kinokuniya | ไม่เอา | เว็บกันบอต ไม่หาทางอ้อม |
| รวมเล่ม | ISBN ตรงกัน หรือชื่อที่ทำความสะอาดแล้วตรงกัน | ปกแข็งกับปกอ่อน ISBN ต่างกัน บางแหล่งไม่มี ISBN |
| Fuzzy match ชื่อ | ไม่ใช้ | ยอมแยกสองรายการดีกว่ารวมผิดเล่ม |
| Fixture | ไม่ commit | เป็นเนื้อหาเว็บอื่น รีโปเป็น public |
| คำเรียกอันดับ | "อันดับที่ร้านประกาศ" | บางร้านแอดมินเลือกเอง ไม่ใช่ยอดขายจริง |

## 5. ไฟล์ที่เกี่ยวข้อง

- `docs/superpowers/specs/2026-10-04-book-watch-engine-design.md` — spec (โครง `latest.json` อยู่ข้อ 5)
- `docs/superpowers/plans/2026-10-04-book-watch-engine.md` — plan 7 task
- `~/Work-space/watch-kb/` — ต้นแบบ (workflow, ntfy, แนวเขียน)

## 6. คำสั่งที่รันแล้วและผล

ทั้งหมดรันจากเครื่อง Platoo (IP ไทย) วันที่ 2026-10-04 ด้วย User-Agent `book-watch/1.0 (+https://github.com/platoo-ada/book-watch)`

| URL | ผล |
|---|---|
| `mp-api.se-ed.com/web-bff/homepage-layout` (ส่ง Origin + Referer) | 200, JSON 305 KB |
| `m2.se-ed.com/product/bestseller/1` | 200, HTML 55 KB, 17 ISBN |
| `www.chulabook.com/` | 200, JSON ใน `__NEXT_DATA__` |
| `amarinbooks.com/wp-json/wc/store/v1/products` | 200 |
| `salmonbooks.net/wp-json/wc/store/v1/products` | 200 |
| `www.the101.world/feed/`, `adaymagazine.com/feed/` | 200, RSS |
| `www.naiin.com/best-sellers-books` | 403, Cloudflare บล็อกแม้ใน browser จริง |
| `thailand.kinokuniya.com` | 403 |

**ยังไม่ได้ทดสอบจาก runner ของ GitHub** (IP ต่างประเทศ)

## 7. ข้อควรระวัง

- **ความเสี่ยงหลัก:** runner GitHub อาจถูกร้านไทยกัน Task 1 ของ plan พิสูจน์เรื่องนี้ก่อนเขียนอย่างอื่น ถ้า SE-ED กับจุฬาฯ ถูกกันทั้งคู่ ให้หยุดแล้วถาม Platoo เรื่องย้ายไปรันบนเครื่องด้วย scheduled task
- รายการของร้านปนของไม่ใช่หนังสือ (หน้ากากอนามัย ของแถม คอร์ส) และคู่มือสอบจำนวนมาก โดยเฉพาะจุฬาฯ ตัวกรองอยู่ใน plan Task 4 และต้องตรวจด้วยตาใน Task 6 Step 5
- ร้านหลายสำนักพิมพ์มีแค่ SE-ED กับจุฬาฯ เล่มที่ติดสองแหล่งขึ้นไปอาจมีน้อย เป็นข้อจำกัดที่ยอมรับแล้ว ไม่ใช่บั๊ก
- ntfy topic อยู่ใน `~/.config/ntfy/config` ห้ามพิมพ์ในแชทหรือเขียนลงไฟล์ในรีโป
- การสร้างรีโป GitHub และ push ครั้งแรก ต้องขอ Platoo ยืนยันก่อน
- จำนวน test ที่ plan ระบุในแต่ละ task (5, 15, 23, 11) นับด้วยมือ ถ้าเลขคลาดแต่ทุกตัวผ่านถือว่าใช้ได้

## 8. งานที่เหลือ เรียงตามลำดับ

1. Platoo ยืนยัน plan และเลือกวิธี build: Subagent-driven หรือ Native (Ada แนะนำ Native เพราะ 7 task ต่อกันเป็นเส้นตรง และโค้ดอยู่ใน plan ครบแล้ว)
2. Build ตาม plan Task 1 ถึง 7
3. หลัง Engine นิ่ง: brainstorm โปรเจกต์ย่อย 2 (Aquarium board) แล้วตามด้วย 3 (`wnv-publish`)
4. ภายหลัง: เติมแหล่ง MEB, Matichon, B2S, Ookbee ทีละแหล่ง (หน้าเปิดได้ ยังไม่ได้แกะโครง)

## 9. ขั้นถัดไปทันที

ถาม Platoo สองข้อ: plan ตรงกับที่ต้องการไหม และใช้วิธี build แบบไหน จากนั้นเริ่ม **Task 1 Step 1** ของ plan (สร้าง `bookwatch/__init__.py`, `tests/__init__.py`, `.gitignore`)

## 10. อ่านก่อนเริ่ม และ skill ที่ควรใช้

อ่านตามลำดับ

1. ไฟล์นี้
2. plan ทั้งไฟล์
3. spec (อ่านคู่กับ plan เมื่อ task อ้างถึง)

Skill

- Native: `superpowers:executing-plans`
- Subagent-driven: `superpowers:subagent-driven-development`
- ก่อนบอกว่าเสร็จ: `superpowers:verification-before-completion`
- จบงาน: `reflect-after-task` และอัปเดตไฟล์นี้เป็นสถานะ shipped
