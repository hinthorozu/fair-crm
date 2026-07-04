"""Tests for tuyap_new output field capabilities exposed via engine catalog."""

from app.modules.scraper.domain.requested_output_fields import output_field_capabilities_from_supports
from app.modules.scraper.manifests.tuyap_new_manifest import TUYAP_NEW_MANIFEST
from app.modules.scraper.services.scraper_dashboard_service import build_adapter_features


def test_tuyap_new_output_field_capabilities() -> None:
    caps = output_field_capabilities_from_supports(TUYAP_NEW_MANIFEST.supports)

    assert caps["customerName"] is True
    assert caps["phone"] is True
    assert caps["email"] is True
    assert caps["address"] is True
    assert caps["website"] is True
    assert caps["hall"] is True
    assert caps["stand"] is True
    assert caps["instagram"] is True
    assert caps["facebook"] is True
    assert caps["linkedin"] is True
    assert caps["youtube"] is True
    assert caps["notes"] is True


def test_tuyap_new_adapter_features_use_standard_output_keys() -> None:
    features = build_adapter_features(TUYAP_NEW_MANIFEST)
    by_key = {feature["key"]: feature for feature in features}

    for key in (
        "customerName",
        "phone",
        "email",
        "address",
        "website",
        "hall",
        "stand",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
        "notes",
    ):
        assert by_key[key]["enabled"] is True

    assert "list_scraping" not in by_key
    assert "category" not in by_key
