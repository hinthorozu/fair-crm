"""Scraper adapter contract — one implementation per fair website."""

from typing import Protocol

from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.types.scraper_context import ScraperContext


class IScraperAdapter(Protocol):
    """Site-specific exhibitor list scraper.

    Each fair portal (TÜYAP, IFM, Hannover, Canton, …) implements this protocol.
    Adapters own URL structure, HTML/API parsing, and pagination only.
    They must not write CRM data or apply business merge rules.
    """

    @property
    def site_key(self) -> str:
        """Stable registry key, e.g. ``tuyap``, ``ifm``, ``hannover``."""

    @property
    def display_name(self) -> str:
        """Human-readable label for admin UI."""

    def scrape(self, context: ScraperContext) -> list[RawCompanyDto]:
        """Fetch and parse exhibitor companies from the fair site."""
