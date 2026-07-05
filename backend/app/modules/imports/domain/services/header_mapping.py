"""Canonical import field definitions and Excel header aliases.

CANONICAL_FIELDS is source-agnostic — all import adapters (Excel, PDF, scraper, database)
must produce row dicts keyed by these fields before entering the shared pipeline.
"""

CANONICAL_FIELDS = frozenset(
    {
        "company_name",
        "email",
        "phone",
        "mobile_phone",
        "website",
        "country",
        "city",
        "address",
        "tax_number",
        "contact_first_name",
        "contact_last_name",
        "contact_title",
        "contact_department",
        "contact_email",
        "contact_phone",
        "contact_mobile_phone",
        "notes",
        "hall",
        "stand",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
        "instagram_url",
        "facebook_url",
        "linkedin_url",
        "youtube_url",
    }
)

HEADER_ALIASES: dict[str, str] = {
    "firma adi": "company_name",
    "firma adı": "company_name",
    "sirket adi": "company_name",
    "şirket adı": "company_name",
    "e-posta": "email",
    "email": "email",
    "telefon": "phone",
    "cep telefonu": "mobile_phone",
    "web": "website",
    "web sitesi": "website",
    "ulke": "country",
    "ülke": "country",
    "sehir": "city",
    "şehir": "city",
    "adres": "address",
    "vergi no": "tax_number",
    "yetkili adi": "contact_first_name",
    "yetkili adı": "contact_first_name",
    "yetkili soyadi": "contact_last_name",
    "yetkili soyadı": "contact_last_name",
    "yetkili unvani": "contact_title",
    "yetkili ünvanı": "contact_title",
    "departman": "contact_department",
    "yetkili e-posta": "contact_email",
    "yetkili telefon": "contact_phone",
    "yetkili cep telefonu": "contact_mobile_phone",
    "notlar": "notes",
    "not": "notes",
    "salon": "hall",
    "salon / hall": "hall",
    "stand": "stand",
    "stand no": "stand",
    "instagram": "instagram_url",
    "facebook": "facebook_url",
    "linkedin": "linkedin_url",
    "youtube": "youtube_url",
    "instagram url": "instagram_url",
    "facebook url": "facebook_url",
    "linkedin url": "linkedin_url",
    "youtube url": "youtube_url",
}

for field in CANONICAL_FIELDS:
    HEADER_ALIASES.setdefault(field, field)
    HEADER_ALIASES.setdefault(field.replace("_", " "), field)


def normalize_header(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("_", " ")
    return " ".join(text.split())


def map_header_to_field(header: str) -> str | None:
    normalized = normalize_header(header)
    return HEADER_ALIASES.get(normalized)
