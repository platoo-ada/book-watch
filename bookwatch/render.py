"""Turn merged books into latest.json, latest.md and the ntfy brief."""
import re

from . import LIST_LABELS, SOURCE_LIST_LABELS, SOURCE_NAMES
from .merge import best_bestseller_rank

EMPTY = "ไม่มีข้อมูลสัปดาห์นี้"
_MD_SPECIAL = re.compile(r"([\\\[\]*_|`<>~])")


def week_id(dt):
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def build_data(generated_at, week, statuses, books, articles):
    return {"schema_version": 1, "generated_at": generated_at.isoformat(timespec="minutes"),
            "week": week, "sources": statuses, "books": books, "articles": articles}


def _esc(text):
    """One line of plain text: whitespace collapsed, Markdown and HTML characters escaped."""
    return _MD_SPECIAL.sub(r"\\\1", " ".join(str(text).split()))


def _url(url):
    """A URL that cannot end a Markdown link early."""
    url = re.sub(r"\s", "%20", url.strip()).replace("<", "%3C").replace(">", "%3E")
    if url.count("(") != url.count(")"):
        url = url.replace("(", "%28").replace(")", "%29")
    return url


def _name(source_id):
    return SOURCE_NAMES.get(source_id, source_id)


def _mention(m):
    label = SOURCE_LIST_LABELS.get((m["source"], m["list"]), LIST_LABELS[m["list"]])
    text = f"{_name(m['source'])} {label}"
    if m["list"] == "bestseller":
        text += f" #{m['rank']}"
    return f"[{text}]({_url(m['url'])})" if m["url"] else text


def _book_line(book, week):
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
    return f"- {head} — " + " · ".join(parts)


def _by_list_rank(books, kinds):
    """Books on any of the given lists, best store rank first, so each store's top picks survive the cut."""
    def best(b):
        return min(m["rank"] for m in b["mentions"] if m["list"] in kinds)
    picked = [b for b in books if set(kinds) & set(b["list_types"])]
    return sorted(picked, key=lambda b: (-b["source_count"], best(b), b["title"]))


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
            # Bullets, not "N. ": Markdown renumbers ordered lists and would hide gaps left by excluded items.
            ranked += [_book_line(b, week) for _, b in rows]
            ranked.append("")
    out += _section("อันดับที่ร้านประกาศ", ranked[:-1] if ranked else [])

    out += _section("ออกใหม่และสั่งจอง",
                    [_book_line(b, week) for b in _by_list_rank(featured, ("new", "preorder"))][:20])
    out += _section("แนะนำ",
                    [_book_line(b, week) for b in _by_list_rank(featured, ("recommended",))][:15])
    out += _section("บทความเกี่ยวกับหนังสือ",
                    [f"- [{_esc(a['title'])}]({_url(a['url'])}) ({_name(a['source'])}, {a['published']})"
                     for a in data["articles"]][:10])

    failed = [f"- {s['name']}: {_esc(s['error'])}" for s in data["sources"] if not s["ok"]]
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
    line3 = (f"ขายดี SE-ED อันดับ {best_bestseller_rank(seed[0])}: {seed[0]['title']}"
             if seed else "ขายดี SE-ED: ไม่มีข้อมูล")

    ok = sum(1 for s in data["sources"] if s["ok"])
    return "\n".join([line1, line2, line3, f"แหล่ง: {ok}/{len(data['sources'])} · {latest_url}"])
