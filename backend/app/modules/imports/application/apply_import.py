from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.activities.domain.value_objects import ActivitySource, ActivityStatus, ActivityType
from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.customers.domain.value_objects import CustomerSource
from app.modules.imports.application.commands import ApplyImportCommand, ApplyImportResult
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.domain.exceptions import ImportBatchAlreadyAppliedError, ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.value_objects import ImportBatchStatus, ImportDecision, ImportRowStatus
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.value_objects import ParticipationStatus
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.shared.email import normalize_email_field

PERMISSION_APPLY = "fair_crm.imports.apply"


@dataclass
class _ParticipationResult:
    id: UUID
    created: bool
    updated: bool


def _merge_email_fields(existing: str | None, incoming: str | None) -> str | None:
    if not incoming:
        return existing
    if not existing:
        return normalize_email_field(incoming)
    combined = f"{existing};{incoming}"
    return normalize_email_field(combined)


def _fill_if_empty(current: str | None, incoming: str | None) -> str | None:
    if current and current.strip():
        return current
    if incoming and str(incoming).strip():
        return str(incoming).strip()
    return current


class ApplyImportUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        customer_repository: CustomerRepository,
        contact_repository: ContactRepository,
        activity_repository: ActivityRepository,
        participation_repository: SqlAlchemyParticipationRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._customer_repository = customer_repository
        self._contact_repository = contact_repository
        self._activity_repository = activity_repository
        self._participation_repository = participation_repository
        self._authorization = authorization
        self._audit = audit

    def execute(self, command: ApplyImportCommand) -> ApplyImportResult:
        if not self._authorization.check_permission(
            organization_id=command.organization_id,
            user_id=command.user_id,
            permission_code=PERMISSION_APPLY,
            access_token=command.access_token,
        ):
            raise ForbiddenError("Permission denied")

        batch = self._batch_repository.get_by_id(command.organization_id, command.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")
        if batch.status == ImportBatchStatus.APPLIED:
            raise ImportBatchAlreadyAppliedError("Import batch already applied")

        fair_id = batch.fair_id
        rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        now = datetime.now(tz=UTC)

        created_count = 0
        updated_count = 0
        skipped_count = 0
        created_participations = 0
        updated_participations = 0
        created_contacts = 0
        invalid_count = sum(1 for row in rows if row.status == ImportRowStatus.INVALID)

        for row in rows:
            if row.status == ImportRowStatus.INVALID:
                continue
            if row.decision is None:
                continue

            if row.decision == ImportDecision.SKIP:
                row.mark_skipped(now=now)
                skipped_count += 1
                continue

            customer: Customer | None = None
            customer_created = False
            customer_updated = False

            if row.decision == ImportDecision.CREATE_NEW:
                customer = self._create_customer(row.normalized_data_json, command, now)
                row.mark_applied_create(customer.id, now=now)
                customer_created = True
                created_count += 1
            elif row.decision == ImportDecision.UPDATE_EXISTING:
                if row.match_customer_id is None:
                    continue
                customer = self._customer_repository.get_by_id(
                    command.organization_id, row.match_customer_id
                )
                if customer is None:
                    continue
                self._update_customer_from_row(customer, row.normalized_data_json, now)
                customer = self._customer_repository.update(customer)
                row.mark_applied_update(customer.id, now=now)
                customer_updated = True
                updated_count += 1

            if customer is None:
                continue

            if fair_id is not None:
                participation = self._apply_participation(
                    command, customer.id, fair_id, row.normalized_data_json, now
                )
                if participation.created:
                    row.mark_participation_created(participation.id, now=now)
                    created_participations += 1
                elif participation.updated:
                    row.mark_participation_updated(participation.id, now=now)
                    updated_participations += 1

            contact_created = self._apply_contact(customer, row.normalized_data_json, command, now)
            if contact_created:
                created_contacts += 1

            action = "created" if customer_created else "updated"
            self._create_import_activity(
                command,
                customer_id=customer.id,
                batch_id=batch.id,
                batch_file=batch.file_name,
                action=action,
                now=now,
            )

        self._row_repository.update_many(rows)

        batch.update_apply_counts(
            created_rows=created_count,
            updated_rows=updated_count,
            skipped_rows=skipped_count,
            created_participations=created_participations,
            updated_participations=updated_participations,
            now=now,
        )
        batch.mark_applied(now=now)
        updated_batch = self._batch_repository.update(batch)

        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.import.applied",
            resource_type="import_batch",
            resource_id=str(updated_batch.id),
            new_values={
                "created_rows": created_count,
                "updated_rows": updated_count,
                "skipped_rows": skipped_count,
                "created_participations": created_participations,
                "updated_participations": updated_participations,
            },
            metadata={"user_id": str(command.user_id)},
        )

        batch_result = batch_to_result(updated_batch, rows)
        return ApplyImportResult(
            batch=batch_result,
            created_rows=created_count,
            updated_rows=updated_count,
            skipped_rows=skipped_count,
            invalid_rows=invalid_count,
            created_participations=created_participations,
            updated_participations=updated_participations,
            created_contacts=created_contacts,
        )

    def _create_customer(
        self,
        data: dict[str, Any],
        command: ApplyImportCommand,
        now: datetime,
    ) -> Customer:
        customer = Customer.create(
            organization_id=command.organization_id,
            display_name=str(data.get("company_name") or "").strip(),
            website=data.get("website"),
            phone=data.get("phone") or data.get("mobile_phone"),
            email=data.get("email"),
            tax_number=data.get("tax_number"),
            country=data.get("country"),
            city=data.get("city"),
            address=data.get("address"),
            description=None,
            source=CustomerSource.EXCEL,
            now=now,
        )
        return self._customer_repository.add(customer)

    def _update_customer_from_row(
        self,
        customer: Customer,
        data: dict[str, Any],
        now: datetime,
    ) -> None:
        merged_email = _merge_email_fields(customer.email, data.get("email"))
        customer.update_fields(
            website=_fill_if_empty(customer.website, data.get("website")),
            phone=_fill_if_empty(customer.phone, data.get("phone") or data.get("mobile_phone")),
            email=merged_email,
            tax_number=_fill_if_empty(customer.tax_number, data.get("tax_number")),
            country=_fill_if_empty(customer.country, data.get("country")),
            city=_fill_if_empty(customer.city, data.get("city")),
            address=_fill_if_empty(customer.address, data.get("address")),
            description=customer.description,
            now=now,
        )

    def _apply_participation(
        self,
        command: ApplyImportCommand,
        customer_id: UUID,
        fair_id: UUID,
        data: dict[str, Any],
        now: datetime,
    ) -> _ParticipationResult:
        existing = self._participation_repository.get_active_by_customer_and_fair(
            command.organization_id, customer_id, fair_id
        )
        hall = data.get("hall")
        stand = data.get("stand")
        notes = data.get("notes")

        if existing is None:
            participation = CustomerFairParticipation.create(
                organization_id=command.organization_id,
                customer_id=customer_id,
                fair_id=fair_id,
                hall=str(hall) if hall else None,
                stand=str(stand) if stand else None,
                participation_status=ParticipationStatus.EXHIBITOR,
                notes=str(notes) if notes else None,
                now=now,
            )
            saved = self._participation_repository.add(participation)
            return _ParticipationResult(id=saved.id, created=True, updated=False)

        changed = False
        if not existing.hall and hall:
            existing.hall = str(hall).strip()
            changed = True
        if not existing.stand and stand:
            existing.stand = str(stand).strip()
            changed = True
        if not existing.notes and notes:
            existing.notes = str(notes).strip()
            changed = True
        if changed:
            existing.updated_at = now
            saved = self._participation_repository.update(existing)
            return _ParticipationResult(id=saved.id, created=False, updated=True)

        return _ParticipationResult(id=existing.id, created=False, updated=False)

    def _apply_contact(
        self,
        customer: Customer,
        data: dict[str, Any],
        command: ApplyImportCommand,
        now: datetime,
    ) -> bool:
        first_name = data.get("contact_first_name")
        last_name = data.get("contact_last_name")
        if not first_name or not last_name:
            return False

        existing = self._contact_repository.find_by_customer_and_name(
            command.organization_id,
            customer.id,
            str(first_name).strip().lower(),
            str(last_name).strip().lower(),
        )

        if existing:
            existing.update_fields(
                title=_fill_if_empty(existing.title, data.get("contact_title")),
                department=_fill_if_empty(existing.department, data.get("contact_department")),
                email=_merge_email_fields(existing.email, data.get("contact_email")),
                phone=_fill_if_empty(existing.phone, data.get("contact_phone")),
                mobile_phone=_fill_if_empty(
                    existing.mobile_phone, data.get("contact_mobile_phone")
                ),
                notes=existing.notes,
                now=now,
            )
            self._contact_repository.update(existing)
            return False

        contact = Contact.create(
            organization_id=command.organization_id,
            customer_id=customer.id,
            first_name=str(first_name),
            last_name=str(last_name),
            title=data.get("contact_title"),
            department=data.get("contact_department"),
            email=data.get("contact_email"),
            phone=data.get("contact_phone"),
            mobile_phone=data.get("contact_mobile_phone"),
            notes=None,
            now=now,
        )
        self._contact_repository.add(contact)
        return True

    def _create_import_activity(
        self,
        command: ApplyImportCommand,
        *,
        customer_id: UUID,
        batch_id: UUID,
        batch_file: str,
        action: str,
        now: datetime,
    ) -> None:
        activity = Activity.create(
            organization_id=command.organization_id,
            customer_id=customer_id,
            contact_id=None,
            activity_type=ActivityType.NOTE,
            subject="Import applied",
            description=f"Batch {batch_id}, file {batch_file}: {action}",
            activity_date=now,
            follow_up_date=None,
            status=ActivityStatus.COMPLETED,
            source=ActivitySource.IMPORT,
            is_active=True,
            now=now,
        )
        self._activity_repository.add(activity)
