# book-watch Board — Design Spec

วันที่: 2026-10-04 · สถานะ: อนุมัติแล้ว build เสร็จ แก้ให้ตรงกับของจริงแล้ว · โปรเจกต์ย่อย 2 จาก 3

โค้ดของโปรเจกต์ย่อยนี้อยู่ในรีโป Aquarium (`~/Work-space/Aquarium`) ไม่ใช่รีโปนี้ spec อยู่ที่นี่เพราะข้อมูลเข้าคือ `latest.json` ของรีโปนี้

## 1. เป้าหมาย

หน้า `/monitor/book-watch` บน Aquarium เป็นโต๊ะทำงานของ Platoo ทุกเช้าวันจันทร์ ใช้เลือกเล่มไปเขียนบทความ Whale and Vibe

สำเร็จเมื่อ: เปิดหน้าเดียวแล้วเห็นว่าสัปดาห์นี้มีเล่มไหนเพิ่งโผล่ครั้งแรก เล่มไหนติดหลายแหล่ง แต่ละร้านจัดอันดับอะไรไว้ โดยเห็นครบทุกเล่มที่ `featured: true` และกดไปหน้าต้นทางได้ทุกรายการ

หน้าเป็น public และโชว์ในฐานะงานใน portfolio ได้ในตัว แต่ไม่ได้ออกแบบเพื่อคนนอกเป็นหลัก

## 2. การตัดสินใจที่ Platoo เลือกแล้ว

| เรื่อง | ตัดสินใจ | ทางที่ไม่เลือก |
|---|---|---|
| ผู้ใช้หลัก | Platoo ใช้เลือกเล่ม โชว์ครบทุกเล่ม | ชิ้นโชว์ที่คัด top 10 ต่อหมวด |
| ปกหนังสือ | ไม่โชว์ ตารางตัวหนังสือล้วน | ดึงรูปตรงจากร้าน |
| การจัดเรียง | หมวดตายตัวตาม `latest.md` และมีบล็อก "New this week" บนสุด | ตารางเดียวพร้อมตัวกรอง |
| โครงโค้ด | แยก board ต่อ slug ใน route `[slug]` เดิม | route ตายตัวแยก, renderer กลางขับด้วย schema |

Ada ถือว่าตกลงโดยไม่ได้ถาม และ Platoo ไม่ค้านตอนอนุมัติ design

- label, heading, nav เป็นภาษาอังกฤษ ส่วนชื่อเล่ม ผู้เขียน ป้ายของร้าน หัวข้อบทความ เป็นไทยตามแหล่ง เหมือน flood-watch
- โชว์เฉพาะสัปดาห์ล่าสุด
- เล่มที่ `featured: false` ไม่โชว์ บอกเฉพาะจำนวน

## 3. ขอบเขต

อยู่ในขอบเขต

- board `/monitor/book-watch` อ่าน `latest.json` `schema_version: 1`
- ย้ายเนื้อ flood-watch ออกจาก `app/monitor/[slug]/page.tsx` ไปไฟล์ของตัวเอง โดยไม่แก้เนื้อใน
- card ใบที่สองบนหน้า `/monitor` (ได้จาก registry เอง)

นอกขอบเขต

- หน้าย้อนหลังรายสัปดาห์
- ตัวกรองหรือการค้นหา และ client component ใดๆ
- ปกหนังสือ
- project card ของ book-watch บนหน้า Projects (ใช้ skill `aquarium-add-card` เป็นงานแยก)
- การต่อ `latest.json` เข้า `wnv-publish` (โปรเจกต์ย่อย 3)
- การแก้ Engine หรือโครง `latest.json`

## 4. ข้อมูลเข้า

URL ตั้งต้น: `https://raw.githubusercontent.com/platoo-ada/book-watch/main/latest.json`

โครงตาม spec Engine ข้อ 5 board อ่าน field ต่อไปนี้

