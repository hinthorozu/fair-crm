from app.modules.customers.domain.services.normalizers import (
    compute_normalized_name,
    normalize_company_name,
    normalize_email,
    normalize_phone,
    normalize_website,
)


def test_turkish_company_name_normalization():
    assert normalize_company_name("SİNAN ELEKTRONİK ANONİM ŞİRKETİ") == "SINAN ELEKTRONIK"
    assert normalize_company_name("Sinan Elektronik A.Ş.") == "SINAN ELEKTRONIK"


def test_company_name_normalization_strips_ltd_and_sti_suffixes():
    assert normalize_company_name("A.R.T. YAYINCILIK LTD.") == "A R T YAYINCILIK"
    assert normalize_company_name("A.R.T. YAYINCILIK LTD. ŞTİ.") == "A R T YAYINCILIK"
    assert normalize_company_name("Example Trading LIMITED") == "EXAMPLE TRADING"
    assert normalize_company_name("Example Trading LTD STI") == "EXAMPLE TRADING"


def test_compute_normalized_name_prefers_legal_name():
    assert compute_normalized_name(
        display_name="Display Co",
        legal_name="Legal A.Ş.",
    ) == "LEGAL"


def test_phone_normalization_turkish():
    assert normalize_phone("0212 555 0101") == "902125550101"
    assert normalize_phone("+90 532 000 1122") == "905320001122"


def test_email_normalization():
    assert normalize_email("  Info@Example.COM ") == "info@example.com"


def test_website_normalization():
    assert normalize_website("https://www.Example.com/path") == "example.com"
