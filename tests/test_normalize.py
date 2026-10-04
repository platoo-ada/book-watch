import unittest

from bookwatch.normalize import clean_title, maybe_translated, title_key, valid_isbn13


class IsbnTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(valid_isbn13("9786164810600"), "9786164810600")
        self.assertEqual(valid_isbn13("978-616-481-060-0"), "9786164810600")

    def test_wrong_check_digit(self):
        self.assertIsNone(valid_isbn13("9786164810601"))

    def test_not_an_isbn(self):
        for value in ("5524300004247", "1000261851", "", None, "97861648106"):
            self.assertIsNone(valid_isbn13(value), value)


class CleanTitleTest(unittest.TestCase):
    def test_strips_stacked_format_parentheses(self):
        self.assertEqual(
            clean_title("Bitcoin Age ไขประวัติศาสตร์เงินแห่งอนาคต (ปกแข็ง) (สินค้าสั่งจอง)"),
            "Bitcoin Age ไขประวัติศาสตร์เงินแห่งอนาคต")

    def test_strips_bracket_prefix(self):
        self.assertEqual(clean_title("[ตาก] Atomic Habits เพราะชีวิตดีได้กว่าที่เป็น"),
                         "Atomic Habits เพราะชีวิตดีได้กว่าที่เป็น")

    def test_strips_known_format_words(self):
        self.assertEqual(clean_title("BEYOND THE STORY : 10-YEAR RECORD OF BTS (รอบปกติ)"),
                         "BEYOND THE STORY : 10-YEAR RECORD OF BTS")
        self.assertEqual(clean_title("ปรัชญาทั่วไป (ฉบับปรับปรุง)"), "ปรัชญาทั่วไป")
        self.assertEqual(clean_title("หงส์ลายมังกร (ปกแข็ง)"), "หงส์ลายมังกร")
        self.assertEqual(clean_title("HARRY POTTER (HC) (เฉพาะจอง)"), "HARRY POTTER (HC)")

    def test_strips_store_tags_seen_in_real_data(self):
        self.assertEqual(clean_title("บ้านใต้ทะเล 100 ชั้น – ปกแข็ง"), "บ้านใต้ทะเล 100 ชั้น")
        self.assertEqual(clean_title("ไฉ่ซิ้ง มั่งคั่งอย่างเทพ (พร้อมโปสการ์ดลายเซ็นนักเขียน) (ราคาปก 295.-)"),
                         "ไฉ่ซิ้ง มั่งคั่งอย่างเทพ")
        self.assertEqual(clean_title("Origin ออริจิน พิมพ์ 9 (re-newed)"), "Origin ออริจิน พิมพ์ 9")
        self.assertEqual(clean_title("Inferno สู่นรกภูมิ 4 (New)"), "Inferno สู่นรกภูมิ 4")
        self.assertEqual(clean_title("The Lost Symbol สาส์นลับที่สาบสูญ 3(New)"), "The Lost Symbol สาส์นลับที่สาบสูญ 3")
        self.assertEqual(clean_title("เรื่องของสัตว์อันตรายน่ากลัวที่สุดในโลก (อ่อน)"), "เรื่องของสัตว์อันตรายน่ากลัวที่สุดในโลก")
        self.assertEqual(clean_title("PREORDER ชุด SET 3 เล่ม ครบรอบ 50 ปี 6 ตุลาฯ"), "ชุด SET 3 เล่ม ครบรอบ 50 ปี 6 ตุลาฯ")

    def test_keeps_parentheses_that_only_look_like_tags(self):
        for title in ("เที่ยวคนเดียว (New York)", "ชีวิตดี (ที่ยังไม่พร้อม)", "นิทานก่อนนอน (ฉบับอ่อนโยน)"):
            self.assertEqual(clean_title(title), title)

    def test_numbered_bracket_prefix_is_part_of_the_title(self):
        self.assertEqual(clean_title("[เล่ม 1] มหากาพย์"), "[เล่ม 1] มหากาพย์")
        self.assertNotEqual(title_key(clean_title("[เล่ม 1] มหากาพย์")), title_key(clean_title("[เล่ม 2] มหากาพย์")))
        self.assertEqual(clean_title("[1984]"), "[1984]")

    def test_tag_words_inside_other_words_are_kept(self):
        for title in ("คนดี (ที่จองหอง)", "รักแรก (จองเวร)", "ชีวิต (พร้อมจะรัก)", "Pre-Order Economy เศรษฐกิจแห่งการรอ"):
            self.assertEqual(clean_title(title), title)

    def test_preorder_prefix_takes_its_colon(self):
        self.assertEqual(clean_title("PREORDER: ดาวเคราะห์"), "ดาวเคราะห์")
        self.assertEqual(clean_title("PRE-ORDER : ดาวเคราะห์ (สินค้าสั่งจอง)"), "ดาวเคราะห์")

    def test_title_that_is_only_a_tag_is_not_emptied(self):
        self.assertEqual(clean_title("[ตาก]"), "[ตาก]")
        self.assertEqual(clean_title("PREORDER"), "PREORDER")
        self.assertEqual(clean_title("(ปกแข็ง)"), "(ปกแข็ง)")

    def test_keeps_meaningful_parentheses(self):
        self.assertEqual(clean_title("รัฐศาสตร์เบื้องต้น (การปกครอง)"), "รัฐศาสตร์เบื้องต้น (การปกครอง)")

    def test_collapses_whitespace(self):
        self.assertEqual(clean_title("  J.K. ROWLING\xa0  ผจญภัย  "), "J.K. ROWLING ผจญภัย")

    def test_none_and_empty(self):
        self.assertEqual(clean_title(None), "")
        self.assertEqual(clean_title(""), "")


class TitleKeyTest(unittest.TestCase):
    def test_ignores_case_space_and_punctuation(self):
        self.assertEqual(title_key("Atomic Habits: เพราะชีวิตดีได้"), title_key("atomic  habits เพราะชีวิตดีได้"))

    def test_keeps_thai_vowels_and_tone_marks(self):
        self.assertNotEqual(title_key("ป่า"), title_key("ปา"))


class TranslatedTest(unittest.TestCase):
    def test_translator_given(self):
        self.assertTrue(maybe_translated("วิมลพรรณ ปิตธวัชชัย", "ชูวัส เลี้ยงพันธุ์สกุล"))

    def test_foreign_script_author(self):
        self.assertTrue(maybe_translated("J.K. ROWLING", None))
        self.assertFalse(maybe_translated("สมชาย จิว", None))
        self.assertFalse(maybe_translated("暮兰舟 มู่หลันโจว", None))  # mixed script is not evidence

    def test_translated_category(self):
        self.assertTrue(maybe_translated(None, None, ["นิยาย, นิยายแปล"]))
        self.assertFalse(maybe_translated(None, None, ["เรื่องแปลก"]))

    def test_no_evidence_means_no_flag(self):
        self.assertFalse(maybe_translated(None, None))
        self.assertFalse(maybe_translated(None, None, ["Books", "นิยายสืบสวน"]))


if __name__ == "__main__":
    unittest.main()