- ระดับบน: `schema_version`, `generated_at`, `week`
- `sources[]`: `id`, `name`, `url`, `ok`, `error`, `fetched_at`, `count`
- `books[]`: `key`, `title`, `author`, `translator`, `maybe_translated`, `source_count`, `list_types`, `featured`, `excluded_reason`, `first_seen`, `mentions[]`
- `mentions[]`: `source`, `list`, `rank`, `label`, `url`
- `articles[]`: `source`, `title`, `url`, `published`

ไม่อ่าน: `isbn`, `category`, `article_sources`, `matched_keys`, `cover`, `title_raw`

ขนาดจริงรอบแรก 289 KB หนังสือ 281 เล่ม `featured` 134 เล่ม ต่ำกว่าเพดาน 2 MB ของ data cache ใน Next

ชื่อแหล่งที่แสดง: `mentions[].source` และ `articles[].source` เป็น id board มีตารางแปลงของตัวเอง ถ้าไม่มี id ในตารางให้แสดง id ตรงๆ

| id | ชื่อที่แสดง |
|---|---|
| `seed` | SE-ED |
| `chula` | ศูนย์หนังสือจุฬาฯ |
| `amarin` | Amarin |
| `salmon` | Salmon |
| `the101` | The 101 |
| `aday` | a day |

ตารางนี้ซ้ำกับ `SOURCE_NAMES` ใน `bookwatch/__init__.py` เมื่อ Engine เพิ่มแหล่ง ต้องเพิ่มที่ board ด้วย ไม่เพิ่มก็ไม่พัง แค่เห็น id แทนชื่อ

## 5. หน้าตา

โครงหน้า หัว และ component เดียวกับ flood-watch (Spec Sheet, Section, Block, Data Table ตาม `DESIGN.md` ของ Aquarium) เรียงจากบนลงล่าง

### 5.1 หัว

`h1` "Book Watch" และ Bracket `[ Back ]` ไป `/monitor`, `[ Sources ]` ไป `#sources` (เฉพาะเมื่อมีข้อมูล)

ใต้ Spec sheet มีแถว Bracket กระโดดไปแต่ละหมวด: `[ New ]` `[ Featured ]` `[ Rankings ]` `[ Releases ]` `[ Recommended ]` `[ Articles ]` ชี้ไป `id` ของหมวดนั้น แสดงครบทุกตัวแม้หมวดจะว่าง

### 5.2 Spec sheet

| แถว | ค่า | ตัวอย่าง |
|---|---|---|
| `WEEK` | `week` ตามที่ไฟล์ให้ | 2026-W41 |
| `UPDATED` | `generated_at` ผ่าน `formatDateTime` | 05 Oct 2026 08:41 |
| `SOURCES` | จำนวนแถว `sources` ที่ `ok` ต่อทั้งหมด | 9/9 available |
| `TITLES` | จำนวนที่โชว์ และจำนวนที่ซ่อนแยกเหตุผล | 134 shown · 147 hidden (81 exam and reference, 54 not books, 12 not Thai) |
| `NEW THIS WEEK` | จำนวนเล่ม `featured` ที่ `first_seen` เท่ากับ `week` | 12 |

ข้อความเหตุผลที่ซ่อน: `exam_reference` เป็น "exam and reference", `not_book` เป็น "not books", `not_thai` เป็น "not Thai" ค่าอื่นแสดงตามค่าจริง เหตุผลที่จำนวนเป็น 0 ไม่แสดง

### 5.3 หมวด

ทุกหมวดคิดจากเล่มที่ `featured: true` เท่านั้น และโชว์ครบทุกเล่ม ไม่ตัดจำนวน

