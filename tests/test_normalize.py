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
        self.assertTrue(maybe_translated("หงส์ลายมังกร", "ชูวัส เลี้ยงพันธุ์สกุล"))

    def test_two_latin_words_then_thai(self):
        self.assertTrue(maybe_translated("Atomic Habits เพราะชีวิตดีได้กว่าที่เป็น", None))

    def test_thai_title(self):
        self.assertFalse(maybe_translated("อยากเป็นคนธรรมดา ไม่ต้องอ่าน", None))

    def test_single_latin_word_or_all_latin(self):
        self.assertFalse(maybe_translated("Fearless ความกลัวสูญสิ้น", None))
        self.assertFalse(maybe_translated("BEYOND THE STORY", None))


if __name__ == "__main__":
    unittest.main()
