from datetime import UTC, datetime
from uuid import uuid4

from app.modules.customers.application.customer_field_grouping import (
    analyze_customer_groups_by_field,
    grouping_keys_for_customer,
)
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel


def _seed_customer(
    db_session,
    organization_id,
    *,
    display_name: str,
    normalized_name: str,
) -> CustomerModel:
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=display_name,
        normalized_name=normalized_name,
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def test_grouping_keys_for_customer_uses_all_emails(db_session, organization_id):
    customer = _seed_customer(
        db_session,
        organization_id,
        display_name="Multi Email Co",
        normalized_name="multi email co",
    )
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                email="shared@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                email="other@example.com",
                is_primary=False,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
        SqlAlchemyCustomerCommunicationRepository,
    )

    communications = SqlAlchemyCustomerCommunicationRepository(db_session).load_for_customer(customer.id)
    keys = grouping_keys_for_customer("email", customer, communications)

    assert keys == ["shared@example.com", "other@example.com"]


def test_analyze_customer_groups_by_email_customer_in_two_duplicate_groups(db_session, organization_id):
    """Hub customer with two emails can belong to two duplicate groups at once."""
    hub = _seed_customer(db_session, organization_id, display_name="Hub Co", normalized_name="hub co")
    partner_b = _seed_customer(db_session, organization_id, display_name="Partner B", normalized_name="partner b")
    partner_c = _seed_customer(db_session, organization_id, display_name="Partner C", normalized_name="partner c")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=hub.id,
                email="shared-one@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=hub.id,
                email="shared-two@example.com",
                is_primary=False,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=partner_b.id,
                email="shared-one@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=partner_c.id,
                email="shared-two@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    summary, member_rows = analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="email",
    )

    assert summary.duplicate_groups == 2
    assert summary.customers_in_duplicate_groups == 4
    assert {row.group_key for row in member_rows} == {
        "shared-one@example.com",
        "shared-two@example.com",
    }
    hub_rows = [row for row in member_rows if row.customer_id == hub.id]
    assert len(hub_rows) == 2
    assert {row.group_key for row in hub_rows} == {
        "shared-one@example.com",
        "shared-two@example.com",
    }


def test_build_duplicate_customer_groups_dataset_persists_customer_in_multiple_email_groups(
    db_session,
    organization_id,
):
    from app.modules.system_admin.application.data_operation_dataset_builders import (
        build_duplicate_customer_groups_dataset,
    )
    from app.modules.system_admin.infrastructure.persistence.models import SystemDataOperationDatasetRowModel

    hub = _seed_customer(db_session, organization_id, display_name="Hub Co", normalized_name="hub co")
    partner_b = _seed_customer(db_session, organization_id, display_name="Partner B", normalized_name="partner b")
    partner_c = _seed_customer(db_session, organization_id, display_name="Partner C", normalized_name="partner c")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=hub.id,
                email="shared-one@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=hub.id,
                email="shared-two@example.com",
                is_primary=False,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=partner_b.id,
                email="shared-one@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=partner_c.id,
                email="shared-two@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    run_id = uuid4()
    summary = build_duplicate_customer_groups_dataset(
        db_session,
        organization_id=organization_id,
        run_id=run_id,
        group_by="email",
    )
    assert summary.duplicate_groups == 2
    assert summary.customers_in_duplicate_groups == 4

    rows = (
        db_session.query(SystemDataOperationDatasetRowModel)
        .filter(SystemDataOperationDatasetRowModel.run_id == run_id)
        .order_by(
            SystemDataOperationDatasetRowModel.duplicate_group_key.asc(),
            SystemDataOperationDatasetRowModel.entity_id.asc(),
        )
        .all()
    )
    assert len(rows) == 4
    hub_rows = [row for row in rows if row.entity_id == hub.id]
    assert len(hub_rows) == 2
    assert {row.duplicate_group_key for row in hub_rows} == {
        "shared-one@example.com",
        "shared-two@example.com",
    }

    build_duplicate_customer_groups_dataset(
        db_session,
        organization_id=organization_id,
        run_id=run_id,
        group_by="email",
    )
    rerun_count = (
        db_session.query(SystemDataOperationDatasetRowModel)
        .filter(SystemDataOperationDatasetRowModel.run_id == run_id)
        .count()
    )
    assert rerun_count == 4


def test_analyze_customer_groups_by_email_allows_customer_in_multiple_groups(db_session, organization_id):
    first = _seed_customer(db_session, organization_id, display_name="Co A", normalized_name="co a")
    second = _seed_customer(db_session, organization_id, display_name="Co B", normalized_name="co b")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first.id,
                email="shared@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first.id,
                email="only-a@example.com",
                is_primary=False,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=second.id,
                email="shared@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=second.id,
                email="only-b@example.com",
                is_primary=False,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    summary, member_rows = analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="email",
    )

    assert summary.duplicate_groups == 1
    assert summary.customers_in_duplicate_groups == 2
    assert {row.group_key for row in member_rows} == {"shared@example.com"}
    assert {row.customer_id for row in member_rows} == {first.id, second.id}


