"""Tests for enrichment source URLs in merge preview."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.imports.application.merge_preview_builder import MergePreviewBuilder
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.services.enrichment_merge_sources import extract_enrichment_field_sources
from app.modules.imports.domain.services.merge_preview import build_merge_preview
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus, ImportSourceType
from tests.modules.imports.test_merge_preview import _Customer, _customer_communication_kwargs, _row


def test_extract_enrichment_field_sources_from_nested_raw():
    raw_data = {
        "company_name": "Acme",
        "raw": {
            "email_source_url": "https://acme.test/iletisim",
            "phone_source_url": "https://acme.test/contact",
            "instagram_source_url": "https://acme.test/social",
            "source_url": "https://acme.test",
            "ignored": "not-a-url",
        },
    }
    sources = extract_enrichment_field_sources(raw_data)
    assert sources["email"] == "https://acme.test/iletisim"
    assert sources["phone"] == "https://acme.test/contact"
    assert sources["instagram_url"] == "https://acme.test/social"
    assert sources["website"] == "https://acme.test"
    assert "ignored" not in sources


def test_merge_preview_includes_source_url_on_email_field():
    data = {"company_name": "Acme", "email": "info@acme.test"}
    preview = build_merge_preview(
        _row(data, decision=ImportDecision.UPDATE_EXISTING, status=ImportRowStatus.READY_TO_UPDATE),
        customer=_Customer(display_name="Acme", email=None),
        participation=None,
        contact=None,
        fair_id=None,
        field_source_urls={"email": "https://acme.test/iletisim"},
        **_customer_communication_kwargs(_Customer(display_name="Acme", email=None)),
    )
    email = next(f for f in preview["groups"][0]["fields"] if f["field_key"] == "email")
    assert email["source_url"] == "https://acme.test/iletisim"


def test_merge_preview_omits_source_url_without_enrichment_sources():
    data = {"company_name": "Acme", "email": "info@acme.test"}
    preview = build_merge_preview(
        _row(data),
        customer=None,
        participation=None,
        contact=None,
        fair_id=uuid4(),
    )
    email = next(f for f in preview["groups"][0]["fields"] if f["field_key"] == "email")
    assert "source_url" not in email


def test_merge_preview_builder_adds_sources_for_enrichment_batch(db_session, organization_id):
    now = datetime.now(tz=UTC)
    batch = ImportBatch.create_from_canonical(
        organization_id=organization_id,
        fair_id=None,
        source_type=ImportSourceType.SCRAPER,
        file_name="customer_contact_enrichment-run.json",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        raw_preview_json={
            "canonical_source": {"adapter_key": "customer_contact_enrichment", "type": "scraper"},
        },
        now=now,
    )

    row = ImportRow.create(
        batch_id=batch.id,
        organization_id=organization_id,
        row_number=1,
        raw_data_json={
            "company_name": "Enrichment Co",
            "raw": {"email_source_url": "https://enrichment.test/kaynak"},
        },
        normalized_data_json={"company_name": "Enrichment Co", "email": "info@enrichment.test"},
        status=ImportRowStatus.READY_TO_UPDATE,
        validation_errors_json=None,
        match_customer_id=None,
        match_confidence=None,
        match_reason="enrichment_customer_id",
        now=now,
    )

    from unittest.mock import MagicMock

    builder = MergePreviewBuilder(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    preview = builder.build_for_row(organization_id, batch, row)

    email = next(f for f in preview["groups"][0]["fields"] if f["field_key"] == "email")
    assert email["source_url"] == "https://enrichment.test/kaynak"


def test_merge_preview_builder_omits_sources_for_tuyap_batch(db_session, organization_id):
    now = datetime.now(tz=UTC)
    batch = ImportBatch.create_from_canonical(
        organization_id=organization_id,
        fair_id=uuid4(),
        source_type=ImportSourceType.SCRAPER,
        file_name="tuyap_old-run.json",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        raw_preview_json={"canonical_source": {"adapter_key": "tuyap_old", "type": "scraper"}},
        now=now,
    )
    row = ImportRow.create(
        batch_id=batch.id,
        organization_id=organization_id,
        row_number=1,
        raw_data_json={
            "company_name": "Fair Co",
            "raw": {"email_source_url": "https://should-not-show.test"},
        },
        normalized_data_json={"company_name": "Fair Co", "email": "info@fair.test"},
        status=ImportRowStatus.READY_TO_CREATE,
        validation_errors_json=None,
        match_customer_id=None,
        match_confidence=None,
        match_reason=None,
        now=now,
    )

    from unittest.mock import MagicMock

    builder = MergePreviewBuilder(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    preview = builder.build_for_row(organization_id, batch, row)

    email = next(f for f in preview["groups"][0]["fields"] if f["field_key"] == "email")
    assert "source_url" not in email
