"""Title cleaning and ISBN checks. Knows nothing about any specific source."""
import re
import unicodedata

_PREFIX = re.compile(r"^\s*\[[^\]]*\]\s*")
_FORMAT_PAREN = re.compile(
    r"\s*\([^()]*(?:ปกแข็ง|ปกอ่อน|ปกใหม่|จอง|รอบปกติ|รอบพิเศษ|พิมพ์ครั้งที่|ฉบับปรับปรุง)[^()]*\)\s*$")
_LATIN_THEN_THAI = re.compile(
    r"^[A-Za-z][A-Za-z0-9'’&:.\-]*(?:\s+[A-Za-z0-9&][A-Za-z0-9'’&:.\-]*)+\s+[฀-๿]")


def valid_isbn13(value):
    s = re.sub(r"[\s-]", "", str(value or ""))
    if not re.fullmatch(r"97[89]\d{10}", s):
        return None
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(s[:12]))
    return s if (10 - total % 10) % 10 == int(s[12]) else None


def clean_title(raw):
    s = re.sub(r"\s+", " ", str(raw or "").replace("\xa0", " ")).strip()
    while True:
        t = _FORMAT_PAREN.sub("", _PREFIX.sub("", s)).strip()
        if t == s:
            return s
        s = t


def title_key(title):
    # Drop punctuation (P), separators (Z), symbols (S), control (C). Keep letters, digits, Thai marks (M).
    return "".join(c for c in title.lower() if unicodedata.category(c)[0] not in "PZSC")


def maybe_translated(clean, translator):
    return bool(translator) or bool(_LATIN_THEN_THAI.match(clean))
