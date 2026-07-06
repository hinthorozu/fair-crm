from app.modules.scraper.domain.requested_output_fields import default_requested_fields_for_capabilities
from app.modules.scraper.manifests.customer_contact_enrichment_manifest import (
    CUSTOMER_CONTACT_ENRICHMENT_MANIFEST,
)
from app.modules.scraper.domain.requested_output_fields import output_field_capabilities_from_supports


def test_enrichment_default_requested_fields_only_email():
    caps = output_field_capabilities_from_supports(CUSTOMER_CONTACT_ENRICHMENT_MANIFEST.supports)
    assert default_requested_fields_for_capabilities(caps) == ["email"]