| ลำดับ | หมวด | เล่มที่เข้า | การเรียง |
|---|---|---|---|
| 1 | New this week | `first_seen` เท่ากับ `week` | ลำดับใน `books[]` |
| 2 | Featured | `source_count` อย่างน้อย 2 | ลำดับใน `books[]` |
| 3 | Store rankings | มี mention ที่ `list` เป็น `bestseller` แยก Block ต่อ id แหล่ง | `rank` น้อยไปมาก แล้วชื่อ |
| 4 | New releases and preorders | มี mention ที่ `list` เป็น `new` หรือ `preorder` | ดูด้านล่าง |
| 5 | Recommended | มี mention ที่ `list` เป็น `recommended` | ดูด้านล่าง |
| 6 | Articles | `articles[]` ทุกรายการ | ลำดับในไฟล์ |
| 7 | Sources | `sources[]` ทุกแถว | ลำดับในไฟล์ |

ลำดับใน `books[]` คือลำดับที่ Engine เรียงไว้แล้ว (spec Engine ข้อ 7) board ไม่เรียงใหม่

การเรียงของหมวด 4 และ 5 ตาม spec Engine ข้อ 7: `source_count` มากไปน้อย แล้วอันดับดีที่สุดของเล่มในรายการของหมวดนั้นน้อยไปมาก แล้วชื่อ ชื่อเทียบด้วยลำดับ code point ไม่ขึ้นกับ locale เพื่อให้ผลคงที่

Block ใน Store rankings เรียงตามลำดับที่ id แหล่งปรากฏครั้งแรกใน `sources[]` แหล่งเดียวมีหลายรายการ `bestseller` ได้ (SE-ED มี 3 ชุด) เลขอันดับจึงซ้ำกันได้ และเลขที่หายคือเล่มที่ถูกกรอง ใต้หัวหมวดมีบรรทัด "Rank as published by the store. Not sales figures."

เล่มเดียวติดหลายรายการได้ จึงโผล่ได้หลายหมวด

### 5.4 หนึ่งแถวของตารางหนังสือ

| คอลัมน์ | ค่า |
|---|---|
| Rank | เฉพาะหมวด Store rankings: `rank` ของ mention นั้น |
| Title | `title` |
| Author | `author` ถ้ามี และ "tr. `translator`" ถ้ามี ไม่มีทั้งคู่เว้นว่าง |
| Flags | `NEW` เมื่อ `first_seen` เท่ากับ `week`, `Possibly translated` เมื่อ `maybe_translated` ตัดบรรทัดได้ |
| Listed | Bracket ต่อ mention หนึ่งตัว ข้อความคือ `<ชื่อแหล่ง> · <label> #<rank>` ไป `url` ของ mention ในหมวด Store rankings ไม่ใส่ชื่อแหล่ง เพราะหัว Block บอกแล้ว |

- `label` แสดงตามที่ร้านเรียก ไม่แปล ร้านสำนักพิมพ์จึงขึ้นว่า "ยอดนิยมในร้านสำนักพิมพ์" เอง board ไม่ต้องรู้ว่าร้านไหนเป็นสำนักพิมพ์
- ในหมวด Store rankings หนึ่งแถวคือหนึ่ง mention คอลัมน์ Listed แสดงเฉพาะ mention นั้น หมวดอื่นหนึ่งแถวคือหนึ่งเล่ม คอลัมน์ Listed แสดง mention ทุกรายการของเล่ม
- ในหมวด New this week ไม่แสดงป้าย `NEW` เพราะทุกแถวเป็นของใหม่
- ตารางกว้างเลื่อนใน `overflow-x-auto` ของตัวเอง ชื่อไทยยาวตัดบรรทัดได้ คอลัมน์ Rank ไม่ตัด ช่องชื่อเล่มกว้างอย่างน้อย 12rem
- Flags อยู่ก่อน Listed (แก้หลัง build, Platoo ยืนยัน 2026-10-04): Bracket ไม่ตัดบรรทัด จึงเป็นคอลัมน์ที่กว้างและเลื่อนพ้นจอได้ กับข้อมูลจริงลำดับเดิมทำให้ Flags หลุดจอที่ความกว้าง 1280

### 5.5 Articles

