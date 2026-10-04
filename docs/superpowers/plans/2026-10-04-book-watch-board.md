# book-watch Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่ม board `/monitor/book-watch` บน Aquarium ที่อ่าน `latest.json` (`schema_version: 1`) ของ book-watch แล้วแสดงทุกเล่มที่ `featured` เป็นตารางตัวหนังสือ แบ่งหมวดตายตัว มีบล็อก "New this week" บนสุด

**Architecture:** Route `app/monitor/[slug]/page.tsx` เดิมเหลือแค่โครงหน้าและตาราง slug → board เนื้อ flood-watch ย้ายไป `components/monitor/FloodWatchBoard.tsx` โดยไม่แก้เนื้อใน primitive ที่ใช้ร่วม (`SpecSheet`, `Section`, `Block`, `Table`, `Unavailable`) ย้ายไป `components/monitor/parts.tsx` ตรรกะของ book-watch ทั้งหมดเป็น pure function ใน `lib/book-watch.ts` และ `components/monitor/BookWatchBoard.tsx` แค่ render

**Tech Stack:** Next.js 16.2.12 (App Router, server component ล้วน), React 19, TypeScript strict, Tailwind 4, test ด้วย `node --test` (Node 26 ตัด type ของ `.ts` เอง)

**Spec:** `~/Work-space/book-watch/docs/superpowers/specs/2026-10-04-book-watch-board-design.md` (อ่านคู่กับ plan นี้)

**รีโปที่แก้:** `~/Work-space/Aquarium` (private, push = auto-deploy ขึ้น Vercel) ทุก path ใน plan นี้อ้างจาก root ของ Aquarium ยกเว้นระบุเป็นอื่น

## Global Constraints

- อ่าน `~/Work-space/Aquarium/HANDOFF.md` และ `CLAUDE.md` ก่อนแตะโค้ด
- ทำบน branch `book-watch-board` แตกจาก `main` ห้าม commit บน `main` ห้าม push และห้าม merge จนกว่า Platoo ยืนยัน
- `git add` ระบุไฟล์ทุกครั้ง ห้าม `git commit -a` และห้าม `git add .`
- ห้ามเพิ่ม dependency ห้ามเพิ่ม client component (`"use client"`) ห้ามแก้ `tsconfig.json`
- ห้ามนำข้อมูลงานจริงเข้า repo และห้ามก๊อป `latest.json` จริงเข้า repo ข้อมูลทดสอบแต่งขึ้นเองเท่านั้น
- label, heading, nav เป็นภาษาอังกฤษ ไม่ใช้ em-dash ข้อความจากแหล่ง (ชื่อเล่ม ผู้เขียน ป้ายร้าน หัวข้อบทความ) แสดงตามต้นทาง ไม่แปล
- ลิงก์ทุกตัวเป็น `Bracket` (`components/Bracket.tsx`) ไม่ใช้ `<a>` เปล่า
- สีและเส้นใช้ token เดิม (`text-muted`, `border-line`, `text-ink`) ไม่เพิ่มสี ไม่ระบายสีตามสถานะ
- ข้อความจากแหล่ง render เป็น text node ของ React เท่านั้น ห้าม `dangerouslySetInnerHTML`
- `lib/book-watch.ts` ต้องไม่มี runtime import และใช้ได้เฉพาะ syntax ที่ลบ type ออกได้ตรงๆ (ห้าม `enum`, ห้าม parameter property, ห้าม `namespace`) เพราะ `node --test` โหลดไฟล์นี้โดยตรง
- HTML ส่วน `<article>` ของ `/monitor/flood-watch` ต้องเหมือนเดิมทุกตัวอักษรเมื่อใช้ snapshot เดียวกัน
- commit message ลงท้ายด้วยบรรทัด `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
- ใน plan นี้ `$S` คือโฟลเดอร์ scratch นอก repo (เช่น scratchpad ของ session) ไฟล์ทดลองทุกไฟล์อยู่ใน `$S` ไม่อยู่ใน repo

## Review Focus

ข้อมูลที่ spec ไม่ได้พูดถึงแต่ของจริงเจอได้ แต่ละข้อมี test ผูกไว้ใน task ที่เป็นเจ้าของโค้ด

1. `week` เป็นค่าว่างหรือหายไป: ห้ามถือว่าทุกเล่มเป็นของใหม่ บล็อก New this week ต้องว่าง (Task 3 test "empty week")
2. `rank` เป็น 0, ติดลบ, ทศนิยม หรือข้อความที่ไม่ใช่ตัวเลข: ถือเป็น `null` ไม่แสดง `#` และเรียงไว้ท้าย (Task 2 test "rank", Task 3 test "null rank last")
3. เล่ม `featured` ที่ `mentions` ว่างหรือหาย: ยังนับใน `TITLES` และยังขึ้น New this week ได้ แต่ไม่เข้าหมวดรายการใด และไม่ทำให้พัง (Task 3 test "no mentions")
4. `sources[].url` ที่ไม่ใช่ `http(s)`: ห้ามเป็น `href` ต้องเป็น `null` แล้ว board แสดงเป็นข้อความ (Task 2 test "source url")
5. `mentions[].source` เป็น id ที่ไม่มีใน `sources[]` หรือชื่อชนกับ property ของ object เช่น `constructor`: ต้องได้กลุ่มของตัวเองต่อท้าย และ `sourceName` คืน id ไม่คืน function (Task 3 test "unknown source id")

---

## File Structure

| ไฟล์ | สถานะ | หน้าที่ |
|---|---|---|
| `lib/monitor.ts` | แก้ | `Snapshot` มี `raw: unknown` |
| `components/monitor/parts.tsx` | ใหม่ | `SpecSheet`, `Section`, `Block`, `Table`, `Unavailable`, type `BoardResult`, type `SourceLine` |
| `components/monitor/FloodWatchBoard.tsx` | ใหม่ | เนื้อ flood-watch ที่ย้ายมา export `floodWatchBoard(snapshot)` |
| `app/monitor/[slug]/page.tsx` | แก้ | metadata, หัวหน้า, ตาราง `BOARDS`, สถานะ Unavailable |
| `lib/book-watch.ts` | ใหม่ | type, `parseBookWatch`, ฟังก์ชันคัดและเรียง, ข้อความสรุป |
| `lib/book-watch.test.mjs` | ใหม่ | test ของ `lib/book-watch.ts` |
| `package.json` | แก้ | script `test` |
| `components/monitor/BookWatchBoard.tsx` | ใหม่ | board ของ book-watch export `bookWatchBoard(snapshot)` |
| `content/monitors.ts` | แก้ | entry `book-watch` |
| `CLAUDE.md`, `HANDOFF.md` | แก้ | เอกสารตามของจริง |

---

### Task 1: ย้าย flood-watch ออกจากหน้า `[slug]` โดยผลไม่เปลี่ยน

**Files:**
- Modify: `lib/monitor.ts` (type `Snapshot` และ `parseSnapshot`)
- Create: `components/monitor/parts.tsx`
- Create: `components/monitor/FloodWatchBoard.tsx`
- Modify: `app/monitor/[slug]/page.tsx` (ทั้งไฟล์)

**Interfaces:**
- Consumes: ของเดิมใน `lib/monitor.ts` และ `components/Bracket.tsx`
- Produces:
  - `Snapshot = { generatedAt: string; sources: RawSource[]; raw: unknown }`
  - จาก `@/components/monitor/parts`: `SpecSheet({ rows: [string, string][] })`, `Section({ title, id?, children })`, `Block({ title, source?, sources?, children })`, `Table({ head, rows, numeric?, nowrap?, thai?, wide?, controls?, label? })`, `Unavailable({ reason, attemptedAt })`, `type SourceLine = { url: string; fetched_at: string }`, `type BoardResult = { ok: true; view: React.ReactNode } | { ok: false; reason: string }`
  - จาก `@/components/monitor/FloodWatchBoard`: `floodWatchBoard(snapshot: Snapshot): BoardResult`

- [ ] **Step 1: เตรียม branch**

```bash
cd ~/Work-space/Aquarium
git status -sb          # ต้องเป็น "## main...origin/main" และไม่มีไฟล์ค้าง
git pull
git switch -c book-watch-board
```

ถ้า tree ไม่สะอาดหรืออยู่ branch อื่น หยุดแล้วถาม Platoo

- [ ] **Step 2: เก็บ HTML ของ flood-watch ก่อนแก้ (baseline)**

```bash
mkdir -p $S/fix
curl -s https://raw.githubusercontent.com/platoo-ada/watch-kb/main/latest.json -o $S/fix/flood.json
python3 -c "import json;d=json.load(open('$S/fix/flood.json'));print(len(d['sources']))"   # ต้องได้ตัวเลข ไม่ error
(cd $S/fix && python3 -m http.server 47200 --bind 127.0.0.1 >/dev/null 2>&1 &)
WATCH_KB_URL=http://127.0.0.1:47200/flood.json npm run build
WATCH_KB_URL=http://127.0.0.1:47200/flood.json npx next start -p 3011 &
sleep 3
curl -s http://localhost:3011/monitor/flood-watch \
  | python3 -c "import re,sys;print(re.search(r'<article.*?</article>',sys.stdin.read(),re.S).group(0))" \
  > $S/flood-before.html
wc -c $S/flood-before.html      # ต้องมากกว่า 5000
grep -c "Data unavailable" $S/flood-before.html   # ต้องเป็น 0
pkill -f "next start -p 3011"
```

