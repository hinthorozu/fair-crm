from pathlib import Path
from uuid import uuid4

import pytest

from app.modules.scraper.adapters.customer_contact_enrichment_adapter import CustomerContactEnrichmentAdapter
from app.modules.scraper.core.scraper_run_logger import NullScraperRunLogger
from app.modules.scraper.types.scraper_context import ScraperContext

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "customer_enrichment"


def _fixture_fetcher(url: str) -> str:
    mapping = {
        "https://ornek.com": "home_page.html",
        "https://ornek.com/iletisim": "contact_page.html",
        "https://ornek.com/kurumsal/hakkimizda": "contact_page.html",
    }
    file_name = mapping.get(url.rstrip("/"))
    if file_name is None:
        raise ValueError(f"Unexpected URL: {url}")
    return (FIXTURES / file_name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_customer_contact_enrichment_adapter_extracts_contacts_from_fixture_site():
    customer_id = uuid4()
    adapter = CustomerContactEnrichmentAdapter()
    context = ScraperContext(
        options={
            "enrichment_candidates": [
                {
                    "customer_id": str(customer_id),
                    "company_name": "Örnek Firma",
                    "website": "https://ornek.com",
                }
            ],
            "requested_fields": ["email", "phone", "address", "instagram", "facebook"],
            "max_pages": 5,
            "fetcher": _fixture_fetcher,
            "run_logger": NullScraperRunLogger(),
        }
    )

    rows = await adapter.scrape_async(context)

    assert len(rows) == 1
    row = rows[0]
    assert row.company_name == "Örnek Firma"
    assert row.email in {"info@ornek.com", "destek@ornek.com"}
    assert row.phone is not None
    assert row.address is not None
    assert row.metadata["external_id"] == str(customer_id)
    assert row.metadata["customer_id"] == str(customer_id)


@pytest.mark.asyncio
async def test_customer_contact_enrichment_adapter_returns_empty_when_no_candidates():
    adapter = CustomerContactEnrichmentAdapter()
    context = ScraperContext(options={"run_logger": NullScraperRunLogger()})
    rows = await adapter.scrape_async(context)
    assert rows == []


def _js_redirect_fixture_fetcher(url: str) -> str:
    mapping = {
        "https://ornektarim.com.tr": "js_redirect_home.html",
        "https://ornektarim.com.tr/tr": "js_redirect_target.html",
    }
    file_name = mapping.get(url.rstrip("/"))
    if file_name is None:
        raise ValueError(f"Unexpected URL: {url}")
    return (FIXTURES / file_name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_customer_contact_enrichment_adapter_follows_js_redirect_and_ranks_domain_match():
    """End-to-end regression for the agroder.com.tr case: homepage is a bare
    `window.location` shell, and the real page's footer has a mismatched
    `mailto:` vs. visible-text email. The adapter must still find the
    site's own address as the primary result."""
    customer_id = uuid4()
    adapter = CustomerContactEnrichmentAdapter()
    context = ScraperContext(
        options={
            "enrichment_candidates": [
                {
                    "customer_id": str(customer_id),
                    "company_name": "Örnek Tarım",
                    "website": "ornektarim.com.tr",
                }
            ],
            "requested_fields": ["email"],
            "max_pages": 5,
            "fetcher": _js_redirect_fixture_fetcher,
            "run_logger": NullScraperRunLogger(),
        }
    )

    rows = await adapter.scrape_async(context)

    assert len(rows) == 1
    row = rows[0]
    assert row.email == "ornektarim@ornektarim.com.tr"
