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
