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


    def test_first_seen_survives_a_week_where_the_book_was_missing(self):
        # Week 1 saw the book; last week's latest.json did not (its feed was down).
        (self.out / "weekly").mkdir()
        (self.out / "weekly" / "2026-W01.json").write_text(json.dumps({"books": [
            {"key": "isbn:9786168224465", "title": "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "first_seen": "2026-W01"}]}),
            encoding="utf-8")
        (self.out / "weekly" / "2026-W02.json").write_text('{"books": []}', encoding="utf-8")
        (self.out / "weekly" / "broken.json").write_text("{not json", encoding="utf-8")
        (self.out / "latest.json").write_text('{"books": []}', encoding="utf-8")
        run.main(self.out, ok_getter, FEEDS)
        data = json.loads((self.out / "latest.json").read_text(encoding="utf-8"))
        self.assertEqual(data["books"][0]["first_seen"], "2026-W01")
        self.assertIn("ใหม่สัปดาห์นี้: 0 เล่ม", (self.out / "brief.txt").read_text(encoding="utf-8"))


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
