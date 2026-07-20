"""Tests for enrichment run log TXT formatter."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.scraper.domain.scraper_run_log import ScraperRunLog, ScraperRunLogLevel
from app.modules.scraper.services.enrichment_run_log_txt_formatter import (
    build_console_txt_export,
    format_console_log_block,
    format_console_time,
    format_enrichment_step_label,
)


def test_format_enrichment_step_label_uses_turkish_labels():
    assert format_enrichment_step_label("website_fetch_started") == "Web sitesi taranıyor"
    assert format_enrichment_step_label("candidates_to_process") == "candidates to process"


def test_format_console_time_uses_istanbul_hh_mm_ss():
    value = datetime(2026, 7, 20, 20, 3, 13, tzinfo=UTC)
    assert format_console_time(value) == "23:03:13"


def test_format_console_log_block_matches_run_detail_layout():
    log = ScraperRunLog(
        id=uuid4(),
        run_id=uuid4(),
        level=ScraperRunLogLevel.INFO,
        step="website_fetch_started",
        message="Sayfa isteniyor:\nhttps://example.test",
        created_at=datetime(2026, 7, 20, 20, 3, 13, tzinfo=UTC),
        metadata=None,
    )

    assert format_console_log_block(log) == (
        "23:03:13 [Web sitesi taranıyor]\nSayfa isteniyor:\nhttps://example.test"
    )


def test_build_console_txt_export_separates_entries_with_blank_line():
    run_id = uuid4()
    first = ScraperRunLog(
        id=uuid4(),
        run_id=run_id,
        level=ScraperRunLogLevel.INFO,
        step="website_fetch_started",
        message="Sayfa isteniyor: https://a.test",
        created_at=datetime(2026, 7, 20, 20, 3, 13, tzinfo=UTC),
        metadata=None,
    )
    second = ScraperRunLog(
        id=uuid4(),
        run_id=run_id,
        level=ScraperRunLogLevel.INFO,
        step="website_fetch_success",
        message="Sayfa alındı: https://a.test",
        created_at=datetime(2026, 7, 20, 20, 3, 15, tzinfo=UTC),
        metadata=None,
    )

    body = build_console_txt_export([first, second])

    assert body == (
        "23:03:13 [Web sitesi taranıyor]\n"
        "Sayfa isteniyor: https://a.test\n"
        "\n"
        "23:03:15 [Web sitesi yüklendi]\n"
        "Sayfa alındı: https://a.test\n"
    )
