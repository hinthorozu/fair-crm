"""Tests for adapter output format resolution."""

from uuid import uuid4

from app.modules.scraper.services.adapter_instance_resolver import resolve_output_formats
from app.modules.scraper.types.scraper_site import ScraperSiteKey


def test_resolve_output_formats_uses_manifest_defaults(db_session, organization_id):
    formats = resolve_output_formats(
        db_session,
        organization_id,
        ScraperSiteKey.TUYAP_NEW,
    )
    assert formats.json_handoff is True
    assert formats.excel is True


def test_resolve_output_formats_honors_request_overrides(db_session, organization_id):
    formats = resolve_output_formats(
        db_session,
        organization_id,
        ScraperSiteKey.TUYAP_NEW,
        output_json_override=False,
        output_excel_override=True,
    )
    assert formats.json_handoff is False
    assert formats.excel is True