เก็บ server ที่ port 47200 ไว้ใช้ต่อใน Step 7

- [ ] **Step 3: เพิ่ม `raw` ใน `Snapshot`**

ใน `lib/monitor.ts` แก้ type และบรรทัด return ของ `parseSnapshot`

```ts
export type Snapshot = {
  generatedAt: string;
  sources: RawSource[];
  /** The whole payload, for boards whose shape is not `sources[].data` (book-watch). */
  raw: unknown;
};
```

```ts
  return { generatedAt: str(json.generated_at), sources, raw: json };
```

- [ ] **Step 4: สร้าง `components/monitor/parts.tsx`**

ย้ายฟังก์ชัน `Unavailable`, `SpecSheet`, `Section`, `Block`, `Table` จาก `app/monitor/[slug]/page.tsx` มาทั้งตัว ไม่แก้ className ไม่แก้ comment ใส่ `export` หน้าทุกฟังก์ชัน หัวไฟล์เป็นดังนี้

```tsx
import Bracket from "@/components/Bracket";
import { domainOf, formatDateTime, formatTime } from "@/lib/monitor";

/** What a block's source line needs. A flood-watch `RawSource` fits as is. */
export type SourceLine = { url: string; fetched_at: string };

/** What a board hands back to the page: its view, or why it cannot render. */
export type BoardResult =
  | { ok: true; view: React.ReactNode }
  | { ok: false; reason: string };
```

จุดเดียวที่แก้ในเนื้อที่ย้าย: prop ของ `Block` เปลี่ยน type จาก `RawSource` เป็น `SourceLine` (เนื้อฟังก์ชันใช้แค่ `url` กับ `fetched_at` อยู่แล้ว)

```tsx
  title: string;
  source?: SourceLine;
  sources?: SourceLine[];
  children: React.ReactNode;
```

- [ ] **Step 5: สร้าง `components/monitor/FloodWatchBoard.tsx`**

ย้ายฟังก์ชัน `Board`, `ThailandSection`, `ProvinceSection`, `SourcesSection`, `Quote`, `NoticeList` มาทั้งตัว ไม่แก้เนื้อใน ไม่ใส่ `export` ให้ฟังก์ชันเหล่านี้ หัวไฟล์และท้ายไฟล์เป็นดังนี้

```tsx
import Bracket from "@/components/Bracket";
import {
  Block,
  Section,
  SpecSheet,
  Table,
  type BoardResult,
} from "@/components/monitor/parts";
import {
  METRO_PROVINCES,
  SOURCE,
  WATCHED_PROVINCES,
  domainOf,
  formatDateTime,
  formatNumber,
  formatTime,
  okSource,
  parseNotices,
  parseRain,
  parseText,
  parseWater,
  type RainData,
  type RawSource,
  type Snapshot,
  type WaterData,
} from "@/lib/monitor";

export function floodWatchBoard(snapshot: Snapshot): BoardResult {
  return { ok: true, view: <Board snapshot={snapshot} /> };
}
```

- [ ] **Step 6: เขียน `app/monitor/[slug]/page.tsx` ใหม่ทั้งไฟล์**

```tsx
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Bracket from "@/components/Bracket";
import { floodWatchBoard } from "@/components/monitor/FloodWatchBoard";
import { Unavailable, type BoardResult } from "@/components/monitor/parts";
import { MONITORS, getMonitor } from "@/content/monitors";
import { fetchSnapshot, type Snapshot } from "@/lib/monitor";
import { openGraph } from "@/lib/site";

type Params = { params: Promise<{ slug: string }> };

/** One renderer per board. A registry entry without one is a 404, not a blank page. */
const BOARDS: Record<string, (snapshot: Snapshot) => BoardResult> = {
  "flood-watch": floodWatchBoard,
};

export function generateStaticParams() {
  return MONITORS.map((m) => ({ slug: m.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const monitor = getMonitor(slug);
  if (!monitor) return {};
  return {
    // The project page about this board is "<title> — Aquarium"; this is the board.
    title: `${monitor.title} — Monitor — Aquarium`,
    description: monitor.summary,
    alternates: { canonical: `/monitor/${slug}` },
    openGraph: openGraph(
      `${monitor.title} — Monitor`,
      monitor.summary,
      `/monitor/${slug}`,
    ),
  };
}

export default async function MonitorDetailPage({ params }: Params) {
  const { slug } = await params;
  const monitor = getMonitor(slug);
  if (!monitor || !Object.hasOwn(BOARDS, slug)) notFound();

  const result = await fetchSnapshot(monitor);
  const board: BoardResult = result.ok
    ? BOARDS[slug](result.snapshot)
    : { ok: false, reason: result.reason };

  return (
    <article className="mx-auto w-full max-w-4xl py-8">
      <div className="mx-auto flex w-full max-w-2xl flex-wrap items-baseline justify-between gap-x-4 gap-y-2 pointer-coarse:gap-y-7">
        <h1 className="font-grotesque text-h1">{monitor.title}</h1>
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs pointer-coarse:gap-y-7">
          <Bracket label="Back" href="/monitor" />
          {board.ok && <Bracket label="Sources" href="#sources" />}
          {monitor.writeup && (
            <Bracket label={monitor.writeup} href={monitor.writeup} />
          )}
        </div>
      </div>

      {board.ok ? (
        board.view
      ) : (
        <Unavailable reason={board.reason} attemptedAt={result.fetchedAt} />
      )}
    </article>
  );
}
```

ก่อนเขียนทับ เทียบส่วน `generateMetadata` และ `<article>` กับไฟล์เดิมบรรทัดต่อบรรทัด ถ้าไฟล์เดิมต่างจากที่ plan นี้คัดมา (เช่น Bracket ของ `writeup` ใช้ label อื่น) ให้ยึดไฟล์เดิม แล้วแก้เฉพาะส่วน `BOARDS`, `board` และ import

- [ ] **Step 7: พิสูจน์ว่า flood-watch ออกเหมือนเดิม**

```bash
npx tsc --noEmit                     # ไม่มี error
npm run lint                         # 0 error
WATCH_KB_URL=http://127.0.0.1:47200/flood.json npm run build
WATCH_KB_URL=http://127.0.0.1:47200/flood.json npx next start -p 3011 &
sleep 3
curl -s http://localhost:3011/monitor/flood-watch \
  | python3 -c "import re,sys;print(re.search(r'<article.*?</article>',sys.stdin.read(),re.S).group(0))" \
  > $S/flood-after.html
cmp $S/flood-before.html $S/flood-after.html && echo SAME
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3011/monitor/nope   # 404
pkill -f "next start -p 3011"
```

Expected: `SAME` และ `404` ถ้า `cmp` รายงานต่าง ให้ `diff` ดูแล้วแก้ไฟล์ที่ย้าย ห้ามแก้ baseline

- [ ] **Step 8: Commit**

```bash
git add lib/monitor.ts components/monitor/parts.tsx components/monitor/FloodWatchBoard.tsx "app/monitor/[slug]/page.tsx"
git commit -m "refactor: one board module per monitor slug

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `parseBookWatch` และ type ของ book-watch

**Files:**
- Create: `lib/book-watch.ts`
- Create: `lib/book-watch.test.mjs`
- Modify: `package.json` (เพิ่ม script `test`)

**Interfaces:**
- Consumes: ไม่มี
- Produces (จาก `@/lib/book-watch`):

```ts
export type Mention = { source: string; list: string; rank: number | null; label: string; url: string | null };
export type Book = {
  key: string; title: string; author: string; translator: string;
  maybeTranslated: boolean; sourceCount: number; listTypes: string[];
  featured: boolean; excludedReason: string | null; firstSeen: string; mentions: Mention[];
};
export type BookSource = { id: string; name: string; url: string | null; fetched_at: string; ok: boolean; error: string | null; count: number | null };
export type Article = { source: string; title: string; url: string | null; published: string };
export type BookWatchData = { week: string; generatedAt: string; sources: BookSource[]; books: Book[]; articles: Article[] };
export type ParseResult = { ok: true; data: BookWatchData } | { ok: false; reason: string };
export function parseBookWatch(raw: unknown): ParseResult;
```

- [ ] **Step 1: เพิ่ม script `test` ใน `package.json`**

```json
    "lint": "eslint",
    "test": "node --test \"lib/**/*.test.mjs\""
```

- [ ] **Step 2: เขียน test ที่ยัง fail**

สร้าง `lib/book-watch.test.mjs`

```js
import test from "node:test";
import assert from "node:assert/strict";
import { parseBookWatch } from "./book-watch.ts";

