# book-watch Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every Monday morning, fetch Thai bookstore and publisher lists, merge the same book across sources, rank by number of independent sources, and publish `latest.md`, `latest.json`, a weekly snapshot, and an ntfy push.

**Architecture:** One Python package (`bookwatch/`) with four stages: `sources.py` turns raw text from each site into uniform Entry dicts; `normalize.py` + `merge.py` group entries into books, filter and rank them with no knowledge of any specific site; `render.py` turns the result into JSON, Markdown and a 4-line brief. `run.py` wires the stages and a GitHub Actions workflow runs it weekly.

**Tech Stack:** Python 3.12, standard library only (`urllib`, `json`, `re`, `html`, `unicodedata`, `unittest`). GitHub Actions. ntfy.sh.

**Spec:** `docs/superpowers/specs/2026-10-04-book-watch-engine-design.md`

## Global Constraints

- Python 3.12, stdlib only. No `pip install`, no `requirements.txt`.
- Tests use `unittest` and must pass with no network access. Run with `python3 -m unittest discover -s tests -v` from the repo root.
- User-Agent for every request: `book-watch/1.0 (+https://github.com/platoo-ada/book-watch)`.
- At most 10 HTTP requests per run. Timeout 40 seconds per request. No retry within a run.
- A feed that fails or parses to 0 items is recorded with `ok: false` and an error string. It never crashes the run and never produces a blank section.
- No estimated or invented values. A field the source does not give is `null`.
- Timestamps that come from a source are stored as the source wrote them. `generated_at` and `fetched_at` carry `+07:00`.
- The word for store rankings in user-facing output is "อันดับที่ร้านประกาศ", never "ยอดขาย".
- User-facing output (`latest.md`, `brief.txt`, README) is Thai. Code, identifiers and commit messages are English.
- Blocked sources (naiin.com, Kinokuniya TH) are out of scope. Do not add workarounds.
- The repo is public. Never commit the ntfy topic, recorded third-party pages (`tests/fixtures/`), or any data about Platoo's employer.
- Creating the GitHub repo and the first push need Platoo's explicit confirmation (Task 1 Step 8). Once given, later pushes in this plan are covered.
- End every commit message with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

Inputs the spec implies but that are easy to miss. Each has a test in the owning task.

1. A site answers HTTP 200 with a block page or changed layout, so the parser raises or finds nothing. Expected: that feed is listed under "ดึงไม่ได้", other feeds still render. (Task 1 `test_parse_error_is_recorded`, Task 3 `test_chula_without_next_data_raises`)
2. A product record has a missing or null name, null category, or empty variants. Expected: the record is skipped or fields are `null`, no exception. (Task 3 `test_seed_api_skips_nameless_and_tolerates_nulls`)
3. Last week's `latest.json` is missing, truncated, or from an older shape. Expected: every book gets the current week as `first_seen`, no exception. (Task 6 `test_load_prev_tolerates_garbage`)
4. A week where no book appears in two sources, or SE-ED has no bestseller. Expected: `brief.txt` and `latest.md` say so in words, no `IndexError`. (Task 5 `test_brief_with_no_data`, `test_markdown_empty_sections_say_so`)
5. A title containing Markdown characters such as `[`, `]`, `*`, `|`. Expected: the title renders as text and links stay intact. (Task 5 `test_markdown_escapes_titles`)

## File Structure

```
book-watch/
  run.py                       entry point: fetch, merge, render, write files
  bookwatch/
    __init__.py                shared constants: SOURCE_NAMES, LIST_ORDER, LIST_LABELS
    fetch.py                   get(), run_feed(): one feed in, (status, items) out
    sources.py                 one parser per site + FEEDS table
    normalize.py               clean_title, title_key, valid_isbn13, maybe_translated
    merge.py                   merge_entries, attach_articles, sort_books + filter word lists
    render.py                  week_id, build_data, to_markdown, to_brief
  tools/
    probe.py                   reachability check for every feed URL
    record_fixtures.py         saves one real response per feed into tests/fixtures/
  tests/
    fixtures/                  recorded real responses (Task 3), gitignored
    test_fetch.py  test_normalize.py  test_sources.py
    test_merge.py  test_render.py  test_run.py
  .github/workflows/probe.yml  manual reachability check from a GitHub runner
  .github/workflows/fetch.yml  weekly run
  .gitignore  README.md
  latest.md  latest.json  weekly/   generated
```

Shared data shapes used by every task:

```python
# Entry: one row reported by one source. Built by sources.entry().
{"source": "seed", "list": "bestseller", "rank": 1, "title_raw": "...", "url": "...",
 "author": None, "translator": None, "isbn": None, "category": None, "cover": None,
 "lang": None, "is_book": True, "label": None}
# list is one of: "bestseller", "recommended", "new", "preorder"

# Article: one RSS item. Built by sources.parse_rss().
{"source": "the101", "title": "...", "url": "...", "published": "...", "summary": "..."}

# Feed: one HTTP request. Listed in sources.FEEDS.
{"id": "seed", "name": "SE-ED (API)", "url": "...", "kind": "books" | "articles",
 "parse": callable(text) -> list, "headers": {...} (optional)}

# Status: result of one feed. Built by fetch.run_feed().
{"id": "seed", "name": "SE-ED (API)", "url": "...", "ok": True, "error": None,
 "fetched_at": "2026-10-05T08:31+07:00", "count": 62}
```

---

### Task 1: Scaffold, fetch layer, and runner reachability gate

This task ends with a decision: can a GitHub runner reach the Thai stores? Do not start Task 2 until the gate in Step 9 is resolved.

**Files:**
- Create: `bookwatch/__init__.py`, `bookwatch/fetch.py`, `tools/probe.py`, `tests/__init__.py`, `tests/test_fetch.py`, `.github/workflows/probe.yml`, `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `bookwatch.SOURCE_NAMES: dict[str, str]`, `bookwatch.LIST_ORDER: tuple[str, ...]`, `bookwatch.LIST_LABELS: dict[str, str]`
  - `fetch.UA: str`, `fetch.TZ`, `fetch.now() -> datetime`
  - `fetch.get(url: str, headers: dict | None = None, timeout: int = 40) -> str`
  - `fetch.run_feed(feed: dict, getter=fetch.get) -> tuple[dict, list]` returning `(status, items)`. `getter` is called as `getter(url, headers)`. Never raises.

- [ ] **Step 1: Create package constants and ignore file**

`bookwatch/__init__.py`:

```python
"""book-watch: weekly Thai book lists merged across sources."""

SOURCE_NAMES = {
    "seed": "SE-ED",
    "chula": "ศูนย์หนังสือจุฬาฯ",
    "amarin": "Amarin",
    "salmon": "Salmon",
    "the101": "The 101",
    "aday": "a day",
}
LIST_ORDER = ("bestseller", "recommended", "new", "preorder")
LIST_LABELS = {"bestseller": "ขายดี", "recommended": "แนะนำ", "new": "ออกใหม่", "preorder": "สั่งจอง"}
```

`tests/__init__.py`: empty file.

`.gitignore`:

```
__pycache__/
brief.txt
tests/fixtures/
.DS_Store
```

`tests/fixtures/` holds raw pages recorded from the stores and magazines. They stay on the local machine and are never committed, because the repo is public and those pages are other people's content.

- [ ] **Step 2: Write the failing tests**

`tests/test_fetch.py`:

```python
import unittest

from bookwatch import fetch


def feed(parse, **extra):
    f = {"id": "x", "name": "X", "url": "https://example.test/x", "kind": "books", "parse": parse}
    f.update(extra)
    return f


