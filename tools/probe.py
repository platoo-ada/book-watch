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
