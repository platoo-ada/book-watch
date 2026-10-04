"""Title cleaning and ISBN checks. Knows nothing about any specific source."""
import re
import unicodedata

_THAI = "฀-๿"
# A leading bracket is a store tag only when it holds no digit: "[ตาก]" goes, "[เล่ม 1]" stays.
_PREFIX = re.compile(r"^\s*(?:\[[^\]\d]*\]|PRE-?ORDER\b\s*:?)\s*")
# A trailing parenthesis is a store tag when it holds a format word, starts with a bundle phrase,
# or is exactly a short edition marker. Any other parenthesis is part of the title.
# "จอง" must end its word, so "(สั่งจอง)" matches and "(ที่จองหอง)" does not.
_FORMAT_PAREN = re.compile(
    r"\s*\((?:[^()]*(?:ปกแข็ง|ปกอ่อน|ปกใหม่|จอง(?![" + _THAI + r"])|รอบปกติ|รอบพิเศษ|พิมพ์ครั้งที่|ฉบับปรับปรุง)[^()]*"
    r"|\s*พร้อม(?:ของ|สินค้า|โปสการ์ด|ชุด|ที่คั่น|ที่แขวน|ลายเซ็น|กล่อง|เฉลย|คลิป|ไฟล์|CD|MP3)[^()]*"
    r"|\s*ราคาปก[^()]*"
    r"|\s*(?:New|re-newed|อ่อน|แข็ง)\s*)\)\s*$")
_FORMAT_DASH = re.compile(r"\s*[–—-]\s*(?:ปกแข็ง|ปกอ่อน)\s*$")
_LATIN_THEN_THAI = re.compile(
    r"^[A-Za-z][A-Za-z0-9'’&:.\-]*(?:\s+[A-Za-z0-9&][A-Za-z0-9'’&:.\-]*)+\s+[" + _THAI + r"]")


def valid_isbn13(value):
    s = re.sub(r"[\s-]", "", str(value or ""))
    if not re.fullmatch(r"97[89]\d{10}", s):
        return None
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(s[:12]))
    return s if (10 - total % 10) % 10 == int(s[12]) else None


def clean_title(raw):
    raw = s = re.sub(r"\s+", " ", str(raw or "").replace("\xa0", " ")).strip()
    while True:
        t = _FORMAT_DASH.sub("", _FORMAT_PAREN.sub("", _PREFIX.sub("", s))).strip()
        if t == s:
            return s or raw  # a title that is nothing but a tag keeps its text
        s = t


def title_key(title):
    # Drop punctuation (P), separators (Z), symbols (S), control (C). Keep letters, digits, Thai marks (M).
    return "".join(c for c in title.lower() if unicodedata.category(c)[0] not in "PZSC")


def maybe_translated(clean, translator):
    return bool(translator) or bool(_LATIN_THEN_THAI.match(clean))