class RunFeedTest(unittest.TestCase):
    def test_ok_feed_reports_count(self):
        status, items = fetch.run_feed(feed(lambda text: [text, text]), getter=lambda url, headers: "body")
        self.assertTrue(status["ok"])
        self.assertEqual(status["count"], 2)
        self.assertIsNone(status["error"])
        self.assertEqual(items, ["body", "body"])
        self.assertTrue(status["fetched_at"].endswith("+07:00"))

    def test_network_error_is_recorded(self):
        def boom(url, headers):
            raise OSError("connection refused")
        status, items = fetch.run_feed(feed(lambda text: [1]), getter=boom)
        self.assertFalse(status["ok"])
        self.assertEqual(items, [])
        self.assertIn("OSError", status["error"])

    def test_parse_error_is_recorded(self):
        def bad_parse(text):
            raise ValueError("not json")
        status, items = fetch.run_feed(feed(bad_parse), getter=lambda url, headers: "<html>blocked</html>")
        self.assertFalse(status["ok"])
        self.assertEqual(items, [])
        self.assertIn("not json", status["error"])

    def test_zero_items_is_a_failure(self):
        status, items = fetch.run_feed(feed(lambda text: []), getter=lambda url, headers: "{}")
        self.assertFalse(status["ok"])
        self.assertIn("parsed 0 items", status["error"])

    def test_feed_headers_are_passed_to_getter(self):
        seen = {}
        def getter(url, headers):
            seen.update(headers)
            return "x"
        fetch.run_feed(feed(lambda text: [1], headers={"Origin": "https://a.test"}), getter=getter)
        self.assertEqual(seen, {"Origin": "https://a.test"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: ERROR, `cannot import name 'fetch' from 'bookwatch'`.

- [ ] **Step 4: Implement `bookwatch/fetch.py`**

```python
"""HTTP get and the per-feed wrapper. A feed that fails is recorded, never silently blank."""
import datetime
import sys
import urllib.request

TZ = datetime.timezone(datetime.timedelta(hours=7))
UA = "book-watch/1.0 (+https://github.com/platoo-ada/book-watch)"


def now():
    return datetime.datetime.now(TZ)


def get(url, headers=None, timeout=40):
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def run_feed(feed, getter=get):
    """Fetch and parse one feed. Returns (status, items). Never raises."""
    status = {"id": feed["id"], "name": feed["name"], "url": feed["url"], "ok": False,
              "error": None, "fetched_at": now().isoformat(timespec="minutes"), "count": 0}
    items = []
    try:
        items = feed["parse"](getter(feed["url"], dict(feed.get("headers") or {})))
        if not items:
            raise ValueError("parsed 0 items")
        status["ok"] = True
        status["count"] = len(items)
    except Exception as e:
        items = []
        status["error"] = f"{type(e).__name__}: {e}"[:200]
    print(f"[{'ok ' if status['ok'] else 'ERR'}] {feed['name']}: {status['error'] or status['count']}", file=sys.stderr)
    return status, items
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: 5 tests, OK.

- [ ] **Step 6: Write the probe script and workflow**

`tools/probe.py`:

```python
#!/usr/bin/env python3
"""Print whether each feed URL is reachable from this machine. Exit 1 if no store answers."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from bookwatch import fetch  # noqa: E402

SEED_HEADERS = {"Origin": "https://www.se-ed.com", "Referer": "https://www.se-ed.com/"}
URLS = [
    ("seed-api", "https://mp-api.se-ed.com/web-bff/homepage-layout", SEED_HEADERS, True),
    ("seed-rank", "https://m2.se-ed.com/product/bestseller/1", None, True),
    ("chula", "https://www.chulabook.com/", None, True),
    ("amarin", "https://amarinbooks.com/wp-json/wc/store/v1/products?orderby=popularity&order=desc&per_page=20", None, False),
    ("salmon", "https://salmonbooks.net/wp-json/wc/store/v1/products?orderby=popularity&order=desc&per_page=20", None, False),
    ("the101", "https://www.the101.world/feed/", None, False),
    ("aday", "https://adaymagazine.com/feed/", None, False),
]


def main():
    stores_ok = 0
    for name, url, headers, is_store in URLS:
        try:
            body = fetch.get(url, headers)
            print(f"OK   {name:10} {len(body):>8} chars")
            stores_ok += is_store
        except Exception as e:
            print(f"FAIL {name:10} {type(e).__name__}: {e}")
    print(f"multi-publisher stores reachable: {stores_ok}/3")
    return 0 if stores_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

`.github/workflows/probe.yml`:

```yaml
name: probe
on:
  workflow_dispatch:
jobs:
  probe:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python3 tools/probe.py
```

- [ ] **Step 7: Run the probe locally**

Run: `python3 tools/probe.py`
Expected: seven `OK` lines and `multi-publisher stores reachable: 3/3` (verified from a Thai IP on 2026-10-04).

- [ ] **Step 8: Commit, create the GitHub repo, push**

Creating the public repo is outward-facing. Confirm with Platoo before running `gh repo create` unless they already said to proceed.

```bash
git add bookwatch tests tools .github .gitignore
git commit -m "feat: fetch layer and reachability probe

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
gh repo create platoo-ada/book-watch --public --source . --push \
  --description "Weekly Thai book lists merged across stores and publishers"
```

- [ ] **Step 9: Run the probe on a GitHub runner (GATE)**

```bash
gh workflow run probe.yml -R platoo-ada/book-watch
sleep 20
gh run watch -R platoo-ada/book-watch "$(gh run list -R platoo-ada/book-watch --workflow probe.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
gh run view -R platoo-ada/book-watch --log "$(gh run list -R platoo-ada/book-watch --workflow probe.yml --limit 1 --json databaseId --jq '.[0].databaseId')" | grep -E 'OK  |FAIL|reachable'
```

Decide from the output:

- `multi-publisher stores reachable: 1/3` or better: continue to Task 2. Write down which feeds printed `FAIL`; Task 3 Step 9 removes them from `FEEDS` and Task 7 lists them in the README.
- `0/3`: STOP. Report to Platoo that GitHub runners cannot reach SE-ED or Chulabook, and that the fallback in the spec (section 12) is to run the same code on Platoo's Mac from a scheduled task. Do not continue until Platoo chooses.

---

### Task 2: Title and ISBN normalisation

**Files:**
- Create: `bookwatch/normalize.py`, `tests/test_normalize.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `valid_isbn13(value) -> str | None` (the 13 digits, or `None`)
  - `clean_title(raw) -> str`
  - `title_key(title: str) -> str` (lowercase, no spaces, punctuation or symbols)
  - `maybe_translated(clean: str, translator) -> bool`

- [ ] **Step 1: Write the failing tests**

`tests/test_normalize.py`:

```python
import unittest

from bookwatch.normalize import clean_title, maybe_translated, title_key, valid_isbn13


class IsbnTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(valid_isbn13("9786164810600"), "9786164810600")
        self.assertEqual(valid_isbn13("978-616-481-060-0"), "9786164810600")

    def test_wrong_check_digit(self):
        self.assertIsNone(valid_isbn13("9786164810601"))

    def test_not_an_isbn(self):
        for value in ("5524300004247", "1000261851", "", None, "97861648106"):
            self.assertIsNone(valid_isbn13(value), value)


class CleanTitleTest(unittest.TestCase):
    def test_strips_stacked_format_parentheses(self):
        self.assertEqual(
            clean_title("Bitcoin Age ไขประวัติศาสตร์เงินแห่งอนาคต (ปกแข็ง) (สินค้าสั่งจอง)"),
            "Bitcoin Age ไขประวัติศาสตร์เงินแห่งอนาคต")

    def test_strips_bracket_prefix(self):
        self.assertEqual(clean_title("[ตาก] Atomic Habits เพราะชีวิตดีได้กว่าที่เป็น"),
                         "Atomic Habits เพราะชีวิตดีได้กว่าที่เป็น")

    def test_strips_known_format_words(self):
        self.assertEqual(clean_title("BEYOND THE STORY : 10-YEAR RECORD OF BTS (รอบปกติ)"),
                         "BEYOND THE STORY : 10-YEAR RECORD OF BTS")
        self.assertEqual(clean_title("ปรัชญาทั่วไป (ฉบับปรับปรุง)"), "ปรัชญาทั่วไป")
        self.assertEqual(clean_title("หงส์ลายมังกร (ปกแข็ง)"), "หงส์ลายมังกร")
        self.assertEqual(clean_title("HARRY POTTER (HC) (เฉพาะจอง)"), "HARRY POTTER (HC)")

    def test_keeps_meaningful_parentheses(self):
        self.assertEqual(clean_title("รัฐศาสตร์เบื้องต้น (การปกครอง)"), "รัฐศาสตร์เบื้องต้น (การปกครอง)")

    def test_collapses_whitespace(self):
        self.assertEqual(clean_title("  J.K. ROWLING\xa0  ผจญภัย  "), "J.K. ROWLING ผจญภัย")

    def test_none_and_empty(self):
        self.assertEqual(clean_title(None), "")
        self.assertEqual(clean_title(""), "")


class TitleKeyTest(unittest.TestCase):
    def test_ignores_case_space_and_punctuation(self):
        self.assertEqual(title_key("Atomic Habits: เพราะชีวิตดีได้"), title_key("atomic  habits เพราะชีวิตดีได้"))

    def test_keeps_thai_vowels_and_tone_marks(self):
        self.assertNotEqual(title_key("ป่า"), title_key("ปา"))


class TranslatedTest(unittest.TestCase):
    def test_translator_given(self):
        self.assertTrue(maybe_translated("หงส์ลายมังกร", "ชูวัส เลี้ยงพันธุ์สกุล"))

    def test_two_latin_words_then_thai(self):
        self.assertTrue(maybe_translated("Atomic Habits เพราะชีวิตดีได้กว่าที่เป็น", None))

    def test_thai_title(self):
        self.assertFalse(maybe_translated("อยากเป็นคนธรรมดา ไม่ต้องอ่าน", None))

    def test_single_latin_word_or_all_latin(self):
        self.assertFalse(maybe_translated("Fearless ความกลัวสูญสิ้น", None))
        self.assertFalse(maybe_translated("BEYOND THE STORY", None))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_normalize -v`
Expected: ERROR, `No module named 'bookwatch.normalize'`.

- [ ] **Step 3: Implement `bookwatch/normalize.py`**

```python
"""Title cleaning and ISBN checks. Knows nothing about any specific source."""
import re
import unicodedata

_PREFIX = re.compile(r"^\s*\[[^\]]*\]\s*")
_FORMAT_PAREN = re.compile(
    r"\s*\([^()]*(?:ปกแข็ง|ปกอ่อน|ปกใหม่|จอง|รอบปกติ|รอบพิเศษ|พิมพ์ครั้งที่|ฉบับปรับปรุง)[^()]*\)\s*$")
_LATIN_THEN_THAI = re.compile(
    r"^[A-Za-z][A-Za-z0-9'’&:.\-]*(?:\s+[A-Za-z0-9&][A-Za-z0-9'’&:.\-]*)+\s+[฀-๿]")


def valid_isbn13(value):
    s = re.sub(r"[\s-]", "", str(value or ""))
    if not re.fullmatch(r"97[89]\d{10}", s):
        return None
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(s[:12]))
    return s if (10 - total % 10) % 10 == int(s[12]) else None


def clean_title(raw):
    s = re.sub(r"\s+", " ", str(raw or "").replace("\xa0", " ")).strip()
    while True:
        t = _FORMAT_PAREN.sub("", _PREFIX.sub("", s)).strip()
        if t == s:
            return s
        s = t


def title_key(title):
    # Drop punctuation (P), separators (Z), symbols (S), control (C). Keep letters, digits, Thai marks (M).
    return "".join(c for c in title.lower() if unicodedata.category(c)[0] not in "PZSC")


def maybe_translated(clean, translator):
    return bool(translator) or bool(_LATIN_THEN_THAI.match(clean))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_normalize -v`
Expected: 15 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add bookwatch/normalize.py tests/test_normalize.py
git commit -m "feat: title cleaning and ISBN validation

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Source parsers and the feed table

Each parser takes the response text and returns a list. Parsers are the only code that knows a site's layout.

Verified layouts (2026-10-04):

- **SE-ED API** JSON: `homepageLayout.sections[]`, each a dict with one key. Product sections use the key `recommendedProductSection` or `popularProductSection`; under it, the same key again holds `{"adminSelected": {"title": ...}}` or `{"newest": {"title": ...}}`, and `products[]` holds `{"physicalProduct": {"physicalProduct": {id, name, category: {id, name}, cover, variants: [{sku}]}}}`. Some products are `{"eVoucher": ...}`; skip those. Book categories have ids starting with `book`.
- **SE-ED ranking** HTML: each book is `<a class='box' onclick='...' href='/Detail/<slug>/<code>' title='<title>'>` in rank order. `<code>` is an ISBN for books and another number for non-books.
- **Chulabook** HTML: `<script id="__NEXT_DATA__">` holds JSON; `props.pageProps` has `best_seller.rows`, `new_book.rows`, `pre.rows`, and `recommend[]` with `key`, `name_th`, `products`. Rows have `id`, `name`, `author`, `translator`, `isbn`, `barcode`, `lang`, `type`, `main_url_name`, `picture`.
- **WooCommerce** (Amarin, Salmon) JSON array: `name`, `sku`, `permalink`, `categories[].name`, `images[].src`. Names are HTML-escaped.
- **RSS**: `<item>` with `<title>`, `<link>`, `<pubDate>`, `<description>`, values often wrapped in CDATA.

**Files:**
- Create: `bookwatch/sources.py`, `tests/test_sources.py`, `tools/record_fixtures.py`, `tests/fixtures/*` (recorded locally, gitignored)
- Modify: `tools/probe.py` (use `FEEDS` instead of its own URL list)

**Interfaces:**
- Consumes: `normalize.valid_isbn13(value) -> str | None`
- Produces:
  - `entry(source, list_kind, rank, title_raw, url, **extra) -> dict` (Entry shape from File Structure)
  - `parse_seed_api(text) -> list[Entry]`, `parse_seed_rank(text) -> list[Entry]`, `parse_chula(text) -> list[Entry]`
  - `parse_woo(text, source, list_kind, label) -> list[Entry]`
  - `parse_rss(text, source) -> list[Article]`
  - `FEEDS: list[Feed]` (9 feeds; each has a `fixture` filename used by tests and the recorder)

- [ ] **Step 1: Write the failing tests**

`tests/test_sources.py`:

```python
import json
import pathlib
import unittest

from bookwatch import sources

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def seed_product(pid, name, cat_id="book-abc-def", sku="9786164810600"):
    return {"physicalProduct": {"physicalProduct": {
        "id": pid, "name": name, "cover": f"https://img.test/{pid}",
        "category": {"id": cat_id, "name": "หมวด"}, "variants": [{"sku": sku}]}}}


def seed_section(wrapper, mode, title, products):
    return {wrapper: {wrapper: {mode: {"title": title}}, "products": products}}


class SeedApiTest(unittest.TestCase):
    def parse(self, sections):
        return sources.parse_seed_api(json.dumps({"homepageLayout": {"sections": sections}}))

    def test_maps_section_titles_to_lists(self):
        out = self.parse([
            seed_section("recommendedProductSection", "adminSelected", "สินค้าขายดีประจำวัน", [seed_product("a1", "เล่ม A")]),
            seed_section("popularProductSection", "adminSelected", "สินค้าแนะนำประจำสัปดาห์", [seed_product("b1", "เล่ม B")]),
            seed_section("recommendedProductSection", "newest", "สินค้าออกใหม่", [seed_product("c1", "เล่ม C")]),
            seed_section("recommendedProductSection", "adminSelected", "PRE-ORDER : สินค้าสั่งจอง", [seed_product("d1", "เล่ม D")]),
            {"heroBannerSection": {"title": "Cover Banner", "banners": []}},
        ])
        self.assertEqual([(e["title_raw"], e["list"]) for e in out],
                         [("เล่ม A", "bestseller"), ("เล่ม B", "recommended"), ("เล่ม C", "new"), ("เล่ม D", "preorder")])
        first = out[0]
        self.assertEqual(first["source"], "seed")
        self.assertEqual(first["rank"], 1)
        self.assertEqual(first["url"], "https://www.se-ed.com/physical/a1")
        self.assertEqual(first["isbn"], "9786164810600")
        self.assertEqual(first["label"], "สินค้าขายดีประจำวัน")
        self.assertTrue(first["is_book"])

    def test_non_book_category_is_flagged(self):
        out = self.parse([seed_section("recommendedProductSection", "adminSelected", "สินค้าขายดีประจำวัน",
                                       [seed_product("m1", "หน้ากากอนามัย", cat_id="health-1")])])
        self.assertFalse(out[0]["is_book"])

    def test_unknown_section_title_is_skipped(self):
        out = self.parse([seed_section("recommendedProductSection", "adminSelected", "โปรโมชั่นประจำเดือน",
                                       [seed_product("x1", "เล่ม X")])])
        self.assertEqual(out, [])

    def test_seed_api_skips_nameless_and_tolerates_nulls(self):
        nulls = {"physicalProduct": {"physicalProduct": {"id": "n1", "name": "เล่ม N", "category": None,
                                                           "cover": None, "variants": []}}}
        out = self.parse([seed_section("recommendedProductSection", "adminSelected", "สินค้าขายดีประจำวัน", [
            {"eVoucher": {"id": "v1"}},
            seed_product("z1", None),
            nulls,
        ])])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["rank"], 1)
        self.assertIsNone(out[0]["isbn"])
        self.assertIsNone(out[0]["category"])
        self.assertFalse(out[0]["is_book"])


class SeedRankTest(unittest.TestCase):
    HTML = (
        "<div class='pro-item'><a class='box' onclick='return DetailTheater(this);' "
        "href='/Detail/%E0%B8%AD/9786168224465' title='อยากเป็นคนธรรมดา ไม่ต้องอ่าน'><span>1</span></a></div>"
        "<div class='pro-item'><a class='box' onclick='return DetailTheater(this);' "
        "href='/Detail/Bear/5524300004247' title='Bear &amp; Friends Coloring Book'><span>2</span></a></div>"
        "<a class='box' onclick='x' href='/Detail/%E0%B8%AD/9786168224465' title='อยากเป็นคนธรรมดา ไม่ต้องอ่าน'></a>"
    )

    def test_parses_in_rank_order_and_dedupes(self):
        out = sources.parse_seed_rank(self.HTML)
        self.assertEqual([(e["rank"], e["title_raw"]) for e in out],
                         [(1, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน"), (2, "Bear & Friends Coloring Book")])
        self.assertEqual(out[0]["url"], "https://m2.se-ed.com/Detail/%E0%B8%AD/9786168224465")
        self.assertEqual(out[0]["list"], "bestseller")
        self.assertTrue(out[0]["is_book"])
        self.assertFalse(out[1]["is_book"])

    def test_layout_change_gives_empty_list(self):
        self.assertEqual(sources.parse_seed_rank("<html><body>new layout</body></html>"), [])


class ChulaTest(unittest.TestCase):
    def html(self, page_props):
        data = json.dumps({"props": {"pageProps": page_props}}, ensure_ascii=False)
        return f'<html><script id="__NEXT_DATA__" type="application/json">{data}</script></html>'

    def row(self, pid, name, **extra):
        r = {"id": pid, "name": name, "author": "ผู้เขียน\xa0", "translator": None, "isbn": "9786166362633",
             "barcode": "9786166362633", "lang": "th", "type": "book", "main_url_name": "history",
             "picture": f"https://api.chulabook.com/images/pid-{pid}.webp"}
        r.update(extra)
        return r

    def test_parses_all_lists(self):
        out = sources.parse_chula(self.html({
            "best_seller": {"rows": [self.row("1", "หงส์ลายมังกร (ปกแข็ง)", translator="ชูวัส")]},
            "new_book": {"rows": [self.row("2", "พม่า")]},
            "pre": {"rows": [self.row("3", "HARRY POTTER", lang="en")]},
            "recommend": [
                {"key": "PRE_ORDER", "name_th": "Pre-Order", "products": [self.row("3", "HARRY POTTER", lang="en")]},
                {"key": "Distribute_Chula", "name_th": "หนังสือจัดจำหน่าย", "products": [self.row("4", "เล่มจัดจำหน่าย")]},
                {"key": "CUCourse", "name_th": "คอร์สออนไลน์", "products": [self.row("5", "คอร์ส", type="course")]},
            ],
        }))
        self.assertEqual([(e["title_raw"], e["list"]) for e in out], [
            ("หงส์ลายมังกร (ปกแข็ง)", "bestseller"), ("พม่า", "new"), ("HARRY POTTER", "preorder"),
            ("HARRY POTTER", "preorder"), ("เล่มจัดจำหน่าย", "recommended"), ("คอร์ส", "recommended")])
        first = out[0]
        self.assertEqual(first["url"], "https://www.chulabook.com/product/1")
        self.assertEqual(first["author"], "ผู้เขียน")
        self.assertEqual(first["translator"], "ชูวัส")
        self.assertEqual(first["category"], "history")
        self.assertEqual(out[2]["lang"], "en")
        self.assertEqual(out[4]["label"], "หนังสือจัดจำหน่าย")
        self.assertFalse(out[5]["is_book"])

    def test_missing_sections_are_tolerated(self):
        out = sources.parse_chula(self.html({"best_seller": {"rows": [self.row("1", "เล่มเดียว")]}}))
        self.assertEqual(len(out), 1)

    def test_chula_without_next_data_raises(self):
        with self.assertRaises(ValueError):
            sources.parse_chula("<html><body>Attention Required! | Cloudflare</body></html>")


class WooTest(unittest.TestCase):
    def test_parses_products(self):
        text = json.dumps([
            {"name": "Bear &amp; Friends", "sku": "9786162986901", "permalink": "https://salmonbooks.net/product/a/",
             "categories": [{"name": "Books"}], "images": [{"src": "https://img.test/a.jpg"}]},
            {"name": "PET Bookmark", "sku": "0000403107", "permalink": "https://amarinbooks.com/product/b/",
             "categories": [{"name": "ของแถม/พรีเมี่ยม"}], "images": []},
            {"name": None, "sku": "", "permalink": "https://x.test/", "categories": [], "images": []},
        ])
        out = sources.parse_woo(text, "salmon", "new", "ออกใหม่")
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["title_raw"], "Bear & Friends")
        self.assertEqual((out[0]["source"], out[0]["list"], out[0]["rank"], out[0]["label"]), ("salmon", "new", 1, "ออกใหม่"))
        self.assertEqual(out[0]["cover"], "https://img.test/a.jpg")
        self.assertTrue(out[0]["is_book"])
        self.assertFalse(out[1]["is_book"])
        self.assertIsNone(out[1]["cover"])


class RssTest(unittest.TestCase):
    XML = """<rss><channel><title>Feed</title>
    <item><title><![CDATA[รีวิวหนังสือ &amp; นักเขียน]]></title><link>https://a.test/1</link>
      <pubDate>Sat, 03 Oct 2026 17:20:32 +0000</pubDate>
      <description><![CDATA[<p>คำโปรย <b>ตัวหนา</b></p>]]></description></item>
    <item><title>ไม่มีลิงก์</title></item>
    </channel></rss>"""

    def test_parses_items(self):
        out = sources.parse_rss(self.XML, "the101")
        self.assertEqual(out, [{"source": "the101", "title": "รีวิวหนังสือ & นักเขียน", "url": "https://a.test/1",
                                "published": "Sat, 03 Oct 2026 17:20:32 +0000", "summary": "คำโปรย ตัวหนา"}])


class FeedsTest(unittest.TestCase):
    def test_feed_table_is_well_formed(self):
        self.assertLessEqual(len(sources.FEEDS), 10)
        for f in sources.FEEDS:
            self.assertIn(f["kind"], ("books", "articles"))
            self.assertTrue(f["url"].startswith("https://"))
            self.assertTrue(callable(f["parse"]))

    def test_recorded_fixtures_parse(self):
        for f in sources.FEEDS:
            path = FIXTURES / f["fixture"]
            if not path.exists():
                self.skipTest(f"fixture not recorded: {f['fixture']}")
            items = f["parse"](path.read_text(encoding="utf-8"))
            self.assertGreater(len(items), 0, f["name"])
            for item in items:
                self.assertTrue(item["url"], f["name"])
                self.assertTrue(item.get("title_raw") or item.get("title"), f["name"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_sources -v`
Expected: ERROR, `cannot import name 'sources' from 'bookwatch'`.

- [ ] **Step 3: Implement `bookwatch/sources.py`**

```python
"""One parser per site, plus the feed table. The only module that knows site layouts."""
import html
import json
import re

from .normalize import valid_isbn13

SEED_LISTS = (("ขายดี", "bestseller"), ("แนะนำ", "recommended"), ("ออกใหม่", "new"),
              ("PRE-ORDER", "preorder"), ("สั่งจอง", "preorder"))
NON_BOOK_CATS = ("ของแถม", "พรีเมี่ยม", "SALMART")

_SEED_RANK = re.compile(r"<a class='box'[^>]*?href='(/Detail/[^']*/([^/']+))'\s+title='([^']*)'")
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_ITEM = re.compile(r"<item\b[^>]*>(.*?)</item>", re.S)


def entry(source, list_kind, rank, title_raw, url, **extra):
    e = {"source": source, "list": list_kind, "rank": rank, "title_raw": title_raw, "url": url,
         "author": None, "translator": None, "isbn": None, "category": None, "cover": None,
         "lang": None, "is_book": True, "label": None}
    e.update(extra)
    return e


def _seed_list(title):
    for word, kind in SEED_LISTS:
        if word in title:
            return kind
    return None


def parse_seed_api(text):
    out = []
    for sec in json.loads(text)["homepageLayout"]["sections"]:
        for wrapper in ("recommendedProductSection", "popularProductSection"):
            box = sec.get(wrapper)
            if not isinstance(box, dict):
                continue
            meta = box.get(wrapper) or {}
            title = next((v["title"] for v in meta.values() if isinstance(v, dict) and v.get("title")), "")
            kind = _seed_list(title)
            if not kind:
                continue
            rank = 0
            for item in box.get("products") or []:
                p = (item.get("physicalProduct") or {}).get("physicalProduct")
                if not p or not p.get("name"):
                    continue
                rank += 1
                cat = p.get("category") or {}
                variants = p.get("variants") or [{}]
                out.append(entry(
                    "seed", kind, rank, p["name"], f"https://www.se-ed.com/physical/{p['id']}",
                    isbn=(variants[0] or {}).get("sku"), category=cat.get("name"), cover=p.get("cover"),
                    is_book=str(cat.get("id") or "").startswith("book"), label=title.strip()))
    return out


def parse_seed_rank(text):
    out, seen = [], set()
    for href, code, title in _SEED_RANK.findall(text):
        if href in seen or not title.strip():
            continue
        seen.add(href)
        out.append(entry("seed", "bestseller", len(out) + 1, html.unescape(title),
                         "https://m2.se-ed.com" + href, isbn=code,
                         is_book=valid_isbn13(code) is not None, label="หนังสือขายดีรายวัน"))
    return out


def _chula_rows(rows, kind, label):
    out = []
    for r in rows or []:
        if not r.get("name"):
            continue
        out.append(entry(
            "chula", kind, len(out) + 1, r["name"], f"https://www.chulabook.com/product/{r['id']}",
            author=(r.get("author") or "").strip() or None,
            translator=(r.get("translator") or "").strip() or None,
            isbn=r.get("isbn") or r.get("barcode"), category=r.get("main_url_name"),
            cover=r.get("picture"), lang=r.get("lang"), is_book=r.get("type") == "book", label=label))
    return out


def parse_chula(text):
    m = _NEXT_DATA.search(text)
    if not m:
        raise ValueError("__NEXT_DATA__ not found")
    pp = json.loads(m.group(1))["props"]["pageProps"]
    out = []
    for key, kind, label in (("best_seller", "bestseller", "หนังสือขายดี"),
                             ("new_book", "new", "หนังสือใหม่"), ("pre", "preorder", "Pre-Order")):
        out += _chula_rows((pp.get(key) or {}).get("rows"), kind, label)
    for group in pp.get("recommend") or []:
        kind = "preorder" if group.get("key") == "PRE_ORDER" else "recommended"
        out += _chula_rows(group.get("products"), kind, group.get("name_th"))
    return out


def parse_woo(text, source, list_kind, label):
    out = []
    for p in json.loads(text):
        if not p.get("name"):
            continue
        cats = [html.unescape(c.get("name") or "") for c in p.get("categories") or []]
        images = p.get("images") or []
        out.append(entry(
            source, list_kind, len(out) + 1, html.unescape(p["name"]), p.get("permalink"),
            isbn=p.get("sku") or None, category=", ".join(cats) or None,
            cover=images[0].get("src") if images else None,
            is_book=not any(bad in c for c in cats for bad in NON_BOOK_CATS), label=label))
    return out


def _tag(block, name):
    m = re.search(rf"<{name}\b[^>]*>(.*?)</{name}>", block, re.S)
    if not m:
        return ""
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S)
    s = re.sub(r"<[^>]+>", " ", html.unescape(s))
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_rss(text, source):
    out = []
    for block in _ITEM.findall(text):
        title, link = _tag(block, "title"), _tag(block, "link")
        if title and link:
            out.append({"source": source, "title": title, "url": link,
                        "published": _tag(block, "pubDate"), "summary": _tag(block, "description")[:500]})
    return out


def _woo_url(host, orderby):
    return f"https://{host}/wp-json/wc/store/v1/products?orderby={orderby}&order=desc&per_page=20"


def _woo(source, list_kind, label):
    return lambda text: parse_woo(text, source, list_kind, label)


def _rss(source):
    return lambda text: parse_rss(text, source)


FEEDS = [
    {"id": "seed", "name": "SE-ED (API)", "kind": "books", "fixture": "seed_api.json",
     "url": "https://mp-api.se-ed.com/web-bff/homepage-layout",
     "headers": {"Origin": "https://www.se-ed.com", "Referer": "https://www.se-ed.com/"},
     "parse": parse_seed_api},
    {"id": "seed", "name": "SE-ED (จัดอันดับ)", "kind": "books", "fixture": "seed_rank.html",
     "url": "https://m2.se-ed.com/product/bestseller/1", "parse": parse_seed_rank},
    {"id": "chula", "name": "ศูนย์หนังสือจุฬาฯ", "kind": "books", "fixture": "chula.html",
     "url": "https://www.chulabook.com/", "parse": parse_chula},
    {"id": "amarin", "name": "Amarin (ยอดนิยม)", "kind": "books", "fixture": "amarin_popular.json",
     "url": _woo_url("amarinbooks.com", "popularity"), "parse": _woo("amarin", "bestseller", "ยอดนิยมในร้านสำนักพิมพ์")},
    {"id": "amarin", "name": "Amarin (ออกใหม่)", "kind": "books", "fixture": "amarin_new.json",
     "url": _woo_url("amarinbooks.com", "date"), "parse": _woo("amarin", "new", "ออกใหม่")},
    {"id": "salmon", "name": "Salmon (ยอดนิยม)", "kind": "books", "fixture": "salmon_popular.json",
     "url": _woo_url("salmonbooks.net", "popularity"), "parse": _woo("salmon", "bestseller", "ยอดนิยมในร้านสำนักพิมพ์")},
    {"id": "salmon", "name": "Salmon (ออกใหม่)", "kind": "books", "fixture": "salmon_new.json",
     "url": _woo_url("salmonbooks.net", "date"), "parse": _woo("salmon", "new", "ออกใหม่")},
    {"id": "the101", "name": "The 101", "kind": "articles", "fixture": "the101.xml",
     "url": "https://www.the101.world/feed/", "parse": _rss("the101")},
    {"id": "aday", "name": "a day", "kind": "articles", "fixture": "aday.xml",
     "url": "https://adaymagazine.com/feed/", "parse": _rss("aday")},
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_sources -v`
Expected: all pass except `test_recorded_fixtures_parse`, which reports `skipped 'fixture not recorded: seed_api.json'`.

- [ ] **Step 5: Write the fixture recorder**

`tools/record_fixtures.py`:

```python
#!/usr/bin/env python3
"""Save one real response per feed into tests/fixtures/. Run by hand when a site changes."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bookwatch import fetch, sources  # noqa: E402


def main():
    out = ROOT / "tests" / "fixtures"
    out.mkdir(parents=True, exist_ok=True)
    for feed in sources.FEEDS:
        try:
            text = fetch.get(feed["url"], feed.get("headers"))
            (out / feed["fixture"]).write_text(text, encoding="utf-8")
            print(f"saved {feed['fixture']} ({len(text)} chars)")
        except Exception as e:
            print(f"FAIL {feed['fixture']}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Record fixtures and run the real-data test**

```bash
python3 tools/record_fixtures.py
python3 -m unittest tests.test_sources -v
du -sh tests/fixtures
```

Expected: nine `saved` lines; `test_recorded_fixtures_parse` passes (not skipped); fixtures total roughly 3 MB; `git status --short` does not list `tests/fixtures/`.

If a parser fails on real data, the layout differs from the "Verified layouts" notes above. Open the fixture, find the difference, fix the parser, and add an inline test case for the shape you found. Do not weaken the assertion.

- [ ] **Step 7: Point the probe at the feed table**

Replace the whole of `tools/probe.py` with:

```python
#!/usr/bin/env python3
"""Print whether each feed URL is reachable from this machine. Exit 1 if no store answers."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from bookwatch import fetch, sources  # noqa: E402

STORES = ("seed", "chula")


def main():
    stores_ok = set()
    for feed in sources.FEEDS:
        try:
            body = fetch.get(feed["url"], feed.get("headers"))
            print(f"OK   {feed['name']:22} {len(body):>8} chars")
            if feed["id"] in STORES:
                stores_ok.add(feed["id"])
        except Exception as e:
            print(f"FAIL {feed['name']:22} {type(e).__name__}: {e}")
    print(f"multi-publisher stores reachable: {len(stores_ok)}/{len(STORES)}")
    return 0 if stores_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

Run: `python3 tools/probe.py`
Expected: nine `OK` lines and `multi-publisher stores reachable: 2/2`.

- [ ] **Step 8: Commit**

```bash
git add bookwatch/sources.py tests/test_sources.py tools
git commit -m "feat: source parsers, feed table, fixture recorder

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

- [ ] **Step 9: Apply the Task 1 gate result**

If Task 1 Step 9 printed `FAIL` for any feed on the GitHub runner, delete that feed's dict from `FEEDS`, run the tests, and commit with message `chore: drop feeds unreachable from GitHub runners`. If nothing failed, skip this step.

---

### Task 4: Merge, filter, rank

**Files:**
- Create: `bookwatch/merge.py`, `tests/test_merge.py`

**Interfaces:**
- Consumes:
  - `normalize.valid_isbn13`, `normalize.clean_title`, `normalize.title_key`, `normalize.maybe_translated`
  - `bookwatch.LIST_ORDER`
  - Entry and Article shapes (File Structure section)
- Produces:
  - `merge_entries(entries: list[Entry], prev_first_seen: dict[str, str], week: str) -> list[Book]`
  - `attach_articles(books: list[Book], articles: list[Article]) -> list[dict]` (mutates `article_sources` and `source_count` on books; returns output articles with `matched_keys`, without `summary`)
  - `sort_books(books: list[Book]) -> None` (in place)
  - Book shape:

```python
{"key": "isbn:9786164810600", "isbn": "9786164810600", "title": "...", "author": None,
 "translator": None, "category": None, "maybe_translated": False, "article_sources": [],
 "source_count": 2, "list_types": ["bestseller", "recommended"], "featured": True,
 "excluded_reason": None, "first_seen": "2026-W41",
 "mentions": [{"source": "seed", "list": "bestseller", "rank": 1, "label": "...",
               "title_raw": "...", "url": "...", "cover": None}]}
```

  `prev_first_seen` maps a book key (`isbn:...` or `title:...`) to the week it was first seen.

- [ ] **Step 1: Write the failing tests**

`tests/test_merge.py`:

```python
import unittest

from bookwatch import merge
from bookwatch.sources import entry

WEEK = "2026-W41"
ISBN_A = "9786164810600"
ISBN_B = "9786168224465"


def books_by_title(books):
    return {b["title"]: b for b in books}


class MergeTest(unittest.TestCase):
    def test_same_isbn_from_two_sources_is_one_book(self):
        books = merge.merge_entries([
            entry("seed", "bestseller", 3, "ชื่อแบบร้าน A", "https://a", isbn=ISBN_A),
            entry("chula", "new", 1, "ชื่อแบบร้าน B ที่สะกดต่าง", "https://b", isbn=ISBN_A, author="ผู้เขียน"),
        ], {}, WEEK)
        self.assertEqual(len(books), 1)
        b = books[0]
        self.assertEqual(b["key"], "isbn:" + ISBN_A)
        self.assertEqual(b["source_count"], 2)
        self.assertEqual(b["list_types"], ["bestseller", "new"])
        self.assertEqual(b["author"], "ผู้เขียน")
        self.assertTrue(b["featured"])
        self.assertEqual(b["first_seen"], WEEK)
        self.assertEqual(len(b["mentions"]), 2)

    def test_same_clean_title_joins_entry_without_isbn(self):
        books = merge.merge_entries([
            entry("seed", "bestseller", 1, "เป็นเราคือพิเศษ (ปกแข็ง)", "https://a", isbn=ISBN_A),
            entry("amarin", "bestseller", 2, "เป็นเราคือพิเศษ", "https://b", isbn="1000240512"),
        ], {}, WEEK)
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["key"], "isbn:" + ISBN_A)
        self.assertEqual(books[0]["source_count"], 2)

    def test_hardcover_and_paperback_are_one_book(self):
        books = merge.merge_entries([
            entry("seed", "new", 1, "หงส์ลายมังกร (ปกแข็ง)", "https://a", isbn=ISBN_A),
            entry("chula", "new", 1, "หงส์ลายมังกร (ปกอ่อน)", "https://b", isbn=ISBN_B),
        ], {}, WEEK)
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["key"], "isbn:" + min(ISBN_A, ISBN_B))
        self.assertEqual(books[0]["title"], "หงส์ลายมังกร")

    def test_two_feeds_of_one_source_count_once(self):
        books = merge.merge_entries([
            entry("seed", "bestseller", 4, "เล่มเดียว", "https://api", isbn=ISBN_A),
            entry("seed", "bestseller", 2, "เล่มเดียว", "https://rank", isbn=ISBN_A),
        ], {}, WEEK)
        self.assertEqual(books[0]["source_count"], 1)
        self.assertEqual(len(books[0]["mentions"]), 1)
        self.assertEqual(books[0]["mentions"][0]["rank"], 2)
        self.assertEqual(books[0]["mentions"][0]["url"], "https://rank")

    def test_different_books_stay_apart(self):
        books = merge.merge_entries([
            entry("seed", "new", 1, "เล่มหนึ่ง", "https://a", isbn=ISBN_A),
            entry("seed", "new", 2, "เล่มสอง", "https://b", isbn=ISBN_B),
        ], {}, WEEK)
        self.assertEqual(len(books), 2)

    def test_title_only_book_gets_title_key(self):
        books = merge.merge_entries([entry("amarin", "new", 1, "Super Stimulated สุขซ่อนพิษ", "https://a")], {}, WEEK)
        self.assertEqual(books[0]["key"], "title:superstimulatedสุขซ่อนพิษ")
        self.assertIsNone(books[0]["isbn"])
        self.assertTrue(books[0]["maybe_translated"])

    def test_blank_title_is_dropped(self):
        self.assertEqual(merge.merge_entries([entry("seed", "new", 1, "  ", "https://a")], {}, WEEK), [])

    def test_translator_marks_translated(self):
        books = merge.merge_entries([entry("chula", "new", 1, "หงส์ลายมังกร", "https://a", translator="ชูวัส")], {}, WEEK)
        self.assertTrue(books[0]["maybe_translated"])
        self.assertEqual(books[0]["translator"], "ชูวัส")


class FilterTest(unittest.TestCase):
    def reason(self, *entries):
        return merge.merge_entries(list(entries), {}, WEEK)[0]["excluded_reason"]

    def test_not_book(self):
        self.assertEqual(self.reason(entry("seed", "bestseller", 1, "หน้ากากอนามัย Welcare", "https://a", is_book=False)),
                         "not_book")

    def test_book_if_any_source_says_book(self):
        self.assertIsNone(self.reason(
            entry("seed", "bestseller", 1, "นิยายเล่มหนึ่ง", "https://a", is_book=False, isbn=ISBN_A),
            entry("chula", "bestseller", 1, "นิยายเล่มหนึ่ง", "https://b", is_book=True, isbn=ISBN_A)))

    def test_not_thai(self):
        self.assertEqual(self.reason(entry("chula", "preorder", 1, "HARRY POTTER", "https://a", lang="en")), "not_thai")

    def test_unknown_language_is_kept(self):
        self.assertIsNone(self.reason(entry("seed", "new", 1, "นิยายเล่มหนึ่ง", "https://a")))

    def test_exam_by_title_word(self):
        for title in ("TGAT2 & TGAT3 การคิดอย่างมีเหตุผล", "พจนานุกรมไทย ฉบับทันสมัย", "ติวเข้ม Science",
                      "TU MOCK TEST ข้อสอบจำลอง", "แนวข้อสอบจำลอง A-Level ชีววิทยา", "คณิตคิดเร็ว อนุบาล 2",
                      "SUPER SCIENCE สรุปวิทยาศาสตร์ ม.ต้น", "ภาษาไทย ป.3"):
            self.assertEqual(self.reason(entry("seed", "bestseller", 1, title, "https://a")), "exam_reference", title)

    def test_exam_by_source_category(self):
        self.assertEqual(self.reason(entry("chula", "bestseller", 1, "ประลองโจทย์สังคม", "https://a", category="test-prep")),
                         "exam_reference")

    def test_excluded_books_are_kept_but_not_featured(self):
        books = merge.merge_entries([entry("seed", "bestseller", 1, "พจนานุกรมไทย", "https://a")], {}, WEEK)
        self.assertEqual(len(books), 1)
        self.assertFalse(books[0]["featured"])


class FirstSeenTest(unittest.TestCase):
    def test_keeps_previous_week_by_key(self):
        books = merge.merge_entries([entry("seed", "new", 1, "เล่มเก่า", "https://a", isbn=ISBN_A)],
                                    {"isbn:" + ISBN_A: "2026-W39"}, WEEK)
        self.assertEqual(books[0]["first_seen"], "2026-W39")

    def test_keeps_previous_week_when_key_changes_from_title_to_isbn(self):
        books = merge.merge_entries([entry("seed", "new", 1, "เล่มเก่า", "https://a", isbn=ISBN_A)],
                                    {"title:เล่มเก่า": "2026-W40"}, WEEK)
        self.assertEqual(books[0]["first_seen"], "2026-W40")


class ArticleTest(unittest.TestCase):
    def setUp(self):
        self.books = merge.merge_entries([
            entry("seed", "bestseller", 1, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "https://a", isbn=ISBN_A),
            entry("seed", "new", 1, "รัก", "https://b", isbn=ISBN_B),
        ], {}, WEEK)

    def test_matching_article_adds_a_source(self):
        out = merge.attach_articles(self.books, [
            {"source": "the101", "title": "รีวิวหนังสือ อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "url": "https://x/1",
             "published": "Sat, 03 Oct 2026", "summary": ""}])
        book = books_by_title(self.books)["อยากเป็นคนธรรมดา ไม่ต้องอ่าน"]
        self.assertEqual(book["article_sources"], ["the101"])
        self.assertEqual(book["source_count"], 2)
        self.assertEqual(out, [{"source": "the101", "title": "รีวิวหนังสือ อยากเป็นคนธรรมดา ไม่ต้องอ่าน",
                                "url": "https://x/1", "published": "Sat, 03 Oct 2026", "matched_keys": ["isbn:" + ISBN_A]}])

    def test_short_titles_never_match(self):
        merge.attach_articles(self.books, [
            {"source": "aday", "title": "หนังสือว่าด้วยความรัก", "url": "https://x/2", "published": "", "summary": ""}])
        self.assertEqual(books_by_title(self.books)["รัก"]["source_count"], 1)

    def test_non_book_articles_are_dropped(self):
        out = merge.attach_articles(self.books, [
            {"source": "the101", "title": "50 ปี 6 ตุลา", "url": "https://x/3", "published": "", "summary": "การเมืองไทย"}])
        self.assertEqual(out, [])

    def test_book_article_without_match_is_kept(self):
        out = merge.attach_articles(self.books, [
            {"source": "aday", "title": "คุยกับนักเขียนรุ่นใหม่", "url": "https://x/4", "published": "", "summary": ""}])
        self.assertEqual(out[0]["matched_keys"], [])

    def test_two_articles_from_one_source_count_once(self):
        article = {"source": "the101", "title": "หนังสือ อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "url": "https://x/5",
                   "published": "", "summary": ""}
        merge.attach_articles(self.books, [article, dict(article, url="https://x/6")])
        self.assertEqual(books_by_title(self.books)["อยากเป็นคนธรรมดา ไม่ต้องอ่าน"]["source_count"], 2)


class SortTest(unittest.TestCase):
    def test_order(self):
        books = merge.merge_entries([
            entry("seed", "new", 1, "ข เล่มแหล่งเดียว", "https://1"),
            entry("seed", "new", 2, "ก เล่มแหล่งเดียว", "https://2"),
            entry("seed", "bestseller", 5, "เล่มสองแหล่ง", "https://3", isbn=ISBN_A),
            entry("chula", "bestseller", 1, "เล่มสองแหล่ง", "https://4", isbn=ISBN_A),
            entry("seed", "bestseller", 2, "เล่มขายดีอันดับสอง", "https://5"),
            entry("seed", "bestseller", 1, "พจนานุกรม ติดอันดับหนึ่ง", "https://6"),
            entry("seed", "bestseller", 9, "เล่มสองประเภท", "https://7", isbn=ISBN_B),
            entry("seed", "recommended", 1, "เล่มสองประเภท", "https://8", isbn=ISBN_B),
        ], {}, WEEK)
        merge.sort_books(books)
        self.assertEqual([b["title"] for b in books], [
            "เล่มสองแหล่ง", "เล่มสองประเภท", "เล่มขายดีอันดับสอง",
            "ก เล่มแหล่งเดียว", "ข เล่มแหล่งเดียว", "พจนานุกรม ติดอันดับหนึ่ง"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_merge -v`
Expected: ERROR, `cannot import name 'merge' from 'bookwatch'`.

- [ ] **Step 3: Implement `bookwatch/merge.py`**

```python
"""Group entries into books, filter, rank. Knows nothing about any specific source."""
import re

from . import LIST_ORDER
from .normalize import clean_title, maybe_translated, title_key, valid_isbn13

# Edit these lists to tune filtering. Latin words must be upper case.
EXAM_WORDS = ("คู่มือสอบ", "เตรียมสอบ", "ติวเข้ม", "ข้อสอบ", "แบบทดสอบ", "แบบฝึกหัด", "แบบเรียน",
              "พจนานุกรม", "TGAT", "TPAT", "A-LEVEL", "MOCK TEST", "อนุบาล", "ประถม", "มัธยม",
              "ม.ต้น", "ม.ปลาย")
EXAM_CATEGORIES = ("test-prep",)
BOOK_WORDS = ("หนังสือ", "นักเขียน", "สำนักพิมพ์", "นักอ่าน", "วรรณกรรม", "นิยาย", "งานแปล")
MIN_MATCH_LEN = 8

_GRADE = re.compile(r"[ปม]\.\s?[1-6]")
_MENTION_FIELDS = ("source", "list", "rank", "label", "title_raw", "url", "cover")
_NO_RANK = 9999


def _is_exam(title, categories):
    texts = [title.upper()] + [c.upper() for c in categories]
    return (any(w in t for t in texts for w in EXAM_WORDS)
            or bool(_GRADE.search(title))
            or any(c in EXAM_CATEGORIES for c in categories))


def _excluded_reason(title, entries):
    if not any(e["is_book"] for e in entries):
        return "not_book"
    langs = {e["lang"] for e in entries if e["lang"]}
    if langs and "th" not in langs:
        return "not_thai"
    if _is_exam(title, [e["category"] for e in entries if e["category"]]):
        return "exam_reference"
    return None


def merge_entries(entries, prev_first_seen, week):
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    rows = []
    for e in entries:
        clean = clean_title(e["title_raw"])
        tkey = "title:" + title_key(clean)
        if tkey == "title:":
            continue
        isbn = valid_isbn13(e["isbn"])
        find(tkey)
        if isbn:
            parent[find("isbn:" + isbn)] = find(tkey)
        rows.append((e, clean, tkey, isbn))

    groups = {}
    for row in rows:
        groups.setdefault(find(row[2]), []).append(row)

    books = []
    for members in groups.values():
        members.sort(key=lambda r: (r[0]["source"], LIST_ORDER.index(r[0]["list"]), r[0]["rank"]))
        ents = [r[0] for r in members]
        isbns = sorted({r[3] for r in members if r[3]})
        tkeys = sorted({r[2] for r in members})
        title = members[0][1]
        key = "isbn:" + isbns[0] if isbns else tkeys[0]

        mentions = {}
        for e in ents:
            k = (e["source"], e["list"])
            if k not in mentions or e["rank"] < mentions[k]["rank"]:
                mentions[k] = {f: e[f] for f in _MENTION_FIELDS}
        mention_list = sorted(mentions.values(), key=lambda m: (m["source"], LIST_ORDER.index(m["list"])))

        def first(field):
            return next((e[field] for e in ents if e[field]), None)

        translator = first("translator")
        reason = _excluded_reason(title, ents)
        books.append({
            "key": key,
            "isbn": isbns[0] if isbns else None,
            "title": title,
            "author": first("author"),
            "translator": translator,
            "category": first("category"),
            "maybe_translated": maybe_translated(title, translator),
            "article_sources": [],
            "source_count": len({m["source"] for m in mention_list}),
            "list_types": [k for k in LIST_ORDER if any(m["list"] == k for m in mention_list)],
            "featured": reason is None,
            "excluded_reason": reason,
            "first_seen": next((prev_first_seen[k] for k in [key] + tkeys if k in prev_first_seen), week),
            "mentions": mention_list,
        })
    return books


def attach_articles(books, articles):
    index = []
    for b in books:
        short = title_key(b["title"].split(":")[0])
        if len(short) >= MIN_MATCH_LEN:
            index.append((short, b))

    out = []
    for a in articles:
        text = a["title"] + " " + a.get("summary", "")
        if not any(w in text for w in BOOK_WORDS):
            continue
        haystack = title_key(text)
        matched = []
        for short, b in index:
            if short in haystack:
                matched.append(b["key"])
                if a["source"] not in b["article_sources"]:
                    b["article_sources"].append(a["source"])
        out.append({"source": a["source"], "title": a["title"], "url": a["url"],
                    "published": a["published"], "matched_keys": sorted(matched)})

    for b in books:
        b["source_count"] = len({m["source"] for m in b["mentions"]} | set(b["article_sources"]))
    return out


def best_bestseller_rank(book):
    return min((m["rank"] for m in book["mentions"] if m["list"] == "bestseller"), default=_NO_RANK)


def sort_books(books):
    books.sort(key=lambda b: (not b["featured"], -b["source_count"], -len(b["list_types"]),
                              best_bestseller_rank(b), b["title"]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_merge -v`
Expected: 23 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add bookwatch/merge.py tests/test_merge.py
git commit -m "feat: merge entries into books, filter, rank

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: Render JSON, Markdown and brief

**Files:**
- Create: `bookwatch/render.py`, `tests/test_render.py`

**Interfaces:**
- Consumes:
  - `bookwatch.SOURCE_NAMES`, `bookwatch.LIST_LABELS`
  - `merge.best_bestseller_rank(book) -> int`
  - Book shape (Task 4), Status shape (File Structure), output article shape `{"source", "title", "url", "published", "matched_keys"}`
- Produces:
  - `week_id(dt: datetime) -> str` such as `"2026-W41"`
  - `build_data(generated_at: datetime, week: str, statuses: list, books: list, articles: list) -> dict` (the `latest.json` document, `schema_version: 1`)
  - `to_markdown(data: dict) -> str`
  - `to_brief(data: dict, latest_url: str) -> str` (exactly 4 lines)

- [ ] **Step 1: Write the failing tests**

`tests/test_render.py`:

```python
import datetime
import unittest

from bookwatch import merge, render
from bookwatch.fetch import TZ
from bookwatch.sources import entry

NOW = datetime.datetime(2026, 10, 5, 8, 31, tzinfo=TZ)
WEEK = "2026-W41"
OK = {"id": "seed", "name": "SE-ED (API)", "url": "https://s", "ok": True, "error": None,
      "fetched_at": "2026-10-05T08:31+07:00", "count": 5}
BAD = {"id": "chula", "name": "ศูนย์หนังสือจุฬาฯ", "url": "https://c", "ok": False,
       "error": "HTTPError: HTTP Error 403: Forbidden", "fetched_at": "2026-10-05T08:31+07:00", "count": 0}


def make_data(entries, articles=(), statuses=(OK,), prev=None):
    books = merge.merge_entries(list(entries), prev or {}, WEEK)
    arts = merge.attach_articles(books, list(articles))
    merge.sort_books(books)
    return render.build_data(NOW, WEEK, list(statuses), books, arts)


FULL = [
    entry("seed", "bestseller", 1, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "https://seed/1", isbn="9786168224465"),
    entry("chula", "bestseller", 2, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "https://chula/1", isbn="9786168224465", author="นักเขียน ก"),
    entry("seed", "new", 1, "Atomic Habits เพราะชีวิตดีได้กว่าที่เป็น", "https://seed/2"),
    entry("seed", "recommended", 1, "เล่มแนะนำ", "https://seed/3"),
    entry("seed", "bestseller", 2, "พจนานุกรมไทย", "https://seed/4"),
]


class WeekIdTest(unittest.TestCase):
    def test_iso_week(self):
        self.assertEqual(render.week_id(NOW), "2026-W41")
        self.assertEqual(render.week_id(datetime.datetime(2027, 1, 1, 9, 0, tzinfo=TZ)), "2026-W53")


class BuildDataTest(unittest.TestCase):
    def test_document_shape(self):
        data = make_data(FULL)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["generated_at"], "2026-10-05T08:31+07:00")
        self.assertEqual(data["week"], WEEK)
        self.assertEqual(data["sources"], [OK])
        self.assertEqual(len(data["books"]), 4)
        self.assertEqual(data["articles"], [])


class MarkdownTest(unittest.TestCase):
    def test_sections_and_content(self):
        md = render.to_markdown(make_data(FULL, statuses=(OK, BAD)))
        for heading in ("## เล่มเด่นของสัปดาห์", "## อันดับที่ร้านประกาศ", "## ออกใหม่และสั่งจอง",
                        "## แนะนำ", "## บทความเกี่ยวกับหนังสือ", "## ดึงไม่ได้"):
            self.assertIn(heading, md)
        self.assertIn("ดึงได้ 1 จาก 2", md)
        featured = md.split("## เล่มเด่นของสัปดาห์")[1].split("## ")[0]
        self.assertIn("อยากเป็นคนธรรมดา ไม่ต้องอ่าน", featured)
        self.assertIn("นักเขียน ก", featured)
        self.assertIn("[SE-ED ขายดี #1](https://seed/1)", featured)
        self.assertIn("[ศูนย์หนังสือจุฬาฯ ขายดี #2](https://chula/1)", featured)
        self.assertIn("ใหม่สัปดาห์นี้", featured)
        self.assertNotIn("Atomic Habits", featured)
        new = md.split("## ออกใหม่และสั่งจอง")[1].split("## ")[0]
        self.assertIn("Atomic Habits", new)
        self.assertIn("อาจเป็นงานแปล", new)
        self.assertIn("ศูนย์หนังสือจุฬาฯ: HTTPError: HTTP Error 403: Forbidden", md)
        self.assertNotIn("ยอดขาย", md)

    def test_excluded_books_do_not_appear(self):
        self.assertNotIn("พจนานุกรมไทย", render.to_markdown(make_data(FULL)))

    def test_markdown_empty_sections_say_so(self):
        md = render.to_markdown(make_data([entry("seed", "bestseller", 1, "พจนานุกรมไทย", "https://seed/4")]))
        self.assertEqual(md.count("ไม่มีข้อมูลสัปดาห์นี้"), 5)
        self.assertIn("ดึงได้ครบทุกแหล่ง", md)

    def test_markdown_escapes_titles(self):
        md = render.to_markdown(make_data([
            entry("seed", "new", 1, "รวมเรื่องสั้น [ฉบับ*พิเศษ*] | เล่ม_1", "https://seed/9")]))
        self.assertIn(r"รวมเรื่องสั้น \[ฉบับ\*พิเศษ\*\] \| เล่ม\_1", md)
        self.assertIn("[SE-ED ออกใหม่](https://seed/9)", md)

    def test_mention_without_url_renders_as_text(self):
        md = render.to_markdown(make_data([entry("salmon", "new", 1, "เล่มไม่มีลิงก์", None)]))
        self.assertIn("Salmon ออกใหม่", md)
        self.assertNotIn("](None)", md)

    def test_not_new_when_seen_before(self):
        md = render.to_markdown(make_data(FULL, prev={"isbn:9786168224465": "2026-W39"}))
        featured = md.split("## เล่มเด่นของสัปดาห์")[1].split("## ")[0]
        self.assertNotIn("ใหม่สัปดาห์นี้", featured)

    def test_articles_listed(self):
        md = render.to_markdown(make_data(FULL, articles=[
            {"source": "the101", "title": "คุยกับนักเขียน", "url": "https://x/1", "published": "Sat, 03 Oct 2026", "summary": ""}]))
        self.assertIn("[คุยกับนักเขียน](https://x/1) (The 101, Sat, 03 Oct 2026)", md)


class BriefTest(unittest.TestCase):
    def test_brief_lines(self):
        lines = render.to_brief(make_data(FULL, statuses=(OK, BAD)), "https://latest").split("\n")
        self.assertEqual(lines, [
            "เล่มเด่น: อยากเป็นคนธรรมดา ไม่ต้องอ่าน (2 แหล่ง)",
            "ใหม่สัปดาห์นี้: 3 เล่ม เช่น อยากเป็นคนธรรมดา ไม่ต้องอ่าน",
            "ขายดี SE-ED อันดับ 1: อยากเป็นคนธรรมดา ไม่ต้องอ่าน",
            "แหล่ง: 1/2 · https://latest",
        ])

    def test_brief_with_no_data(self):
        lines = render.to_brief(make_data([entry("seed", "bestseller", 1, "พจนานุกรมไทย", "https://seed/4")]),
                                "https://latest").split("\n")
        self.assertEqual(lines, [
            "เล่มเด่น: ไม่มีเล่มที่ติด 2 แหล่งขึ้นไป",
            "ใหม่สัปดาห์นี้: 0 เล่ม",
            "ขายดี SE-ED: ไม่มีข้อมูล",
            "แหล่ง: 1/1 · https://latest",
        ])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render -v`
Expected: ERROR, `cannot import name 'render' from 'bookwatch'`.

- [ ] **Step 3: Implement `bookwatch/render.py`**

```python
"""Turn merged books into latest.json, latest.md and the ntfy brief."""
import re

from . import LIST_LABELS, SOURCE_NAMES
from .merge import best_bestseller_rank

EMPTY = "ไม่มีข้อมูลสัปดาห์นี้"
_MD_SPECIAL = re.compile(r"([\\\[\]*_|`])")


def week_id(dt):
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def build_data(generated_at, week, statuses, books, articles):
    return {"schema_version": 1, "generated_at": generated_at.isoformat(timespec="minutes"),
            "week": week, "sources": statuses, "books": books, "articles": articles}


def _esc(text):
    return _MD_SPECIAL.sub(r"\\\1", text)


def _name(source_id):
    return SOURCE_NAMES.get(source_id, source_id)


def _mention(m):
    text = f"{_name(m['source'])} {LIST_LABELS[m['list']]}"
    if m["list"] == "bestseller":
        text += f" #{m['rank']}"
    return f"[{text}]({m['url']})" if m["url"] else text


def _book_line(book, week, prefix="- "):
    head = f"**{_esc(book['title'])}**"
    if book["author"]:
        head += f" / {_esc(book['author'])}"
    parts = [_mention(m) for m in book["mentions"]]
    if book["article_sources"]:
        parts.append("บทความ: " + ", ".join(_name(s) for s in book["article_sources"]))
    if book["maybe_translated"]:
        parts.append("อาจเป็นงานแปล")
    if book["first_seen"] == week:
        parts.append("ใหม่สัปดาห์นี้")
    return f"{prefix}{head} — " + " · ".join(parts)


def _section(title, lines):
    return [f"## {title}", ""] + (lines or [EMPTY]) + [""]


def to_markdown(data):
    week = data["week"]
    featured = [b for b in data["books"] if b["featured"]]
    ok = sum(1 for s in data["sources"] if s["ok"])
    out = [f"# book-watch {week}", "",
           f"สร้างเมื่อ {data['generated_at']} · ดึงได้ {ok} จาก {len(data['sources'])} แหล่ง", ""]

    out += _section("เล่มเด่นของสัปดาห์",
                    [_book_line(b, week) for b in featured if b["source_count"] >= 2][:15])

    ranked = []
    for source_id in SOURCE_NAMES:
        rows = sorted(((m["rank"], b) for b in featured for m in b["mentions"]
                       if m["source"] == source_id and m["list"] == "bestseller"), key=lambda r: r[0])[:10]
        if rows:
            ranked += [f"### {_name(source_id)}", ""]
            ranked += [_book_line(b, week, prefix=f"{rank}. ") for rank, b in rows]
            ranked.append("")
    out += _section("อันดับที่ร้านประกาศ", ranked[:-1] if ranked else [])

    out += _section("ออกใหม่และสั่งจอง",
                    [_book_line(b, week) for b in featured if {"new", "preorder"} & set(b["list_types"])][:20])
    out += _section("แนะนำ",
                    [_book_line(b, week) for b in featured if "recommended" in b["list_types"]][:15])
    out += _section("บทความเกี่ยวกับหนังสือ",
                    [f"- [{_esc(a['title'])}]({a['url']}) ({_name(a['source'])}, {a['published']})"
                     for a in data["articles"]][:10])

    failed = [f"- {s['name']}: {s['error']}" for s in data["sources"] if not s["ok"]]
    out += ["## ดึงไม่ได้", ""] + (failed or ["ดึงได้ครบทุกแหล่ง"])
    return "\n".join(out)


def to_brief(data, latest_url):
    week = data["week"]
    featured = [b for b in data["books"] if b["featured"]]
    top = [b for b in featured if b["source_count"] >= 2][:3]
    if top:
        names = [f"{top[0]['title']} ({top[0]['source_count']} แหล่ง)"] + [b["title"] for b in top[1:]]
        line1 = "เล่มเด่น: " + ", ".join(names)
    else:
        line1 = "เล่มเด่น: ไม่มีเล่มที่ติด 2 แหล่งขึ้นไป"

    new = [b for b in featured if b["first_seen"] == week]
    line2 = f"ใหม่สัปดาห์นี้: {len(new)} เล่ม" + (f" เช่น {new[0]['title']}" if new else "")

    seed = sorted((b for b in featured
                   if any(m["source"] == "seed" and m["list"] == "bestseller" for m in b["mentions"])),
                  key=best_bestseller_rank)
    line3 = f"ขายดี SE-ED อันดับ 1: {seed[0]['title']}" if seed else "ขายดี SE-ED: ไม่มีข้อมูล"

    ok = sum(1 for s in data["sources"] if s["ok"])
    return "\n".join([line1, line2, line3, f"แหล่ง: {ok}/{len(data['sources'])} · {latest_url}"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render -v`
Expected: 11 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add bookwatch/render.py tests/test_render.py
git commit -m "feat: render latest.json, latest.md and ntfy brief

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Entry point and first real run

**Files:**
- Create: `run.py`, `tests/test_run.py`

**Interfaces:**
- Consumes:
  - `fetch.run_feed(feed, getter) -> (status, items)`, `fetch.get`, `fetch.now()`
  - `sources.FEEDS`
  - `merge.merge_entries(entries, prev_first_seen, week)`, `merge.attach_articles(books, articles)`, `merge.sort_books(books)`
  - `render.week_id(dt)`, `render.build_data(generated_at, week, statuses, books, articles)`, `render.to_markdown(data)`, `render.to_brief(data, latest_url)`
  - `normalize.clean_title`, `normalize.title_key`
- Produces:
  - `run.load_prev(path: pathlib.Path) -> dict[str, str]`
  - `run.main(out_dir=".", getter=fetch.get, feeds=None) -> int` (0 on success, 1 when every feed failed)
  - Files in `out_dir`: `latest.md`, `latest.json`, `brief.txt`, `weekly/<week>.md`, `weekly/<week>.json`

- [ ] **Step 1: Write the failing tests**

`tests/test_run.py`:

```python
import json
import pathlib
import tempfile
import unittest

import run
from bookwatch.sources import entry


def books_feed(name, items):
    return {"id": "seed", "name": name, "url": f"https://feed.test/{name}", "kind": "books",
            "parse": lambda text: items}


def articles_feed(items):
    return {"id": "the101", "name": "The 101", "url": "https://feed.test/rss", "kind": "articles",
            "parse": lambda text: items}


def ok_getter(url, headers):
    return "body"


def failing_getter(url, headers):
    raise OSError("network down")


FEEDS = [
    books_feed("ok", [entry("seed", "bestseller", 1, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "https://seed/1",
                            isbn="9786168224465")]),
    books_feed("empty", []),
    articles_feed([{"source": "the101", "title": "รีวิวหนังสือ อยากเป็นคนธรรมดา ไม่ต้องอ่าน",
                    "url": "https://x/1", "published": "Sat, 03 Oct 2026", "summary": ""}]),
]


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_all_outputs(self):
        self.assertEqual(run.main(self.out, ok_getter, FEEDS), 0)
        data = json.loads((self.out / "latest.json").read_text(encoding="utf-8"))
        week = data["week"]
        for name in ("latest.md", "brief.txt", f"weekly/{week}.md", f"weekly/{week}.json"):
            self.assertTrue((self.out / name).exists(), name)
        self.assertEqual([s["ok"] for s in data["sources"]], [True, False, True])
        self.assertEqual(data["sources"][1]["error"], "ValueError: parsed 0 items")
        self.assertEqual(data["books"][0]["source_count"], 2)
        self.assertEqual(data["articles"][0]["matched_keys"], ["isbn:9786168224465"])
        self.assertNotIn("summary", data["articles"][0])
        self.assertEqual((self.out / "latest.json").read_text(encoding="utf-8"),
                         (self.out / f"weekly/{week}.json").read_text(encoding="utf-8"))
        self.assertIn("- empty: ValueError: parsed 0 items", (self.out / "latest.md").read_text(encoding="utf-8"))
        self.assertEqual(len((self.out / "brief.txt").read_text(encoding="utf-8").strip().split("\n")), 4)

    def test_all_feeds_failing_writes_nothing(self):
        self.assertEqual(run.main(self.out, failing_getter, FEEDS), 1)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_all_feeds_failing_keeps_last_week(self):
        (self.out / "latest.json").write_text('{"keep": true}', encoding="utf-8")
        self.assertEqual(run.main(self.out, failing_getter, FEEDS), 1)
        self.assertEqual((self.out / "latest.json").read_text(encoding="utf-8"), '{"keep": true}')

    def test_first_seen_survives_a_second_run(self):
        run.main(self.out, ok_getter, FEEDS)
        path = self.out / "latest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["books"][0]["first_seen"] = "2026-W01"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        run.main(self.out, ok_getter, FEEDS)
        again = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(again["books"][0]["first_seen"], "2026-W01")


class LoadPrevTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / "latest.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_keys_and_title_keys(self):
        self.path.write_text(json.dumps({"books": [
            {"key": "isbn:9786168224465", "title": "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "first_seen": "2026-W39"}]}),
            encoding="utf-8")
        self.assertEqual(run.load_prev(self.path), {
            "isbn:9786168224465": "2026-W39",
            "title:อยากเป็นคนธรรมดาไม่ต้องอ่าน": "2026-W39"})

    def test_load_prev_tolerates_garbage(self):
        self.assertEqual(run.load_prev(self.path), {})
        for text in ("", "{not json", "[]", '{"books": [{"title": "ไม่มี key"}]}', '{"books": "wrong"}'):
            self.path.write_text(text, encoding="utf-8")
            self.assertEqual(run.load_prev(self.path), {}, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_run -v`
Expected: ERROR, `No module named 'run'`.

- [ ] **Step 3: Implement `run.py`**

```python
#!/usr/bin/env python3
"""book-watch entry point: fetch every feed, merge, rank, write latest.* and the weekly snapshot."""
import json
import pathlib
import sys

from bookwatch import fetch, merge, render, sources
from bookwatch.normalize import clean_title, title_key

LATEST_URL = "https://github.com/platoo-ada/book-watch/blob/main/latest.md"


def load_prev(path):
    """Map book key and title key to first_seen from last run's latest.json. Empty on any problem."""
    try:
        prev = {}
        for b in json.loads(path.read_text(encoding="utf-8"))["books"]:
            prev[b["key"]] = b["first_seen"]
            prev.setdefault("title:" + title_key(clean_title(b["title"])), b["first_seen"])
        return prev
    except Exception:
        return {}


def main(out_dir=".", getter=fetch.get, feeds=None):
    out = pathlib.Path(out_dir)
    statuses, entries, articles = [], [], []
    for feed in feeds if feeds is not None else sources.FEEDS:
        status, items = fetch.run_feed(feed, getter)
        statuses.append(status)
        (articles if feed["kind"] == "articles" else entries).extend(items)

    if not any(s["ok"] for s in statuses):
        print("every feed failed; keeping last week's files", file=sys.stderr)
        return 1

    now = fetch.now()
    week = render.week_id(now)
    books = merge.merge_entries(entries, load_prev(out / "latest.json"), week)
    out_articles = merge.attach_articles(books, articles)
    merge.sort_books(books)
    data = render.build_data(now, week, statuses, books, out_articles)

    markdown = render.to_markdown(data)
    document = json.dumps(data, ensure_ascii=False, indent=1)
    (out / "weekly").mkdir(exist_ok=True)
    for path, text in ((out / "latest.md", markdown), (out / "latest.json", document),
                       (out / "weekly" / f"{week}.md", markdown), (out / "weekly" / f"{week}.json", document),
                       (out / "brief.txt", render.to_brief(data, LATEST_URL))):
        path.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the whole test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: all tests pass, none skipped (fixtures from Task 3 are present locally).

- [ ] **Step 5: Run for real and inspect the output**

```bash
python3 run.py
cat brief.txt
sed -n 1,60p latest.md
python3 -c "
import json, collections
d = json.load(open('latest.json'))
b = d['books']
print('feeds ok:', sum(s['ok'] for s in d['sources']), '/', len(d['sources']))
print('books:', len(b), 'featured:', sum(x['featured'] for x in b), 'multi-source:', sum(x['featured'] and x['source_count'] >= 2 for x in b))
print('excluded:', dict(collections.Counter(x['excluded_reason'] for x in b if x['excluded_reason'])))
print('featured sample:', [x['title'][:30] for x in b if x['featured']][:15])
"
```

Expected: stderr shows `[ok ]` for all nine feeds; `brief.txt` has 4 lines; `latest.md` has all six `##` sections.

Read the printed "featured sample" and the "ออกใหม่และสั่งจอง" section with your own eyes. Check each of these, and fix in `merge.py` word lists (adding a test case to `tests/test_merge.py` for every word you add) if any fail:

- No non-book item (mask, bookmark, voucher, course) is featured.
- No exam-prep book, textbook or dictionary is featured.
- No English-language-only edition from Chulabook is featured.
- Titles show no leftover format tags such as `(ปกแข็ง)` or `[ตาก]`.

Report the counts and anything you changed. If "multi-source" is 0, that is an expected limitation (spec section 13), not a bug; report it and continue.

- [ ] **Step 6: Commit code and the first data files**

```bash
git add run.py tests/test_run.py bookwatch tests latest.md latest.json weekly
git commit -m "feat: run.py entry point and first weekly data

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push
```

---

### Task 7: Weekly workflow, ntfy, README

**Files:**
- Create: `.github/workflows/fetch.yml`, `README.md`

**Interfaces:**
- Consumes: `python3 run.py` exit code and the files it writes; repo secret `NTFY_TOPIC`.
- Produces: a scheduled run every Monday 08:30 Asia/Bangkok that commits data and pushes a notification.

- [ ] **Step 1: Write the workflow**

`.github/workflows/fetch.yml`:

```yaml
name: fetch
on:
  schedule:
    - cron: "30 1 * * 1"   # Monday 08:30 Asia/Bangkok
  workflow_dispatch:
permissions:
  contents: write
jobs:
  fetch:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: test
        run: python3 -m unittest discover -s tests
      - name: fetch sources
        run: python3 run.py
      - name: commit
        run: |
          git config user.name "book-watch bot"
          git config user.email "bot@users.noreply.github.com"
          git add latest.md latest.json weekly/
          git diff --cached --quiet || git commit -m "data: $(date -u +%Y-%m-%dT%H:%MZ)"
          git push
      - name: notify
        if: always()
        env:
          NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
        run: |
          if [ -f brief.txt ]; then msg="$(cat brief.txt)"; prio=default; else msg="book-watch: fetch ล้มเหลว ดู Actions log"; prio=high; fi
          curl -fsS -o /dev/null -H "Title: book-watch $(TZ=Asia/Bangkok date +%d/%m\ %H:%M)" -H "Priority: $prio" -H "Tags: books" \
            -d "$msg" "https://ntfy.sh/$NTFY_TOPIC"
```

- [ ] **Step 2: Set the ntfy secret**

The topic lives in `~/.config/ntfy/config` on Platoo's Mac. Do not print it, paste it in chat, or write it to any file in the repo.

```bash
grep -c . ~/.config/ntfy/config
```

Open the file with the Read tool to see which line holds the topic name, then pipe only that value into `gh secret set NTFY_TOPIC -R platoo-ada/book-watch` on stdin (for example with `sed -n '<line>p' ~/.config/ntfy/config | cut -d= -f2 | tr -d ' "\n' | gh secret set NTFY_TOPIC -R platoo-ada/book-watch`, adjusted to the file's actual format).

Verify: `gh secret list -R platoo-ada/book-watch` shows `NTFY_TOPIC`.

- [ ] **Step 3: Write `README.md`**

```markdown
# book-watch

เฝ้าตลาดหนังสือไทยและหนังสือแปลไทยรายสัปดาห์ ดึงรายการขายดี แนะนำ และออกใหม่จากร้านและสำนักพิมพ์ รวมเล่มเดียวกันจากหลายแหล่ง แล้วเรียงตามจำนวนแหล่งอิสระที่พูดถึง

- ผลล่าสุด: [latest.md](latest.md) และ [latest.json](latest.json)
- ย้อนหลัง: `weekly/YYYY-Www.md`
- รอบ: ทุกวันจันทร์ 08:30 น. (GitHub Actions ไม่รับประกันเวลา อาจช้าได้หลายชั่วโมง)

## แหล่งข้อมูล

| แหล่ง | ได้อะไร |
|---|---|
| SE-ED | ขายดี แนะนำ ออกใหม่ สั่งจอง |
| ศูนย์หนังสือจุฬาฯ | ขายดี ออกใหม่ แนะนำ สั่งจอง |
| Amarin | ยอดนิยมและออกใหม่ในร้านสำนักพิมพ์ |
| Salmon | ยอดนิยมและออกใหม่ในร้านสำนักพิมพ์ |
| The 101, a day | บทความเกี่ยวกับหนังสือ |

## ข้อจำกัดที่ควรรู้

- "อันดับที่ร้านประกาศ" ไม่ใช่ยอดขายจริง บางร้านเป็นรายการที่แอดมินเลือก
- ไม่มีนายอินทร์และ Kinokuniya เพราะเว็บกันการดึงอัตโนมัติ
- ร้านสำนักพิมพ์ (Amarin, Salmon) แสดงเฉพาะหนังสือของตัวเอง
- ป้าย "อาจเป็นงานแปล" เป็นการเดาจากชื่อหรือจากชื่อผู้แปลที่แหล่งให้มา
- เล่มเดียวกันที่แต่ละร้านสะกดชื่อต่างกันและไม่มี ISBN จะแยกเป็นสองรายการ
- หนังสือคู่มือสอบ แบบเรียน พจนานุกรม และหนังสือภาษาต่างประเทศ ถูกเก็บใน `latest.json` (`featured: false`) แต่ไม่แสดงใน `latest.md`

## รันเอง

ต้องมี Python 3.12 ขึ้นไป ไม่มี dependency

    python3 -m unittest discover -s tests   # ทดสอบ ไม่ต่อเน็ต
    python3 run.py                          # ดึงจริง เขียน latest.* และ weekly/
    python3 tools/probe.py                  # เช็คว่าแต่ละแหล่งยังเข้าถึงได้

สั่งรันบน GitHub ทันที: `gh workflow run fetch.yml -R platoo-ada/book-watch`

## แก้ไข

- **เว็บเปลี่ยนโครง** (แหล่งขึ้นหมวด "ดึงไม่ได้" พร้อม `parsed 0 items`): แก้ตัวแกะของแหล่งนั้นใน `bookwatch/sources.py` แล้วรัน `python3 tools/record_fixtures.py` เพื่อบันทึกตัวอย่างใหม่
- **เพิ่มแหล่ง**: เขียนฟังก์ชัน `parse_<ชื่อ>(text)` ที่คืนรายการจาก `entry(...)` เพิ่ม 1 แถวใน `FEEDS` และเพิ่มชื่อใน `SOURCE_NAMES` (`bookwatch/__init__.py`) รวมทุกแหล่งไม่เกิน 10 คำขอต่อรอบ
- **ปรับคำกรอง**: แก้ `EXAM_WORDS`, `EXAM_CATEGORIES`, `BOOK_WORDS` ต้นไฟล์ `bookwatch/merge.py` และ `NON_BOOK_CATS` ใน `bookwatch/sources.py`
- **โครง `latest.json`**: ดู spec ใน `docs/superpowers/specs/` ถ้าเปลี่ยนโครงให้ขยับ `schema_version`
```

If Task 3 Step 9 dropped any feed, remove its row from the source table and add one line under "ข้อจำกัดที่ควรรู้" naming the source and saying it is unreachable from GitHub runners.

- [ ] **Step 4: Commit and push**

```bash
git add .github/workflows/fetch.yml README.md
git commit -m "feat: weekly workflow with ntfy, README

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push
```

- [ ] **Step 5: Run the workflow and verify end to end**

```bash
gh workflow run fetch.yml -R platoo-ada/book-watch
sleep 20
RUN="$(gh run list -R platoo-ada/book-watch --workflow fetch.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
gh run watch -R platoo-ada/book-watch "$RUN" --exit-status
gh run view -R platoo-ada/book-watch "$RUN" --log | grep -E '\[(ok |ERR)\]'
git pull
git log --oneline -3
```

Expected:

- The run finishes green.
- The log shows one `[ok ]` or `[ERR]` line per feed. Compare with the local run in Task 6: a feed that is `ok` locally but `ERR` on the runner is blocked for runner IPs; handle it as in Task 3 Step 9 and note it in the README.
- `git log` shows a `data: ...` commit from "book-watch bot" (or no new commit if the data is identical to the Task 6 commit).
- Ask Platoo to confirm the ntfy notification arrived on their phone with a 4-line body. This is the one check that cannot be verified from the terminal.

- [ ] **Step 6: Record the project in memory and hand off**

Write a project memory file `project_book_watch.md` in `/Users/supasistpimto/.claude/projects/-Users-supasistpimto/memory/` (type `project`) with: repo path and GitHub name, weekly schedule, how to trigger a run by hand, the list of live feeds, the known limits from README, and that sub-projects 2 (Aquarium `/monitor/book-watch`) and 3 (`wnv-publish` input) are not started and depend on `latest.json` `schema_version: 1`. Add one line to `MEMORY.md`. Link `[[project_watch_kb]]` and `[[project_aquarium_portfolio]]`. Also add a `book-watch/` row to the Folder Map table in `/Users/supasistpimto/Work-space/CLAUDE.md`, next to the `watch-kb/` row, pointing to `README.md` and the memory file.
