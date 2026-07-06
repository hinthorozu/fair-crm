"""Tests for tuyap_old output field capabilities exposed via manifest."""

from app.modules.scraper.domain.requested_output_fields import output_field_capabilities_from_supports
from app.modules.scraper.manifests.tuyap_old_manifest import TUYAP_OLD_MANIFEST
from app.modules.scraper.services.scraper_dashboard_service import build_adapter_features


def test_tuyap_old_output_field_capabilities() -> None:
    caps = output_field_capabilities_from_supports(TUYAP_OLD_MANIFEST.supports)

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


def test_tuyap_old_adapter_features_use_standard_output_keys() -> None:
    features = build_adapter_features(TUYAP_OLD_MANIFEST)
    by_key = {feature["key"]: feature for feature in features}

    assert by_key["customerName"]["enabled"] is True
    assert by_key["phone"]["enabled"] is True
    assert by_key["address"]["enabled"] is True
    assert by_key["website"]["enabled"] is True
    assert by_key["hall"]["enabled"] is True
    assert by_key["stand"]["enabled"] is True
    assert by_key["notes"]["enabled"] is True
    assert by_key["email"]["enabled"] is True
    assert by_key["instagram"]["enabled"] is True
    assert by_key["facebook"]["enabled"] is True
    assert by_key["linkedin"]["enabled"] is True
    assert by_key["youtube"]["enabled"] is True
