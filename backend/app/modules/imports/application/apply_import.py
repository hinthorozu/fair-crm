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
from app.shared.email import normalize_email_field

PERMISSION_APPLY = "fair_crm.imports.apply"


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
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._customer_repository = customer_repository
        self._contact_repository = contact_repository
        self._activity_repository = activity_repository
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

        rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        now = datetime.now(tz=UTC)

        created_count = 0
        updated_count = 0
        skipped_count = 0
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

            if row.decision == ImportDecision.CREATE_NEW:
                customer = self._create_customer(row.normalized_data_json, command, now)
                row.mark_applied_create(customer.id, now=now)
                self._maybe_create_contact(customer, row.normalized_data_json, command, now)
                self._create_import_activity(
                    command,
                    customer_id=customer.id,
                    subject="Customer imported",
                    batch_file=batch.file_name,
                    now=now,
                )
                created_count += 1
                continue

            if row.decision == ImportDecision.UPDATE_EXISTING:
                if row.match_customer_id is None:
                    continue
                customer = self._customer_repository.get_by_id(
                    command.organization_id, row.match_customer_id
                )
                if customer is None:
                    continue
                self._update_customer_from_row(customer, row.normalized_data_json, now)
                saved = self._customer_repository.update(customer)
                self._maybe_merge_contact(saved, row.normalized_data_json, command, now)
                self._create_import_activity(
                    command,
                    customer_id=saved.id,
                    subject="Import update",
                    batch_file=batch.file_name,
                    now=now,
                )
                row.mark_applied_update(saved.id, now=now)
                updated_count += 1

        self._row_repository.update_many(rows)

        batch.update_apply_counts(
            created_rows=created_count,
            updated_rows=updated_count,
            skipped_rows=skipped_count,
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
            description=self._build_description(data),
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
            description=_fill_if_empty(customer.description, self._build_description(data)),
            now=now,
        )

    def _maybe_create_contact(
        self,
        customer: Customer,
        data: dict[str, Any],
        command: ApplyImportCommand,
        now: datetime,
    ) -> None:
        first_name = data.get("contact_first_name")
        last_name = data.get("contact_last_name")
        if not first_name or not last_name:
            return

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
            notes=data.get("notes"),
            now=now,
        )
        self._contact_repository.add(contact)

    def _maybe_merge_contact(
        self,
        customer: Customer,
        data: dict[str, Any],
        command: ApplyImportCommand,
        now: datetime,
    ) -> None:
        first_name = data.get("contact_first_name")
        last_name = data.get("contact_last_name")
        if not first_name or not last_name:
            return

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
                mobile_phone=_fill_if_empty(existing.mobile_phone, data.get("contact_mobile_phone")),
                notes=_fill_if_empty(existing.notes, data.get("notes")),
                now=now,
            )
            self._contact_repository.update(existing)
            return

        self._maybe_create_contact(customer, data, command, now)

    def _create_import_activity(
        self,
        command: ApplyImportCommand,
        *,
        customer_id: UUID,
        subject: str,
        batch_file: str,
        now: datetime,
    ) -> None:
        activity = Activity.create(
            organization_id=command.organization_id,
            customer_id=customer_id,
            contact_id=None,
            activity_type=ActivityType.NOTE,
            subject=subject,
            description=f"Import batch: {batch_file}",
            activity_date=now,
            follow_up_date=None,
            status=ActivityStatus.COMPLETED,
            source=ActivitySource.IMPORT,
            is_active=True,
            now=now,
        )
        self._activity_repository.add(activity)

    def _build_description(self, data: dict[str, Any]) -> str | None:
        parts: list[str] = []
        if data.get("notes"):
            parts.append(str(data["notes"]))
        fair_parts = []
        if data.get("fair_name"):
            fair_parts.append(str(data["fair_name"]))
        if data.get("hall"):
            fair_parts.append(f"Salon: {data['hall']}")
        if data.get("stand"):
            fair_parts.append(f"Stand: {data['stand']}")
        if fair_parts:
            parts.append(" | ".join(fair_parts))
        return "\n".join(parts) if parts else None
