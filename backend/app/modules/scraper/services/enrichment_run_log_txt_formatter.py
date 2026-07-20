"""Format enrichment run console logs for TXT export matching Run Detail UI."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from app.modules.scraper.domain.scraper_run_log import ScraperRunLog

# Turkey uses UTC+3 year-round; matches tr-TR Run Detail console time display.
_CONSOLE_TIMEZONE = timezone(timedelta(hours=3))

_ENRICHMENT_STEP_LABELS: dict[str, str] = {
    "candidate_selected": "Aday seçildi",
    "website_fetch_started": "Web sitesi taranıyor",
    "website_fetch_success": "Web sitesi yüklendi",
    "website_fetch_failed": "Web sitesi yüklenemedi",
    "contact_extracted": "İletişim bilgisi çıkarıldı",
    "email_found": "E-posta bulundu",
    "not_found": "E-posta bulunamadı",
    "handoff_row_created": "Import satırı oluşturuldu",
    "run_finished": "Çalışma tamamlandı",
}


def format_enrichment_step_label(step: str) -> str:
    if step in _ENRICHMENT_STEP_LABELS:
        return _ENRICHMENT_STEP_LABELS[step]
    return step.replace("_", " ")


def format_console_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(_CONSOLE_TIMEZONE).strftime("%H:%M:%S")


def format_console_log_block(log: ScraperRunLog) -> str:
    time_label = format_console_time(log.created_at)
    step_label = format_enrichment_step_label(log.step)
    return f"{time_label} [{step_label}]\n{log.message}"


def build_console_txt_export(logs: list[ScraperRunLog]) -> str:
    if not logs:
        return ""
    blocks = [format_console_log_block(log) for log in logs]
    return "\n\n".join(blocks) + "\n"
