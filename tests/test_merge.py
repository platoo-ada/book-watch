import unittest

from bookwatch import merge
from bookwatch.sources import entry

WEEK = "2026-W41"
ISBN_A = "9786164810600"
ISBN_B = "9786168224465"


def books_by_title(books):
    return {b["title"]: b for b in books}


class MergeTest(unittest.TestCase):
    def test_same_isbn_from_two_sources_is_one_book(self):
        books = merge.merge_entries([
            entry("seed", "bestseller", 3, "ชื่อแบบร้าน A", "https://a", isbn=ISBN_A),
            entry("chula", "new", 1, "ชื่อแบบร้าน B ที่สะกดต่าง", "https://b", isbn=ISBN_A, author="ผู้เขียน"),
        ], {}, WEEK)
        self.assertEqual(len(books), 1)
        b = books[0]
        self.assertEqual(b["key"], "isbn:" + ISBN_A)
        self.assertEqual(b["source_count"], 2)
        self.assertEqual(b["list_types"], ["bestseller", "new"])
        self.assertEqual(b["author"], "ผู้เขียน")
        self.assertTrue(b["featured"])
        self.assertEqual(b["first_seen"], WEEK)
        self.assertEqual(len(b["mentions"]), 2)

    def test_same_clean_title_joins_entry_without_isbn(self):
        books = merge.merge_entries([
            entry("seed", "bestseller", 1, "เป็นเราคือพิเศษ (ปกแข็ง)", "https://a", isbn=ISBN_A),
            entry("amarin", "bestseller", 2, "เป็นเราคือพิเศษ", "https://b", isbn="1000240512"),
        ], {}, WEEK)
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["key"], "isbn:" + ISBN_A)
        self.assertEqual(books[0]["source_count"], 2)

    def test_hardcover_and_paperback_are_one_book(self):
        books = merge.merge_entries([
            entry("seed", "new", 1, "หงส์ลายมังกร (ปกแข็ง)", "https://a", isbn=ISBN_A),
            entry("chula", "new", 1, "หงส์ลายมังกร (ปกอ่อน)", "https://b", isbn=ISBN_B),
        ], {}, WEEK)
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["key"], "isbn:" + min(ISBN_A, ISBN_B))
        self.assertEqual(books[0]["title"], "หงส์ลายมังกร")

    def test_two_feeds_of_one_source_count_once(self):
        books = merge.merge_entries([
            entry("seed", "bestseller", 4, "เล่มเดียว", "https://api", isbn=ISBN_A),
            entry("seed", "bestseller", 2, "เล่มเดียว", "https://rank", isbn=ISBN_A),
        ], {}, WEEK)
        self.assertEqual(books[0]["source_count"], 1)
        self.assertEqual(len(books[0]["mentions"]), 1)
        self.assertEqual(books[0]["mentions"][0]["rank"], 2)
        self.assertEqual(books[0]["mentions"][0]["url"], "https://rank")

    def test_different_books_stay_apart(self):
        books = merge.merge_entries([
            entry("seed", "new", 1, "เล่มหนึ่ง", "https://a", isbn=ISBN_A),
            entry("seed", "new", 2, "เล่มสอง", "https://b", isbn=ISBN_B),
        ], {}, WEEK)
        self.assertEqual(len(books), 2)

    def test_title_only_book_gets_title_key(self):
        books = merge.merge_entries([entry("amarin", "new", 1, "Super Stimulated สุขซ่อนพิษ", "https://a")], {}, WEEK)
        self.assertEqual(books[0]["key"], "title:superstimulatedสุขซ่อนพิษ")
        self.assertIsNone(books[0]["isbn"])

    def test_english_title_alone_is_not_translated(self):
        books = merge.merge_entries([entry("salmon", "new", 1, "SEE LANKA เอวังที่ลังกา", "https://a")], {}, WEEK)
        self.assertFalse(books[0]["maybe_translated"])

    def test_latin_author_or_translated_category_marks_translated(self):
        books = merge.merge_entries([
            entry("chula", "preorder", 1, "แพ็กชุด POCKET POTTERS", "https://a", author="J.K. ROWLING"),
            entry("amarin", "new", 1, "เทวากับซาตาน", "https://b", category="นิยาย, นิยายแปล"),
        ], {}, WEEK)
        self.assertEqual([b["maybe_translated"] for b in books], [True, True])

    def test_blank_title_is_dropped(self):
        self.assertEqual(merge.merge_entries([entry("seed", "new", 1, "  ", "https://a")], {}, WEEK), [])

    def test_translator_marks_translated(self):
        books = merge.merge_entries([entry("chula", "new", 1, "หงส์ลายมังกร", "https://a", translator="ชูวัส")], {}, WEEK)
        self.assertTrue(books[0]["maybe_translated"])
        self.assertEqual(books[0]["translator"], "ชูวัส")