ตารางคอลัมน์ Source, Title, Published, Link: ชื่อแหล่ง, หัวข้อเป็นข้อความ, `published` ตามที่ feed ให้ ไม่แปลงเขตเวลา, ลิงก์เป็น Bracket ที่ข้อความคือ domain ของ `url` (ลิงก์ทุกตัวบน Aquarium เป็น Bracket ตาม design system หัวข้อจึงไม่เป็นลิงก์เอง)

### 5.6 Sources

ตารางคอลัมน์ Source, Status, Fetched, Items, Domain เรียงคอลัมน์แบบ flood-watch และเพิ่ม Items จาก `count` แหล่งที่ `ok: false` ขึ้นรายการ "Unavailable this run" พร้อม `error` ปิดท้ายด้วยบรรทัด "All values as reported by source at stated time. No estimates."

### 5.7 หมวดว่าง

ไม่เว้นว่าง เขียนเป็นประโยค

| หมวด | ข้อความ |
|---|---|
| New this week ไม่มีเล่มใหม่ | No new titles this week. |
| New this week ทุกเล่มที่โชว์เป็นของใหม่ | Every title is new this week. See the sections below. |
| Featured | No title appeared in two or more sources this week. |
| Store rankings, New releases and preorders, Recommended | No data this week. |
| Articles | No book articles this week. |

กรณี "ทุกเล่มเป็นของใหม่" เกิดในสัปดาห์แรกของประวัติ (W40) บล็อกนี้จะซ้ำกับทั้งหน้า จึงไม่แสดงตาราง ถ้าไม่มีเล่ม `featured` เลย ใช้ข้อความ "No new titles this week."

## 6. โครงโค้ดใน Aquarium

| ไฟล์ | สถานะ | หน้าที่ |
|---|---|---|
| `content/monitors.ts` | แก้ | เพิ่ม entry `slug: "book-watch"`, `title: "Book Watch"`, `urlEnv: "BOOK_WATCH_URL"`, `tokenEnv: "BOOK_WATCH_TOKEN"` ไม่มี `writeup` |
| `lib/monitor.ts` | แก้ | `Snapshot` มี field `raw: unknown` เก็บ JSON ทั้งก้อน field เดิมและ parser เดิมไม่เปลี่ยน |
| `lib/book-watch.ts` | ใหม่ | type, parser และฟังก์ชันคัดและเรียงของแต่ละหมวด เป็น pure function ไม่ fetch ไม่มี JSX |
| `app/monitor/[slug]/page.tsx` | แก้ | เหลือ `generateStaticParams`, `generateMetadata`, หัวหน้า, สถานะ Unavailable และเลือก board ตาม slug |
| `components/monitor/FloodWatchBoard.tsx` | ใหม่ | เนื้อ flood-watch ย้ายมาทั้งก้อน (Board, ThailandSection, ProvinceSection, SourcesSection, Quote, NoticeList) |
| `components/monitor/BookWatchBoard.tsx` | ใหม่ | board ของ book-watch รับ `Snapshot` |
| `components/monitor/parts.tsx` | ใหม่ | `SpecSheet`, `Section`, `Block`, `Table` ย้ายออกจากหน้าเดิม ใช้ร่วมสอง board |

การเลือก board: ตาราง slug ไป component ใน `page.tsx` slug ที่อยู่ใน registry แต่ไม่มี board ให้ `notFound()`

`lib/book-watch.ts` มีหน้าต่อไปนี้

- `parseBookWatch(raw)` คืน `{ ok: true, data }` หรือ `{ ok: false, reason }`
- `newThisWeek(data)`, `featuredTitles(data)`, `storeRankings(data)`, `newAndPreorders(data)`, `recommended(data)`, `hiddenCounts(data)`
- `sourceName(id)`

หน้า `/monitor` ไม่แก้ `fetchSnapshot` อ่าน `generated_at` และ `sources[].ok` ของ book-watch ได้อยู่แล้ว meta ของ card จะขึ้น "Updated … · 9/9 sources" เอง

ไม่เพิ่ม dependency ไม่เพิ่ม client component