// Made-up titles only. Never paste real latest.json content here.
function mention(over = {}) {
  return {
    source: "seed",
    list: "bestseller",
    rank: 1,
    label: "ขายดีรายวัน",
    title_raw: "x",
    url: "https://shop.example/book/1",
    cover: "https://shop.example/cover.png",
    ...over,
  };
}

function book(over = {}) {
  return {
    key: "isbn:0000000000001",
    isbn: "0000000000001",
    title: "เล่มทดสอบ",
    author: null,
    translator: null,
    category: null,
    maybe_translated: false,
    article_sources: [],
    source_count: 1,
    list_types: ["bestseller"],
    featured: true,
    excluded_reason: null,
    first_seen: "2026-W41",
    mentions: [mention()],
    ...over,
  };
}

function source(over = {}) {
  return {
    id: "seed",
    name: "SE-ED (API)",
    url: "https://shop.example/api",
    ok: true,
    error: null,
    fetched_at: "2026-10-05T08:31+07:00",
    count: 10,
    ...over,
  };
}

function payload(over = {}) {
  return {
    schema_version: 1,
    generated_at: "2026-10-05T08:31+07:00",
    week: "2026-W41",
    sources: [source()],
    books: [book()],
    articles: [],
    ...over,
  };
}

function parsed(over = {}) {
  const r = parseBookWatch(payload(over));
  assert.equal(r.ok, true);
  return r.data;
}

test("parse: complete payload keeps every book, source and article", () => {
  const r = parseBookWatch(
    payload({
      books: [book(), book({ key: "isbn:2", title: "เล่มสอง" })],
      sources: [source(), source({ id: "chula", name: "ศูนย์หนังสือจุฬาฯ" })],
      articles: [
        { source: "the101", title: "บทความ", url: "https://news.example/a", published: "Mon, 05 Oct 2026", matched_keys: [] },
      ],
    }),
  );
  assert.equal(r.ok, true);
  assert.equal(r.data.week, "2026-W41");
  assert.equal(r.data.generatedAt, "2026-10-05T08:31+07:00");
  assert.equal(r.data.books.length, 2);
  assert.equal(r.data.sources.length, 2);
  assert.equal(r.data.articles.length, 1);
  assert.equal(r.data.articles[0].published, "Mon, 05 Oct 2026");
  assert.deepEqual(r.data.books[0].mentions[0], {
    source: "seed",
    list: "bestseller",
    rank: 1,
    label: "ขายดีรายวัน",
    url: "https://shop.example/book/1",
  });
});

test("parse: schema_version 2 is refused and the reason names it", () => {
  const r = parseBookWatch(payload({ schema_version: 2 }));
  assert.deepEqual(r, { ok: false, reason: "Unsupported schema version 2" });
});

test("parse: missing schema_version is refused", () => {
  const p = payload();
  delete p.schema_version;
  assert.deepEqual(parseBookWatch(p), { ok: false, reason: "Unsupported schema version (missing)" });
});

test("parse: a payload that is not an object is refused", () => {
  assert.deepEqual(parseBookWatch([1, 2]), { ok: false, reason: "Unexpected payload" });
  assert.deepEqual(parseBookWatch(null), { ok: false, reason: "Unexpected payload" });
});

test("parse: books that is not an array becomes an empty list", () => {
  const d = parsed({ books: "nope", sources: null, articles: 7 });
  assert.deepEqual(d.books, []);
  assert.deepEqual(d.sources, []);
  assert.deepEqual(d.articles, []);
});

test("parse: a book without a title is skipped, the others stay", () => {
  const d = parsed({ books: [book({ title: null }), book({ title: "  " }), book({ title: "อยู่ต่อ" })] });
  assert.deepEqual(d.books.map((b) => b.title), ["อยู่ต่อ"]);
});

test("parse: missing book fields degrade, nothing throws", () => {
  const d = parsed({ books: [{ title: "โล่ง" }] });
  assert.deepEqual(d.books[0], {
    key: "",
    title: "โล่ง",
    author: "",
    translator: "",
    maybeTranslated: false,
    sourceCount: 0,
    listTypes: [],
    featured: false,
    excludedReason: null,
    firstSeen: "",
    mentions: [],
  });
});

test("parse: rank accepts a positive integer or a digit string, anything else is null", () => {
  const ranks = [3, "4", 0, -1, 2.5, "abc", null, undefined];
  const d = parsed({ books: [book({ mentions: ranks.map((rank) => mention({ rank })) })] });
  assert.deepEqual(d.books[0].mentions.map((m) => m.rank), [3, 4, null, null, null, null, null, null]);
});

test("parse: a mention url that is not http(s) becomes null", () => {
  const urls = ["javascript:alert(1)", "data:text/html,x", "//shop.example/x", "", null, "HTTPS://shop.example/ok"];
  const d = parsed({ books: [book({ mentions: urls.map((url) => mention({ url })) })] });
  assert.deepEqual(d.books[0].mentions.map((m) => m.url), [null, null, null, null, null, "HTTPS://shop.example/ok"]);
});

test("parse: a source url or article url that is not http(s) becomes null", () => {
  const d = parsed({
    sources: [source({ url: "javascript:alert(1)" }), source({ url: "http://shop.example/feed" })],
    articles: [{ source: "aday", title: "หัวข้อ", url: "ftp://x", published: "" }],
  });
  assert.deepEqual(d.sources.map((s) => s.url), [null, "http://shop.example/feed"]);
  assert.equal(d.articles[0].url, null);
});

test("parse: an article without a title is skipped", () => {
  const d = parsed({ articles: [{ source: "aday", title: "", url: "https://a.example" }, { source: "aday", title: "มีชื่อ", url: "https://a.example" }] });
  assert.deepEqual(d.articles.map((a) => a.title), ["มีชื่อ"]);
});

test("parse: source count and error keep their types", () => {
  const d = parsed({ sources: [source({ ok: false, error: "HTTP 503", count: null }), source({ count: "12" })] });
  assert.deepEqual(d.sources.map((s) => [s.ok, s.error, s.count]), [[false, "HTTP 503", null], [true, null, 12]]);
});
```

- [ ] **Step 3: รันให้เห็น fail**

Run: `npm test`
Expected: FAIL ด้วย `Cannot find module` ชี้ `lib/book-watch.ts`

- [ ] **Step 4: เขียน `lib/book-watch.ts` ส่วน parser**

```ts
/*
 * Data layer for /monitor/book-watch. Pure functions over a book-watch `latest.json`
 * (schema_version 1): no fetch, no JSX, no runtime imports. `node --test` loads this
 * file as is, so keep to syntax that erases cleanly (no enum, no parameter properties).
 *
 * Payload: { schema_version, generated_at, week, sources[], books[], articles[] }
 * Field-level damage degrades to an empty value. Only a wrong schema_version refuses.
 */

export const SUPPORTED_SCHEMA = 1;

export type Mention = {
  source: string;
  list: string;
  rank: number | null;
  label: string;
  url: string | null;
};

export type Book = {
  key: string;
  title: string;
  author: string;
  translator: string;
  maybeTranslated: boolean;
  sourceCount: number;
  listTypes: string[];
  featured: boolean;
  excludedReason: string | null;
  firstSeen: string;
  mentions: Mention[];
};

export type BookSource = {
  id: string;
  name: string;
  url: string | null;
  fetched_at: string;
  ok: boolean;
  error: string | null;
  count: number | null;
};

export type Article = {
  source: string;
  title: string;
  url: string | null;
  published: string;
};

export type BookWatchData = {
  week: string;
  generatedAt: string;
  sources: BookSource[];
  books: Book[];
  articles: Article[];
};

export type ParseResult =
  | { ok: true; data: BookWatchData }
  | { ok: false; reason: string };

export function parseBookWatch(raw: unknown): ParseResult {
  if (!isRecord(raw)) return { ok: false, reason: "Unexpected payload" };
  if (raw.schema_version !== SUPPORTED_SCHEMA) {
    const seen =
      raw.schema_version === undefined
        ? "(missing)"
        : String(JSON.stringify(raw.schema_version)).slice(0, 20);
    return { ok: false, reason: `Unsupported schema version ${seen}` };
  }
  return {
    ok: true,
    data: {
      week: str(raw.week),
      generatedAt: str(raw.generated_at),
      sources: arr(raw.sources).filter(isRecord).map(parseSource),
      books: arr(raw.books)
        .filter(isRecord)
        .map(parseBook)
        .filter((b) => b.title !== ""),
      articles: arr(raw.articles)
        .filter(isRecord)
        .map(parseArticle)
        .filter((a) => a.title !== ""),
    },
  };
}

function parseSource(s: Record<string, unknown>): BookSource {
  return {
    id: str(s.id),
    name: str(s.name),
    url: safeUrl(s.url),
    fetched_at: str(s.fetched_at),
    ok: s.ok === true,
    error: typeof s.error === "string" ? s.error : null,
    count: num(s.count),
  };
}

