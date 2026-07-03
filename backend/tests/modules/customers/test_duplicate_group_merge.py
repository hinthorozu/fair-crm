from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.application.duplicate_group_merge import (
    DuplicateGroupMemberContext,
    DuplicateGroupMergeSelection,
    build_duplicate_group_merge_preview,
    build_communication_index,
    raise_for_invalid_merge_selection,
)
from app.modules.customers.domain.communication_entities import (
    CustomerCommunications,
    CustomerEmail,
)
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType


def _customer(
    customer_id,
    *,
    display_name: str,
    legal_name: str | None = None,
    city: str | None = None,
    country: str | None = None,
) -> Customer:
    now = datetime.now(tz=UTC)
    return Customer(
        id=customer_id,
        organization_id=uuid4(),
        display_name=display_name,
        legal_name=legal_name,
        trade_name=None,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD,
        status=CustomerStatus.ACTIVE,
        tax_number=None,
        tax_office=None,
        country=country,
        city=city,
        district=None,
        address=None,
        description=None,
        source=CustomerSource.MANUAL,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def test_merge_preview_deduplicates_selected_emails():
    first_id = uuid4()
    second_id = uuid4()
    email_one = uuid4()
    email_two = uuid4()
    now = datetime.now(tz=UTC)
    members = [
        DuplicateGroupMemberContext(customer=_customer(first_id, display_name="Co A"), participations=[]),
        DuplicateGroupMemberContext(customer=_customer(second_id, display_name="Co B"), participations=[]),
    ]
    communications = {
        first_id: CustomerCommunications(
            phones=[],
            emails=[
                CustomerEmail(
                    id=email_one,
                    customer_id=first_id,
                    email="shared@example.com",
                    is_primary=True,
                    created_at=now,
                )
            ],
            websites=[],
        ),
        second_id: CustomerCommunications(
            phones=[],
            emails=[
                CustomerEmail(
                    id=email_two,
                    customer_id=second_id,
                    email="shared@example.com",
                    is_primary=False,
                    created_at=now,
                ),
                CustomerEmail(
                    id=uuid4(),
                    customer_id=second_id,
                    email="other@example.com",
                    is_primary=False,
                    created_at=now,
                ),
            ],
            websites=[],
        ),
    }
    selection = DuplicateGroupMergeSelection(
        surviving_customer_id=first_id,
        scalar_selections={
            "company_name": first_id,
            "legal_name": first_id,
            "trade_name": first_id,
            "city": first_id,
            "country": first_id,
        },
        selected_email_ids=(email_one, email_two),
        selected_phone_ids=(),
        selected_website_ids=(),
    )

    preview = build_duplicate_group_merge_preview(
        group_key="shared@example.com",
        group_by="email",
        members=members,
        communications_by_customer=communications,
        selection=selection,
    )

    assert preview.is_valid is True
    assert preview.statistics.emails_before == 2
    assert preview.statistics.emails_after == 1
    assert preview.emails[0].value == "shared@example.com"
    assert preview.customers_to_archive == [second_id]


def test_merge_preview_reports_mixed_scalar_warning():
    first_id = uuid4()
    second_id = uuid4()
    members = [
        DuplicateGroupMemberContext(
            customer=_customer(first_id, display_name="Co A", city="Istanbul"),
            participations=[],
        ),
        DuplicateGroupMemberContext(
            customer=_customer(second_id, display_name="Co B", city="Ankara"),
            participations=[],
        ),
    ]
    selection = DuplicateGroupMergeSelection(
        surviving_customer_id=first_id,
        scalar_selections={
            "company_name": first_id,
            "legal_name": first_id,
            "trade_name": first_id,
            "city": second_id,
            "country": first_id,
        },
        selected_email_ids=(),
        selected_phone_ids=(),
        selected_website_ids=(),
    )

    preview = build_duplicate_group_merge_preview(
        group_key="co a",
        group_by="company_name",
        members=members,
        communications_by_customer={},
        selection=selection,
    )

    assert any(issue.code == "mixed_scalar_selection" for issue in preview.warnings)


def test_merge_preview_requires_email_when_group_has_emails():
    customer_id = uuid4()
    members = [
        DuplicateGroupMemberContext(customer=_customer(customer_id, display_name="Co A"), participations=[]),
    ]
    now = datetime.now(tz=UTC)
    communications = {
        customer_id: CustomerCommunications(
            phones=[],
            emails=[
                CustomerEmail(
                    id=uuid4(),
                    customer_id=customer_id,
                    email="only@example.com",
                    is_primary=True,
                    created_at=now,
                )
            ],
            websites=[],
        ),
    }
    selection = DuplicateGroupMergeSelection(
        surviving_customer_id=customer_id,
        scalar_selections={
            "company_name": customer_id,
            "legal_name": customer_id,
            "trade_name": customer_id,
            "city": customer_id,
            "country": customer_id,
        },
        selected_email_ids=(),
        selected_phone_ids=(),
        selected_website_ids=(),
    )

    preview = build_duplicate_group_merge_preview(
        group_key="only@example.com",
        group_by="email",
        members=members,
        communications_by_customer=communications,
        selection=selection,
    )

    assert preview.is_valid is False
    assert any(issue.code == "email_required" for issue in preview.validation_errors)


def test_communication_index_rejects_foreign_ids():
    customer_id = uuid4()
    members = [
        DuplicateGroupMemberContext(customer=_customer(customer_id, display_name="Co A"), participations=[]),
    ]
    foreign_email_id = uuid4()
    selection = DuplicateGroupMergeSelection(
        surviving_customer_id=customer_id,
        scalar_selections={
            "company_name": customer_id,
            "legal_name": customer_id,
            "trade_name": customer_id,
            "city": customer_id,
            "country": customer_id,
        },
        selected_email_ids=(foreign_email_id,),
        selected_phone_ids=(),
        selected_website_ids=(),
    )

    preview = build_duplicate_group_merge_preview(
        group_key="co a",
        group_by="company_name",
        members=members,
        communications_by_customer={customer_id: CustomerCommunications(phones=[], emails=[], websites=[])},
        selection=selection,
    )

    assert preview.is_valid is False
    assert any(issue.code == "missing_email_id" for issue in preview.validation_errors)
    assert build_communication_index(members, {}) == {}


def test_raise_for_invalid_merge_selection_rejects_foreign_communication_ids():
    customer_id = uuid4()
    members = [
        DuplicateGroupMemberContext(customer=_customer(customer_id, display_name="Co A"), participations=[]),
    ]
    foreign_email_id = uuid4()
    selection = DuplicateGroupMergeSelection(
        surviving_customer_id=customer_id,
        scalar_selections={
            "company_name": customer_id,
            "legal_name": customer_id,
            "trade_name": customer_id,
            "city": customer_id,
            "country": customer_id,
        },
        selected_email_ids=(foreign_email_id,),
        selected_phone_ids=(),
        selected_website_ids=(),
    )
    preview = build_duplicate_group_merge_preview(
        group_key="co a",
        group_by="company_name",
        members=members,
        communications_by_customer={customer_id: CustomerCommunications(phones=[], emails=[], websites=[])},
        selection=selection,
    )

    try:
        raise_for_invalid_merge_selection(preview.validation_errors)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "not found in this duplicate group" in str(exc)


def test_build_duplicate_group_merge_preview_rejects_empty_group():
    customer_id = uuid4()
    selection = DuplicateGroupMergeSelection(
        surviving_customer_id=customer_id,
        scalar_selections={
            "company_name": customer_id,
            "legal_name": customer_id,
            "trade_name": customer_id,
            "city": customer_id,
            "country": customer_id,
        },
        selected_email_ids=(),
        selected_phone_ids=(),
        selected_website_ids=(),
    )

    try:
        build_duplicate_group_merge_preview(
            group_key="missing",
            group_by="email",
            members=[],
            communications_by_customer={},
            selection=selection,
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "no customers" in str(exc).lower()
