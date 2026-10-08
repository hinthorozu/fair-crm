from datetime import UTC, date, datetime
from uuid import uuid4

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.auth import create_test_token
from app.integrations.kyrox_core.dev_bypass import NoOpAuditAdapter
from app.integrations.kyrox_core.super_admin import get_super_admin_reader
from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailBatchModel
from app.modules.fairs.api.dependencies import get_audit_adapter
from app.modules.fairs.application.merge_system_fair import (
    SystemFairDuplicateService,
    SystemFairMergeBlockedError,
    SystemFairMergeCommand,
    repoint_operation_documents,
)
from app.modules.fairs.application.sync_tobb_system_fairs import SyncTobbSystemFairsUseCase
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.exceptions import SystemFairAlreadyMergedError
from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.fairs.infrastructure.tobb_calendar import TobbFairRow
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.operations.infrastructure.persistence.models import OperationModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.quote_templates.infrastructure.models import QuoteTemplateModel
from app.modules.quotes.infrastructure.models import QuoteModel
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel
from app.modules.todos.infrastructure.persistence.models import TodoModel


class _Audit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def record_event(self, **kwargs) -> None:
        self.events.append(kwargs)


class _Reader:
    def __init__(self, row: TobbFairRow) -> None:
        self.row = row

    def read(self, year: int) -> list[TobbFairRow]:
        return [self.row]


def _service(db_session, audit=None) -> SystemFairDuplicateService:
    return SystemFairDuplicateService(
        db_session,
        SqlAlchemyFairRepository(db_session),
        audit or NoOpAuditAdapter(),
    )


def _fair(db_session, **overrides) -> Fair:
    now = datetime.now(tz=UTC)
    name = overrides.pop("name")
    values = {
        "id": uuid4(),
        "organization_id": None,
        "name": name,
        "organizer": "TOBB",
        "venue": "Tüyap",
        "city": "İstanbul",
        "country": "Türkiye",
        "start_date": date(2026, 10, 1),
        "end_date": date(2026, 10, 4),
        "website": "https://example.test",
        "status": FairStatus.PLANNED,
        "description": None,
        "normalized_name": compute_normalized_name(name=name),
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
        "origin": "system",
        "source": "tobb",
        "external_id": "2026:1",
        "adapter_key": None,
        "source_url": None,
        "scraper_config": None,
    }
    values.update(overrides)
    return SqlAlchemyFairRepository(db_session).add(Fair(**values))


def _command(organization_id, user_id, source_id, target_id) -> SystemFairMergeCommand:
    return SystemFairMergeCommand(
        organization_id=organization_id,
        user_id=user_id,
        access_token="token",
        source_fair_id=source_id,
        target_fair_id=target_id,
    )


def _customer(db_session, organization_id) -> CustomerModel:
    now = datetime.now(tz=UTC)
    row = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Musteri",
        normalized_name="musteri",
        customer_type="lead",
        status="active",
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _participation(db_session, organization_id, customer_id, fair_id, hall: str) -> CustomerFairParticipationModel:
    now = datetime.now(tz=UTC)
    row = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer_id,
        fair_id=fair_id,
        hall=hall,
        stand="S1",
        notes="not",
        participation_status="exhibitor",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_repoint_operation_documents_changes_only_fair_reference_keys():
    source = uuid4()
    target = uuid4()
    other = uuid4()
    config, typed, changed = repoint_operation_documents(
        source_kind="fair",
        source_config={
            "source_ids": [str(source), str(target), str(other)],
            "fair_id": str(source),
            "note": str(source),
        },
        type_config={"fair_ids": [str(source), str(other)], "label": "keep"},
        source_id=source,
        target_id=target,
    )

    assert changed is True
    assert config["source_ids"] == [str(target), str(other)]
    assert config["fair_id"] == str(target)
    assert config["note"] == str(source)
    assert typed["fair_ids"] == [str(target), str(other)]
    assert typed["label"] == "keep"

    untouched, _typed, changed = repoint_operation_documents(
        source_kind="customer",
        source_config={"source_ids": [str(source)]},
        type_config={"run_note": str(source)},
        source_id=source,
        target_id=target,
    )
    assert changed is False
    assert untouched["source_ids"] == [str(source)]