function parseBook(b: Record<string, unknown>): Book {
  return {
    key: str(b.key),
    title: str(b.title).trim(),
    author: str(b.author).trim(),
    translator: str(b.translator).trim(),
    maybeTranslated: b.maybe_translated === true,
    sourceCount: num(b.source_count) ?? 0,
    listTypes: arr(b.list_types).filter((v): v is string => typeof v === "string"),
    featured: b.featured === true,
    excludedReason:
      typeof b.excluded_reason === "string" && b.excluded_reason !== ""
        ? b.excluded_reason
        : null,
    firstSeen: str(b.first_seen),
    mentions: arr(b.mentions).filter(isRecord).map(parseMention),
  };
}

function parseMention(m: Record<string, unknown>): Mention {
  const rank = num(m.rank);
  return {
    source: str(m.source),
    list: str(m.list),
    // A store rank is a position: 1, 2, 3. Anything else is not a rank.
    rank: rank !== null && Number.isInteger(rank) && rank >= 1 ? rank : null,
    label: str(m.label).trim(),
    url: safeUrl(m.url),
  };
}

function parseArticle(a: Record<string, unknown>): Article {
  return {
    source: str(a.source),
    title: str(a.title).trim(),
    url: safeUrl(a.url),
    published: str(a.published).trim(),
  };
}

// ---------- Guards ----------

/** Source data ends up in an href. Only absolute http(s) may. */
function safeUrl(v: unknown): string | null {
  return typeof v === "string" && /^https?:\/\//i.test(v) ? v : null;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function str(v: unknown): string {
  return typeof v === "string" ? v : typeof v === "number" ? String(v) : "";
}

function num(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function arr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
```

- [ ] **Step 5: รันให้ผ่าน**

Run: `npm test`
Expected: PASS 12 ตัว fail 0

Run: `npx tsc --noEmit && npm run lint`
Expected: ไม่มี error

- [ ] **Step 6: Commit**

```bash
git add package.json lib/book-watch.ts lib/book-watch.test.mjs
git commit -m "feat: defensive parser for the book-watch snapshot

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: ฟังก์ชันคัด เรียง และข้อความสรุป

**Files:**
- Modify: `lib/book-watch.ts` (ต่อท้ายก่อนส่วน Guards)
- Modify: `lib/book-watch.test.mjs` (ต่อท้าย)

**Interfaces:**
- Consumes: `Book`, `Mention`, `BookWatchData`, `parseBookWatch` จาก Task 2 และ helper `book()`, `mention()`, `source()`, `parsed()` ในไฟล์ test
- Produces:

```ts
export function sourceName(id: string): string;
export function mentionText(m: Mention): string;                    // "SE-ED · ขายดีรายวัน #2"
export function isNew(book: Book, data: BookWatchData): boolean;
export function newThisWeek(data: BookWatchData): { books: Book[]; allNew: boolean };
export function featuredTitles(data: BookWatchData): Book[];
export type RankingRow = { book: Book; mention: Mention };
export type RankingGroup = { source: string; rows: RankingRow[] };
export function storeRankings(data: BookWatchData): RankingGroup[];
export function newAndPreorders(data: BookWatchData): Book[];
export function recommended(data: BookWatchData): Book[];
export type HiddenCounts = { shown: number; hidden: number; reasons: { reason: string; count: number }[] };
export function hiddenCounts(data: BookWatchData): HiddenCounts;
export function titlesSummary(h: HiddenCounts): string;             // "134 shown · 147 hidden (81 exam and reference, 54 not books, 12 not Thai)"
```

- [ ] **Step 1: เขียน test ที่ยัง fail**

แก้บรรทัด import บนสุดของ `lib/book-watch.test.mjs` เป็น

```js
import {
  featuredTitles,
  hiddenCounts,
  isNew,
  mentionText,
  newAndPreorders,
  newThisWeek,
  parseBookWatch,
  recommended,
  sourceName,
  storeRankings,
  titlesSummary,
} from "./book-watch.ts";
```

ต่อท้ายไฟล์

```js
const titles = (books) => books.map((b) => b.title);

test("newThisWeek: only featured books first seen this week, in file order", () => {
  const d = parsed({
    books: [
      book({ title: "ใหม่ ข", first_seen: "2026-W41" }),
      book({ title: "เก่า", first_seen: "2026-W40" }),
      book({ title: "ใหม่ ก", first_seen: "2026-W41" }),
      book({ title: "ใหม่แต่ถูกกรอง", first_seen: "2026-W41", featured: false, excluded_reason: "not_book" }),
    ],
  });
  const r = newThisWeek(d);
  assert.deepEqual(titles(r.books), ["ใหม่ ข", "ใหม่ ก"]);
  assert.equal(r.allNew, false);
});

test("newThisWeek: reports when every shown title is new", () => {
  const d = parsed({
    books: [book({ title: "ก" }), book({ title: "ข" }), book({ title: "ซ่อน", featured: false, first_seen: "2026-W39" })],
  });
  assert.equal(newThisWeek(d).allNew, true);
});

test("newThisWeek: empty week never marks a title as new", () => {
  const d = parsed({ week: "", books: [book({ first_seen: "" }), book({ first_seen: "2026-W41" })] });
  assert.deepEqual(newThisWeek(d), { books: [], allNew: false });
  assert.equal(isNew(d.books[0], d), false);
});

test("newThisWeek: no shown titles at all is not 'all new'", () => {
  const d = parsed({ books: [book({ featured: false })] });
  assert.deepEqual(newThisWeek(d), { books: [], allNew: false });
});

test("featuredTitles: two or more sources only", () => {
  const d = parsed({
    books: [
      book({ title: "สองแหล่ง", source_count: 2 }),
      book({ title: "แหล่งเดียว", source_count: 1 }),
      book({ title: "สามแหล่งแต่ถูกกรอง", source_count: 3, featured: false }),
    ],
  });
  assert.deepEqual(titles(featuredTitles(d)), ["สองแหล่ง"]);
});

test("storeRankings: grouped by source id in sources[] order, sorted by rank, duplicate ranks both kept", () => {
  const d = parsed({
    sources: [source({ id: "chula" }), source({ id: "seed" }), source({ id: "seed", name: "SE-ED (จัดอันดับ)" })],
    books: [
      book({ title: "ซีเอ็ด 2", mentions: [mention({ source: "seed", rank: 2 })] }),
      book({ title: "จุฬา 1", mentions: [mention({ source: "chula", rank: 1 })] }),
      book({ title: "ซีเอ็ด 1 ข", mentions: [mention({ source: "seed", rank: 1, label: "ชุดสอง" })] }),
      book({ title: "ซีเอ็ด 1 ก", mentions: [mention({ source: "seed", rank: 1 })] }),
    ],
  });
  const g = storeRankings(d);
  assert.deepEqual(g.map((x) => x.source), ["chula", "seed"]);
  assert.deepEqual(g[1].rows.map((r) => [r.mention.rank, r.book.title]), [
    [1, "ซีเอ็ด 1 ก"],
    [1, "ซีเอ็ด 1 ข"],
    [2, "ซีเอ็ด 2"],
  ]);
});

test("storeRankings: only bestseller mentions, only featured books, null rank last", () => {
  const d = parsed({
    books: [
      book({ title: "ไม่มีอันดับ", mentions: [mention({ rank: null })] }),
      book({ title: "ถูกกรอง", featured: false, mentions: [mention({ rank: 1 })] }),
      book({ title: "ออกใหม่", mentions: [mention({ list: "new", rank: 1 })] }),
      book({ title: "อันดับ 5", mentions: [mention({ rank: 5 }), mention({ list: "new", rank: 1 })] }),
    ],
  });
  const g = storeRankings(d);
  assert.equal(g.length, 1);
  assert.deepEqual(g[0].rows.map((r) => r.book.title), ["อันดับ 5", "ไม่มีอันดับ"]);
  assert.equal(g[0].rows[0].mention.list, "bestseller");
});

test("storeRankings: unknown source id gets its own group after the known ones", () => {
  const d = parsed({
    sources: [source({ id: "seed" })],
    books: [
      book({ title: "แปลก", mentions: [mention({ source: "constructor", rank: 1 })] }),
      book({ title: "ปกติ", mentions: [mention({ source: "seed", rank: 1 })] }),
    ],
  });
  assert.deepEqual(storeRankings(d).map((x) => x.source), ["seed", "constructor"]);
  assert.equal(sourceName("constructor"), "constructor");
});

test("storeRankings: a featured book with no mentions is in no group", () => {
  const d = parsed({ books: [book({ title: "ไร้รายการ", mentions: [] })] });
  assert.deepEqual(storeRankings(d), []);
  assert.deepEqual(newAndPreorders(d), []);
  assert.deepEqual(recommended(d), []);
  assert.deepEqual(titles(newThisWeek(d).books), ["ไร้รายการ"]);
  assert.equal(hiddenCounts(d).shown, 1);
});

test("newAndPreorders: source count first, then best rank in new or preorder, then title", () => {
  const d = parsed({
    books: [
      book({ title: "ข", mentions: [mention({ list: "new", rank: 1 })] }),
      book({ title: "ก", mentions: [mention({ list: "preorder", rank: 1 })] }),
      book({ title: "อันดับ 3", mentions: [mention({ list: "new", rank: 3 }), mention({ list: "preorder", rank: 9 })] }),
      book({ title: "สองแหล่ง", source_count: 2, mentions: [mention({ list: "new", rank: 8 })] }),
      book({ title: "ขายดีอย่างเดียว", mentions: [mention({ list: "bestseller", rank: 1 })] }),
      book({ title: "ถูกกรอง", featured: false, mentions: [mention({ list: "new", rank: 1 })] }),
    ],
  });
  assert.deepEqual(titles(newAndPreorders(d)), ["สองแหล่ง", "ก", "ข", "อันดับ 3"]);
});

test("recommended: ranks by the recommended list, never by a bestseller rank on the same book", () => {
  const d = parsed({
    books: [
      book({ title: "แนะนำ 5 ขายดี 1", mentions: [mention({ list: "recommended", rank: 5 }), mention({ list: "bestseller", rank: 1 })] }),
      book({ title: "แนะนำ 2", mentions: [mention({ list: "recommended", rank: 2 })] }),
      book({ title: "แนะนำไม่มีอันดับ", mentions: [mention({ list: "recommended", rank: null })] }),
    ],
  });
  assert.deepEqual(titles(recommended(d)), ["แนะนำ 2", "แนะนำ 5 ขายดี 1", "แนะนำไม่มีอันดับ"]);
});

test("hiddenCounts: split by reason, known reasons first, unknown reasons as given", () => {
  const hide = (reason, n) => Array.from({ length: n }, () => book({ featured: false, excluded_reason: reason }));
  const d = parsed({
    books: [book(), book(), ...hide("mystery", 1), ...hide("not_thai", 2), ...hide("exam_reference", 3), ...hide(null, 1)],
  });
  assert.deepEqual(hiddenCounts(d), {
    shown: 2,
    hidden: 7,
    reasons: [
      { reason: "exam_reference", count: 3 },
      { reason: "not_thai", count: 2 },
      { reason: "mystery", count: 1 },
      { reason: "unspecified", count: 1 },
    ],
  });
});

test("titlesSummary: English reason labels, zero reasons omitted", () => {
  assert.equal(
    titlesSummary({ shown: 134, hidden: 147, reasons: [
      { reason: "exam_reference", count: 81 },
      { reason: "not_book", count: 54 },
      { reason: "not_thai", count: 12 },
    ] }),
    "134 shown · 147 hidden (81 exam and reference, 54 not books, 12 not Thai)",
  );
  assert.equal(titlesSummary({ shown: 5, hidden: 0, reasons: [] }), "5 shown");
  assert.equal(titlesSummary({ shown: 0, hidden: 1, reasons: [{ reason: "mystery", count: 1 }] }), "0 shown · 1 hidden (1 mystery)");
});

test("sourceName and mentionText", () => {
  assert.equal(sourceName("seed"), "SE-ED");
  assert.equal(sourceName("chula"), "ศูนย์หนังสือจุฬาฯ");
  assert.equal(sourceName("newshop"), "newshop");
  const d = parsed({ books: [book({ mentions: [
    mention({ source: "amarin", label: "ยอดนิยมในร้านสำนักพิมพ์", rank: 2 }),
    mention({ source: "seed", label: "", list: "new", rank: null }),
  ] })] });
  assert.equal(mentionText(d.books[0].mentions[0]), "Amarin · ยอดนิยมในร้านสำนักพิมพ์ #2");
  assert.equal(mentionText(d.books[0].mentions[1]), "SE-ED · new");
});
```

- [ ] **Step 2: รันให้เห็น fail**

Run: `npm test`
Expected: FAIL ด้วย `does not provide an export named 'featuredTitles'`

- [ ] **Step 3: เขียนฟังก์ชัน**

แทรกใน `lib/book-watch.ts` ก่อนบรรทัด `// ---------- Guards ----------`

```ts
// ---------- Names ----------

// Mirrors SOURCE_NAMES in book-watch (bookwatch/__init__.py). A new source there
// shows up here as its id until it is added.
const SOURCE_NAMES: Record<string, string> = {
  seed: "SE-ED",
  chula: "ศูนย์หนังสือจุฬาฯ",
  amarin: "Amarin",
  salmon: "Salmon",
  the101: "The 101",
  aday: "a day",
};

export function sourceName(id: string): string {
  return Object.hasOwn(SOURCE_NAMES, id) ? SOURCE_NAMES[id] : id;
}

/** "SE-ED · ขายดีรายวัน #2". The label is the store's own wording, never translated. */
export function mentionText(m: Mention): string {
  const rank = m.rank === null ? "" : ` #${m.rank}`;
  return `${sourceName(m.source)} · ${m.label || m.list}${rank}`;
}

