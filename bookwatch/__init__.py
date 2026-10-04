"""book-watch: weekly Thai book lists merged across sources."""

SOURCE_NAMES = {
    "seed": "SE-ED",
    "chula": "ศูนย์หนังสือจุฬาฯ",
    "amarin": "Amarin",
    "salmon": "Salmon",
    "the101": "The 101",
    "aday": "a day",
}
LIST_ORDER = ("bestseller", "recommended", "new", "preorder")
# Publisher stores sort by popularity; that is not a bestseller chart, so the label says so.
SOURCE_LIST_LABELS = {("amarin", "bestseller"): "ยอดนิยม", ("salmon", "bestseller"): "ยอดนิยม"}
LIST_LABELS = {"bestseller": "ขายดี", "recommended": "แนะนำ", "new": "ออกใหม่", "preorder": "สั่งจอง"}