def test_analyze_customer_groups_dedupes_customer_within_same_group(db_session, organization_id):
    first = _seed_customer(db_session, organization_id, display_name="Co A", normalized_name="co a")
    second = _seed_customer(db_session, organization_id, display_name="Co B", normalized_name="co b")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerPhoneModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first.id,
                phone="0212 555 0101",
                is_primary=True,
                created_at=now,
            ),
            CustomerPhoneModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first.id,
                phone="+90 212 555 0101",
                is_primary=False,
                created_at=now,
            ),
            CustomerPhoneModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=second.id,
                phone="0212 555 0101",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    _summary, member_rows = analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="phone",
    )

    phone_group_rows = [row for row in member_rows if row.group_key == "902125550101"]
    assert len(phone_group_rows) == 2
    assert len({row.customer_id for row in phone_group_rows}) == 2


def test_analyze_customer_groups_by_website_uses_all_rows(db_session, organization_id):
    first = _seed_customer(db_session, organization_id, display_name="Co A", normalized_name="co a")
    second = _seed_customer(db_session, organization_id, display_name="Co B", normalized_name="co b")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first.id,
                website="https://www.example.com",
                is_primary=False,
                created_at=now,
            ),
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=second.id,
                website="http://example.com/path",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    summary, member_rows = analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="website",
    )

    assert summary.duplicate_groups == 1
    assert {row.group_key for row in member_rows} == {"example.com"}
    assert len(member_rows) == 2


def test_analyze_customer_groups_includes_archived_customers(db_session, organization_id):
    active = _seed_customer(db_session, organization_id, display_name="Active Co", normalized_name="active co")
    archived = _seed_customer(db_session, organization_id, display_name="Archived Co", normalized_name="archived co")
    archived.deleted_at = datetime.now(tz=UTC)
    archived.status = CustomerStatus.ARCHIVED.value
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=active.id,
                email="shared@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=archived.id,
                email="shared@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    summary, member_rows = analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="email",
    )

    assert summary.duplicate_groups == 1
    assert {row.customer_id for row in member_rows} == {active.id, archived.id}
    assert summary.total_customers == 2


def test_analyze_customer_groups_excludes_deleted_customers(db_session, organization_id):
    active = _seed_customer(db_session, organization_id, display_name="Active Co", normalized_name="active co")
    deleted = _seed_customer(db_session, organization_id, display_name="Deleted Co", normalized_name="deleted co")
    deleted.deleted_at = datetime.now(tz=UTC)
    deleted.status = CustomerStatus.DELETED.value
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=active.id,
                email="shared@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=deleted.id,
                email="shared@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    summary, member_rows = analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="email",
    )

    assert summary.duplicate_groups == 0
    assert member_rows == []
    assert summary.total_customers == 1


def test_analyze_customer_groups_by_company_name_groups_similar_legal_suffixes(
    db_session,
    organization_id,
):
    first = _seed_customer(
        db_session,
        organization_id,
        display_name="A.R.T. YAYINCILIK LTD.",
        normalized_name="a r t yayincilik ltd",
    )
    second = _seed_customer(
        db_session,
        organization_id,
        display_name="A.R.T. YAYINCILIK LTD. ŞTİ.",
        normalized_name="a r t yayincilik",
    )
    db_session.flush()

    summary, member_rows = analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="company_name",
    )

    assert summary.duplicate_groups == 1
    assert summary.customers_in_duplicate_groups == 2
    assert {row.customer_id for row in member_rows} == {first.id, second.id}
    assert len({row.group_key for row in member_rows}) == 1
    assert member_rows[0].group_key == "A R T YAYINCILIK"


def test_analyze_customer_groups_by_company_name_fuzzy_flag_controls_similarity_merge(
    db_session,
    organization_id,
    monkeypatch,
):
    _seed_customer(
        db_session,
        organization_id,
        display_name="Flag Test Co",
        normalized_name="flag test co",
    )
    db_session.flush()

    from app.modules.customers.application.duplicate_company_name_grouping import (
        CompanyNameBucketMergeResult,
    )

    merge_calls: list[bool] = []

    def spy_merge(buckets):
        merge_calls.append(True)
        return CompanyNameBucketMergeResult(buckets=buckets, merge_events=())

    monkeypatch.setattr(
        "app.modules.customers.application.duplicate_company_name_grouping.merge_similar_company_name_buckets",
        spy_merge,
    )

    analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="company_name",
        company_name_fuzzy_matching=False,
    )
    analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="company_name",
        company_name_fuzzy_matching=True,
    )

    assert merge_calls == [True]


def test_analyze_customer_groups_by_company_name_excludes_deleted_customers(
    db_session,
    organization_id,
):
    active = _seed_customer(
        db_session,
        organization_id,
        display_name="A.R.T. YAYINCILIK LTD.",
        normalized_name="a r t yayincilik ltd",
    )
    deleted = _seed_customer(
        db_session,
        organization_id,
        display_name="A.R.T. YAYINCILIK LTD. ŞTİ.",
        normalized_name="a r t yayincilik",
    )
    deleted.deleted_at = datetime.now(tz=UTC)
    deleted.status = CustomerStatus.DELETED.value
    db_session.flush()

    summary, member_rows = analyze_customer_groups_by_field(
        db_session,
        organization_id=organization_id,
        group_by="company_name",
    )

    assert summary.duplicate_groups == 0
    assert member_rows == []
    assert summary.total_customers == 1