ถ้าระหว่าง build พบว่า `Table` ของ flood-watch รับแถวแบบที่ book-watch ต้องการไม่ได้ (เช่น เซลล์ที่มีหลายลิงก์) ให้ขยาย `Table` แบบที่ผลของ flood-watch ไม่เปลี่ยน ไม่เขียนตารางตัวที่สอง

## 7. เมื่อข้อมูลผิดปกติ

| กรณี | ผล |
|---|---|
| fetch ล้ม, HTTP ไม่ใช่ 2xx, เกิน 10 วินาที | สถานะ Unavailable เดิม: `UPDATED` Data unavailable, `LAST ATTEMPT`, `REASON` |
| `schema_version` ไม่ใช่ 1 หรือไม่มี | สถานะ Unavailable, `REASON` "Unsupported schema version `<ค่า>`" ไม่พยายาม render |
| field ระดับเล่มหายหรือผิดชนิด | ข้อความเป็นค่าว่าง ตัวเลขเป็น `null` รายการเป็นรายการว่าง ไม่ throw |
| เล่มไม่มี `title` | ข้ามเล่มนั้น |
| `url` ไม่ขึ้นต้นด้วย `http://` หรือ `https://` | แสดงเป็นข้อความธรรมดา ไม่เป็นลิงก์ |
| แหล่งบางตัว `ok: false` | หมวดที่เหลือแสดงตามปกติ แหล่งนั้นขึ้นใน "Unavailable this run" |
| `rank` เป็น `null` | ไม่แสดง `#<rank>` ในลิงก์ และเรียงไว้ท้ายสุด |

ข้อความจากแหล่งทั้งหมด render เป็น text node ของ React ไม่ใช้ `dangerouslySetInnerHTML`

หน้า index `/monitor` ไม่ตรวจ `schema_version` จึงยังขึ้น "Updated …" ได้แม้ board จะขึ้น Unavailable เพราะ schema ยอมรับความไม่ตรงกันนี้ เพราะการแก้ต้องแตะหน้า index และจะเกิดเฉพาะตอนขยับ schema ซึ่งต้องแก้ board อยู่แล้ว

## 8. การทดสอบ

Aquarium ยังไม่มี test runner ใช้ `node --test` กับไฟล์ `.ts` โดยตรง (Node 26 ตัด type เองได้ ไม่เพิ่ม dependency) test อยู่ที่ `lib/book-watch.test.mjs` (ไฟล์ `.mjs` import `./book-watch.ts` ตรงๆ จึงไม่ต้องแก้ `tsconfig.json`) ข้อมูลทดสอบแต่งขึ้นเองในไฟล์ test ไม่ก๊อป `latest.json` จริงเข้า repo

ทุกข้อเขียน test ก่อน และต้องเห็น fail ก่อน (TDD)

`parseBookWatch`

1. JSON ครบถ้วน คืน `ok: true` พร้อมจำนวนเล่ม แหล่ง บทความตรงกับข้อมูลเข้า
2. `schema_version: 2` คืน `ok: false` และ reason มีเลข 2
3. ไม่มี `schema_version` คืน `ok: false`
4. `books` ไม่ใช่ array คืน `ok: true` และรายการเล่มว่าง
5. เล่มที่ไม่มี `title` ถูกข้าม เล่มอื่นยังอยู่
6. `rank` เป็นข้อความตัวเลข แปลงเป็นตัวเลข `rank` ที่แปลงไม่ได้เป็น `null`
7. `url` เป็น `javascript:alert(1)` ถูกทำเป็นไม่มีลิงก์

การคัดและเรียง