// ---------- Selection (featured titles only) ----------

function shown(data: BookWatchData): Book[] {
  return data.books.filter((b) => b.featured);
}

export function isNew(book: Book, data: BookWatchData): boolean {
  return data.week !== "" && book.firstSeen === data.week;
}

/** `allNew`: the first week on record, when the block would repeat the whole page. */
export function newThisWeek(data: BookWatchData): {
  books: Book[];
  allNew: boolean;
} {
  const all = shown(data);
  const books = all.filter((b) => isNew(b, data));
  return { books, allNew: all.length > 0 && books.length === all.length };
}

export function featuredTitles(data: BookWatchData): Book[] {
  return shown(data).filter((b) => b.sourceCount >= 2);
}

export type RankingRow = { book: Book; mention: Mention };
export type RankingGroup = { source: string; rows: RankingRow[] };

/** One group per source id, in `sources[]` order; ids seen only in mentions go last. */
export function storeRankings(data: BookWatchData): RankingGroup[] {
  const groups = new Map<string, RankingRow[]>();
  for (const s of data.sources) {
    if (!groups.has(s.id)) groups.set(s.id, []);
  }
  for (const book of shown(data)) {
    for (const mention of book.mentions) {
      if (mention.list !== "bestseller") continue;
      const rows = groups.get(mention.source) ?? [];
      rows.push({ book, mention });
      groups.set(mention.source, rows);
    }
  }
  return [...groups]
    .filter(([, rows]) => rows.length > 0)
    .map(([source, rows]) => ({
      source,
      rows: rows.sort(
        (a, b) =>
          cmp(rankOrLast(a.mention.rank), rankOrLast(b.mention.rank)) ||
          cmp(a.book.title, b.book.title),
      ),
    }));
}

export function newAndPreorders(data: BookWatchData): Book[] {
  return byStoreRank(data, ["new", "preorder"]);
}

export function recommended(data: BookWatchData): Book[] {
  return byStoreRank(data, ["recommended"]);
}

/** book-watch engine spec §7: source count, then best rank within these lists, then title. */
function byStoreRank(data: BookWatchData, lists: string[]): Book[] {
  const best = (b: Book) =>
    Math.min(
      ...b.mentions
        .filter((m) => lists.includes(m.list))
        .map((m) => rankOrLast(m.rank)),
    );
  return shown(data)
    .filter((b) => b.mentions.some((m) => lists.includes(m.list)))
    .sort(
      (a, b) =>
        cmp(b.sourceCount, a.sourceCount) ||
        cmp(best(a), best(b)) ||
        cmp(a.title, b.title),
    );
}

function rankOrLast(rank: number | null): number {
  return rank === null ? Number.POSITIVE_INFINITY : rank;
}

/** Plain code-unit order: the same result on every machine, whatever its locale. */
function cmp<T extends number | string>(a: T, b: T): number {
  return a === b ? 0 : a < b ? -1 : 1;
}

// ---------- Hidden titles ----------

export type HiddenCounts = {
  shown: number;
  hidden: number;
  reasons: { reason: string; count: number }[];
};

const KNOWN_REASONS = ["exam_reference", "not_book", "not_thai"];

const REASON_LABELS: Record<string, string> = {
  exam_reference: "exam and reference",
  not_book: "not books",
  not_thai: "not Thai",
};

export function hiddenCounts(data: BookWatchData): HiddenCounts {
  const counts = new Map<string, number>();
  let visible = 0;
  for (const b of data.books) {
    if (b.featured) {
      visible += 1;
      continue;
    }
    const reason = b.excludedReason ?? "unspecified";
    counts.set(reason, (counts.get(reason) ?? 0) + 1);
  }
  const order = [
    ...KNOWN_REASONS.filter((r) => counts.has(r)),
    ...[...counts.keys()].filter(
      (r) => !KNOWN_REASONS.includes(r) && r !== "unspecified",
    ),
    ...(counts.has("unspecified") ? ["unspecified"] : []),
  ];
  return {
    shown: visible,
    hidden: data.books.length - visible,
    reasons: order.map((reason) => ({ reason, count: counts.get(reason) ?? 0 })),
  };
}

export function titlesSummary(h: HiddenCounts): string {
  if (h.hidden === 0) return `${h.shown} shown`;
  const parts = h.reasons.map(
    (r) =>
      `${r.count} ${Object.hasOwn(REASON_LABELS, r.reason) ? REASON_LABELS[r.reason] : r.reason}`,
  );
  return `${h.shown} shown · ${h.hidden} hidden (${parts.join(", ")})`;
}
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `npm test`
Expected: PASS 26 ตัว fail 0

