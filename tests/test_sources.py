import json
import pathlib
import unittest

from bookwatch import sources

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def seed_product(pid, name, cat_id="book-abc-def", sku="9786164810600"):
    return {"physicalProduct": {"physicalProduct": {
        "id": pid, "name": name, "cover": f"https://img.test/{pid}",
        "category": {"id": cat_id, "name": "หมวด"}, "variants": [{"sku": sku}]}}}


def seed_section(wrapper, mode, title, products):
    return {wrapper: {wrapper: {mode: {"title": title}}, "products": products}}


class SeedApiTest(unittest.TestCase):
    def parse(self, sections):
        return sources.parse_seed_api(json.dumps({"homepageLayout": {"sections": sections}}))

    def test_maps_section_titles_to_lists(self):
        out = self.parse([
            seed_section("recommendedProductSection", "adminSelected", "สินค้าขายดีประจำวัน", [seed_product("a1", "เล่ม A")]),
            seed_section("popularProductSection", "adminSelected", "สินค้าแนะนำประจำสัปดาห์", [seed_product("b1", "เล่ม B")]),
            seed_section("recommendedProductSection", "newest", "สินค้าออกใหม่", [seed_product("c1", "เล่ม C")]),
            seed_section("recommendedProductSection", "adminSelected", "PRE-ORDER : สินค้าสั่งจอง", [seed_product("d1", "เล่ม D")]),
            {"heroBannerSection": {"title": "Cover Banner", "banners": []}},
        ])
        self.assertEqual([(e["title_raw"], e["list"]) for e in out],
                         [("เล่ม A", "bestseller"), ("เล่ม B", "recommended"), ("เล่ม C", "new"), ("เล่ม D", "preorder")])
        first = out[0]
        self.assertEqual(first["source"], "seed")
        self.assertEqual(first["rank"], 1)
        self.assertEqual(first["url"], "https://www.se-ed.com/physical/a1")
        self.assertEqual(first["isbn"], "9786164810600")
        self.assertEqual(first["label"], "สินค้าขายดีประจำวัน")
        self.assertTrue(first["is_book"])

    def test_non_book_category_is_flagged(self):
        out = self.parse([seed_section("recommendedProductSection", "adminSelected", "สินค้าขายดีประจำวัน",
                                       [seed_product("m1", "หน้ากากอนามัย", cat_id="health-1")])])
        self.assertFalse(out[0]["is_book"])

    def test_unknown_section_title_is_skipped(self):
        out = self.parse([seed_section("recommendedProductSection", "adminSelected", "โปรโมชั่นประจำเดือน",
                                       [seed_product("x1", "เล่ม X")])])
        self.assertEqual(out, [])

    def test_seed_api_null_category_with_isbn_is_a_book(self):
        p = {"physicalProduct": {"physicalProduct": {"id": "n2", "name": "เล่มไม่มีหมวด", "category": None,
                                                       "cover": None, "variants": [{"sku": "9786164810600"}]}}}
        out = self.parse([seed_section("recommendedProductSection", "adminSelected", "สินค้าขายดีประจำวัน", [p])])
        self.assertTrue(out[0]["is_book"])

    def test_seed_api_row_without_id_is_skipped_not_fatal(self):
        bad = seed_product("x", "เล่มไม่มี id")
        del bad["physicalProduct"]["physicalProduct"]["id"]
        out = self.parse([seed_section("recommendedProductSection", "adminSelected", "สินค้าขายดีประจำวัน",
                                       [bad, seed_product("g1", "เล่มดี")])])
        self.assertEqual([(e["title_raw"], e["rank"]) for e in out], [("เล่มดี", 1)])

    def test_seed_api_skips_nameless_and_tolerates_nulls(self):
        nulls = {"physicalProduct": {"physicalProduct": {"id": "n1", "name": "เล่ม N", "category": None,
                                                           "cover": None, "variants": []}}}
        out = self.parse([seed_section("recommendedProductSection", "adminSelected", "สินค้าขายดีประจำวัน", [
            {"eVoucher": {"id": "v1"}},
            seed_product("z1", None),
            nulls,
        ])])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["rank"], 1)
        self.assertIsNone(out[0]["isbn"])
        self.assertIsNone(out[0]["category"])
        self.assertFalse(out[0]["is_book"])