8. `newThisWeek` คืนเฉพาะเล่ม `featured` ที่ `first_seen` เท่ากับ `week` และคงลำดับเดิม
9. `newThisWeek` บอกได้ว่าทุกเล่มเป็นของใหม่ (กรณี W40)
10. `featuredTitles` คืนเฉพาะ `source_count` อย่างน้อย 2
11. `storeRankings` แยกตาม id แหล่ง เรียงตาม `rank` และคงเลขอันดับซ้ำไว้ทั้งคู่
12. `storeRankings` ไม่รวมเล่ม `featured: false`
13. `newAndPreorders` เรียง `source_count` ก่อน แล้วอันดับดีที่สุดในรายการ `new` หรือ `preorder` แล้วชื่อ
14. `recommended` ใช้อันดับในรายการ `recommended` เท่านั้น ไม่ใช้อันดับ `bestseller` ของเล่มเดียวกัน
15. `hiddenCounts` นับแยกตาม `excluded_reason` และรวมเหตุผลที่ไม่รู้จักตามค่าจริง
16. `sourceName` ของ id ที่ไม่รู้จักคืน id นั้น

หน้าจริง ชี้ `BOOK_WATCH_URL` ไป server ในเครื่อง ตรวจ 5 กรณี

| กรณี | ต้องเห็น |
|---|---|
| ข้อมูลปกติ มีเล่มเก่าและเล่มใหม่ปนกัน | ทุกหมวดมีตาราง ป้าย `NEW` เฉพาะเล่มใหม่ |
| ไม่มีเล่มติด 2 แหล่ง | Featured ขึ้นประโยคหมวดว่าง |
| แหล่ง 1 ตัว `ok: false` | `SOURCES` 8/9 และแหล่งนั้นอยู่ใน Unavailable this run |
| `schema_version: 2` | สถานะ Unavailable พร้อมเหตุผล |
| server รับ connection แต่ไม่ตอบ | สถานะ Unavailable "Timed out after 10 s" และ build ไม่ค้าง |

flood-watch ไม่ถดถอย: เก็บ HTML ของ `/monitor/flood-watch` ก่อนย้ายไฟล์ โดยชี้ `WATCH_KB_URL` ไป snapshot คงที่ในเครื่อง หลังย้ายเก็บอีกครั้งด้วย snapshot เดิม ส่วน `<article>` ต้องเหมือนกันทุกตัวอักษร

ปิดงาน: `tsc --noEmit` ผ่าน, lint 0 error, `npm run build` ผ่าน, เปิด `/monitor`, `/monitor/book-watch`, `/monitor/flood-watch` ที่ความกว้าง 1280 และ 375 ไม่ล้นแนวนอน console 0 error, ตรวจด้วยข้อมูลจริงจาก URL ตั้งต้นอีกครั้ง

## 9. การ deploy

- ทำบน branch แยกใน Aquarium ไม่ทำบน `main`
- push และ merge ต้องให้ Platoo ยืนยันก่อน
- ไม่ต้องตั้ง env บน Vercel เพราะรีโป book-watch เป็น public และ URL ตั้งต้นอยู่ใน registry
- หลัง deploy ตรวจ prod: `/monitor` มี card 2 ใบ, `/monitor/book-watch` ขึ้นข้อมูลจริง, `/monitor/flood-watch` เหมือนเดิม
- อัปเดต `HANDOFF.md` ของ Aquarium และของรีโปนี้

## 10. ข้อจำกัดที่รู้อยู่

- ข้อมูลในหน้าเก่าได้ถึง 1 ชั่วโมง (revalidate 3600 วินาที) เพียงพอสำหรับข้อมูลรายสัปดาห์
- รีโป Aquarium เป็น private แต่เว็บเป็น public ห้ามนำข้อมูลงานจริงเข้า ข้อมูลของ board มาจากร้านหนังสือสาธารณะทั้งหมด
- ตารางชื่อแหล่งซ้ำกับ Engine (ข้อ 4)
- สัปดาห์ที่ cron ของ Engine ไม่รัน หน้ายังโชว์สัปดาห์ก่อน ดูได้จาก `WEEK` และ `UPDATED`
- เล่ม 134 เล่มทำให้หน้ายาว ใช้แถว Bracket กระโดดหมวด (ข้อ 5.1) นำทาง ถ้าใช้งานจริงแล้วช้า ค่อยพิจารณาตัวกรองเป็นงานรอบถัดไป