Run: `npx tsc --noEmit && npm run lint`
Expected: ไม่มี error

- [ ] **Step 5: Commit**

```bash
git add lib/book-watch.ts lib/book-watch.test.mjs
git commit -m "feat: section selectors and summaries for the book-watch board

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `BookWatchBoard` และลงทะเบียน board

**Files:**
- Create: `components/monitor/BookWatchBoard.tsx`
- Modify: `content/monitors.ts` (เพิ่ม entry ท้าย `MONITORS`)
- Modify: `app/monitor/[slug]/page.tsx` (import และ `BOARDS`)

**Interfaces:**
- Consumes: ทุกอย่างใน Produces ของ Task 1, 2, 3
- Produces: `bookWatchBoard(snapshot: Snapshot): BoardResult` จาก `@/components/monitor/BookWatchBoard`

- [ ] **Step 1: สร้างข้อมูลทดสอบ 4 ชุดใน `$S` (แต่งขึ้น ไม่อยู่ใน repo)**

```bash
mkdir -p $S/bw && cat > $S/bw/make.py <<'EOF'
import json, copy
def m(src, lst, rank, label, n): return {"source": src, "list": lst, "rank": rank, "label": label,
    "title_raw": "x", "url": f"https://{src}.example/book/{n}", "cover": None}
def b(n, title, first, mentions, sc=1, feat=True, why=None, author=None, tr=False):
    return {"key": f"isbn:{n}", "isbn": str(n), "title": title, "author": author, "translator": None,
            "category": None, "maybe_translated": tr, "article_sources": [], "source_count": sc,
            "list_types": sorted({x["list"] for x in mentions}), "featured": feat,
            "excluded_reason": why, "first_seen": first, "mentions": mentions}
def s(i, name, ok=True, err=None, count=10):
    return {"id": i, "name": name, "url": f"https://{i}.example/feed", "ok": ok, "error": err,
            "fetched_at": "2026-10-05T08:31+07:00", "count": count}
base = {"schema_version": 1, "generated_at": "2026-10-05T08:31+07:00", "week": "2026-W41",
  "sources": [s("seed","SE-ED (API)"), s("seed","SE-ED (จัดอันดับ)"), s("chula","ศูนย์หนังสือจุฬาฯ"),
              s("amarin","Amarin (ยอดนิยม)"), s("amarin","Amarin (ออกใหม่)"), s("salmon","Salmon (ยอดนิยม)"),
              s("salmon","Salmon (ออกใหม่)"), s("the101","The 101"), s("aday","a day")],
  "books": [
    b(1, "เล่มติดสองแหล่ง ทดสอบ", "2026-W40", [m("seed","bestseller",2,"ขายดีรายวัน",1), m("chula","recommended",1,"หนังสือแนะนำ",1)], sc=2, author="นักเขียน สมมติ"),
    b(2, "เล่มใหม่สัปดาห์นี้ ทดสอบ", "2026-W41", [m("amarin","new",1,"ออกใหม่",2)], tr=True),
    b(3, "เล่มเก่าขายดี ทดสอบ", "2026-W40", [m("seed","bestseller",4,"ขายดีรายวัน",3), m("seed","bestseller",4,"ขายดีสำนักพิมพ์",3)]),
    b(4, "ชื่อยาวมากไม่มีช่องว่าง" * 6, "2026-W40", [m("salmon","bestseller",1,"ยอดนิยมในร้านสำนักพิมพ์",4), m("salmon","new",3,"ออกใหม่",4)]),
    b(5, "เล่มสั่งจอง ทดสอบ", "2026-W41", [m("chula","preorder",2,"Pre-Order",5)]),
    b(6, "คู่มือสอบ ทดสอบ", "2026-W41", [m("seed","bestseller",1,"ขายดีรายวัน",6)], feat=False, why="exam_reference"),
    b(7, "ของไม่ใช่หนังสือ ทดสอบ", "2026-W41", [m("seed","bestseller",3,"ขายดีรายวัน",7)], feat=False, why="not_book"),
  ],
  "articles": [{"source": "the101", "title": "บทความทดสอบเรื่องหนังสือ", "url": "https://the101.example/a",
                "published": "Mon, 05 Oct 2026 01:00:00 +0000", "matched_keys": []}]}
def out(name, d): json.dump(d, open(name, "w"), ensure_ascii=False)
out("normal.json", base)
d = copy.deepcopy(base); d["books"][0]["source_count"] = 1; out("nofeatured.json", d)
d = copy.deepcopy(base); d["sources"][2].update(ok=False, error="HTTP 503", count=None); out("failed.json", d)
d = copy.deepcopy(base); d["schema_version"] = 2; out("schema2.json", d)
EOF
(cd $S/bw && python3 make.py && ls *.json && python3 -m http.server 47201 --bind 127.0.0.1 >/dev/null 2>&1 &)
```

Expected: มีไฟล์ `failed.json nofeatured.json normal.json schema2.json`

- [ ] **Step 2: ลงทะเบียน board ก่อน เพื่อเห็นหน้ายัง fail**

ใน `content/monitors.ts` เพิ่ม entry ต่อจาก `flood-watch`

```ts
  {
    slug: "book-watch",
    title: "Book Watch",
    summary:
      "Bestseller, new release and recommended lists from Thai bookshops and publishers, merged every Monday.",
    dataUrl:
      "https://raw.githubusercontent.com/platoo-ada/book-watch/main/latest.json",
    urlEnv: "BOOK_WATCH_URL",
    tokenEnv: "BOOK_WATCH_TOKEN",
  },
```

และแก้ comment ของ field `dataUrl` ใน type `MonitorEntry` จาก `(WATCH_KB_URL)` เป็น `(see urlEnv)`

รัน dev แล้วเช็คว่ายังไม่มี board

```bash
BOOK_WATCH_URL=http://127.0.0.1:47201/normal.json npx next dev -p 3010 &
sleep 5
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3010/monitor/book-watch
pkill -f "next dev -p 3010"
```

Expected: `404` (มีใน registry แต่ยังไม่มีใน `BOARDS`)

- [ ] **Step 3: เขียน `components/monitor/BookWatchBoard.tsx`**

```tsx
import Bracket from "@/components/Bracket";
import {
  Block,
  Section,
  SpecSheet,
  Table,
  type BoardResult,
  type SourceLine,
} from "@/components/monitor/parts";
import {
  featuredTitles,
  hiddenCounts,
  isNew,
  mentionText,
  newAndPreorders,
  newThisWeek,
  parseBookWatch,
  recommended,
  sourceName,
  storeRankings,
  titlesSummary,
  type Book,
  type BookSource,
  type BookWatchData,
  type Mention,
} from "@/lib/book-watch";
import {
  domainOf,
  formatDateTime,
  formatTime,
  type Snapshot,
} from "@/lib/monitor";

export function bookWatchBoard(snapshot: Snapshot): BoardResult {
  const parsed = parseBookWatch(snapshot.raw);
  if (!parsed.ok) return { ok: false, reason: parsed.reason };
  return { ok: true, view: <Board data={parsed.data} /> };
}

const JUMPS: [string, string][] = [
  ["New", "#new"],
  ["Featured", "#featured"],
  ["Rankings", "#rankings"],
  ["Releases", "#releases"],
  ["Recommended", "#recommended"],
  ["Articles", "#articles"],
];