class FilterTest(unittest.TestCase):
    def reason(self, *entries):
        return merge.merge_entries(list(entries), {}, WEEK)[0]["excluded_reason"]

    def test_not_book(self):
        self.assertEqual(self.reason(entry("seed", "bestseller", 1, "หน้ากากอนามัย Welcare", "https://a", is_book=False)),
                         "not_book")

    def test_book_if_any_source_says_book(self):
        self.assertIsNone(self.reason(
            entry("seed", "bestseller", 1, "นิยายเล่มหนึ่ง", "https://a", is_book=False, isbn=ISBN_A),
            entry("chula", "bestseller", 1, "นิยายเล่มหนึ่ง", "https://b", is_book=True, isbn=ISBN_A)))

    def test_not_thai(self):
        self.assertEqual(self.reason(entry("chula", "preorder", 1, "HARRY POTTER", "https://a", lang="en")), "not_thai")

    def test_unknown_language_is_kept(self):
        self.assertIsNone(self.reason(entry("seed", "new", 1, "นิยายเล่มหนึ่ง", "https://a")))

    def test_exam_by_title_word(self):
        for title in ("TGAT2 & TGAT3 การคิดอย่างมีเหตุผล", "พจนานุกรมไทย ฉบับทันสมัย", "ติวเข้ม Science",
                      "TU MOCK TEST ข้อสอบจำลอง", "แนวข้อสอบจำลอง A-Level ชีววิทยา", "คณิตคิดเร็ว อนุบาล 2",
                      "SUPER SCIENCE สรุปวิทยาศาสตร์ ม.ต้น", "ภาษาไทย ป.3", "TOPIK 1"):
            self.assertEqual(self.reason(entry("seed", "bestseller", 1, title, "https://a")), "exam_reference", title)

    def test_grade_pattern_does_not_match_bangkok_abbreviation(self):
        self.assertIsNone(self.reason(entry("seed", "new", 1, "เที่ยว กทม. 1 วัน", "https://a")))
        self.assertEqual(self.reason(entry("seed", "new", 1, "สรุปเข้มม.4", "https://a")), "exam_reference")

    def test_exam_by_source_category(self):
        self.assertEqual(self.reason(entry("chula", "bestseller", 1, "ประลองโจทย์สังคม", "https://a", category="test-prep")),
                         "exam_reference")

    def test_clinical_textbook_category_is_excluded(self):
        self.assertEqual(self.reason(entry("chula", "recommended", 1, "การพยาบาลจิตเวช", "https://a",
                                           category="medical-and-nursing", lang="th")), "exam_reference")

    def test_excluded_books_are_kept_but_not_featured(self):
        books = merge.merge_entries([entry("seed", "bestseller", 1, "พจนานุกรมไทย", "https://a")], {}, WEEK)
        self.assertEqual(len(books), 1)
        self.assertFalse(books[0]["featured"])


class FirstSeenTest(unittest.TestCase):
    def test_keeps_previous_week_by_key(self):
        books = merge.merge_entries([entry("seed", "new", 1, "เล่มเก่า", "https://a", isbn=ISBN_A)],
                                    {"isbn:" + ISBN_A: "2026-W39"}, WEEK)
        self.assertEqual(books[0]["first_seen"], "2026-W39")

    def test_keeps_previous_week_when_key_changes_from_title_to_isbn(self):
        books = merge.merge_entries([entry("seed", "new", 1, "เล่มเก่า", "https://a", isbn=ISBN_A)],
                                    {"title:เล่มเก่า": "2026-W40"}, WEEK)
        self.assertEqual(books[0]["first_seen"], "2026-W40")


