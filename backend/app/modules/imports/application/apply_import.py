from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.ports import ActivityRepository
from app.modules.activities.domain.value_objects import ActivitySource, ActivityStatus, ActivityType
from app.modules.contacts.domain.entities import Contact
from app.modules.contacts.domain.ports import ContactRepository
from app.modules.customers.application.communication_parsing import (
    emails_from_scalar,
    phones_from_scalar,
    websites_from_scalar,
)
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.customers.domain.value_objects import CustomerSource
from app.modules.imports.application.commands import ApplyImportCommand, ApplyImportResult
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.domain.exceptions import ImportBatchAlreadyAppliedError, ImportBatchNotFoundError
from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.batch_status import is_batch_terminal
from app.modules.imports.domain.services.merge_preview import default_decision_for_row
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.value_objects import ParticipationStatus
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)
from app.modules.scraper.services.customer_enrichment_state_service import (
    is_enrichment_import_batch,
    record_enrichment_apply_outcome,
)
from app.modules.imports.domain.services.social_url_fields import social_urls_from_mapping
from app.shared.email import normalize_email_field
from app.shared.url_normalization import normalize_optional_url

PERMISSION_APPLY = "fair_crm.imports.apply"


@dataclass
class RowApplyCounters:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    created_participations: int = 0
    updated_participations: int = 0
    created_contacts: int = 0
    applied: bool = False
    created_customer_id: UUID | None = None
    updated_customer_id: UUID | None = None
    created_participation_id: UUID | None = None
    updated_participation_id: UUID | None = None


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


def _import_social_url(data: dict[str, Any], url_key: str) -> str | None:
    urls = social_urls_from_mapping(data)
    return normalize_optional_url(urls.get(url_key))


class ApplyImportUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        customer_repository: CustomerRepository,
        communication_sync: CustomerCommunicationSyncService,
        contact_repository: ContactRepository,
        activity_repository: ActivityRepository,
        participation_repository: SqlAlchemyParticipationRepository,
        authorization: AuthorizationPort,
        audit: HttpAuditAdapter,
        db: Session,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._customer_repository = customer_repository
        self._communication_sync = communication_sync
        self._contact_repository = contact_repository
        self._activity_repository = activity_repository
        self._participation_repository = participation_repository
        self._authorization = authorization
        self._audit = audit
        self._db = db

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
        if is_batch_terminal(batch.status):
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
            counters = self.finalize_applied_row(batch, row, command, now)
            created_count += counters.created
            updated_count += counters.updated
            skipped_count += counters.skipped
            created_participations += counters.created_participations
            updated_participations += counters.updated_participations
            created_contacts += counters.created_contacts

        remaining_rows = self._row_repository.list_by_batch(command.organization_id, command.batch_id)
        batch = self.sync_batch_progress(batch, remaining_rows, now=now)
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

        batch_result = batch_to_result(updated_batch, remaining_rows)
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

    def finalize_applied_row(
        self,
        batch: ImportBatch,
        row: ImportRow,
        command: ApplyImportCommand,
        now: datetime,
    ) -> RowApplyCounters:
        counters = self.apply_single_row(batch, row, command, now)
        if not counters.applied:
            return counters

        self._row_repository.delete_many(
            command.organization_id,
            command.batch_id,
            [row.id],
        )
        batch.increment_apply_counts(
            created_rows=counters.created,
            updated_rows=counters.updated,
            skipped_rows=counters.skipped,
            created_participations=counters.created_participations,
            updated_participations=counters.updated_participations,
            now=now,
        )
        return counters

    def apply_single_row(
        self,
        batch: ImportBatch,
        row: ImportRow,
        command: ApplyImportCommand,
        now: datetime,
    ) -> RowApplyCounters:
        counters = RowApplyCounters()
        decision = row.decision or default_decision_for_row(row)
        if decision is None:
            return counters

        if decision == ImportDecision.SKIP:
            counters.skipped = 1
            counters.applied = True
            return counters

        if row.status == ImportRowStatus.INVALID:
            return counters

        fair_id = batch.fair_id
        enrichment_batch = is_enrichment_import_batch(batch)
        had_email_before = False
        contact_before: dict[str, Any] | None = None
        if enrichment_batch and row.match_customer_id is not None:
            matched = self._customer_repository.get_by_id(
                command.organization_id, row.match_customer_id
            )
            if matched is not None:
                contact_before = self._enrichment_contact_snapshot(matched)
                had_email_before = bool(contact_before["emails"])

        if decision == ImportDecision.MANUAL_REVIEW:
            return counters

        customer: Customer | None = None
        customer_created = False

        if decision == ImportDecision.CREATE_NEW:
            customer = self._create_customer(row.normalized_data_json, command, now)
            counters.created_customer_id = customer.id
            customer_created = True
            counters.created = 1
        elif decision == ImportDecision.UPDATE_EXISTING:
            if row.match_customer_id is None:
                return counters
            customer = self._customer_repository.get_by_id(
                command.organization_id, row.match_customer_id
            )
            if customer is None:
                return counters
            self._update_customer_from_row(customer, row.normalized_data_json, command, now)
            customer = self._customer_repository.update(customer)
            counters.updated_customer_id = customer.id
            counters.updated = 1
        elif decision == ImportDecision.PARTICIPATION_ONLY:
            if row.match_customer_id is None:
                return counters
            customer = self._customer_repository.get_by_id(
                command.organization_id, row.match_customer_id
            )
            if customer is None:
                return counters
            counters.updated_customer_id = customer.id
            counters.updated = 1

        if customer is None:
            return counters

        if fair_id is not None:
            participation = self._apply_participation(
                command, customer.id, fair_id, row.normalized_data_json, now
            )
            if participation.created:
                counters.created_participation_id = participation.id
                counters.created_participations = 1
            elif participation.updated:
                counters.updated_participation_id = participation.id
                counters.updated_participations = 1

        if decision not in (
            ImportDecision.PARTICIPATION_ONLY,
            ImportDecision.MANUAL_REVIEW,
        ):
            contact_created = self._apply_contact(customer, row.normalized_data_json, command, now)
            if contact_created:
                counters.created_contacts = 1

            action = "created" if customer_created else "updated"
            self._create_import_activity(
                command,
                customer_id=customer.id,
                batch_id=batch.id,
                batch_file=batch.file_name,
                action=action,
                now=now,
            )
        elif decision == ImportDecision.PARTICIPATION_ONLY and fair_id is not None:
            self._create_import_activity(
                command,
                customer_id=customer.id,
                batch_id=batch.id,
                batch_file=batch.file_name,
                action="participation_only",
                now=now,
            )

        counters.applied = True

        if enrichment_batch and customer is not None:
            contact_after = self._enrichment_contact_snapshot(customer)
            before = contact_before or {
                "emails": set(),
                "phones": set(),
                "address": None,
                "instagram_url": None,
                "facebook_url": None,
                "linkedin_url": None,
                "youtube_url": None,
            }
            email_written = bool(contact_after["emails"] - before["emails"])
            phone_written = bool(contact_after["phones"] - before["phones"])
            profile_written = any(
                not before[key] and contact_after[key]
                for key in ("address", "instagram_url", "facebook_url", "linkedin_url", "youtube_url")
            )
            crm_data_written = email_written or phone_written or profile_written
            record_enrichment_apply_outcome(
                self._db,
                organization_id=command.organization_id,
                customer_id=customer.id,
                had_email_before=had_email_before,
                email_written=email_written,
                crm_data_written=crm_data_written,
            )

        return counters

    def sync_batch_progress(
        self,
        batch: ImportBatch,
        rows: list[ImportRow],
        *,
        now: datetime,
    ) -> ImportBatch:
        if not rows:
            batch.mark_completed(now=now)
        return batch

    def _create_customer(
        self,
        data: dict[str, Any],
        command: ApplyImportCommand,
        now: datetime,
    ) -> Customer:
        customer = Customer.create(
            organization_id=command.organization_id,
            display_name=str(data.get("company_name") or "").strip(),
            tax_number=data.get("tax_number"),
            country=data.get("country"),
            city=data.get("city"),
            address=data.get("address"),
            description=None,
            instagram_url=_import_social_url(data, "instagram_url"),
            facebook_url=_import_social_url(data, "facebook_url"),
            linkedin_url=_import_social_url(data, "linkedin_url"),
            youtube_url=_import_social_url(data, "youtube_url"),
            source=CustomerSource.EXCEL,
            now=now,
        )
        saved = self._customer_repository.add(customer)
        self._sync_import_communications(
            saved.id,
            command.organization_id,
            data,
            now,
            merge=False,
        )
        return saved

    def _update_customer_from_row(
        self,
        customer: Customer,
        data: dict[str, Any],
        command: ApplyImportCommand,
        now: datetime,
    ) -> None:
        customer.update_fields(
            tax_number=_fill_if_empty(customer.tax_number, data.get("tax_number")),
            country=_fill_if_empty(customer.country, data.get("country")),
            city=_fill_if_empty(customer.city, data.get("city")),
            address=_fill_if_empty(customer.address, data.get("address")),
            description=customer.description,
            instagram_url=_fill_if_empty(customer.instagram_url, _import_social_url(data, "instagram_url")),
            facebook_url=_fill_if_empty(customer.facebook_url, _import_social_url(data, "facebook_url")),
            linkedin_url=_fill_if_empty(customer.linkedin_url, _import_social_url(data, "linkedin_url")),
            youtube_url=_fill_if_empty(customer.youtube_url, _import_social_url(data, "youtube_url")),
            now=now,
        )
        self._sync_import_communications(
            customer.id,
            command.organization_id,
            data,
            now,
            merge=True,
        )

    def _sync_import_communications(
        self,
        customer_id: UUID,
        organization_id: UUID,
        data: dict[str, Any],
        now: datetime,
        *,
        merge: bool,
    ) -> None:
        phones: list[str] = []
        emails: list[str] = []
        websites: list[str] = []

        if merge:
            existing = self._communication_sync.load_for_customer(customer_id)
            phones = [item.phone for item in existing.phones]
            emails = [item.email for item in existing.emails]
            websites = [item.website for item in existing.websites]

        incoming_phone = data.get("phone") or data.get("mobile_phone")
        if incoming_phone and not phones:
            phones = phones_from_scalar(str(incoming_phone))

        incoming_email = data.get("email")
        if incoming_email:
            if not emails:
                emails = emails_from_scalar(str(incoming_email))
            else:
                merged_scalar = _merge_email_fields(";".join(emails), str(incoming_email))
                emails = emails_from_scalar(merged_scalar) if merged_scalar else emails

        incoming_website = data.get("website")
        if incoming_website and not websites:
            websites = websites_from_scalar(str(incoming_website))

        self._communication_sync.sync_from_value_lists(
            organization_id=organization_id,
            customer_id=customer_id,
            now=now,
            phones=phones,
            emails=emails,
            websites=websites,
            sync_phone=True,
            sync_email=True,
            sync_website=True,
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
        from app.modules.imports.domain.services.contact_import import (
            find_existing_contact_for_import,
            has_contact_import_fields,
            resolve_contact_identity,
        )

        if not has_contact_import_fields(data):
            return False

        first_name, last_name = resolve_contact_identity(data)
        existing = find_existing_contact_for_import(
            self._contact_repository,
            organization_id=command.organization_id,
            customer_id=customer.id,
            data=data,
        )

        if existing:
            filled_first = _fill_if_empty(existing.first_name, first_name)
            filled_last = _fill_if_empty(existing.last_name, last_name)
            existing.update_fields(
                first_name=filled_first if filled_first != existing.first_name else None,
                last_name=filled_last if filled_last != existing.last_name else None,
                title=_fill_if_empty(existing.title, data.get("contact_title")),
                department=_fill_if_empty(existing.department, data.get("contact_department")),
                email=_merge_email_fields(existing.email, data.get("contact_email")),
                phone=_fill_if_empty(existing.phone, data.get("contact_phone")),
                mobile_phone=_fill_if_empty(
                    existing.mobile_phone, data.get("contact_mobile_phone")
                ),
                linkedin=_fill_if_empty(existing.linkedin, data.get("contact_linkedin")),
                notes=_fill_if_empty(existing.notes, data.get("contact_notes")),
                now=now,
            )
            self._contact_repository.update(existing)
            return False

        contact = Contact.create(
            organization_id=command.organization_id,
            customer_id=customer.id,
            first_name=first_name,
            last_name=last_name,
            title=data.get("contact_title"),
            department=data.get("contact_department"),
            email=data.get("contact_email"),
            phone=data.get("contact_phone"),
            mobile_phone=data.get("contact_mobile_phone"),
            linkedin=data.get("contact_linkedin"),
            notes=data.get("contact_notes"),
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

    def _customer_email_set(self, customer_id: UUID) -> set[str]:
        communications = self._communication_sync.load_for_customer(customer_id)
        return {(item.email or "").strip().lower() for item in communications.emails if item.email}

    def _customer_phone_set(self, customer_id: UUID) -> set[str]:
        communications = self._communication_sync.load_for_customer(customer_id)
        return {(item.phone or "").strip() for item in communications.phones if item.phone}

    def _enrichment_contact_snapshot(self, customer: Customer) -> dict[str, Any]:
        return {
            "emails": self._customer_email_set(customer.id),
            "phones": self._customer_phone_set(customer.id),
            "address": (customer.address or "").strip() or None,
            "instagram_url": (customer.instagram_url or "").strip() or None,
            "facebook_url": (customer.facebook_url or "").strip() or None,
            "linkedin_url": (customer.linkedin_url or "").strip() or None,
            "youtube_url": (customer.youtube_url or "").strip() or None,
        }

    def _customer_has_email(self, customer_id: UUID) -> bool:
        return bool(self._customer_email_set(customer_id))
