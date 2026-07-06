"""Manifest for customer website contact enrichment adapter."""

from app.modules.scraper.manifests.scraper_manifest import (
    ScraperBrowser,
    ScraperManifest,
    ScraperOutput,
    ScraperStatus,
    ScraperSupports,
)
from app.modules.scraper.types.scraper_site import ScraperSiteKey

CUSTOMER_CONTACT_ENRICHMENT_MANIFEST = ScraperManifest(
    adapter_key=ScraperSiteKey.CUSTOMER_CONTACT_ENRICHMENT,
    display_name="Müşteri İletişim Zenginleştirme",
    version="1.0.0",
    supported_sites=("customer-websites",),
    supports=ScraperSupports(
        list_scraping=False,
        detail_scraping=True,
        pagination=False,
        website=False,
        email=True,
        phone=True,
        address=True,
        category=False,
        description=False,
    ),
    output=ScraperOutput(
        json_handoff=True,
        excel=False,
    ),
    browser=ScraperBrowser(
        requires_js=False,
        requires_playwright=False,
    ),
    status=ScraperStatus.EXPERIMENTAL,
    author="KYROX",
    notes=(
        "Enriches existing CRM customers that have a website but no email. "
        "Reads contact pages on the customer website and sends results to import preview."
    ),
    scraper_version="1.0",
    target_site_version="generic",
    last_verified="2026-07-06",
)