function Board({ data }: { data: BookWatchData }) {
  const okCount = data.sources.filter((s) => s.ok).length;
  const fresh = newThisWeek(data);
  const featured = featuredTitles(data);
  const rankings = storeRankings(data);
  const releases = newAndPreorders(data);
  const picks = recommended(data);

  return (
    <>
      <SpecSheet
        rows={[
          ["WEEK", data.week || "n/a"],
          ["UPDATED", formatDateTime(data.generatedAt)],
          ["SOURCES", `${okCount}/${data.sources.length} available`],
          ["TITLES", titlesSummary(hiddenCounts(data))],
          ["NEW THIS WEEK", String(fresh.books.length)],
        ]}
      />

      <nav
        aria-label="Sections"
        className="mx-auto mt-6 flex w-full max-w-2xl flex-wrap gap-x-4 gap-y-2 text-xs pointer-coarse:gap-y-7"
      >
        {JUMPS.map(([label, href]) => (
          <Bracket key={href} label={label} href={href} />
        ))}
      </nav>

      <Section title="New this week" id="new">
        {fresh.books.length === 0 ? (
          <Empty text="No new titles this week." />
        ) : fresh.allNew ? (
          <Empty text="Every title is new this week. See the sections below." />
        ) : (
          <BookTable
            label="New this week"
            books={fresh.books}
            data={data}
            flagNew={false}
          />
        )}
      </Section>

      <Section title="Featured" id="featured">
        {featured.length === 0 ? (
          <Empty text="No title appeared in two or more sources this week." />
        ) : (
          <BookTable label="Featured" books={featured} data={data} />
        )}
      </Section>

      <Section title="Store rankings" id="rankings">
        <p className="font-mono text-xs text-muted">
          Rank as published by the store. Not sales figures.
        </p>
        {rankings.length === 0 ? (
          <Empty text="No data this week." />
        ) : (
          rankings.map((group) => (
            <Block
              key={group.source}
              title={sourceName(group.source)}
              sources={sourceLines(data.sources, group.source)}
            >
              <Table
                wide
                controls
                label={`${sourceName(group.source)} rankings`}
                head={["Rank", "Title", "Author", "Listed", "Flags"]}
                rows={group.rows.map(({ book, mention }) => [
                  mention.rank === null ? "n/a" : String(mention.rank),
                  book.title,
                  byline(book),
                  <Listed key="listed" mentions={[mention]} title={book.title} />,
                  flags(book, data, true),
                ])}
                numeric={[0]}
                nowrap={[4]}
                thai={[1, 2, 3]}
              />
            </Block>
          ))
        )}
      </Section>

      <Section title="New releases and preorders" id="releases">
        {releases.length === 0 ? (
          <Empty text="No data this week." />
        ) : (
          <BookTable label="New releases and preorders" books={releases} data={data} />
        )}
      </Section>

      <Section title="Recommended" id="recommended">
        {picks.length === 0 ? (
          <Empty text="No data this week." />
        ) : (
          <BookTable label="Recommended" books={picks} data={data} />
        )}
      </Section>

      <Section title="Articles" id="articles">
        {data.articles.length === 0 ? (
          <Empty text="No book articles this week." />
        ) : (
          <Table
            wide
            controls
            label="Articles"
            head={["Source", "Title", "Published", "Link"]}
            rows={data.articles.map((a) => [
              sourceName(a.source),
              a.title,
              a.published || "n/a",
              a.url ? (
                <Bracket
                  key="link"
                  label={domainOf(a.url)}
                  href={a.url}
                  external
                  ariaLabel={`${domainOf(a.url)}, article: ${a.title}`}
                />
              ) : (
                "n/a"
              ),
            ])}
            nowrap={[0, 3]}
            thai={[1]}
          />
        )}
      </Section>

      <SourcesSection sources={data.sources} />
    </>
  );
}

// ---------- Pieces ----------

function Empty({ text }: { text: string }) {
  return <p className="font-mono text-xs text-muted">{text}</p>;
}

function BookTable({
  label,
  books,
  data,
  flagNew = true,
}: {
  label: string;
  books: Book[];
  data: BookWatchData;
  /** Off inside "New this week", where every row would carry the flag. */
  flagNew?: boolean;
}) {
  return (
    <Table
      wide
      controls
      label={label}
      head={["Title", "Author", "Listed", "Flags"]}
      rows={books.map((book) => [
        book.title,
        byline(book),
        <Listed key="listed" mentions={book.mentions} title={book.title} />,
        flags(book, data, flagNew),
      ])}
      nowrap={[3]}
      thai={[0, 1, 2]}
    />
  );
}

function Listed({ mentions, title }: { mentions: Mention[]; title: string }) {
  if (mentions.length === 0) return null;
  return (
    // Stacked brackets: on touch the row gap keeps the 45px targets apart.
    <ul className="flex flex-col gap-y-1 pointer-coarse:gap-y-7">
      {mentions.map((m, i) => {
        const text = mentionText(m);
        return (
          <li key={i}>
            {m.url ? (
              <Bracket
                label={text}
                href={m.url}
                external
                ariaLabel={`${text}, ${title}`}
              />
            ) : (
              text
            )}
          </li>
        );
      })}
    </ul>
  );
}

function byline(book: Book): string {
  return [book.author, book.translator ? `tr. ${book.translator}` : ""]
    .filter(Boolean)
    .join(" · ");
}

