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
