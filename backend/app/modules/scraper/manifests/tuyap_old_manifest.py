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
    version="1.0.0",
    supported_sites=(
        "istanbulkitapfuari.com",
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
        requires_js=False,
        requires_playwright=False,
    ),
    status=ScraperStatus.STABLE,
    author="KYROX",
    notes=(
        "İstanbul Kitap Fuarı legacy exhibitor list scraping. "
        "List page includes contact and location; detail page adds Firma Hakkında notes."
    ),
    scraper_version="1.0",
    target_site_version="istanbulkitapfuari.com",
    last_verified="2026-07-06",
)
