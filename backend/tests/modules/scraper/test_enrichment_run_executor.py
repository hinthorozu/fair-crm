"""Tests for enrichment run executor candidate query timing logs."""

from __future__ import annotations

from uuid import uuid4

from app.modules.scraper.core.scraper_run_logger import NullScraperRunLogger
from app.modules.scraper.services.enrichment_run_executor import execute_enrichment_run


class _CollectingRunLogger(NullScraperRunLogger):
    def __init__(self) -> None:
        self.entries: list[tuple[str, str, dict | None]] = []

    def info(self, step: str, message: str, *, metadata: dict | None = None) -> None:
        self.entries.append((step, message, metadata))

    def warning(self, step: str, message: str, *, metadata: dict | None = None) -> None:
        self.entries.append((step, message, metadata))


def test_execute_enrichment_run_logs_candidate_query_finished(db_session, organization_id):
    run_logger = _CollectingRunLogger()
    execute_enrichment_run(
        db_session,
        organization_id,
        run_id=uuid4(),
        run_logger=run_logger,
        limit=5,
        requested_fields=["email"],
    )

    steps = [entry[0] for entry in run_logger.entries]
    assert "candidates_query_finished" in steps
    assert "candidates_loaded" in steps

    finished = next(entry for entry in run_logger.entries if entry[0] == "candidates_query_finished")
    assert finished[2] is not None
    assert "duration_ms" in finished[2]
    assert "candidates_count" in finished[2]

    loaded = next(entry for entry in run_logger.entries if entry[0] == "candidates_loaded")
    assert loaded[2] is not None
    assert "candidate_count" in loaded[2]
