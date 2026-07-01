import re
import unicodedata

TURKISH_CHAR_MAP = str.maketrans(
    {
        "Ç": "c",
        "ç": "c",
        "Ğ": "g",
        "ğ": "g",
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ö": "o",
        "ö": "o",
        "Ş": "s",
        "ş": "s",
        "Ü": "u",
        "ü": "u",
    }
)

LEGAL_SUFFIX_PATTERNS = [
    r"\banonim\s+sirketi\b",
    r"\ba\.?\s*s\.?\b",
    r"\bas\b",
    r"\bltd\.?\s*sti\b",
    r"\bltd\.?\b",
    r"\blimited\s+sirketi\b",
    r"\blimited\b",
    r"\bsanayi\b",
    r"\bsan\.?\b",
    r"\bticaret\b",
    r"\btic\.?\b",
    r"\bdis\s+ticaret\b",
    r"\bithalat\b",
    r"\bihracat\b",
    r"\bve\b",
]


def normalize_import_company_name(value: str) -> str:
    """Normalize company name for import duplicate detection (lowercase key)."""
    text = value.strip()
    if not text:
        return ""

    text = text.translate(TURKISH_CHAR_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    previous = None
    while previous != text:
        previous = text
        for pattern in LEGAL_SUFFIX_PATTERNS:
            text = re.sub(pattern, " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    return text
