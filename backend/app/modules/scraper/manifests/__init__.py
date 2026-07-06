"""Declarative manifests for scraper adapters."""

from app.modules.scraper.manifests.scraper_manifest import (
    ScraperBrowser,
    ScraperManifest,
    ScraperOutput,
    ScraperStatus,
    ScraperSupports,
)
from app.modules.scraper.manifests.customer_contact_enrichment_manifest import (
    CUSTOMER_CONTACT_ENRICHMENT_MANIFEST,
)
from app.modules.scraper.manifests.tuyap_new_manifest import TUYAP_NEW_MANIFEST
from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST

_BUILTIN_MANIFESTS: tuple[ScraperManifest, ...] = (
    TUYAP_OLD_MANIFEST,
    TUYAP_NEW_MANIFEST,
    CUSTOMER_CONTACT_ENRICHMENT_MANIFEST,
)


def register_builtin_manifests(registry: "ManifestRegistry") -> None:
    for manifest in _BUILTIN_MANIFESTS:
        registry.register(manifest)


__all__ = [
    "CUSTOMER_CONTACT_ENRICHMENT_MANIFEST",
    "TUYAP_NEW_MANIFEST",
    "TUYAP_OLD_MANIFEST",
    "ScraperBrowser",
    "ScraperManifest",
    "ScraperOutput",
    "ScraperStatus",
    "ScraperSupports",
    "register_builtin_manifests",
]


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.scraper.core.manifest_registry import ManifestRegistry
