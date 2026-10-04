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
