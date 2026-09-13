"""كتالوج الرصيد وخدمة تسويق السيرة الذاتية."""

TOPUP_PACKAGES = [
    {"code": "topup_57", "points": 57, "amount": 19, "saving": ""},
    {"code": "topup_176", "points": 176, "amount": 49, "saving": "وفّر 15%"},
    {"code": "topup_425", "points": 425, "amount": 99, "saving": "وفّر 30%"},
    {"code": "topup_545", "points": 545, "amount": 119, "saving": "وفّر 33%"},
    {"code": "topup_665", "points": 665, "amount": 139, "saving": "وفّر 36%"},
]

BLAST_CATEGORIES = [
    ("it", "تقنية ومعلومات"),
    ("finance", "مالية ومحاسبة"),
    ("health", "صحة وطب"),
    ("education", "تعليم وتدريب"),
    ("construction", "مقاولات وعقارات"),
    ("energy", "نفط وطاقة"),
    ("hospitality", "سياحة وضيافة"),
    ("legal", "قانون واستشارات"),
    ("industry", "صناعة وتصنيع"),
    ("media", "تسويق وإعلام"),
]

BLAST_PACKAGES = [
    {"code": "blast_100", "companies": 100, "points": 50},
    {"code": "blast_300", "companies": 300, "points": 116},
    {"code": "blast_800", "companies": 800, "points": 241},
    {"code": "blast_1833", "companies": 1833, "points": 448},
]


def category_name(code: str) -> str:
    return dict(BLAST_CATEGORIES).get(code, code)