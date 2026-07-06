"""Summary metrics for customer contact enrichment runs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.scraper.dto.enrichment_result_dto import EnrichmentResultDto


def build_enrichment_run_summary(
    results: list[EnrichmentResultDto],
    *,
    dry_run: bool,
    import_batch_id: UUID | None,
    import_rows: int,
) -> dict[str, Any]:
    return {
        "customers_scanned": len(results),
        "emails_found": sum(1 for result in results if result.emails),
        "phones_found": sum(1 for result in results if result.phones),
        "not_found": sum(1 for result in results if result.status == "not_found"),
        "failed": sum(1 for result in results if result.status == "failed"),
        "found": sum(1 for result in results if result.status == "found"),
        "import_rows": import_rows,
        "dry_run": dry_run,
        "import_batch_created": import_batch_id is not None,
        "import_batch_id": str(import_batch_id) if import_batch_id is not None else None,
    }
