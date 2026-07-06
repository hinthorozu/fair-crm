from pathlib import Path

import pytest

from app.modules.scraper.extractors.contact_extractor import (
    extract_contacts_from_html,
    is_junk_email,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "customer_enrichment"


def test_is_junk_email_filters_common_noise():
    assert is_junk_email("noreply@example.com") is True
    assert is_junk_email("info@example.com") is False
    assert is_junk_email("icon-ada-swabs@2x-1.png") is True


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
