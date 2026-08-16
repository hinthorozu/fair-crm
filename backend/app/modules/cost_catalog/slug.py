import re
import unicodedata

_TURKISH_TRANSLATION = str.maketrans(
    {
        "ı": "i",
        "İ": "i",
        "ş": "s",
        "Ş": "s",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    }
)


def slugify(value: str, *, fallback: str = "kategori", max_length: int = 255) -> str:
    normalized = unicodedata.normalize("NFKD", value.translate(_TURKISH_TRANSLATION))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    slug = slug[:max_length].rstrip("-")
    return slug or fallback


def next_available_slug(base_slug: str, existing_slugs: set[str], *, max_length: int = 255) -> str:
    if base_slug not in existing_slugs:
        return base_slug

    suffix = 2
    while True:
        suffix_text = f"-{suffix}"
        stem = base_slug[: max_length - len(suffix_text)].rstrip("-")
        candidate = f"{stem}{suffix_text}"
        if candidate not in existing_slugs:
            return candidate
        suffix += 1