class ArticleTest(unittest.TestCase):
    def setUp(self):
        self.books = merge.merge_entries([
            entry("seed", "bestseller", 1, "อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "https://a", isbn=ISBN_A),
            entry("seed", "new", 1, "รัก", "https://b", isbn=ISBN_B),
        ], {}, WEEK)

    def test_matching_article_adds_a_source(self):
        out = merge.attach_articles(self.books, [
            {"source": "the101", "title": "รีวิวหนังสือ อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "url": "https://x/1",
             "published": "Sat, 03 Oct 2026", "summary": ""}])
        book = books_by_title(self.books)["อยากเป็นคนธรรมดา ไม่ต้องอ่าน"]
        self.assertEqual(book["article_sources"], ["the101"])
        self.assertEqual(book["source_count"], 2)
        self.assertEqual(out, [{"source": "the101", "title": "รีวิวหนังสือ อยากเป็นคนธรรมดา ไม่ต้องอ่าน",
                                "url": "https://x/1", "published": "Sat, 03 Oct 2026", "matched_keys": ["isbn:" + ISBN_A]}])

    def test_part_of_a_title_before_a_colon_does_not_match(self):
        books = merge.merge_entries([
            entry("seed", "new", 1, "Manifest : 7 ขั้นตอนสู่ทุกสิ่งที่ปรารถนา", "https://a")], {}, WEEK)
        out = merge.attach_articles(books, [
            {"source": "the101", "title": "อ่าน Communist Manifesto ใหม่ในวันที่สำนักพิมพ์เล็กกำลังหายไป",
             "url": "https://x/9", "published": "", "summary": ""}])
        self.assertEqual(out[0]["matched_keys"], [])
        self.assertEqual(books[0]["source_count"], 1)

    def test_short_titles_never_match(self):
        merge.attach_articles(self.books, [
            {"source": "aday", "title": "หนังสือว่าด้วยความรัก", "url": "https://x/2", "published": "", "summary": ""}])
        self.assertEqual(books_by_title(self.books)["รัก"]["source_count"], 1)

    def test_non_book_articles_are_dropped(self):
        out = merge.attach_articles(self.books, [
            {"source": "the101", "title": "50 ปี 6 ตุลา", "url": "https://x/3", "published": "", "summary": "การเมืองไทย"}])
        self.assertEqual(out, [])

    def test_book_article_without_match_is_kept(self):
        out = merge.attach_articles(self.books, [
            {"source": "aday", "title": "คุยกับนักเขียนรุ่นใหม่", "url": "https://x/4", "published": "", "summary": ""}])
        self.assertEqual(out[0]["matched_keys"], [])

    def test_two_articles_from_one_source_count_once(self):
        article = {"source": "the101", "title": "หนังสือ อยากเป็นคนธรรมดา ไม่ต้องอ่าน", "url": "https://x/5",
                   "published": "", "summary": ""}
        merge.attach_articles(self.books, [article, dict(article, url="https://x/6")])
        self.assertEqual(books_by_title(self.books)["อยากเป็นคนธรรมดา ไม่ต้องอ่าน"]["source_count"], 2)


class SortTest(unittest.TestCase):
    def test_order(self):
        books = merge.merge_entries([
            entry("seed", "new", 1, "ข เล่มแหล่งเดียว", "https://1"),
            entry("seed", "new", 2, "ก เล่มแหล่งเดียว", "https://2"),
            entry("seed", "bestseller", 5, "เล่มสองแหล่ง", "https://3", isbn=ISBN_A),
            entry("chula", "bestseller", 1, "เล่มสองแหล่ง", "https://4", isbn=ISBN_A),
            entry("seed", "bestseller", 2, "เล่มขายดีอันดับสอง", "https://5"),
            entry("seed", "bestseller", 1, "พจนานุกรม ติดอันดับหนึ่ง", "https://6"),
            entry("seed", "bestseller", 9, "เล่มสองประเภท", "https://7", isbn=ISBN_B),
            entry("seed", "recommended", 1, "เล่มสองประเภท", "https://8", isbn=ISBN_B),
        ], {}, WEEK)
        merge.sort_books(books)
        self.assertEqual([b["title"] for b in books], [
            "เล่มสองแหล่ง", "เล่มสองประเภท", "เล่มขายดีอันดับสอง",
            "ก เล่มแหล่งเดียว", "ข เล่มแหล่งเดียว", "พจนานุกรม ติดอันดับหนึ่ง"])


if __name__ == "__main__":
    unittest.main()
