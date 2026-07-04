"""Manifest for TÜYAP New / Foodist Expo adapter."""

from app.modules.scraper.manifests.scraper_manifest import (
    ScraperBrowser,
    ScraperManifest,
    ScraperOutput,
    ScraperStatus,
    ScraperSupports,
)
from app.modules.scraper.types.scraper_site import ScraperSiteKey

TUYAP_NEW_MANIFEST = ScraperManifest(
    adapter_key=ScraperSiteKey.TUYAP_NEW,
    display_name="TÜYAP (New)",
    version="1.0.0",
    supported_sites=(
        "foodistexpo.com",
        "foodist.tuyap.online",
    ),
    supports=ScraperSupports(
        list_scraping=True,
        detail_scraping=True,
        pagination=True,
        website=True,
        email=True,
        phone=True,
        address=True,
        category=False,
        description=True,
    ),
    output=ScraperOutput(
        json_handoff=True,
        excel=True,
    ),
    browser=ScraperBrowser(
        requires_js=True,
        requires_playwright=True,
    ),
    status=ScraperStatus.STABLE,
    author="KYROX",
    notes=(
        "Foodist Expo exhibitor list and brand detail scraping. "
        "Playwright preferred; HTTP fallback available when browser access is blocked."
    ),
    scraper_version="1.0",
    target_site_version="unknown",
    last_verified="2026-07-04",
)
