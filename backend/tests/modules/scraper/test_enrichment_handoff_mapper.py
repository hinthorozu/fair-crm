"""Unit tests for enrichment → import handoff email mapping."""

from uuid import uuid4

from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue
from app.modules.scraper.exporters.enrichment_handoff_mapper import enrichment_result_to_raw_company


def test_enrichment_handoff_includes_all_discovered_emails():
    result = EnrichmentResultDto(
        customer_id=uuid4(),
        company_name="Multi Email Co",
        website="https://multi.test",
        status="found",
        emails=[
            SourcedValue(value="info@multi.test", source_url="https://multi.test/contact"),
            SourcedValue(value="sales@multi.test", source_url="https://multi.test/contact"),
            SourcedValue(value="export@multi.test", source_url="https://multi.test/sales"),
        ],
    )

    raw = enrichment_result_to_raw_company(result, requested_fields=["email"])
    assert raw is not None
    assert raw.email == "info@multi.test;sales@multi.test;export@multi.test"
