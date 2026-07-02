"""Bulk link existing CRM customers to the import batch fair (participation only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.domain.services.merge_preview import row_matches_filter
from app.modules.imports.domain.value_objects import ImportDecision, ImportRowStatus
from app.modules.participations.domain.entities import CustomerFairParticipation
from app.modules.participations.domain.value_objects import ParticipationStatus


class LinkExistingRowCategory(StrEnum):
    TO_LINK = "to_link"
    ALREADY_LINKED = "already_linked"
    UNPROCESSABLE = "unprocessable"


class ParticipationLookup(Protocol):
    def get_active_by_customer_and_fair(
        self, organization_id: UUID, customer_id: UUID, fair_id: UUID
    ) -> CustomerFairParticipation | None: ...

    def add(self, participation: CustomerFairParticipation) -> CustomerFairParticipation: ...


class CustomerLookup(Protocol):
    def get_by_id(self, organization_id: UUID, customer_id: UUID): ...


@dataclass(frozen=True)
class BulkLinkExistingPreview:
    action_type: str
    to_process_rows: int
    skipped_already_linked_rows: int
    unprocessable_rows: int
    affected_rows: int
    already_decided_rows: int
    summary: str


@dataclass(frozen=True)
class BulkLinkExistingApplyResult:
    processed_rows: int
    skipped_rows: int
    error_rows: int


def row_in_link_existing_scope(row: ImportRow) -> bool:
    """Pending rows matched to an existing CRM customer (decision-screen will_update scope)."""
    if row.status == ImportRowStatus.INVALID:
        return False
    if row.match_customer_id is None:
        return False
    return row_matches_filter(row, "will_update")


def classify_link_existing_row(
    row: ImportRow,
    *,
    fair_id: UUID | None,
    participation_exists: bool,
    customer_exists: bool,
) -> LinkExistingRowCategory:
    if not row_in_link_existing_scope(row):
        return LinkExistingRowCategory.UNPROCESSABLE
    if fair_id is None:
        return LinkExistingRowCategory.UNPROCESSABLE
    if not customer_exists:
        return LinkExistingRowCategory.UNPROCESSABLE
    if participation_exists:
        return LinkExistingRowCategory.ALREADY_LINKED
    return LinkExistingRowCategory.TO_LINK


def preview_link_existing_to_fair(
    rows: list[ImportRow],
    *,
    fair_id: UUID | None,
    participation_lookup: ParticipationLookup,
    customer_lookup: CustomerLookup,
    organization_id: UUID,
) -> BulkLinkExistingPreview:
    to_link = 0
    already_linked = 0
    unprocessable = 0

    for row in rows:
        if not row_in_link_existing_scope(row):
            continue
        customer_exists = False
        participation_exists = False
        if row.match_customer_id is not None and fair_id is not None:
            customer_exists = (
                customer_lookup.get_by_id(organization_id, row.match_customer_id) is not None
            )
            participation_exists = (
                participation_lookup.get_active_by_customer_and_fair(
                    organization_id, row.match_customer_id, fair_id
                )
                is not None
            )
        category = classify_link_existing_row(
            row,
            fair_id=fair_id,
            participation_exists=participation_exists,
            customer_exists=customer_exists,
        )
        if category == LinkExistingRowCategory.TO_LINK:
            to_link += 1
        elif category == LinkExistingRowCategory.ALREADY_LINKED:
            already_linked += 1
        else:
            unprocessable += 1

    summary = (
        f"{to_link} mevcut müşteri hedef fuara bağlanacak.\n"
        f"{already_linked} kayıt zaten bağlı olduğu için atlanacak.\n"
        f"{unprocessable} kayıt işlenemeyecek."
    )
    return BulkLinkExistingPreview(
        action_type="link_all_existing",
        to_process_rows=to_link,
        skipped_already_linked_rows=already_linked,
        unprocessable_rows=unprocessable,
        affected_rows=to_link,
        already_decided_rows=already_linked,
        summary=summary,
    )


def apply_link_existing_to_fair_row(
    row: ImportRow,
    *,
    batch: ImportBatch,
    participation_lookup: ParticipationLookup,
    customer_lookup: CustomerLookup,
    now: datetime,
) -> LinkExistingRowCategory | None:
    """Apply participation link for one row. Returns category handled or None if out of scope."""
    fair_id = batch.fair_id
    if row.match_customer_id is None or fair_id is None:
        return None

    customer = customer_lookup.get_by_id(batch.organization_id, row.match_customer_id)
    existing = participation_lookup.get_active_by_customer_and_fair(
        batch.organization_id, row.match_customer_id, fair_id
    )
    category = classify_link_existing_row(
        row,
        fair_id=fair_id,
        participation_exists=existing is not None,
        customer_exists=customer is not None,
    )

    if category == LinkExistingRowCategory.UNPROCESSABLE:
        return None

    data = row.normalized_data_json or {}
    if category == LinkExistingRowCategory.TO_LINK:
        participation = CustomerFairParticipation.create(
            organization_id=batch.organization_id,
            customer_id=row.match_customer_id,
            fair_id=fair_id,
            hall=str(data["hall"]).strip() if data.get("hall") else None,
            stand=str(data["stand"]).strip() if data.get("stand") else None,
            participation_status=ParticipationStatus.EXHIBITOR,
            notes=str(data["notes"]).strip() if data.get("notes") else None,
            now=now,
        )
        participation_lookup.add(participation)
        return category

    if existing is None:
        return None
    return category


def apply_link_existing_to_fair_batch(
    rows: list[ImportRow],
    *,
    batch: ImportBatch,
    participation_lookup: ParticipationLookup,
    customer_lookup: CustomerLookup,
    now: datetime | None = None,
) -> BulkLinkExistingApplyResult:
    ts = now or datetime.now(tz=UTC)
    processed = 0
    skipped = 0
    errors = 0

    for row in rows:
        try:
            result = apply_link_existing_to_fair_row(
                row,
                batch=batch,
                participation_lookup=participation_lookup,
                customer_lookup=customer_lookup,
                now=ts,
            )
            if result == LinkExistingRowCategory.TO_LINK:
                processed += 1
            elif result == LinkExistingRowCategory.ALREADY_LINKED:
                skipped += 1
            elif result is None and row_in_link_existing_scope(row):
                errors += 1
        except Exception:
            errors += 1

    return BulkLinkExistingApplyResult(
        processed_rows=processed,
        skipped_rows=skipped,
        error_rows=errors,
    )
