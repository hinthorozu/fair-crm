"""TÜYAP legacy exhibitor portal — placeholder adapter."""

from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_site import ScraperSiteKey


class TuyapOldAdapter:
    """Scrapes exhibitor lists from the legacy TÜYAP website (prototype)."""

    def __init__(self, browser: BrowserService | None = None) -> None:
        self._browser = browser

    @property
    def site_key(self) -> str:
        return ScraperSiteKey.TUYAP_OLD

    @property
    def display_name(self) -> str:
        return "TÜYAP (Old)"

    def scrape(self, context: ScraperContext) -> list[RawCompanyDto]:
        return [
            RawCompanyDto(
                company_name="TÜYAP Old Placeholder Exhibitor A",
                hall="1",
                stand="101",
                source_url=context.list_url,
                metadata={"adapter": self.site_key, "placeholder": True},
            ),
            RawCompanyDto(
                company_name="TÜYAP Old Placeholder Exhibitor B",
                hall="2",
                stand="205",
                email="info@tuyap-old-placeholder.test",
                source_url=context.list_url,
                metadata={"adapter": self.site_key, "placeholder": True},
            ),
        ]
