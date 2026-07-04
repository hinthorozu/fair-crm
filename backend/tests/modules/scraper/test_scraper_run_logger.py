"""Tests for capped warning run logger."""

from app.modules.scraper.core.scraper_run_logger import WARNING_LOG_CAP, CappedWarningRunLogger, NullScraperRunLogger


class _CollectingLogger(NullScraperRunLogger):
    def __init__(self) -> None:
        self.warnings: list[tuple[str, str]] = []

    def warning(self, step: str, message: str, *, metadata=None) -> None:
        self.warnings.append((step, message))


def test_capped_warning_logger_stops_at_cap():
    inner = _CollectingLogger()
    logger = CappedWarningRunLogger(inner, cap=3)

    for index in range(5):
        logger.warning("detail_scrape_progress", f"warning-{index}")

    assert len(inner.warnings) == 3
    assert logger._suppressed == 2  # noqa: SLF001


def test_capped_warning_logger_flushes_suppressed_summary():
    inner = _CollectingLogger()
    logger = CappedWarningRunLogger(inner, cap=2)

    for index in range(5):
        logger.warning("detail_scrape_progress", f"warning-{index}")

    logger.flush_suppressed_warnings()

    assert len(inner.warnings) == 3
    assert inner.warnings[-1][1] == f"3 uyarı limit nedeniyle gösterilmedi (limit: 2)"


def test_default_warning_cap_is_200():
    assert WARNING_LOG_CAP == 200
