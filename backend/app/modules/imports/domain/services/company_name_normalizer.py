"""Turkish-aware company name normalization for import duplicate detection."""

from __future__ import annotations

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

# Legal / form tokens — excluded from *core* token comparison (not deleted from full normalize key).
LEGAL_SUFFIX_TOKENS: frozenset[str] = frozenset(
    {
        "anonim",
        "sirketi",
        "sirket",
        "limited",
        "ltd",
        "sti",
        "sanayi",
        "san",
        "ticaret",
        "tic",
        "ithalat",
        "ith",
        "ihracat",
        "ihr",
        "ve",
        "company",
        "co",
        "llc",
        "paz",
        "pazarlama",
        "dis",
        "tica",
    }
)

# Abbreviation → canonical token for equivalence matching.
TOKEN_CANONICAL: dict[str, str] = {
    "san": "sanayi",
    "sanayii": "sanayi",
    "tic": "ticaret",
    "ith": "ithalat",
    "ihr": "ihracat",
    "sti": "sirketi",
    "ltd": "limited",
    "as": "anonim",
    "co": "company",
    "urun": "urunleri",
    "urunler": "urunleri",
    "gida": "gida",
    "urunleri": "urunleri",
    "appliances": "appliance",
    "textiles": "textile",
    "technologies": "technology",
    "products": "product",
    "electric": "electrical",
    "electronics": "electronic",
    "elektronik": "electronic",
    "elektrik": "electrical",
    "machines": "machine",
    "machinery": "machine",
    "makina": "machine",
    "makine": "machine",
    "makinalari": "machine",
    "makineleri": "machine",
    "iml": "imalat",
}

# Generic sector / industry tokens — overlap on these alone must not imply a duplicate.
# Includes Turkish CRM sectors and English catalog generics seen in live FP chains
# (ZHONGSHAN/TONGXIANG electrical/textile/appliance groupings).
SECTOR_GENERIC_TOKENS: frozenset[str] = frozenset(
    {
        "gida",
        "tarim",
        "tekstil",
        "textile",
        "insaat",
        "otomotiv",
        "kimya",
        "mobilya",
        "plastik",
        "enerji",
        "lojistik",
        "yazilim",
        "turizm",
        "saglik",
        "medikal",
        "otomasyon",
        "ambalaj",
        "ahsap",
        "seramik",
        "boya",
        "kimyevi",
        # English / bilingual catalog generics
        "electrical",
        "electronic",
        "appliance",
        "machine",
        "equipment",
        "industrial",
        "industry",
        "technology",
        "trading",
        "trade",
        "manufacturing",
        "manufacture",
        "product",
        "products",
    }
)

# Multi-word legal phrases stripped from normalized string (lowercase ASCII).
LEGAL_SUFFIX_PHRASES = [
    r"\banonim\s+sirketi\b",
    r"\banonim\s+sirket\b",
    r"\ba\.?\s*s\.?\b",
    r"\bas\b",
    r"\bltd\.?\s*sti\.?\b",
    r"\bltd\.?\s*sti\b",
    r"\blimited\s+sirketi\b",
    r"\blimited\s+sirket\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\bsanayi\s+ve\s+ticaret\b",
    r"\bsan\.?\s+ve\s+tic\.?\b",
    r"\bsanayii\b",
    r"\bsanayi\b",
    r"\bsan\.?\b",
    r"\bticaret\b",
    r"\btic\.?\b",
    r"\bdış\s+ticaret\b",
    r"\bdis\s+ticaret\b",
    r"\bdis\s+tic\.?\b",
    r"\bithalat\b",
    r"\bihracat\b",
    r"\bith\.?\b",
    r"\bihr\.?\b",
    r"\bşirketi\b",
    r"\bsirketi\b",
    r"\bsti\.?\b",
    r"\bcompany\b",
    r"\bco\.?\b",
    r"\bllc\b",
    r"\bpaz\.?\b",
    r"\bpazarlama\b",
    r"\bve\b",
]


def normalize_import_company_name(value: str) -> str:
    """Normalize company name to lowercase ASCII comparison key."""
    text = value.strip()
    if not text:
        return ""

    text = text.translate(TURKISH_CHAR_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    # Dotted abbreviations (ÜRÜN.GIDA, SAN.TİC.LTD.ŞTİ.) → spaced tokens
    text = re.sub(r"[.\-/]+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    previous = None
    while previous != text:
        previous = text
        for pattern in LEGAL_SUFFIX_PHRASES:
            text = re.sub(pattern, " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    return text


def company_name_comparison_key(*, display_name: str, legal_name: str | None = None) -> str:
    """Shared exact-match key for Import + Admin company-name duplicate detection.

    Prefers legal_name when present; otherwise display_name. Uses the import
    normalizer so both flows share one comparison baseline.
    """
    source = legal_name.strip() if legal_name and legal_name.strip() else display_name
    return normalize_import_company_name(source)


def tokenize_company_name(normalized: str) -> list[str]:
    if not normalized:
        return []
    return [t for t in normalized.split() if t]


def canonicalize_token(token: str) -> str:
    return TOKEN_CANONICAL.get(token, token)


def core_tokens(tokens: list[str]) -> list[str]:
    """Tokens used for distinctive name comparison (legal suffixes excluded)."""
    canonical = [canonicalize_token(t) for t in tokens]
    core = [t for t in canonical if t not in LEGAL_SUFFIX_TOKENS]
    return core if core else canonical


def canonical_token_set(tokens: list[str]) -> set[str]:
    return {canonicalize_token(t) for t in tokens if t}
