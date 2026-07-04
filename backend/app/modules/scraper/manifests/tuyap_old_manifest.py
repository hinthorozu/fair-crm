"""Manifest for TÜYAP Old legacy portal adapter."""

from app.modules.scraper.manifests.scraper_manifest import (
    ScraperBrowser,
    ScraperManifest,
    ScraperOutput,
    ScraperStatus,
    ScraperSupports,
)
from app.modules.scraper.types.scraper_site import ScraperSiteKey

TUYAP_OLD_MANIFEST = ScraperManifest(
    adapter_key=ScraperSiteKey.TUYAP_OLD,
    display_name="TÜYAP (Old)",
    version="0.1.0",
    supported_sites=(
        "tuyap.com.tr",
    ),
    supports=ScraperSupports(
        list_scraping=True,
        detail_scraping=False,
        pagination=False,
        website=False,
        email=True,
        phone=False,
        address=False,
        category=False,
        description=False,
    ),
    output=ScraperOutput(
        json_handoff=True,
        excel=True,
    ),
    browser=ScraperBrowser(
        requires_js=False,
        requires_playwright=False,
    ),
    status=ScraperStatus.EXPERIMENTAL,
    author="KYROX",
    notes="Legacy TÜYAP portal placeholder adapter. Not production-ready.",
    scraper_version="1.0",
    target_site_version="unknown",
    last_verified="2026-07-04",
)
