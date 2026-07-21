"""Enrichment state transitions after import apply."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.activities.infrastructure.repositories.activity_repository import SqlAlchemyActivityRepository
from app.modules.contacts.infrastructure.repositories.contact_repository import SqlAlchemyContactRepository
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.imports.application.apply_import_decisions import (
    ApplyImportDecisionsCommand,
    ApplyImportDecisionsUseCase,
)
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.commands import ApplyImportCommand
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.value_objects import (
    ImportBatchStatus,
    ImportDecision,
    ImportRowStatus,
    ImportSourceType,
)
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.modules.scraper.domain.customer_enrichment_state import CustomerEnrichmentScanStatus
from app.modules.scraper.infrastructure.persistence.models import CustomerEnrichmentStateModel
from app.modules.scraper.services.customer_enrichment_state_service import (
    is_customer_scan_eligible,
    load_state_map,
    record_enrichment_apply_outcome,
)
from tests.conftest import AllowAllAuthorization, NoOpAudit


def _seed_customer(db_session, organization_id, *, display_name: str) -> CustomerModel:
    now = datetime.now(tz=UTC)
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name=display_name,
        normalized_name=display_name.lower(),
        customer_type=CustomerType.LEAD.value,
        status=CustomerStatus.ACTIVE.value,
        source="manual",
        created_at=now,
        updated_at=now,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def _seed_pending_merge_state(
    db_session,
    organization_id,
    customer: CustomerModel,
    *,
    email_found: str = "found@apply.example",
) -> None:
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerEnrichmentStateModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            website="https://apply.test",
            last_enrichment_run_id=None,
            last_email_scan_at=now,
            last_email_scan_status=CustomerEnrichmentScanStatus.PENDING_MERGE,
            last_email_found=email_found,
            last_source_url="https://apply.test/contact",
            last_error=None,
            retry_after=None,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()


def _enrichment_batch(organization_id) -> ImportBatch:
    now = datetime.now(tz=UTC)
    return ImportBatch.create_from_canonical(
        organization_id=organization_id,
        fair_id=None,
        source_type=ImportSourceType.SCRAPER,
        file_name="customer_contact_enrichment-test.json",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        raw_preview_json={
            "canonical_source": {"adapter_key": "customer_contact_enrichment"},
        },
        now=now,
    )


def _build_apply_use_case(db_session) -> ApplyImportUseCase:
    comm_repo = SqlAlchemyCustomerCommunicationRepository(db_session)
    return ApplyImportUseCase(
        SqlAlchemyImportBatchRepository(db_session),
        SqlAlchemyImportRowRepository(db_session),
        SqlAlchemyCustomerRepository(db_session),
        CustomerCommunicationSyncService(comm_repo),
        SqlAlchemyContactRepository(db_session),
        SqlAlchemyActivityRepository(db_session),
        SqlAlchemyParticipationRepository(db_session),
        AllowAllAuthorization(),
        NoOpAudit(),
        db_session,
    )


def test_record_enrichment_apply_outcome_email_found_keeps_last_email(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Apply Found Co")
    _seed_pending_merge_state(db_session, organization_id, customer, email_found="found@apply.example")

    record_enrichment_apply_outcome(
        db_session,
        organization_id=organization_id,
        customer_id=customer.id,
        had_email_before=False,
        email_written=True,
    )
    db_session.commit()

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.EMAIL_FOUND
    assert state.last_email_found == "found@apply.example"


def test_record_enrichment_apply_outcome_marks_email_found_when_customer_already_had_email(
    db_session, organization_id
):
    customer = _seed_customer(db_session, organization_id, display_name="Apply Existing Email Co")
    _seed_pending_merge_state(
        db_session, organization_id, customer, email_found="new@apply.example"
    )

    record_enrichment_apply_outcome(
        db_session,
        organization_id=organization_id,
        customer_id=customer.id,
        had_email_before=True,
        email_written=False,
    )
    db_session.commit()

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.EMAIL_FOUND
    assert state.last_email_found == "new@apply.example"


def test_record_enrichment_apply_outcome_keeps_pending_merge_when_no_email_written(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Apply Pending Co")
    _seed_pending_merge_state(db_session, organization_id, customer)

    record_enrichment_apply_outcome(
        db_session,
        organization_id=organization_id,
        customer_id=customer.id,
        had_email_before=False,
        email_written=False,
    )
    db_session.commit()

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.PENDING_MERGE


def test_apply_enrichment_import_writes_email_and_marks_email_found(db_session, organization_id, user_id):
    customer = _seed_customer(db_session, organization_id, display_name="Apply Integration Co")
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerWebsiteModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            website="https://apply.test",
            is_primary=True,
            created_at=now,
        )
    )
    _seed_pending_merge_state(db_session, organization_id, customer, email_found="info@apply.example")

    batch = _enrichment_batch(organization_id)
    batch.status = ImportBatchStatus.ANALYZED
    saved_batch = SqlAlchemyImportBatchRepository(db_session).add(batch)

    row = ImportRow.create(
        batch_id=saved_batch.id,
        organization_id=organization_id,
        row_number=1,
        raw_data_json={"external_id": str(customer.id)},
        normalized_data_json={
            "company_name": customer.display_name,
            "external_id": str(customer.id),
            "email": "info@apply.example",
            "website": "https://apply.test",
        },
        status=ImportRowStatus.READY_TO_UPDATE,
        validation_errors_json=None,
        match_customer_id=customer.id,
        match_confidence=100,
        match_reason="enrichment_customer_id",
        now=now,
    )
    row.decision = ImportDecision.UPDATE_EXISTING
    SqlAlchemyImportRowRepository(db_session).add_many([row])
    db_session.commit()

    use_case = _build_apply_use_case(db_session)
    command = ApplyImportCommand(
        organization_id=organization_id,
        user_id=user_id,
        access_token="token",
        batch_id=saved_batch.id,
    )
    counters = use_case.finalize_applied_row(saved_batch, row, command, now)
    db_session.commit()

    assert counters.applied is True
    assert counters.updated == 1

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.EMAIL_FOUND
    assert state.last_email_found == "info@apply.example"

    communications = CustomerCommunicationSyncService(
        SqlAlchemyCustomerCommunicationRepository(db_session)
    ).load_for_customer(customer.id)
    assert any(item.email == "info@apply.example" for item in communications.emails)


def test_apply_enrichment_import_merges_new_email_when_customer_already_has_email(
    db_session, organization_id, user_id
):
    customer = _seed_customer(db_session, organization_id, display_name="Already Has Email Co")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website="https://existing.test",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                email="existing@apply.example",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    _seed_pending_merge_state(db_session, organization_id, customer, email_found="new@apply.example")

    batch = _enrichment_batch(organization_id)
    batch.status = ImportBatchStatus.ANALYZED
    saved_batch = SqlAlchemyImportBatchRepository(db_session).add(batch)

    row = ImportRow.create(
        batch_id=saved_batch.id,
        organization_id=organization_id,
        row_number=1,
        raw_data_json={"external_id": str(customer.id)},
        normalized_data_json={
            "company_name": customer.display_name,
            "external_id": str(customer.id),
            "email": "new@apply.example",
        },
        status=ImportRowStatus.READY_TO_UPDATE,
        validation_errors_json=None,
        match_customer_id=customer.id,
        match_confidence=100,
        match_reason="enrichment_customer_id",
        now=now,
    )
    row.decision = ImportDecision.UPDATE_EXISTING
    SqlAlchemyImportRowRepository(db_session).add_many([row])
    db_session.commit()

    use_case = _build_apply_use_case(db_session)
    command = ApplyImportCommand(
        organization_id=organization_id,
        user_id=user_id,
        access_token="token",
        batch_id=saved_batch.id,
    )
    counters = use_case.finalize_applied_row(saved_batch, row, command, now)
    db_session.commit()

    assert counters.applied is True
    assert counters.updated == 1

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.EMAIL_FOUND
    assert state.last_email_found == "new@apply.example"

    communications = CustomerCommunicationSyncService(
        SqlAlchemyCustomerCommunicationRepository(db_session)
    ).load_for_customer(customer.id)
    emails = {item.email for item in communications.emails}
    assert emails == {"existing@apply.example", "new@apply.example"}


def test_apply_enrichment_import_does_not_duplicate_existing_email(
    db_session, organization_id, user_id
):
    customer = _seed_customer(db_session, organization_id, display_name="Duplicate Email Co")
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            CustomerWebsiteModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                website="https://dup.test",
                is_primary=True,
                created_at=now,
            ),
            CustomerEmailModel(
                id=uuid4(),
                organization_id=organization_id,
                customer_id=customer.id,
                email="info@dup.example",
                is_primary=True,
                created_at=now,
            ),
        ]
    )
    _seed_pending_merge_state(db_session, organization_id, customer, email_found="info@dup.example")

    batch = _enrichment_batch(organization_id)
    batch.status = ImportBatchStatus.ANALYZED
    saved_batch = SqlAlchemyImportBatchRepository(db_session).add(batch)

    row = ImportRow.create(
        batch_id=saved_batch.id,
        organization_id=organization_id,
        row_number=1,
        raw_data_json={"external_id": str(customer.id)},
        normalized_data_json={
            "company_name": customer.display_name,
            "external_id": str(customer.id),
            "email": "info@dup.example",
        },
        status=ImportRowStatus.READY_TO_UPDATE,
        validation_errors_json=None,
        match_customer_id=customer.id,
        match_confidence=100,
        match_reason="enrichment_customer_id",
        now=now,
    )
    row.decision = ImportDecision.UPDATE_EXISTING
    SqlAlchemyImportRowRepository(db_session).add_many([row])
    db_session.commit()

    use_case = _build_apply_use_case(db_session)
    command = ApplyImportCommand(
        organization_id=organization_id,
        user_id=user_id,
        access_token="token",
        batch_id=saved_batch.id,
    )
    use_case.finalize_applied_row(saved_batch, row, command, now)
    db_session.commit()

    communications = CustomerCommunicationSyncService(
        SqlAlchemyCustomerCommunicationRepository(db_session)
    ).load_for_customer(customer.id)
    emails = [item.email for item in communications.emails]
    assert emails == ["info@dup.example"]

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.EMAIL_FOUND


def _build_apply_decisions_use_case(db_session) -> ApplyImportDecisionsUseCase:
    apply_use_case = _build_apply_use_case(db_session)
    return ApplyImportDecisionsUseCase(
        SqlAlchemyImportBatchRepository(db_session),
        SqlAlchemyImportRowRepository(db_session),
        apply_use_case,
        AllowAllAuthorization(),
        NoOpAudit(),
    )


def test_sync_email_write_does_not_delete_pending_merge_state(db_session, organization_id):
    customer = _seed_customer(db_session, organization_id, display_name="Sync Write Co")
    _seed_pending_merge_state(db_session, organization_id, customer, email_found="info@sync.example")
    now = datetime.now(tz=UTC)

    CustomerCommunicationSyncService(
        SqlAlchemyCustomerCommunicationRepository(db_session)
    ).sync_from_value_lists(
        organization_id=organization_id,
        customer_id=customer.id,
        now=now,
        emails=["info@sync.example"],
        sync_email=True,
    )
    db_session.commit()

    state = load_state_map(db_session, organization_id, [customer.id]).get(customer.id)
    assert state is not None
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.PENDING_MERGE
    assert state.last_email_found == "info@sync.example"


def test_apply_enrichment_import_via_decisions_marks_email_found(db_session, organization_id, user_id):
    customer = _seed_customer(db_session, organization_id, display_name="Decisions Apply Co")
    now = datetime.now(tz=UTC)
    db_session.add(
        CustomerWebsiteModel(
            id=uuid4(),
            organization_id=organization_id,
            customer_id=customer.id,
            website="https://apply.test",
            is_primary=True,
            created_at=now,
        )
    )
    _seed_pending_merge_state(db_session, organization_id, customer, email_found="info@apply.example")

    batch = _enrichment_batch(organization_id)
    batch.status = ImportBatchStatus.ANALYZED
    saved_batch = SqlAlchemyImportBatchRepository(db_session).add(batch)

    row = ImportRow.create(
        batch_id=saved_batch.id,
        organization_id=organization_id,
        row_number=1,
        raw_data_json={"external_id": str(customer.id)},
        normalized_data_json={
            "company_name": customer.display_name,
            "external_id": str(customer.id),
            "email": "info@apply.example",
            "website": "https://apply.test",
        },
        status=ImportRowStatus.READY_TO_UPDATE,
        validation_errors_json=None,
        match_customer_id=customer.id,
        match_confidence=100,
        match_reason="enrichment_customer_id",
        now=now,
    )
    row.decision = ImportDecision.UPDATE_EXISTING
    SqlAlchemyImportRowRepository(db_session).add_many([row])
    db_session.commit()

    result = _build_apply_decisions_use_case(db_session).execute(
        ApplyImportDecisionsCommand(
            organization_id=organization_id,
            user_id=user_id,
            access_token="token",
            batch_id=saved_batch.id,
            row_ids=[row.id],
        )
    )
    db_session.commit()

    assert result.processed_count == 1
    assert result.failed_count == 0

    state = load_state_map(db_session, organization_id, [customer.id]).get(customer.id)
    assert state is not None
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.EMAIL_FOUND
    assert state.last_email_found == "info@apply.example"

    communications = CustomerCommunicationSyncService(
        SqlAlchemyCustomerCommunicationRepository(db_session)
    ).load_for_customer(customer.id)
    assert any(item.email == "info@apply.example" for item in communications.emails)

    assert is_customer_scan_eligible(state, website="https://apply.test") is False


def test_apply_enrichment_skip_decision_keeps_pending_merge(db_session, organization_id, user_id):
    customer = _seed_customer(db_session, organization_id, display_name="Skip Decision Co")
    _seed_pending_merge_state(db_session, organization_id, customer)
    now = datetime.now(tz=UTC)

    batch = _enrichment_batch(organization_id)
    batch.status = ImportBatchStatus.ANALYZED
    saved_batch = SqlAlchemyImportBatchRepository(db_session).add(batch)

    row = ImportRow.create(
        batch_id=saved_batch.id,
        organization_id=organization_id,
        row_number=1,
        raw_data_json={"external_id": str(customer.id)},
        normalized_data_json={"company_name": customer.display_name, "email": "skip@apply.example"},
        status=ImportRowStatus.READY_TO_UPDATE,
        validation_errors_json=None,
        match_customer_id=customer.id,
        match_confidence=100,
        match_reason="enrichment_customer_id",
        now=now,
    )
    row.decision = ImportDecision.SKIP
    SqlAlchemyImportRowRepository(db_session).add_many([row])
    db_session.commit()

    use_case = _build_apply_use_case(db_session)
    command = ApplyImportCommand(
        organization_id=organization_id,
        user_id=user_id,
        access_token="token",
        batch_id=saved_batch.id,
    )
    use_case.finalize_applied_row(saved_batch, row, command, now)
    db_session.commit()

    state = load_state_map(db_session, organization_id, [customer.id])[customer.id]
    assert state.last_email_scan_status == CustomerEnrichmentScanStatus.PENDING_MERGE