class SeedRankTest(unittest.TestCase):
    HTML = (
        "<div class='pro-item'><a class='box' onclick='return DetailTheater(this);' "
        "href='/Detail/%E0%B8%AD/9786168224465' title='อยากเป็นคนธรรมดา ไม่ต้องอ่าน'><span>1</span></a></div>"
        "<div class='pro-item'><a class='box' onclick='return DetailTheater(this);' "
        "href='/Detail/Bear/5524300004247' title='Bear &amp; Friends Coloring Book'><span>2</span></a></div>"
        "<a class='box' onclick='x' href='/Detail/%E0%B8%AD/9786168224465' title='อยากเป็นคนธรรมดา ไม่ต้องอ่าน'></a>"
    )

    def test_parses_in_rank_order_and_dedupes(self):
        out = sources.parse_seed_rank(self.HTML)
        self.assertEqual([(e["rank"], e["title_raw"]) for e in out],
                         [(1, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน"), (2, "Bear & Friends Coloring Book")])
        self.assertEqual(out[0]["url"], "https://m2.se-ed.com/Detail/%E0%B8%AD/9786168224465")
        self.assertEqual(out[0]["list"], "bestseller")
        self.assertTrue(out[0]["is_book"])
        self.assertFalse(out[1]["is_book"])

    def test_layout_change_gives_empty_list(self):
        self.assertEqual(sources.parse_seed_rank("<html><body>new layout</body></html>"), [])


class ChulaTest(unittest.TestCase):
    def html(self, page_props):
        data = json.dumps({"props": {"pageProps": page_props}}, ensure_ascii=False)
        return f'<html><script id="__NEXT_DATA__" type="application/json">{data}</script></html>'

    def row(self, pid, name, **extra):
        r = {"id": pid, "name": name, "author": "ผู้เขียน\xa0", "translator": None, "isbn": "9786166362633",
             "barcode": "9786166362633", "lang": "th", "type": "book", "main_url_name": "history",
             "picture": f"https://api.chulabook.com/images/pid-{pid}.webp"}
        r.update(extra)
        return r

    def test_parses_all_lists(self):
        out = sources.parse_chula(self.html({
            "best_seller": {"rows": [self.row("1", "หงส์ลายมังกร (ปกแข็ง)", translator="ชูวัส")]},
            "new_book": {"rows": [self.row("2", "พม่า")]},
            "pre": {"rows": [self.row("3", "HARRY POTTER", lang="en")]},
            "recommend": [
                {"key": "PRE_ORDER", "name_th": "Pre-Order", "products": [self.row("3", "HARRY POTTER", lang="en")]},
                {"key": "Distribute_Chula", "name_th": "หนังสือจัดจำหน่าย", "products": [self.row("4", "เล่มจัดจำหน่าย")]},
                {"key": "CUCourse", "name_th": "คอร์สออนไลน์", "products": [self.row("5", "คอร์ส", type="course")]},
            ],
        }))
        self.assertEqual([(e["title_raw"], e["list"]) for e in out], [
            ("หงส์ลายมังกร (ปกแข็ง)", "bestseller"), ("พม่า", "new"), ("HARRY POTTER", "preorder"),
            ("HARRY POTTER", "preorder"), ("เล่มจัดจำหน่าย", "recommended"), ("คอร์ส", "recommended")])
        first = out[0]
        self.assertEqual(first["url"], "https://www.chulabook.com/product/1")
        self.assertEqual(first["author"], "ผู้เขียน")
        self.assertEqual(first["translator"], "ชูวัส")
        self.assertEqual(first["category"], "history")
        self.assertEqual(out[2]["lang"], "en")
        self.assertEqual(out[4]["label"], "หนังสือจัดจำหน่าย")
        self.assertFalse(out[5]["is_book"])

    def test_chula_row_without_id_is_skipped_not_fatal(self):
        bad = self.row("9", "เล่มไม่มี id")
        del bad["id"]
        out = sources.parse_chula(self.html({"best_seller": {"rows": [bad, self.row("1", "เล่มดี")]}}))
        self.assertEqual([(e["title_raw"], e["rank"]) for e in out], [("เล่มดี", 1)])

    def test_missing_sections_are_tolerated(self):
        out = sources.parse_chula(self.html({"best_seller": {"rows": [self.row("1", "เล่มเดียว")]}}))
        self.assertEqual(len(out), 1)

    def test_chula_without_next_data_raises(self):
        with self.assertRaises(ValueError):
            sources.parse_chula("<html><body>Attention Required! | Cloudflare</body></html>")


class WooTest(unittest.TestCase):
    def test_parses_products(self):
        text = json.dumps([
            {"name": "Bear &amp; Friends", "sku": "9786162986901", "permalink": "https://salmonbooks.net/product/a/",
             "categories": [{"name": "Books"}], "images": [{"src": "https://img.test/a.jpg"}]},
            {"name": "PET Bookmark", "sku": "0000403107", "permalink": "https://amarinbooks.com/product/b/",
             "categories": [{"name": "ของแถม/พรีเมี่ยม"}], "images": []},
            {"name": None, "sku": "", "permalink": "https://x.test/", "categories": [], "images": []},
        ])
        out = sources.parse_woo(text, "salmon", "new", "ออกใหม่")
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["title_raw"], "Bear & Friends")
        self.assertEqual((out[0]["source"], out[0]["list"], out[0]["rank"], out[0]["label"]), ("salmon", "new", 1, "ออกใหม่"))
        self.assertEqual(out[0]["cover"], "https://img.test/a.jpg")
        self.assertTrue(out[0]["is_book"])
        self.assertFalse(out[1]["is_book"])
        self.assertIsNone(out[1]["cover"])
        self.assertIsNone(out[0]["translator"])

    def test_translator_from_credit_line_only(self):
        def product(short):
            return {"name": "เล่ม", "sku": "", "permalink": "https://x.test/", "categories": [], "images": [],
                    "short_description": short}
        text = json.dumps([
            product("<p>เรื่องและภาพ มิโดริ บะโช<br />\nแปล หนึ่งฤทัย ปราดเปรียว<br />\nพบกับสามเพื่อนรัก</p>"),
            product("<p>ผู้เขียน : <strong>มู่หลันโจว</strong><br />\nผู้แปล : <strong>ย้วยยี้</strong><br />\nนักวาด : x</p>"),
            product("<p>นำเรื่องจริงมาดัดแปลงเป็นเรื่องแต่ง</p>\n<p>แปลไปแล้วกว่า 31 ประเทศ ผู้คนแปลกหน้า</p>"),
        ])
        out = sources.parse_woo(text, "amarin", "new", "ออกใหม่")
        self.assertEqual([e["translator"] for e in out], ["หนึ่งฤทัย ปราดเปรียว", "ย้วยยี้", None])


class RssTest(unittest.TestCase):
    XML = """<rss><channel><title>Feed</title>
    <item><title><![CDATA[รีวิวหนังสือ &amp; นักเขียน]]></title><link>https://a.test/1</link>
      <pubDate>Sat, 03 Oct 2026 17:20:32 +0000</pubDate>
      <description><![CDATA[<p>คำโปรย <b>ตัวหนา</b></p>]]></description></item>
    <item><title>ไม่มีลิงก์</title></item>
    </channel></rss>"""

    def test_parses_items(self):
        out = sources.parse_rss(self.XML, "the101")
        self.assertEqual(out, [{"source": "the101", "title": "รีวิวหนังสือ & นักเขียน", "url": "https://a.test/1",
                                "published": "Sat, 03 Oct 2026 17:20:32 +0000", "summary": "คำโปรย ตัวหนา"}])


class FeedsTest(unittest.TestCase):
    def test_feed_table_is_well_formed(self):
        self.assertLessEqual(len(sources.FEEDS), 10)
        for f in sources.FEEDS:
            self.assertIn(f["kind"], ("books", "articles"))
            self.assertTrue(f["url"].startswith("https://"))
            self.assertTrue(callable(f["parse"]))

    def test_recorded_fixtures_parse(self):
        for f in sources.FEEDS:
            path = FIXTURES / f["fixture"]
            if not path.exists():
                self.skipTest(f"fixture not recorded: {f['fixture']}")
            items = f["parse"](path.read_text(encoding="utf-8"))
            self.assertGreater(len(items), 0, f["name"])
            for item in items:
                self.assertTrue(item["url"], f["name"])
                self.assertTrue(item.get("title_raw") or item.get("title"), f["name"])


if __name__ == "__main__":
    unittest.main()
