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
