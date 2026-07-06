from uuid import uuid4

from app.modules.scraper.domain.enrichment_run_summary import build_enrichment_run_summary
from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto, SourcedValue


def test_build_enrichment_run_summary_counts_results():
    customer_id = uuid4()
    summary = build_enrichment_run_summary(
        [
            EnrichmentResultDto(
                customer_id=customer_id,
                company_name="A",
                website="https://a.test",
                emails=[SourcedValue(value="info@a.test", source_url="https://a.test")],
                status="found",
            ),
            EnrichmentResultDto(
                customer_id=uuid4(),
                company_name="B",
                website="https://b.test",
                status="not_found",
            ),
            EnrichmentResultDto(
                customer_id=uuid4(),
                company_name="C",
                website="https://c.test",
                status="failed",
                error="timeout",
            ),
        ],
        dry_run=False,
        import_batch_id=uuid4(),
        import_rows=1,
    )

    assert summary["customers_scanned"] == 3
    assert summary["emails_found"] == 1
    assert summary["not_found"] == 1
    assert summary["failed"] == 1
    assert summary["import_rows"] == 1
    assert summary["import_batch_created"] is True