function flags(book: Book, data: BookWatchData, flagNew: boolean): string {
  return [
    flagNew && isNew(book, data) ? "NEW" : "",
    book.maybeTranslated ? "Possibly translated" : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

/** The feeds behind one source id that answered and have a linkable URL. */
function sourceLines(sources: BookSource[], id: string): SourceLine[] {
  return sources.flatMap((s) =>
    s.id === id && s.ok && s.url ? [{ url: s.url, fetched_at: s.fetched_at }] : [],
  );
}

function SourcesSection({ sources }: { sources: BookSource[] }) {
  const failed = sources.filter((s) => !s.ok);
  return (
    <Section title="Sources" id="sources">
      <Table
        wide
        controls
        label="Sources"
        // Status and time first: on a phone the domain is what scrolls away.
        head={["Source", "Status", "Fetched", "Items", "Domain"]}
        rows={sources.map((s) => [
          s.name,
          s.ok ? "OK" : "Unavailable",
          formatTime(s.fetched_at),
          s.count === null ? "n/a" : String(s.count),
          s.url ? (
            <Bracket
              key="domain"
              label={domainOf(s.url)}
              href={s.url}
              external
              ariaLabel={`${domainOf(s.url)}, source for ${s.name}`}
            />
          ) : (
            "n/a"
          ),
        ])}
        numeric={[3]}
        nowrap={[1, 2, 4]}
        thai={[0]}
      />

      {failed.length > 0 && (
        <div className="mt-6">
          <h3 className="font-mono text-xs text-muted">Unavailable this run</h3>
          <ul className="mt-2 max-w-[30rem] space-y-1 font-mono text-xs">
            {failed.map((s, i) => (
              <li key={i}>
                {s.name}
                {s.error ? `: ${s.error}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-8 font-mono text-xs text-muted">
        All values as reported by source at stated time. No estimates.
      </p>
    </Section>
  );
}
```

- [ ] **Step 4: ต่อเข้า `BOARDS`**

ใน `app/monitor/[slug]/page.tsx` เพิ่ม import และ entry

```tsx
import { bookWatchBoard } from "@/components/monitor/BookWatchBoard";
```

```tsx
const BOARDS: Record<string, (snapshot: Snapshot) => BoardResult> = {
  "flood-watch": floodWatchBoard,
  "book-watch": bookWatchBoard,
};
```

- [ ] **Step 5: ตรวจหน้าจริง 5 กรณี**

กรณีละรอบ: เปิด dev ด้วย `BOOK_WATCH_URL` ของกรณีนั้น, `curl` เก็บ HTML, ปิด dev

```bash
check() {  # $1 = URL ของ snapshot, $2 = ชื่อไฟล์ผล
  BOOK_WATCH_URL=$1 npx next dev -p 3010 >/dev/null 2>&1 &
  sleep 6
  curl -s --max-time 40 http://localhost:3010/monitor/book-watch > $S/bw/$2.html
  pkill -f "next dev -p 3010"; sleep 1
}
check http://127.0.0.1:47201/normal.json normal
check http://127.0.0.1:47201/nofeatured.json nofeatured
check http://127.0.0.1:47201/failed.json failed
check http://127.0.0.1:47201/schema2.json schema2
# server ที่รับ connection แต่ไม่ตอบ
cat > $S/bw/hang.py <<'PY'
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 47202)); s.listen(8)
keep = []
while True: keep.append(s.accept())
PY
python3 $S/bw/hang.py &
check http://127.0.0.1:47202/x.json hang
pkill -f hang.py
```

แล้วตรวจทีละกรณี (ต้องได้ผลตามตารางทุกบรรทัด)

```bash
g() { grep -c "$2" $S/bw/$1.html; }
g normal "2026-W41"                         # >= 1
g normal "5 shown · 2 hidden (1 exam and reference, 1 not books)"   # 1
g normal "9/9 available"                    # >= 1
g normal "คู่มือสอบ ทดสอบ"                  # 0  (เล่มที่ถูกกรองต้องไม่โผล่)
g normal "Possibly translated"              # >= 1
g normal "Rank as published by the store. Not sales figures."        # 1
g normal "Data unavailable"                 # 0
g nofeatured "No title appeared in two or more sources this week."   # 1
g failed "8/9 available"                    # >= 1
g failed "HTTP 503"                         # >= 1
g schema2 "Unsupported schema version 2"    # >= 1
g schema2 'href="#sources"'                 # 0
g hang "Timed out after 10 s"               # >= 1
```

`grep -c` นับบรรทัด HTML ของ Next มักเป็นบรรทัดเดียว ค่า ">= 1" จึงมักเป็น 1 ถ้าได้ 0 ในข้อที่ต้องมี ให้เปิดไฟล์ดูก่อนแก้โค้ด เพราะ React คั่นข้อความที่ต่อกันด้วย `<!-- -->` ได้ (ถ้าเป็นเหตุนี้ ให้ค้นด้วยส่วนของข้อความที่ไม่ถูกคั่น ห้ามแก้ component ให้ grep ผ่าน)

ตรวจป้าย `NEW` ในกรณี normal ด้วยตา: เปิด `http://localhost:3010/monitor/book-watch` (dev ชี้ `normal.json`) ในเบราว์เซอร์ ต้องเห็น

- New this week มี 2 แถว (เล่มใหม่สัปดาห์นี้, เล่มสั่งจอง) และไม่มีคำว่า NEW ในตารางนี้
- Featured มี 1 แถว (เล่มติดสองแหล่ง) Listed มี 2 Bracket
- Store rankings มี Block SE-ED 3 แถว (อันดับ 2 หนึ่งแถว อันดับ 4 ซ้ำกันสองแถว) และ Block Salmon 1 แถว ไม่มี Block ของจุฬาฯ และ Amarin
- New releases and preorders มี 3 แถว เล่มใหม่มีป้าย NEW
- ชื่อยาวไม่มีช่องว่างไม่ดันหน้าให้ล้นแนวนอน (ตารางเลื่อนในตัวเอง)
- ที่ความกว้าง 375 และ 1280: `document.documentElement.scrollWidth <= window.innerWidth` และ console 0 error

- [ ] **Step 6: type, lint, test, build**

```bash
npm test                 # PASS 26
npx tsc --noEmit         # ไม่มี error
npm run lint             # 0 error
BOOK_WATCH_URL=http://127.0.0.1:47201/normal.json WATCH_KB_URL=http://127.0.0.1:47200/flood.json npm run build
```

Expected: build ผ่าน และรายการ route มี `/monitor/book-watch` กับ `/monitor/flood-watch`

- [ ] **Step 7: flood-watch ยังเหมือนเดิม**

```bash
WATCH_KB_URL=http://127.0.0.1:47200/flood.json BOOK_WATCH_URL=http://127.0.0.1:47201/normal.json npx next start -p 3011 &
sleep 3
curl -s http://localhost:3011/monitor/flood-watch \
  | python3 -c "import re,sys;print(re.search(r'<article.*?</article>',sys.stdin.read(),re.S).group(0))" \
  > $S/flood-final.html
cmp $S/flood-before.html $S/flood-final.html && echo SAME
curl -s http://localhost:3011/monitor | grep -c "Book Watch"     # >= 1
pkill -f "next start -p 3011"
```

Expected: `SAME` และหน้า `/monitor` มี card Book Watch

- [ ] **Step 8: Commit**

```bash
git add components/monitor/BookWatchBoard.tsx content/monitors.ts "app/monitor/[slug]/page.tsx"
git commit -m "feat: book-watch board under /monitor

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: ตรวจกับข้อมูลจริง เอกสาร และส่งมอบ

**Files:**
- Modify: `CLAUDE.md` (Aquarium: แถว `/monitor/[slug]` ในตารางโครงหน้า)
- Modify: `HANDOFF.md` (Aquarium: เพิ่มหัวข้อสถานะล่าสุดบนสุด)
- Modify: `~/Work-space/book-watch/HANDOFF.md`

**Interfaces:**
- Consumes: board ที่เสร็จจาก Task 4
- Produces: branch `book-watch-board` พร้อมให้ Platoo ตัดสิน push

- [ ] **Step 1: ตรวจกับ `latest.json` จริง (ไม่ตั้ง `BOOK_WATCH_URL`)**

```bash
npx next dev -p 3010 >/dev/null 2>&1 &
sleep 6
curl -s --max-time 40 http://localhost:3010/monitor/book-watch > $S/bw/real.html
curl -s https://raw.githubusercontent.com/platoo-ada/book-watch/main/latest.json -o $S/bw/real.json
python3 - <<EOF
import json
d = json.load(open("$S/bw/real.json")); html = open("$S/bw/real.html").read()
shown = [b for b in d["books"] if b["featured"]]
print("week in page:", d["week"] in html)
print("shown count in page:", f"{len(shown)} shown" in html)
print("unavailable:", "Data unavailable" in html)
hidden = [b["title"] for b in d["books"] if not b["featured"]]
shown_titles = {b["title"] for b in shown}
leaked = [t for t in hidden if t not in shown_titles and t in html]
print("hidden titles leaked:", len(leaked))
EOF
```

Expected: `True`, `True`, `False`, `0`

เปิดหน้าในเบราว์เซอร์ที่ 1280 และ 375 เลื่อนดูทั้งหน้า: ไม่ล้นแนวนอน, console 0 error, Bracket ใน Listed กดแล้วไปหน้าร้านได้ (ลอง 3 ร้าน), แถว Bracket กระโดดหมวดพาไปหมวดที่ถูก ถ่าย screenshot 2 ขนาดเก็บใน `$S` แล้วปิด dev

ถ้า `week` ยังเป็น `2026-W40` (cron แรกยังไม่รัน) บล็อก New this week จะขึ้น "Every title is new this week. See the sections below." ถือว่าถูก

- [ ] **Step 2: แก้ `CLAUDE.md` ของ Aquarium**

ในตารางโครงหน้า แก้แถว `/monitor/[slug]` ให้บอกว่ามี 2 board และโครงไฟล์ใหม่

```markdown
| `/monitor/[slug]` | Monitor board: `flood-watch` (spec sheet → Thailand / Bangkok Metro / Watched Provinces / Sources) และ `book-watch` (spec sheet → New this week / Featured / Store rankings / New releases and preorders / Recommended / Articles / Sources); data fetch จาก `latest.json` ภายนอก (ISR 1h, `lib/monitor.ts`) ไม่เก็บใน repo; หนึ่ง board = หนึ่งไฟล์ใน `components/monitor/` + หนึ่งแถวใน `BOARDS` ของ `page.tsx`; primitive ร่วมอยู่ `components/monitor/parts.tsx` | projects detail เดียวกัน |
```

ไม่แก้ `DESIGN.md` และ `.impeccable/design.json`: board นี้ใช้ component เดิม (Spec Sheet, Data Table, Board Card, Bracket) ไม่มี pattern ใหม่

- [ ] **Step 3: แก้ `HANDOFF.md` ของ Aquarium**

เพิ่มหัวข้อบนสุดของส่วนสถานะ ใส่วันที่จริงของวันที่ทำ เนื้อหาต้องมีครบ: branch `book-watch-board` ยังไม่ push ยังไม่ merge, ไฟล์ที่เพิ่มและแก้ (ตามตาราง File Structure ของ plan นี้), `npm test` รัน test 26 ตัวของ `lib/book-watch.ts`, ผล verify จริงจาก Task 4 Step 5 ถึง 7 และ Task 5 Step 1 (ใส่ตัวเลขที่เห็นจริง ไม่ก๊อปจาก plan), สิ่งที่ค้าง: Platoo ยืนยัน push, ตรวจ prod หลัง deploy, project card ของ book-watch (งานแยก ใช้ skill `aquarium-add-card`)

- [ ] **Step 4: แก้ `HANDOFF.md` ของ book-watch**

ใน `~/Work-space/book-watch/HANDOFF.md` แก้บรรทัดโปรเจกต์ย่อย 2 (ข้อ 1), งานที่เหลือ (ข้อ 8) และขั้นถัดไป (ข้อ 9) ให้ตรงสถานะจริง: build เสร็จบน branch `book-watch-board` ของ Aquarium, รอ push

- [ ] **Step 5: Commit**

```bash
cd ~/Work-space/Aquarium
git add CLAUDE.md HANDOFF.md
git commit -m "docs: book-watch board in the route map and handoff

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git log --oneline main..book-watch-board      # ต้องเห็น 5 commit
git status -sb                                # ไม่มีไฟล์ค้าง

cd ~/Work-space/book-watch
git add HANDOFF.md
git commit -m "docs: board built on the Aquarium branch, awaiting push

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

- [ ] **Step 6: หยุดและถาม Platoo**

รายงาน: ผล test, ผล verify 5 กรณี, ผลกับข้อมูลจริง, screenshot 2 ขนาด, ผลเทียบ flood-watch แล้วถามว่าจะ push branch และ merge เข้า `main` หรือไม่ (merge = deploy ขึ้น prod) ห้าม push ทั้งสองรีโปก่อนได้คำตอบ

หลัง Platoo ยืนยันและ deploy เสร็จ ตรวจ prod: `/monitor` มี card 2 ใบ, `/monitor/book-watch` ขึ้นข้อมูลจริง, `/monitor/flood-watch` ปกติ แล้วแก้ `HANDOFF.md` ทั้งสองรีโปเป็น shipped และ push ตาม

---

## สิ่งที่ต่างจาก spec ฉบับที่อนุมัติ (แก้ spec ตามแล้ว)

| ข้อ | เดิม | ตอนนี้ | เหตุผล |
|---|---|---|---|
| 5.5 | หัวข้อบทความเป็นลิงก์ | หัวข้อเป็นข้อความ ลิงก์เป็น Bracket แสดง domain | design system ของ Aquarium: ลิงก์ทุกตัวเป็น Bracket |
| 8 | test ที่ `lib/book-watch.test.ts` | `lib/book-watch.test.mjs` | ไฟล์ `.ts` ที่ import `./book-watch.ts` ต้องแก้ `tsconfig.json` ไฟล์ `.mjs` ไม่ต้อง |
| 10 | รีโป Aquarium เป็น public | เป็น private เว็บเป็น public | ตรวจด้วย `gh repo view` |
| 6 | สถานะ Unavailable อยู่ใน `page.tsx` | อยู่ใน `components/monitor/parts.tsx` | board ส่งผลกลับเป็น `BoardResult` หน้าเป็นคน render สถานะ จึงใช้ร่วม |
