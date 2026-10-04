import datetime
import unittest

from bookwatch import merge, render
from bookwatch.fetch import TZ
from bookwatch.sources import entry

NOW = datetime.datetime(2026, 10, 5, 8, 31, tzinfo=TZ)
WEEK = "2026-W41"
OK = {"id": "seed", "name": "SE-ED (API)", "url": "https://s", "ok": True, "error": None,
      "fetched_at": "2026-10-05T08:31+07:00", "count": 5}
BAD = {"id": "chula", "name": "ศูนย์หนังสือจุฬาฯ", "url": "https://c", "ok": False,
       "error": "HTTPError: HTTP Error 403: Forbidden", "fetched_at": "2026-10-05T08:31+07:00", "count": 0}


def make_data(entries, articles=(), statuses=(OK,), prev=None):
    books = merge.merge_entries(list(entries), prev or {}, WEEK)
    arts = merge.attach_articles(books, list(articles))
    merge.sort_books(books)
    return render.build_data(NOW, WEEK, list(statuses), books, arts)


FULL = [
    entry("seed", "bestseller", 1, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "https://seed/1", isbn="9786168224465"),
    entry("chula", "bestseller", 2, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "https://chula/1", isbn="9786168224465", author="นักเขียน ก"),
    entry("seed", "new", 1, "Atomic Habits เพราะชีวิตดีได้กว่าที่เป็น", "https://seed/2"),
    entry("seed", "recommended", 1, "เล่มแนะนำ", "https://seed/3"),
    entry("seed", "bestseller", 2, "พจนานุกรมไทย", "https://seed/4"),
]


class WeekIdTest(unittest.TestCase):
    def test_iso_week(self):
        self.assertEqual(render.week_id(NOW), "2026-W41")
        self.assertEqual(render.week_id(datetime.datetime(2027, 1, 1, 9, 0, tzinfo=TZ)), "2026-W53")


class BuildDataTest(unittest.TestCase):
    def test_document_shape(self):
        data = make_data(FULL)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["generated_at"], "2026-10-05T08:31+07:00")
        self.assertEqual(data["week"], WEEK)
        self.assertEqual(data["sources"], [OK])
        self.assertEqual(len(data["books"]), 4)
        self.assertEqual(data["articles"], [])


