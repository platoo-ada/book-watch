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
