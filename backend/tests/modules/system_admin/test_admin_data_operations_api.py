"""Admin data operations API tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel


def _seed_customers(db_session, organization_id):
    now = datetime.now(tz=UTC)
    customer_with_fair = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Assigned Co",
        normalized_name="assigned co",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    customer_without_fair = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Unassigned Co",
        normalized_name="unassigned co",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([customer_with_fair, customer_without_fair])
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Test Fair",
        normalized_name="test fair",
        status="planned",
        created_at=now,
        updated_at=now,
    )
    participation = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer_with_fair.id,
        fair_id=fair.id,
        participation_status="exhibitor",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([fair, participation])
    db_session.flush()
    return customer_with_fair, customer_without_fair


def test_list_data_operations(client, auth_headers):
    response = client.get("/api/v1/admin/data-operations", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    keys = {item["key"] for item in items}
    assert "analyze_customers_without_fair" in keys
    assert "duplicate_customer_analysis" in keys
    assert "export_duplicate_customers" not in keys
    assert "export_duplicate_customers_by_fair" not in keys
    assert "delete_customers_without_fair" not in keys
    analyze = next(item for item in items if item["key"] == "analyze_customers_without_fair")
    assert analyze["result_mode"] == "dataset"
    assert analyze["dataset_kind"] == "customers_without_fair"
    duplicate = next(item for item in items if item["key"] == "duplicate_customer_analysis")
    assert duplicate["result_mode"] == "dataset"
    assert duplicate["dataset_kind"] == "duplicate_customer_groups"


def test_run_and_poll_duplicate_customer_analysis_dataset(client, auth_headers, db_session, organization_id):
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel

    now = datetime.now(tz=UTC)
    first_id = uuid4()
    second_id = uuid4()
    first = CustomerModel(
        id=first_id,
        organization_id=organization_id,
        display_name="Dup Co A",
        normalized_name="dup co a",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    second = CustomerModel(
        id=second_id,
        organization_id=organization_id,
        display_name="Dup Co B",
        normalized_name="dup co b",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all(
        [
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=second_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    assert create.status_code == 202
    body = create.json()
    run_id = body["id"]
    assert body["operation_key"] == "duplicate_customer_analysis"
    assert body["result_mode"] == "dataset"
    assert body["dataset_kind"] == "duplicate_customer_groups"

    detail = client.get(f"/api/v1/admin/data-operations/runs/{run_id}", headers=auth_headers)
    assert detail.status_code == 200
    run = detail.json()
    assert run["status"] == "completed"
    assert run["result"] == "success"
    assert run["dataset_kind"] == "duplicate_customer_groups"
    assert run["summary_json"]["group_by"] == "email"
    assert run["summary_json"]["total_customers"] == 2
    assert run["summary_json"]["duplicate_groups"] == 1
    assert run["summary_json"]["customers_in_duplicate_groups"] == 2
    assert run["output_files"] == []

    listing = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-customers",
        headers=auth_headers,
    )
    assert listing.status_code == 200
    data = listing.json()
    assert data["pagination"]["totalItems"] == 2
    groups = {item["group_key"] for item in data["items"]}
    assert len(groups) == 1
    assert all(item["group_by"] == "email" for item in data["items"])

    group_listing = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups",
        headers=auth_headers,
    )
    assert group_listing.status_code == 200
    group_data = group_listing.json()
    assert group_data["pagination"]["totalItems"] == 1
    group = group_data["items"][0]
    assert group["group_by"] == "email"
    assert group["customer_count"] == 2
    assert group["fair_count"] == 0
    assert group["group_key"] == "dup@example.com"
    assert group["created_at_min"]
    assert group["created_at_max"]

    group_key = group["group_key"]
    detail = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups/{group_key}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["group_key"] == group_key
    assert detail_body["group_by"] == "email"
    assert len(detail_body["customers"]) == 2
    assert detail_body["merge_policy"]
    for customer in detail_body["customers"]:
        assert "phones" in customer
        assert "emails" in customer
        assert "websites" in customer
        assert len(customer["emails"]) == 1
        assert customer["emails"][0]["email"] == "dup@example.com"


def test_duplicate_customer_analysis_email_customer_in_multiple_groups(
    client,
    auth_headers,
    db_session,
    organization_id,
):
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel

    now = datetime.now(tz=UTC)
    hub_id = uuid4()
    partner_b_id = uuid4()
    partner_c_id = uuid4()
    db_session.add_all(
        [
            CustomerModel(
                id=hub_id,
                organization_id=organization_id,
                display_name="Hub Co",
                normalized_name="hub co",
                customer_type=CustomerType.LEAD.value,
                status=CustomerStatus.ACTIVE.value,
                source="manual",
                created_at=now,
                updated_at=now,
            ),
            CustomerModel(
                id=partner_b_id,
                organization_id=organization_id,
                display_name="Partner B",
                normalized_name="partner b",
                customer_type=CustomerType.LEAD.value,
                status=CustomerStatus.ACTIVE.value,
                source="manual",
                created_at=now,
                updated_at=now,
            ),
            CustomerModel(
                id=partner_c_id,
                organization_id=organization_id,
                display_name="Partner C",
                normalized_name="partner c",
                customer_type=CustomerType.LEAD.value,
                status=CustomerStatus.ACTIVE.value,
                source="manual",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=hub_id,
                email="shared-one@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=hub_id,
                email="shared-two@example.com",
                is_primary=False,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=partner_b_id,
                email="shared-one@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=partner_c_id,
                email="shared-two@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    assert create.status_code == 202
    run_id = create.json()["id"]

    detail = client.get(f"/api/v1/admin/data-operations/runs/{run_id}", headers=auth_headers)
    assert detail.status_code == 200
    run = detail.json()
    assert run["status"] == "completed"
    assert run["result"] == "success"
    assert run["summary_json"]["duplicate_groups"] == 2
    assert run["summary_json"]["customers_in_duplicate_groups"] == 4

    group_listing = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups",
        headers=auth_headers,
    )
    assert group_listing.status_code == 200
    assert group_listing.json()["pagination"]["totalItems"] == 2

    duplicate_customers = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-customers",
        headers=auth_headers,
    )
    assert duplicate_customers.status_code == 200
    assert duplicate_customers.json()["pagination"]["totalItems"] == 4
    hub_rows = [item for item in duplicate_customers.json()["items"] if item["id"] == str(hub_id)]
    assert len(hub_rows) == 2
    assert {item["group_key"] for item in hub_rows} == {
        "shared-one@example.com",
        "shared-two@example.com",
    }

    rerun = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    assert rerun.status_code == 202
    rerun_run = client.get(
        f"/api/v1/admin/data-operations/runs/{rerun.json()['id']}",
        headers=auth_headers,
    )
    assert rerun_run.status_code == 200
    assert rerun_run.json()["status"] == "completed"
    assert rerun_run.json()["result"] == "success"
    assert rerun_run.json()["summary_json"]["duplicate_groups"] == 2


def test_duplicate_group_merge_preview_endpoint(client, auth_headers, db_session, organization_id):
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel

    now = datetime.now(tz=UTC)
    first_id = uuid4()
    second_id = uuid4()
    email_one = uuid4()
    email_two = uuid4()
    first = CustomerModel(
        id=first_id,
        organization_id=organization_id,
        display_name="Dup Co A",
        normalized_name="dup co a",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    second = CustomerModel(
        id=second_id,
        organization_id=organization_id,
        display_name="Dup Co B",
        normalized_name="dup co b",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all(
        [
            CustomerEmailModel(
                id=email_one,
                organization_id=organization_id,
                customer_id=first_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=email_two,
                organization_id=organization_id,
                customer_id=second_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    assert create.status_code == 202
    run_id = create.json()["id"]
    group_key = "dup@example.com"

    preview = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{group_key}/merge-preview",
        headers=auth_headers,
        json={
            "run_id": run_id,
            "surviving_customer_id": str(first_id),
            "scalar_selections": {
                "company_name": str(first_id),
                "legal_name": str(first_id),
                "trade_name": str(first_id),
                "city": str(first_id),
                "country": str(first_id),
            },
            "selected_email_ids": [str(email_one), str(email_two)],
            "selected_phone_ids": [],
            "selected_website_ids": [],
        },
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["group_key"] == group_key
    assert body["surviving_customer_id"] == str(first_id)
    assert body["is_valid"] is True
    assert body["statistics"]["customers_before"] == 2
    assert body["statistics"]["customers_after"] == 1
    assert body["statistics"]["emails_before"] == 2
    assert body["statistics"]["emails_after"] == 1
    assert len(body["emails"]) == 1
    assert body["merged_customer"]["display_name"] == "Dup Co A"
    assert body["customers_to_archive"] == [str(second_id)]
    assert body["participation_summary"]["total_participation_rows"] == 0


def test_duplicate_group_merge_preview_returns_400_for_foreign_communication_id(
    client, auth_headers, db_session, organization_id
):
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel

    now = datetime.now(tz=UTC)
    first_id = uuid4()
    second_id = uuid4()
    email_one = uuid4()
    email_two = uuid4()
    first = CustomerModel(
        id=first_id,
        organization_id=organization_id,
        display_name="Dup Co A",
        normalized_name="dup co a",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    second = CustomerModel(
        id=second_id,
        organization_id=organization_id,
        display_name="Dup Co B",
        normalized_name="dup co b",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all(
        [
            CustomerEmailModel(
                id=email_one,
                organization_id=organization_id,
                customer_id=first_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=email_two,
                organization_id=organization_id,
                customer_id=second_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    assert create.status_code == 202
    run_id = create.json()["id"]
    group_key = "dup@example.com"
    foreign_website_id = uuid4()

    preview = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{group_key}/merge-preview",
        headers={**auth_headers, "Origin": "http://localhost:5173"},
        json={
            "run_id": run_id,
            "surviving_customer_id": str(first_id),
            "scalar_selections": {
                "company_name": str(first_id),
                "legal_name": str(first_id),
                "trade_name": str(first_id),
                "city": str(first_id),
                "country": str(first_id),
            },
            "selected_email_ids": [str(email_one)],
            "selected_phone_ids": [],
            "selected_website_ids": [str(foreign_website_id)],
        },
    )
    assert preview.status_code == 400
    assert "not found in this duplicate group" in preview.json()["detail"].lower()
    assert preview.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_duplicate_group_merge_execute_endpoint(client, auth_headers, db_session, organization_id, user_id):
    from app.modules.customers.domain.value_objects import CustomerStatus
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
    from app.modules.system_admin.infrastructure.persistence.models import DuplicateGroupMergeAuditLogModel

    now = datetime.now(tz=UTC)
    first_id = uuid4()
    second_id = uuid4()
    email_one = uuid4()
    email_two = uuid4()
    first = CustomerModel(
        id=first_id,
        organization_id=organization_id,
        display_name="Dup Co A",
        normalized_name="dup co a",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    second = CustomerModel(
        id=second_id,
        organization_id=organization_id,
        display_name="Dup Co B",
        normalized_name="dup co b",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all(
        [
            CustomerEmailModel(
                id=email_one,
                organization_id=organization_id,
                customer_id=first_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=email_two,
                organization_id=organization_id,
                customer_id=second_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    assert create.status_code == 202
    run_id = create.json()["id"]
    group_key = "dup@example.com"
    assert db_session.query(DuplicateGroupMergeAuditLogModel).count() == 0

    execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{group_key}/merge-execute",
        headers={**auth_headers, "Origin": "http://localhost:5173"},
        json={
            "run_id": run_id,
            "surviving_customer_id": str(first_id),
            "scalar_selections": {
                "company_name": str(first_id),
                "legal_name": str(first_id),
                "trade_name": str(first_id),
                "city": str(first_id),
                "country": str(first_id),
            },
            "selected_email_ids": [str(email_one), str(email_two)],
            "selected_phone_ids": [],
            "selected_website_ids": [],
        },
    )
    assert execute.status_code == 200
    body = execute.json()
    assert body["group_key"] == group_key
    assert body["surviving_customer"]["id"] == str(first_id)
    assert body["surviving_customer"]["display_name"] == "Dup Co A"
    assert body["customers_deleted"] == [str(second_id)]
    assert body["statistics"]["customers_before"] == 2
    assert body["statistics"]["customers_after"] == 1
    assert body["statistics"]["emails_after"] == 1

    db_session.expire_all()
    survivor = db_session.get(CustomerModel, first_id)
    deleted = db_session.get(CustomerModel, second_id)
    assert survivor is not None
    assert deleted is not None
    assert deleted.deleted_at is not None
    assert deleted.status == CustomerStatus.DELETED.value

    survivor_emails = (
        db_session.query(CustomerEmailModel)
        .filter(CustomerEmailModel.customer_id == first_id)
        .all()
    )
    assert len(survivor_emails) == 1
    assert survivor_emails[0].email == "dup@example.com"

    audit_logs = (
        db_session.query(DuplicateGroupMergeAuditLogModel)
        .filter(DuplicateGroupMergeAuditLogModel.organization_id == organization_id)
        .all()
    )
    assert len(audit_logs) == 1
    audit_log = audit_logs[0]
    assert audit_log.executed_by_user_id == user_id
    assert audit_log.executed_by_user_email == "test@example.com"
    assert audit_log.run_id == UUID(run_id)
    assert audit_log.group_key == group_key
    assert audit_log.group_by == "email"
    assert audit_log.surviving_customer_id == first_id
    assert audit_log.archived_customer_ids == [str(second_id)]
    assert audit_log.scalar_field_sources["company_name"] == str(first_id)
    assert audit_log.selected_email_ids == [str(email_one), str(email_two)]
    assert audit_log.selected_phone_ids == []
    assert audit_log.selected_website_ids == []
    assert audit_log.statistics["customers_before"] == 2
    assert audit_log.statistics["customers_after"] == 1
    assert audit_log.statistics["emails_after"] == 1
    assert audit_log.reconstruction_json["surviving_customer"]["display_name"] == "Dup Co A"
    assert len(audit_log.reconstruction_json["final_communications"]["emails"]) == 1
    assert audit_log.executed_at is not None
    assert execute.headers.get("access-control-allow-origin") == "http://localhost:5173"

    groups_after = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups",
        headers=auth_headers,
    )
    assert groups_after.status_code == 200
    assert groups_after.json()["pagination"]["totalItems"] == 0
    assert groups_after.json()["filters"]["liveDuplicateGroups"] == 0

    duplicate_customers_after = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-customers",
        headers=auth_headers,
    )
    assert duplicate_customers_after.status_code == 200
    assert duplicate_customers_after.json()["pagination"]["totalItems"] == 1

    merged_group_detail = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups/{group_key}",
        headers=auth_headers,
    )
    assert merged_group_detail.status_code == 404


def test_duplicate_group_merge_execute_is_idempotent(client, auth_headers, db_session, organization_id):
    from app.modules.customers.domain.value_objects import CustomerStatus
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel

    now = datetime.now(tz=UTC)
    first_id = uuid4()
    second_id = uuid4()
    email_one = uuid4()
    email_two = uuid4()
    db_session.add_all(
        [
            CustomerModel(
                id=first_id,
                organization_id=organization_id,
                display_name="Dup Co A",
                normalized_name="dup co a",
                customer_type=CustomerType.LEAD.value,
                status=CustomerStatus.ACTIVE.value,
                source="manual",
                created_at=now,
                updated_at=now,
            ),
            CustomerModel(
                id=second_id,
                organization_id=organization_id,
                display_name="Dup Co B",
                normalized_name="dup co b",
                customer_type=CustomerType.LEAD.value,
                status=CustomerStatus.ACTIVE.value,
                source="manual",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            CustomerEmailModel(
                id=email_one,
                organization_id=organization_id,
                customer_id=first_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=email_two,
                organization_id=organization_id,
                customer_id=second_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    run_id = create.json()["id"]
    group_key = "dup@example.com"
    payload = {
        "run_id": run_id,
        "surviving_customer_id": str(first_id),
        "scalar_selections": {
            "company_name": str(first_id),
            "legal_name": str(first_id),
            "trade_name": str(first_id),
            "city": str(first_id),
            "country": str(first_id),
        },
        "selected_email_ids": [str(email_one), str(email_two)],
        "selected_phone_ids": [],
        "selected_website_ids": [],
    }

    first_execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{group_key}/merge-execute",
        headers={**auth_headers, "Origin": "http://localhost:5173"},
        json=payload,
    )
    assert first_execute.status_code == 200

    second_execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{group_key}/merge-execute",
        headers={**auth_headers, "Origin": "http://localhost:5173"},
        json=payload,
    )
    assert second_execute.status_code == 200
    assert second_execute.json()["surviving_customer"]["id"] == str(first_id)
    assert second_execute.json()["customers_deleted"] == [str(second_id)]


def test_duplicate_group_merge_execute_rejects_invalid_selection(client, auth_headers, db_session, organization_id):
    from app.modules.customers.infrastructure.persistence.communication_models import CustomerEmailModel
    from app.modules.system_admin.infrastructure.persistence.models import DuplicateGroupMergeAuditLogModel

    now = datetime.now(tz=UTC)
    first_id = uuid4()
    second_id = uuid4()
    email_one = uuid4()
    email_two = uuid4()
    first = CustomerModel(
        id=first_id,
        organization_id=organization_id,
        display_name="Dup Co A",
        normalized_name="dup co a",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    second = CustomerModel(
        id=second_id,
        organization_id=organization_id,
        display_name="Dup Co B",
        normalized_name="dup co b",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all(
        [
            CustomerEmailModel(
                id=email_one,
                organization_id=organization_id,
                customer_id=first_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=email_two,
                organization_id=organization_id,
                customer_id=second_id,
                email="dup@example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    run_id = create.json()["id"]
    group_key = "dup@example.com"
    audit_count_before = db_session.query(DuplicateGroupMergeAuditLogModel).count()

    execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{group_key}/merge-execute",
        headers={**auth_headers, "Origin": "http://localhost:5173"},
        json={
            "run_id": run_id,
            "surviving_customer_id": str(first_id),
            "scalar_selections": {
                "company_name": str(first_id),
                "legal_name": str(first_id),
                "trade_name": str(first_id),
                "city": str(first_id),
                "country": str(first_id),
            },
            "selected_email_ids": [],
            "selected_phone_ids": [],
            "selected_website_ids": [],
        },
    )
    assert execute.status_code == 400
    assert isinstance(execute.json().get("detail"), str)
    assert execute.json()["detail"]
    assert execute.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert db_session.query(DuplicateGroupMergeAuditLogModel).count() == audit_count_before

    db_session.expire_all()
    archived = db_session.get(CustomerModel, second_id)
    assert archived.status == CustomerStatus.ACTIVE.value
    assert archived.deleted_at is None


def test_duplicate_customer_analysis_group_detail_returns_all_communications(
    client, auth_headers, db_session, organization_id
):
    from app.modules.customers.infrastructure.persistence.communication_models import (
        CustomerEmailModel,
        CustomerPhoneModel,
        CustomerWebsiteModel,
    )

    now = datetime.now(tz=UTC)
    first_id = uuid4()
    second_id = uuid4()
    first = CustomerModel(
        id=first_id,
        organization_id=organization_id,
        display_name="Dup Co A",
        normalized_name="dup co a",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    second = CustomerModel(
        id=second_id,
        organization_id=organization_id,
        display_name="Dup Co B",
        normalized_name="dup co b",
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all(
        [
            CustomerPhoneModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first_id,
                phone="0212 555 0101",
                is_primary=True,
                created_at=now,
            ),
            CustomerPhoneModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first_id,
                phone="0532 555 0102",
                is_primary=False,
                created_at=now,
            ),
            CustomerPhoneModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=second_id,
                phone="0212 555 0101",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first_id,
                email="info@example.com",
                is_primary=True,
                created_at=now,
            ),
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=first_id,
                website="https://example.com",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    db_session.flush()

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "phone"},
    )
    assert create.status_code == 202
    run_id = create.json()["id"]

    group_listing = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups",
        headers=auth_headers,
    )
    group_key = group_listing.json()["items"][0]["group_key"]

    detail = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/duplicate-groups/{group_key}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    first_customer = next(item for item in detail.json()["customers"] if item["id"] == str(first_id))
    assert len(first_customer["phones"]) == 2
    assert len(first_customer["emails"]) == 1
    assert len(first_customer["websites"]) == 1


def test_duplicate_customer_analysis_requires_group_by(client, auth_headers):
    response = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_analyze_customers_without_fair_dataset(client, auth_headers, db_session, organization_id):
    _seed_customers(db_session, organization_id)

    create = client.post(
        "/api/v1/admin/data-operations/analyze_customers_without_fair/run",
        headers=auth_headers,
    )
    assert create.status_code == 202
    run_id = create.json()["id"]

    detail = client.get(f"/api/v1/admin/data-operations/runs/{run_id}", headers=auth_headers)
    assert detail.status_code == 200
    run = detail.json()
    assert run["status"] == "completed"
    assert run["result"] == "success"
    assert run["dataset_kind"] == "customers_without_fair"
    assert run["summary_json"]["total_customers"] == 2
    assert run["summary_json"]["customers_with_fair"] == 1
    assert run["summary_json"]["customers_without_fair"] == 1
    assert run["output_files"] == []

    listing = client.get(
        f"/api/v1/admin/data-operations/runs/{run_id}/dataset/customers",
        headers=auth_headers,
    )
    assert listing.status_code == 200
    data = listing.json()
    assert data["pagination"]["totalItems"] == 1
    assert data["items"][0]["display_name"] == "Unassigned Co"


def test_run_unknown_operation_returns_404(client, auth_headers):
    response = client.post(
        "/api/v1/admin/data-operations/unknown_operation/run",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_assign_customers_to_fair_from_analyze_dataset(client, auth_headers, db_session, organization_id):
    _seed_customers(db_session, organization_id)
    now = datetime.now(tz=UTC)
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Assign Target Fair",
        normalized_name="assign target fair",
        status="planned",
        created_at=now,
        updated_at=now,
    )
    db_session.add(fair)
    db_session.flush()
    fair_id = fair.id

    create = client.post(
        "/api/v1/admin/data-operations/analyze_customers_without_fair/run",
        headers=auth_headers,
    )
    assert create.status_code == 202
    analyze_run_id = create.json()["id"]

    listing = client.get(
        f"/api/v1/admin/data-operations/runs/{analyze_run_id}/dataset/customers",
        headers=auth_headers,
    )
    customer_id = listing.json()["items"][0]["id"]

    assign = client.post(
        f"/api/v1/admin/data-operations/runs/{analyze_run_id}/assign-fair",
        headers=auth_headers,
        json={"fair_id": str(fair_id), "customer_ids": [customer_id]},
    )
    assert assign.status_code == 202
    assign_run_id = assign.json()["id"]

    assign_detail = client.get(
        f"/api/v1/admin/data-operations/runs/{assign_run_id}",
        headers=auth_headers,
    )
    assert assign_detail.status_code == 200
    assign_run = assign_detail.json()
    assert assign_run["status"] == "completed"
    assert assign_run["result"] == "success"
    assert assign_run["summary_json"]["assigned_count"] == 1
    assert assign_run["summary_json"]["skipped_count"] == 0
    assert assign_run["summary_json"]["failed_count"] == 0

    listing_after = client.get(
        f"/api/v1/admin/data-operations/runs/{analyze_run_id}/dataset/customers",
        headers=auth_headers,
    )
    assert listing_after.json()["pagination"]["totalItems"] == 0

    analyze_detail = client.get(
        f"/api/v1/admin/data-operations/runs/{analyze_run_id}",
        headers=auth_headers,
    )
    summary = analyze_detail.json()["summary_json"]
    assert summary["customers_with_fair"] == 2
    assert summary["customers_without_fair"] == 0

    participation_count = (
        db_session.query(CustomerFairParticipationModel)
        .filter(
            CustomerFairParticipationModel.organization_id == organization_id,
            CustomerFairParticipationModel.customer_id == UUID(customer_id),
            CustomerFairParticipationModel.fair_id == fair_id,
        )
        .count()
    )
    assert participation_count == 1


def test_delete_selected_customers_from_analyze_dataset(client, auth_headers, db_session, organization_id):
    _seed_customers(db_session, organization_id)

    create = client.post(
        "/api/v1/admin/data-operations/analyze_customers_without_fair/run",
        headers=auth_headers,
    )
    assert create.status_code == 202
    analyze_run_id = create.json()["id"]

    listing = client.get(
        f"/api/v1/admin/data-operations/runs/{analyze_run_id}/dataset/customers",
        headers=auth_headers,
    )
    customer_id = listing.json()["items"][0]["id"]

    delete = client.post(
        f"/api/v1/admin/data-operations/runs/{analyze_run_id}/delete-customers",
        headers=auth_headers,
        json={"customer_ids": [customer_id]},
    )
    assert delete.status_code == 202
    delete_run_id = delete.json()["id"]

    delete_detail = client.get(
        f"/api/v1/admin/data-operations/runs/{delete_run_id}",
        headers=auth_headers,
    )
    assert delete_detail.status_code == 200
    delete_run = delete_detail.json()
    assert delete_run["status"] == "completed"
    assert delete_run["result"] == "success"
    assert delete_run["summary_json"]["deleted_count"] == 1
    assert delete_run["summary_json"]["skipped_count"] == 0
    assert delete_run["summary_json"]["failed_count"] == 0

    listing_after = client.get(
        f"/api/v1/admin/data-operations/runs/{analyze_run_id}/dataset/customers",
        headers=auth_headers,
    )
    assert listing_after.json()["pagination"]["totalItems"] == 0

    analyze_detail = client.get(
        f"/api/v1/admin/data-operations/runs/{analyze_run_id}",
        headers=auth_headers,
    )
    summary = analyze_detail.json()["summary_json"]
    assert summary["total_customers"] == 1
    assert summary["customers_without_fair"] == 0

    assert db_session.get(CustomerModel, UUID(customer_id)) is None
