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


def load_history(out):
    """Earliest first_seen per key across every weekly snapshot and latest.json.

    Reading only last week's file would make a book look new again after one week away
    (for example when its feed was down).
    """
    history = {}
    for path in sorted((out / "weekly").glob("*.json")) + [out / "latest.json"]:
        for key, week in load_prev(path).items():
            if isinstance(week, str) and (key not in history or week < history[key]):
                history[key] = week
    return history


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
    books = merge.merge_entries(entries, load_history(out), week)
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
