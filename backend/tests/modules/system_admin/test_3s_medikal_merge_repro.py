"""Reproduce 3S MEDIKAL 8-customer email duplicate group merge execute."""

from datetime import UTC, date, datetime
from urllib.parse import quote
from uuid import UUID, uuid4

from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel

GROUP_EMAIL = "info@3smedikal.com"


def _seed_3s_medikal_group(db_session, organization_id):
    """8 customers sharing info@3smedikal.com with overlapping fair participations."""
    now = datetime.now(tz=UTC)
    company_names = [
        "3S MEDİKAL TİC. LTD. ŞTİ.",
        "3S MEDİKAL",
        "3S Medikal Ltd",
        "3S MEDİKAL SAN.",
        "3S Medikal Ticaret",
        "3S MEDİKAL İSTANBUL",
        "3S Medikal Co",
        "3S MEDİKAL A.Ş.",
    ]
    phones = ["2323685410", "2323685411", "2323685412", "05321234567"]
    websites = ["3smedikal.com", "www.3smedikal.com", "http://3smedikal.com"]

    customer_ids = []
    email_ids = []
    phone_ids = []
    website_ids = []
    customers = []

    for idx, name in enumerate(company_names):
        cid = uuid4()
        customer_ids.append(cid)
        customers.append(
            CustomerModel(
                id=cid,
                organization_id=organization_id,
                display_name=name,
                legal_name=name if idx % 2 == 0 else None,
                normalized_name=name.lower(),
                customer_type=CustomerType.LEAD.value,
                status=CustomerStatus.ACTIVE.value,
                country="Türkiye" if idx < 4 else None,
                city="İzmir" if idx % 3 == 0 else "İstanbul",
                source="manual",
                created_at=now,
                updated_at=now,
            )
        )

    db_session.add_all(customers)
    db_session.flush()

    comm_rows = []
    for idx, cid in enumerate(customer_ids):
        eid = uuid4()
        email_ids.append(eid)
        comm_rows.append(
            CustomerEmailModel(
                id=eid,
                organization_id=organization_id,
                customer_id=cid,
                email=GROUP_EMAIL,
                is_primary=True,
                created_at=now,
            )
        )
        if idx < len(phones):
            pid = uuid4()
            phone_ids.append(pid)
            comm_rows.append(
                CustomerPhoneModel(
                    id=pid,
                    organization_id=organization_id,
                    customer_id=cid,
                    phone=phones[idx % len(phones)],
                    is_primary=True,
                    created_at=now,
                )
            )
        if idx < len(websites):
            wid = uuid4()
            website_ids.append(wid)
            comm_rows.append(
                CustomerWebsiteModel(
                    id=wid,
                    organization_id=organization_id,
                    customer_id=cid,
                    website=websites[idx % len(websites)],
                    is_primary=idx == 0,
                    created_at=now,
                )
            )
    db_session.add_all(comm_rows)
    db_session.flush()

    fair_names = [
        "IDEX İSTANBUL",
        "MEDİCAL FUAR",
        "SAHA EXPO",
        "EXPOMED",
        "ISTANBUL HEALTH",
        "ANATOLIA MED",
    ]
    fairs = []
    for name in fair_names:
        fairs.append(
            FairModel(
                id=uuid4(),
                organization_id=organization_id,
                name=name,
                normalized_name=name.lower(),
                status="completed",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 5),
                created_at=now,
                updated_at=now,
            )
        )
    db_session.add_all(fairs)
    db_session.flush()

    # 15 participation rows across 8 customers (overlapping fairs like production data)
    participation_plan = [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 2),
        (2, 1),
        (2, 3),
        (3, 0),
        (3, 4),
        (4, 2),
        (4, 5),
        (5, 1),
        (5, 3),
        (6, 4),
        (7, 0),
        (7, 5),
    ]
    participations = []
    for cust_idx, fair_idx in participation_plan:
        participations.append(
            CustomerFairParticipationModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer_ids[cust_idx],
                fair_id=fairs[fair_idx].id,
                participation_status="exhibitor",
                created_at=now,
                updated_at=now,
            )
        )
    db_session.add_all(participations)

    # Survivor has a soft-deleted participation for fair 0 (legacy overlap scenario).
    participations.append(
        CustomerFairParticipationModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer_ids[0],
            fair_id=fairs[0].id,
            participation_status="exhibitor",
            deleted_at=now,
            created_at=now,
            updated_at=now,
        )
    )

    contacts = []
    for idx, cid in enumerate(customer_ids):
        contacts.append(
            ContactModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=cid,
                first_name=f"Contact{idx}",
                last_name="Medikal",
                is_primary=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
    db_session.add_all(contacts)
    db_session.flush()

    return {
        "customer_ids": customer_ids,
        "survivor_id": customer_ids[0],
        "email_ids": email_ids,
        "phone_ids": phone_ids,
        "website_ids": website_ids,
    }


def test_duplicate_group_merge_execute_3s_medikal_group(client, auth_headers, db_session, organization_id):
    seed = _seed_3s_medikal_group(db_session, organization_id)
    survivor_id = seed["survivor_id"]
    customer_ids = seed["customer_ids"]

    create = client.post(
        "/api/v1/admin/data-operations/duplicate_customer_analysis/run",
        headers=auth_headers,
        json={"group_by": "email"},
    )
    assert create.status_code == 202
    run_id = create.json()["id"]
    group_key = GROUP_EMAIL
    encoded_key = quote(group_key, safe="")

    preview = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{encoded_key}/merge-preview",
        headers=auth_headers,
        json={
            "run_id": run_id,
            "surviving_customer_id": str(survivor_id),
            "scalar_selections": {
                "company_name": str(survivor_id),
                "legal_name": str(survivor_id),
                "trade_name": str(survivor_id),
                "city": str(survivor_id),
                "country": str(survivor_id),
            },
            "selected_email_ids": [str(eid) for eid in seed["email_ids"]],
            "selected_phone_ids": [str(pid) for pid in seed["phone_ids"]],
            "selected_website_ids": [str(wid) for wid in seed["website_ids"]],
        },
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["is_valid"] is True, preview_body.get("validation_errors")

    execute = client.post(
        f"/api/v1/admin/data-operations/duplicate-groups/{encoded_key}/merge-execute",
        headers={**auth_headers, "Origin": "http://localhost:5173"},
        json={
            "run_id": run_id,
            "surviving_customer_id": str(survivor_id),
            "scalar_selections": {
                "company_name": str(survivor_id),
                "legal_name": str(survivor_id),
                "trade_name": str(survivor_id),
                "city": str(survivor_id),
                "country": str(survivor_id),
            },
            "selected_email_ids": [str(eid) for eid in seed["email_ids"]],
            "selected_phone_ids": [str(pid) for pid in seed["phone_ids"]],
            "selected_website_ids": [str(wid) for wid in seed["website_ids"]],
        },
    )
    assert execute.status_code == 200, execute.text
    body = execute.json()
    assert body["group_key"] == group_key
    assert body["surviving_customer"]["id"] == str(survivor_id)
    assert len(body["customers_deleted"]) == len(customer_ids) - 1
    assert body["statistics"]["customers_before"] == 8
    assert body["statistics"]["customers_after"] == 1
    assert execute.headers.get("access-control-allow-origin") == "http://localhost:5173"

    db_session.expire_all()
    for loser_id in body["customers_deleted"]:
        loser = db_session.get(CustomerModel, UUID(loser_id) if isinstance(loser_id, str) else loser_id)
        assert loser is not None
        assert loser.status == CustomerStatus.DELETED.value
        assert loser.deleted_at is not None
