from pathlib import Path

import pytest

from app.modules.scraper.extractors.contact_extractor import (
    extract_contacts_from_html,
    is_junk_email,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "customer_enrichment"


def test_is_junk_email_filters_common_noise():
    assert is_junk_email("noreply@example.com") is True
    assert is_junk_email("info@example.com") is True
    assert is_junk_email("info@asmedikal.com.tr") is False
    assert is_junk_email("sales@vector-best.ru") is False
    assert is_junk_email("contact@company.test") is False
    assert is_junk_email("iletisim@firma.com.tr") is False
    assert is_junk_email("icon-ada-swabs@2x-1.png") is True
    assert is_junk_email("youremail@mail.com") is True
    assert is_junk_email("yourname@mail.com") is True
    assert is_junk_email("suemail@mail.com") is True
    assert is_junk_email("mail@example.com") is True
    assert is_junk_email("info@company.com") is False


def test_extract_contacts_from_contact_page_fixture():
    html = (FIXTURES / "contact_page.html").read_text(encoding="utf-8")
    extracted = extract_contacts_from_html(
        html,
        source_url="https://ornek.com/iletisim",
        requested_fields={"email", "phone", "address", "facebook", "linkedin", "youtube"},
    )

    emails = extracted["emails"]
    phones = extracted["phones"]
    address = extracted["address"]
    social = extracted["social_links"]

    assert any(item.value == "destek@ornek.com" for item in emails)
    assert any(item.value.startswith("+90212") for item in phones)
    assert address is not None
    assert "İstanbul" in address.value
    assert social["facebook"] is not None
    assert social["linkedin"] is not None
    assert social["youtube"] is not None


def test_extract_emails_from_home_page_fixture():
    html = (FIXTURES / "home_page.html").read_text(encoding="utf-8")
    extracted = extract_contacts_from_html(
        html,
        source_url="https://ornek.com/",
        requested_fields={"email", "instagram"},
    )

    assert any(item.value == "info@ornek.com" for item in extracted["emails"])
    assert extracted["social_links"]["instagram"] is not None


def test_extract_fakibabatekstil_cloudflare_email_from_fixture():
    html = (FIXTURES / "fakibabatekstil_home.html").read_text(encoding="utf-8")
    source_url = "https://fakibabatekstil.com/"
    extracted = extract_contacts_from_html(
        html,
        source_url=source_url,
        requested_fields={"email", "phone"},
    )

    emails = extracted["emails"]
    phones = extracted["phones"]

    assert any(item.value == "info@fakibabatekstil.com" for item in emails)
    assert all(item.source_url == source_url for item in emails)
    assert any(item.value.startswith("+90224") or "(0224)" in item.value or item.value.startswith("+90") for item in phones)
    assert all(item.source_url == source_url for item in phones)


def test_decode_cfemail_returns_expected_address():
    from app.modules.scraper.extractors.contact_extractor import decode_cfemail

    assert decode_cfemail("97fef9f1f8d7f1f6fcfef5f6f5f6e3f2fce4e3fefbb9f4f8fa") == "info@fakibabatekstil.com"


def test_extract_ignores_junk_email():
    html = "<a href='mailto:noreply@ornek.com'>Mail</a> info@ornek.com"
    extracted = extract_contacts_from_html(
        html,
        source_url="https://ornek.com/",
        requested_fields={"email"},
    )
    values = [item.value for item in extracted["emails"]]
    assert "info@ornek.com" in values
    assert "noreply@ornek.com" not in values


def test_extract_emails_from_js_redirect_target_fixture():
    """Agroder-style regression: footer email in link text, found on the
    real page (post client-side redirect)."""
    html = (FIXTURES / "js_redirect_target.html").read_text(encoding="utf-8")
    extracted = extract_contacts_from_html(
        html,
        source_url="https://ornektarim.com.tr/tr",
        requested_fields={"email"},
    )
    values = [item.value for item in extracted["emails"]]
    assert "ornektarim@ornektarim.com.tr" in values


def test_extract_emails_ranks_site_domain_match_ahead_of_mismatched_mailto():
    """When a `mailto:` href and the visible link text disagree, the address
    matching the crawled site's own domain should be surfaced first, since
    downstream handoff keeps only the first found email."""
    html = (
        "<a href='mailto:info@othertld.tr'>ornektarim@ornektarim.com.tr</a>"
    )
    extracted = extract_contacts_from_html(
        html,
        source_url="https://ornektarim.com.tr/tr",
        requested_fields={"email"},
    )
    values = [item.value for item in extracted["emails"]]
    assert values[0] == "ornektarim@ornektarim.com.tr"
    assert "info@othertld.tr" in values
