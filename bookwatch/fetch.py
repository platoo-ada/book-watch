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