def test_merge_moves_references_archives_source_and_audits(
    db_session, organization_id, user_id
):
    target = _fair(db_session, name="KYROX MERGE FAIR 2026 31. FUARI", external_id="2026:31")
    source = _fair(
        db_session,
        name="KYROX MERGE FAIR 2027 32. FUARI",
        external_id="2027:32",
        start_date=date(2027, 10, 1),
        end_date=date(2027, 10, 4),
        adapter_key="pack",
        source_url="https://source.example",
        scraper_config={"page": 1},
    )
    customer = _customer(db_session, organization_id)
    participation = _participation(db_session, organization_id, customer.id, source.id, "A1")
    now = datetime.now(tz=UTC)
    todo = TodoModel(
        id=uuid4(),
        organization_id=organization_id,
        title="Teklif hazirla",
        status="todo",
        priority="normal",
        category="genel_gorev",
        source_fair_id=source.id,
        created_by=user_id,
        created_at=now,
        updated_at=now,
    )
    template = QuoteTemplateModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Sablon",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([todo, template])
    db_session.flush()
    quote = QuoteModel(
        id=uuid4(),
        organization_id=organization_id,
        todo_id=todo.id,
        customer_id=customer.id,
        fair_id=source.id,
        template_id=template.id,
        quote_date=date(2026, 10, 8),
        status="draft",
        price="",
        selected_items=[],
        created_by=user_id,
        updated_by=user_id,
        created_at=now,
        updated_at=now,
    )
    activity = ActivityModel(
        id=uuid4(),
        organization_id=organization_id,
        fair_id=source.id,
        activity_type="note",
        subject="Gorusme",
        activity_date=now,
        status="done",
        source="manual",
        metadata_json={"fair_id": str(source.id), "fair_name": "eski ad"},
        created_at=now,
        updated_at=now,
    )
    batch = ImportBatchModel(
        id=uuid4(),
        organization_id=organization_id,
        fair_id=source.id,
        source_type="excel",
        file_name="katilim.xlsx",
        status="completed",
        created_at=now,
        updated_at=now,
    )
    email_batch = FairEmailBatchModel(
        id=uuid4(),
        organization_id=organization_id,
        fair_id=source.id,
        template_id=uuid4(),
        recipient_options_json={},
        status="queued",
        created_by_user_id=user_id,
        created_at=now,
        updated_at=now,
    )
    mail = MailSendOperationModel(
        id=uuid4(),
        organization_id=organization_id,
        recipient_email="a@example.test",
        fair_id=source.id,
        fair_name="KYROX MERGE FAIR 2027",
        created_at=now,
        updated_at=now,
    )
    run = ScraperRunHistoryModel(
        id=uuid4(),
        adapter_key="pack",
        status="completed",
        started_at=now,
        fair_id=source.id,
        fair_name="eski scraper adi",
        fair_year=2027,
    )
    other = uuid4()
    operation = OperationModel(
        id=uuid4(),
        organization_id=organization_id,
        operation_type="enrichment",
        title="Zenginlestir",
        status="draft",
        source_kind="fair",
        source_config={"source_ids": [str(source.id), str(other)], "note": str(source.id)},
        type_config={"fair_id": str(source.id)},
        run_settings={"fair_id": str(source.id)},
        created_by=user_id,
        created_at=now,
        updated_at=now,
    )
    customer_operation = OperationModel(
        id=uuid4(),
        organization_id=organization_id,
        operation_type="enrichment",
        title="Musteri",
        status="draft",
        source_kind="customer",
        source_config={"source_ids": [str(source.id)]},
        type_config={},
        run_settings={},
        created_by=user_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all(
        [quote, activity, batch, email_batch, mail, run, operation, customer_operation]
    )
    db_session.flush()
    audit = _Audit()
    service = _service(db_session, audit)
    preview = service.preview(source.id, target.id)
    assert preview.blocking_conflicts == ()
    assert preview.participations == 1
    assert preview.todos == 1
    assert preview.quotes == 1
    assert preview.activities == 1
    assert preview.imports == 1
    assert preview.scraper_runs == 1
    assert preview.email_batches == 1
    assert preview.mail_operations == 1
    assert preview.operations == 1

    result = service.merge(_command(organization_id, user_id, source.id, target.id))
    assert result.operations == preview.operations
    db_session.expire_all()

    kept = db_session.get(FairModel, target.id)
    removed = db_session.get(FairModel, source.id)
    assert kept is not None and kept.deleted_at is None
    assert kept.adapter_key == "pack"
    assert kept.source_url == "https://source.example"
    assert kept.scraper_config == {"page": 1}
    assert removed is not None
    assert removed.status == "archived"
    assert removed.deleted_at is not None
    assert removed.external_id is None
    assert db_session.get(CustomerFairParticipationModel, participation.id).fair_id == target.id
    assert db_session.get(TodoModel, todo.id).source_fair_id == target.id
    assert db_session.get(QuoteModel, quote.id).fair_id == target.id
    moved_activity = db_session.get(ActivityModel, activity.id)
    assert moved_activity.fair_id == target.id
    assert moved_activity.metadata_json["fair_name"] == "eski ad"
    assert moved_activity.subject == "Gorusme"
    assert db_session.get(ImportBatchModel, batch.id).fair_id == target.id
    assert db_session.get(FairEmailBatchModel, email_batch.id).fair_id == target.id
    moved_mail = db_session.get(MailSendOperationModel, mail.id)
    assert moved_mail.fair_id == target.id
    assert moved_mail.fair_name == "KYROX MERGE FAIR 2027"
    moved_run = db_session.get(ScraperRunHistoryModel, run.id)
    assert moved_run.fair_id == target.id
    assert moved_run.fair_name == "eski scraper adi"
    assert moved_run.fair_year == 2027
    moved_operation = db_session.get(OperationModel, operation.id)
    assert moved_operation.source_config["source_ids"] == [str(target.id), str(other)]
    assert moved_operation.source_config["note"] == str(source.id)
    assert moved_operation.type_config["fair_id"] == str(target.id)
    assert moved_operation.run_settings["fair_id"] == str(source.id)
    assert db_session.get(OperationModel, customer_operation.id).source_config["source_ids"] == [
        str(source.id)
    ]
    assert audit.events[0]["action"] == "fair_crm.system_fair.merged"
    assert audit.events[0]["metadata"]["source_fair_id"] == str(source.id)
    assert audit.events[0]["metadata"]["target_fair_id"] == str(target.id)
    assert audit.events[0]["metadata"]["user_id"] == str(user_id)

    try:
        service.merge(_command(organization_id, user_id, source.id, target.id))
        raise AssertionError("second merge should fail")
    except SystemFairAlreadyMergedError:
        pass
    db_session.expire_all()
    assert db_session.get(QuoteModel, quote.id).fair_id == target.id
    assert db_session.get(TodoModel, todo.id).source_fair_id == target.id


def test_organization_fair_cannot_be_merged(db_session, organization_id, user_id):
    system = _fair(db_session, name="KYROX MERGE FAIR 2026 31. FUARI", external_id="2026:31")
    owned = _fair(
        db_session,
        name="KYROX MERGE FAIR 2027 32. FUARI",
        external_id=None,
        origin="organization",
        source="manual",
        organization_id=organization_id,
    )
    service = _service(db_session)
    try:
        service.merge(_command(organization_id, user_id, owned.id, system.id))
        raise AssertionError("organization source should be rejected")
    except ForbiddenError:
        pass
    try:
        service.merge(_command(organization_id, user_id, system.id, owned.id))
        raise AssertionError("organization target should be rejected")
    except ForbiddenError:
        pass


def test_participation_without_collision_moves_and_collision_blocks(
    db_session, organization_id, user_id
):
    target = _fair(db_session, name="KYROX MOVE FAIR 2026 31. FUARI", external_id="2026:41")
    source = _fair(
        db_session,
        name="KYROX MOVE FAIR 2027 32. FUARI",
        external_id="2027:42",
        start_date=date(2027, 5, 1),
        end_date=date(2027, 5, 4),
    )
    customer = _customer(db_session, organization_id)
    moved = _participation(db_session, organization_id, customer.id, source.id, "A1")
    service = _service(db_session)
    service.merge(_command(organization_id, user_id, source.id, target.id))
    db_session.expire_all()
    assert db_session.get(CustomerFairParticipationModel, moved.id).fair_id == target.id
    assert db_session.get(CustomerFairParticipationModel, moved.id).hall == "A1"

    left = _fair(db_session, name="KYROX CLASH FAIR 2026 11. FUARI", external_id="2026:11")
    right = _fair(
        db_session,
        name="KYROX CLASH FAIR 2027 12. FUARI",
        external_id="2027:12",
        start_date=date(2027, 6, 1),
        end_date=date(2027, 6, 4),
    )
    shared = _customer(db_session, organization_id)
    on_left = _participation(db_session, organization_id, shared.id, left.id, "H1")
    on_right = _participation(db_session, organization_id, shared.id, right.id, "H2")
    try:
        service.merge(_command(organization_id, user_id, right.id, left.id))
        raise AssertionError("collision should block")
    except SystemFairMergeBlockedError as exc:
        assert exc.conflicts[0]["code"] == "participation_collision"
    db_session.expire_all()
    assert db_session.get(CustomerFairParticipationModel, on_left.id).hall == "H1"
    assert db_session.get(CustomerFairParticipationModel, on_right.id).fair_id == right.id
    assert db_session.get(FairModel, right.id).status != "archived"


def test_scraper_metadata_conflict_blocks_and_empty_target_receives_source(
    db_session, organization_id, user_id
):
    target = _fair(
        db_session,
        name="KYROX SCRAPE FAIR 2026 31. FUARI",
        external_id="2026:71",
        adapter_key="left",
        source_url="https://left.example",
        scraper_config={"mode": "a"},
    )
    source = _fair(
        db_session,
        name="KYROX SCRAPE FAIR 2027 32. FUARI",
        external_id="2027:72",
        start_date=date(2027, 7, 1),
        end_date=date(2027, 7, 4),
        adapter_key="right",
        source_url="https://right.example",
        scraper_config={"mode": "b"},
    )
    service = _service(db_session)
    try:
        service.merge(_command(organization_id, user_id, source.id, target.id))
        raise AssertionError("scraper conflict should block")
    except SystemFairMergeBlockedError as exc:
        assert any(item["code"] == "scraper_conflict" for item in exc.conflicts)
    db_session.expire_all()
    assert db_session.get(FairModel, target.id).adapter_key == "left"
    assert db_session.get(FairModel, source.id).deleted_at is None

    open_target = _fair(db_session, name="KYROX OPEN FAIR 2026 31. FUARI", external_id="2026:81")
    filled = _fair(
        db_session,
        name="KYROX OPEN FAIR 2027 32. FUARI",
        external_id="2027:82",
        start_date=date(2027, 8, 1),
        end_date=date(2027, 8, 4),
        adapter_key="pack",
        source_url="https://filled.example",
        scraper_config={"page": 2},
    )
    service.merge(_command(organization_id, user_id, filled.id, open_target.id))
    db_session.expire_all()
    kept = db_session.get(FairModel, open_target.id)
    assert kept.adapter_key == "pack"
    assert kept.source_url == "https://filled.example"
    assert kept.scraper_config == {"page": 2}


def test_merge_rolls_back_when_a_later_step_fails(db_session, organization_id, user_id):
    target = _fair(db_session, name="KYROX ROLLBACK FAIR 2026 31. FUARI", external_id="2026:91")
    source = _fair(
        db_session,
        name="KYROX ROLLBACK FAIR 2027 32. FUARI",
        external_id="2027:92",
        start_date=date(2027, 9, 1),
        end_date=date(2027, 9, 4),
    )
    customer = _customer(db_session, organization_id)
    participation = _participation(db_session, organization_id, customer.id, source.id, "R1")
    service = _service(db_session)
    service._failpoint = "after_repoint"
    try:
        service.merge(_command(organization_id, user_id, source.id, target.id))
        raise AssertionError("failpoint should raise")
    except RuntimeError:
        pass
    db_session.expire_all()
    assert db_session.get(CustomerFairParticipationModel, participation.id).fair_id == source.id
    assert db_session.get(FairModel, source.id).deleted_at is None
    assert db_session.get(FairModel, source.id).external_id == "2027:92"


def test_same_year_distinct_editions_are_not_review_groups(db_session):
    _fair(db_session, name="KYROX IJS 2026 59. FUARI", external_id="2026:59")
    _fair(db_session, name="KYROX IJS 2026 60. FUARI", external_id="2026:60")
    groups = _service(db_session).list_groups()
    assert all("IJS" not in group.identity_name for group in groups)


def test_keep_separate_stops_the_matcher_repeating_the_conflict(db_session):
    older = _fair(db_session, name="KYROX DISTINCT FAIR 2026 31. FUARI", external_id="2026:31")
    newer = _fair(
        db_session,
        name="KYROX DISTINCT FAIR 2027 32. FUARI",
        external_id="2027:32",
        start_date=date(2027, 3, 1),
        end_date=date(2027, 3, 4),
    )
    service = _service(db_session)
    assert len(service.list_groups()) == 1
    row = TobbFairRow(
        sequence_no="33",
        name="KYROX DISTINCT FAIR 2028 33. FUARI",
        organizer="TOBB",
        venue="Tüyap",
        city="İstanbul",
        start_date=date(2028, 3, 1),
        end_date=date(2028, 3, 4),
        website="https://example.test",
    )
    sync = SyncTobbSystemFairsUseCase(SqlAlchemyFairRepository(db_session), _Reader(row))
    before = sync.execute(2028)
    assert before.conflicts == 1
    assert before.inserted == 0
    created = service.keep_separate([older.id, newer.id])
    assert created == 2
    assert service.keep_separate([older.id, newer.id]) == 0
    assert service.list_groups() == []
    after = sync.execute(2028)
    assert after.conflicts == 0
    assert after.inserted == 0
    assert after.updated == 0
    active = (
        db_session.query(FairModel)
        .filter(FairModel.origin == "system", FairModel.deleted_at.is_(None))
        .count()
    )
    assert active == 2

    same_year = TobbFairRow(
        sequence_no="80",
        name="KYROX DISTINCT FAIR 2027 32. FUARI",
        organizer="TOBB",
        venue="Tüyap",
        city="İstanbul",
        start_date=date(2027, 3, 2),
        end_date=date(2027, 3, 5),
        website="https://updated.example",
    )
    updated = SyncTobbSystemFairsUseCase(
        SqlAlchemyFairRepository(db_session), _Reader(same_year)
    ).execute(2027)
    assert updated.updated == 1
    assert updated.conflicts == 0
    db_session.expire_all()
    assert db_session.get(FairModel, newer.id).website == "updated.example"


def test_organization_admin_cannot_merge_and_super_admin_can(
    client, db_session, auth_headers, organization_id, user_id
):
    target = _fair(db_session, name="KYROX API FAIR 2026 31. FUARI", external_id="2026:101")
    source = _fair(
        db_session,
        name="KYROX API FAIR 2027 32. FUARI",
        external_id="2027:102",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 1, 4),
    )
    db_session.commit()
    denied = client.post(
        f"/api/v1/fairs/system/{source.id}/merge",
        headers=auth_headers,
        json={"target_fair_id": str(target.id)},
    )
    assert denied.status_code == 403
    db_session.expire_all()
    assert db_session.get(FairModel, source.id).deleted_at is None

    client.app.dependency_overrides[get_super_admin_reader] = lambda: (
        lambda _access_token, _organization_id: True
    )
    client.app.dependency_overrides[get_audit_adapter] = lambda: NoOpAuditAdapter()
    preview = client.post(
        "/api/v1/fairs/system/duplicates/preview",
        headers=auth_headers,
        json={"source_fair_id": str(source.id), "target_fair_id": str(target.id)},
    )
    assert preview.status_code == 200
    assert preview.json()["participations"] == 0
    assert preview.json()["blocking_conflicts"] == []
    merged = client.post(
        f"/api/v1/fairs/system/{source.id}/merge",
        headers=auth_headers,
        json={"target_fair_id": str(target.id)},
    )
    assert merged.status_code == 200
    db_session.expire_all()
    assert db_session.get(FairModel, source.id).status == "archived"
    again = client.post(
        f"/api/v1/fairs/system/{source.id}/merge",
        headers={
            "Authorization": f"Bearer {create_test_token(user_id=user_id)}",
            "X-Organization-Id": str(organization_id),
        },
        json={"target_fair_id": str(target.id)},
    )
    assert again.status_code == 409
