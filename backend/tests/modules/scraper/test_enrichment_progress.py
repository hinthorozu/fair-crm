"""Unit tests for enrichment live progress helpers."""

from types import SimpleNamespace
from uuid import uuid4

from app.modules.scraper.services.enrichment_progress import enrichment_success_fail_counts


def test_enrichment_success_fail_counts_split_found_vs_rest():
    results = [
        SimpleNamespace(status="found"),
        SimpleNamespace(status="not_found"),
        SimpleNamespace(status="failed"),
        SimpleNamespace(status="found"),
        SimpleNamespace(status="skipped"),
    ]
    succeeded, failed = enrichment_success_fail_counts(results)
    assert succeeded == 2
    assert failed == 3
    assert succeeded + failed == len(results)


def test_enrichment_success_fail_counts_empty():
    assert enrichment_success_fail_counts([]) == (0, 0)
