"""Merge preview service tests."""

from uuid import uuid4

from app.modules.imports.domain.entities import ImportRow
from app.modules.imports.domain.services.merge_preview import build_merge_preview
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus


def _row(
    data: dict,
    *,
    decision=None,
    status=ImportRowStatus.READY_TO_CREATE,
    match_customer_id=None,
):
    from datetime import UTC, datetime

    now = datetime.now(tz=UTC)
    row = ImportRow.create(
        batch_id=uuid4(),
        organization_id=uuid4(),
        row_number=1,
        raw_data_json=data,
        normalized_data_json=data,
        status=status,
        validation_errors_json=None,
        match_customer_id=match_customer_id,
        match_confidence=None,
        match_reason=None,
        now=now,
    )
    if decision:
        row.decision = decision
    return row


class _Customer:
    def __init__(self, **kwargs):
        self.display_name = kwargs.get("display_name")
        self.phone = kwargs.get("phone")
        self.email = kwargs.get("email")
        self.website = kwargs.get("website")
        self.country = kwargs.get("country")
        self.city = kwargs.get("city")
        self.address = kwargs.get("address")
        self.tax_number = kwargs.get("tax_number")


class _Participation:
    def __init__(self, **kwargs):
        self.hall = kwargs.get("hall")
        self.stand = kwargs.get("stand")
        self.notes = kwargs.get("notes")
        self.participation_status = kwargs.get("participation_status")


def test_merge_preview_create_new_shows_will_add():
    data = {"company_name": "ABC Makina", "email": "info@abc.com", "hall": "3", "stand": "A12"}
    preview = build_merge_preview(
        _row(data),
        customer=None,
        participation=None,
        contact=None,
        fair_id=uuid4(),
    )
    customer_group = preview["groups"][0]
    email_field = next(f for f in customer_group["fields"] if f["field_key"] == "email")
    assert email_field["outcome"] == "new"
    assert "eklenecek" in preview["summary_lines"][0].lower() or any(
        "E-posta" in line for line in preview["summary_lines"]
    )


def test_merge_preview_update_fill_empty():
    data = {"company_name": "ABC Makina", "email": "info@abc.com", "website": "www.abc.com"}
    customer = _Customer(display_name="ABC Makina", email=None, website=None, address="İstanbul")
    preview = build_merge_preview(
        _row(data, decision=ImportDecision.UPDATE_EXISTING, status=ImportRowStatus.READY_TO_UPDATE),
        customer=customer,
        participation=None,
        contact=None,
        fair_id=uuid4(),
    )
    customer_fields = preview["groups"][0]["fields"]
    email = next(f for f in customer_fields if f["field_key"] == "email")
    website = next(f for f in customer_fields if f["field_key"] == "website")
    address = next(f for f in customer_fields if f["field_key"] == "address")
    assert email["outcome"] == "will_add"
    assert website["outcome"] == "will_add"
    assert address["outcome"] in ("will_keep", "same")


def test_merge_preview_conflict_keeps_db():
    data = {"company_name": "Co", "hall": "A15", "stand": "A15"}
    participation = _Participation(hall="3", stand="A12")
    preview = build_merge_preview(
        _row(
            data,
            decision=ImportDecision.UPDATE_EXISTING,
            status=ImportRowStatus.READY_TO_UPDATE,
        ),
        customer=_Customer(display_name="Co"),
        participation=participation,
        contact=None,
        fair_id=uuid4(),
    )
    part_group = next(g for g in preview["groups"] if g["entity"] == "participation")
    stand = next(f for f in part_group["fields"] if f["field_key"] == "stand")
    assert stand["outcome"] == "conflict"
    assert stand["result_value"] == "A12"
    assert any("korunacak" in line.lower() for line in preview["summary_lines"])


def test_merge_preview_email_union():
    data = {"company_name": "Co", "email": "b@co.com"}
    customer = _Customer(display_name="Co", email="a@co.com")
    preview = build_merge_preview(
        _row(
            data,
            decision=ImportDecision.UPDATE_EXISTING,
            status=ImportRowStatus.READY_TO_UPDATE,
        ),
        customer=customer,
        participation=None,
        contact=None,
        fair_id=uuid4(),
    )
    email = next(f for f in preview["groups"][0]["fields"] if f["field_key"] == "email")
    assert email["outcome"] == "will_update"
    assert "b@co.com" in (email["result_value"] or "")


def test_merge_preview_entity_groups():
    data = {
        "company_name": "Co",
        "contact_first_name": "Ali",
        "contact_last_name": "Veli",
        "hall": "1",
    }
    preview = build_merge_preview(
        _row(data),
        customer=None,
        participation=None,
        contact=None,
        fair_id=uuid4(),
    )
    entities = {g["entity"] for g in preview["groups"]}
    assert "customer" in entities
    assert "participation" in entities
    assert "contact" in entities
