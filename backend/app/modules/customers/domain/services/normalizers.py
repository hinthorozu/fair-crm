import re
import unicodedata
from typing import Optional

TURKISH_CHAR_MAP = str.maketrans(
    {
        "Ç": "C",
        "ç": "c",
        "Ğ": "G",
        "ğ": "g",
        "İ": "I",
        "I": "I",
        "ı": "i",
        "Ö": "O",
        "ö": "o",
        "Ş": "S",
        "ş": "s",
        "Ü": "U",
        "ü": "u",
    }
)

LEGAL_SUFFIX_PATTERNS = [
    r"\bANONIM\s+SIRKETI\b",
    r"\bANONIM\s+SIRKET\b",
    r"\bA\.?\s*S\.?\b",
    r"\bAS\b",
    r"\bLTD\.?\s*STI\.?\b",
    r"\bLIMITED\s+SIRKETI\b",
    r"\bLIMITED\s+SIRKET\b",
    r"\bLTD\.?\b",
    r"\bLIMITED\b",
    r"\bSIRKETI\b",
    r"\bSTI\.?\b",
    r"\bSANAYI\s+VE\s+TICARET\b",
    r"\bSAN\.?\s+VE\s+TIC\.?\b",
    r"\bTICARET\b",
    r"\bTIC\.?\b",
    r"\bSANAYI\b",
    r"\bSAN\.?\b",
    r"\bVE\b",
]


def normalize_company_name(value: str) -> str:
    text = value.strip()
    if not text:
        return ""

    text = text.translate(TURKISH_CHAR_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9\s]", " ", text)

    previous = None
    while previous != text:
        previous = text
        for pattern in LEGAL_SUFFIX_PATTERNS:
            text = re.sub(pattern, " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value.strip())
    if not digits:
        return ""

    if digits.startswith("90") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return "90" + digits[1:]
    if len(digits) == 10:
        return "90" + digits
    return digits


def normalize_email(value: str) -> str:
    """Lowercase and trim a single email address."""
    return value.strip().lower()


def normalize_email_list(value: str | None) -> str | None:
    """Normalize single or multi-email field to canonical semicolon-separated form."""
    from app.shared.email import normalize_email_field

    return normalize_email_field(value)


def normalize_website(value: str) -> str:
    text = value.strip().lower()
    if not text:
        return ""
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^www\.", "", text)
    text = text.split("/")[0].split("?")[0]
    return text


def compute_normalized_name(*, display_name: str, legal_name: Optional[str]) -> str:
    source = legal_name.strip() if legal_name and legal_name.strip() else display_name
    return normalize_company_name(source)