class MarkdownTest(unittest.TestCase):
    def test_sections_and_content(self):
        md = render.to_markdown(make_data(FULL, statuses=(OK, BAD)))
        for heading in ("## เล่มเด่นของสัปดาห์", "## อันดับที่ร้านประกาศ", "## ออกใหม่และสั่งจอง",
                        "## แนะนำ", "## บทความเกี่ยวกับหนังสือ", "## ดึงไม่ได้"):
            self.assertIn(heading, md)
        self.assertIn("ดึงได้ 1 จาก 2", md)
        featured = md.split("## เล่มเด่นของสัปดาห์")[1].split("## ")[0]
        self.assertIn("อยากเป็นคนธรรมดา ไม่ต้องอ่าน", featured)
        self.assertIn("นักเขียน ก", featured)
        self.assertIn("[SE-ED ขายดี #1](https://seed/1)", featured)
        self.assertIn("[ศูนย์หนังสือจุฬาฯ ขายดี #2](https://chula/1)", featured)
        self.assertIn("ใหม่สัปดาห์นี้", featured)
        self.assertNotIn("Atomic Habits", featured)
        new = md.split("## ออกใหม่และสั่งจอง")[1].split("## ")[0]
        self.assertIn("Atomic Habits", new)
        self.assertIn("อาจเป็นงานแปล", new)
        self.assertIn("ศูนย์หนังสือจุฬาฯ: HTTPError: HTTP Error 403: Forbidden", md)
        self.assertNotIn("ยอดขาย", md)

    def test_ranking_lines_are_bullets_so_markdown_cannot_renumber_them(self):
        md = render.to_markdown(make_data([
            entry("seed", "bestseller", 1, "พจนานุกรมไทย", "https://seed/4"),
            entry("seed", "bestseller", 2, "เล่มอันดับสอง", "https://seed/5"),
            entry("seed", "bestseller", 4, "เล่มอันดับสี่", "https://seed/6")]))
        ranked = md.split("## อันดับที่ร้านประกาศ")[1].split("\n## ")[0]
        self.assertIn("### SE-ED", ranked)
        self.assertIn("- **เล่มอันดับสอง** — [SE-ED ขายดี #2](https://seed/5)", ranked)
        self.assertIn("- **เล่มอันดับสี่** — [SE-ED ขายดี #4](https://seed/6)", ranked)
        self.assertNotRegex(ranked, r"(?m)^\d+\. ")

    def test_new_and_recommended_sections_follow_store_rank_not_alphabet(self):
        entries = [entry("seed", "new", 30 - i, f"Latin title {i:02d}", f"https://seed/n{i}") for i in range(25)]
        entries += [entry("amarin", "new", 1, "เล่มใหม่อันดับหนึ่งของร้าน", "https://amarin/1"),
                    entry("seed", "recommended", 9, "Aaa recommended ninth", "https://seed/r9"),
                    entry("chula", "recommended", 1, "เล่มแนะนำอันดับหนึ่ง", "https://chula/r1")]
        md = render.to_markdown(make_data(entries))
        new = md.split("## ออกใหม่และสั่งจอง")[1].split("\n## ")[0]
        self.assertEqual(new.strip().split("\n")[0].split("**")[1], "เล่มใหม่อันดับหนึ่งของร้าน")
        self.assertEqual(new.count("\n- "), 20)
        rec = md.split("## แนะนำ")[1].split("\n## ")[0]
        self.assertLess(rec.index("เล่มแนะนำอันดับหนึ่ง"), rec.index("Aaa recommended ninth"))

    def test_angle_brackets_and_newlines_cannot_break_the_page(self):
        bad = dict(BAD, error="URLError: <urlopen error timed out>")
        md = render.to_markdown(make_data([
            entry("seed", "new", 1, "รวมบทกวี <!-- ซ่อน", "https://seed/1", author="ผู้เขียน\nสองบรรทัด"),
            entry("salmon", "new", 2, "เล่มลิงก์แปลก", "https://x.test/a b)c"),
            entry("salmon", "new", 3, "เล่มลิงก์วงเล็บครบ", "https://x.test/a-(b)/1")],
            statuses=(OK, bad),
            articles=[{"source": "aday", "title": "นักเขียน <b>ตัวหนา</b>", "url": "https://x/1", "published": "", "summary": ""}]))
        self.assertIn(r"URLError: \<urlopen error timed out\>", md)
        self.assertIn(r"รวมบทกวี \<!-- ซ่อน", md)
        self.assertIn("ผู้เขียน สองบรรทัด", md)
        self.assertIn("[Salmon ออกใหม่](https://x.test/a%20b%29c)", md)
        self.assertIn("[Salmon ออกใหม่](https://x.test/a-(b)/1)", md)
        self.assertIn(r"นักเขียน \<b\>ตัวหนา\</b\>", md)

    def test_publisher_store_popularity_is_not_labelled_bestseller(self):
        md = render.to_markdown(make_data([
            entry("amarin", "bestseller", 1, "เล่มยอดนิยมอมรินทร์", "https://amarin/1"),
            entry("salmon", "bestseller", 2, "เล่มยอดนิยมแซลมอน", "https://salmon/2")]))
        self.assertIn("[Amarin ยอดนิยม #1](https://amarin/1)", md)
        self.assertIn("[Salmon ยอดนิยม #2](https://salmon/2)", md)
        self.assertNotIn("Amarin ขายดี", md)

    def test_excluded_books_do_not_appear(self):
        self.assertNotIn("พจนานุกรมไทย", render.to_markdown(make_data(FULL)))

    def test_markdown_empty_sections_say_so(self):
        md = render.to_markdown(make_data([entry("seed", "bestseller", 1, "พจนานุกรมไทย", "https://seed/4")]))
        self.assertEqual(md.count("ไม่มีข้อมูลสัปดาห์นี้"), 5)
        self.assertIn("ดึงได้ครบทุกแหล่ง", md)

    def test_markdown_escapes_titles(self):
        md = render.to_markdown(make_data([
            entry("seed", "new", 1, "รวมเรื่องสั้น [ฉบับ*พิเศษ*] | เล่ม_1", "https://seed/9")]))
        self.assertIn(r"รวมเรื่องสั้น \[ฉบับ\*พิเศษ\*\] \| เล่ม\_1", md)
        self.assertIn("[SE-ED ออกใหม่](https://seed/9)", md)

    def test_mention_without_url_renders_as_text(self):
        md = render.to_markdown(make_data([entry("salmon", "new", 1, "เล่มไม่มีลิงก์", None)]))
        self.assertIn("Salmon ออกใหม่", md)
        self.assertNotIn("](None)", md)

    def test_not_new_when_seen_before(self):
        md = render.to_markdown(make_data(FULL, prev={"isbn:9786168224465": "2026-W39"}))
        featured = md.split("## เล่มเด่นของสัปดาห์")[1].split("## ")[0]
        self.assertNotIn("ใหม่สัปดาห์นี้", featured)

    def test_articles_listed(self):
        md = render.to_markdown(make_data(FULL, articles=[
            {"source": "the101", "title": "คุยกับนักเขียน", "url": "https://x/1", "published": "Sat, 03 Oct 2026", "summary": ""}]))
        self.assertIn("[คุยกับนักเขียน](https://x/1) (The 101, Sat, 03 Oct 2026)", md)


class BriefTest(unittest.TestCase):
    def test_brief_lines(self):
        lines = render.to_brief(make_data(FULL, statuses=(OK, BAD)), "https://latest").split("\n")
        self.assertEqual(lines, [
            "เล่มเด่น: อยากเป็นคนธรรมดา ไม่ต้องอ่าน (2 แหล่ง)",
            "ใหม่สัปดาห์นี้: 3 เล่ม เช่น อยากเป็นคนธรรมดา ไม่ต้องอ่าน",
            "ขายดี SE-ED อันดับ 1: อยากเป็นคนธรรมดา ไม่ต้องอ่าน",
            "แหล่ง: 1/2 · https://latest",
        ])

    def test_brief_reports_the_real_rank_when_rank_one_is_excluded(self):
        lines = render.to_brief(make_data([
            entry("seed", "bestseller", 1, "พจนานุกรมไทย", "https://seed/4"),
            entry("seed", "bestseller", 2, "เล่มอันดับสอง", "https://seed/5")]), "https://latest").split("\n")
        self.assertEqual(lines[2], "ขายดี SE-ED อันดับ 2: เล่มอันดับสอง")

    def test_brief_with_no_data(self):
        lines = render.to_brief(make_data([entry("seed", "bestseller", 1, "พจนานุกรมไทย", "https://seed/4")]),
                                "https://latest").split("\n")
        self.assertEqual(lines, [
            "เล่มเด่น: ไม่มีเล่มที่ติด 2 แหล่งขึ้นไป",
            "ใหม่สัปดาห์นี้: 0 เล่ม",
            "ขายดี SE-ED: ไม่มีข้อมูล",
            "แหล่ง: 1/1 · https://latest",
        ])


if __name__ == "__main__":
    unittest.main()
