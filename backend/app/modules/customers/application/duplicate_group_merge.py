"""Read-only duplicate group merge preview and shared merge calculation for future execute."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.customers.domain.communication_entities import (
    CustomerCommunications,
)
from app.modules.customers.domain.entities import Customer
from app.modules.customers.domain.services.normalizers import (
    compute_normalized_name,
    normalize_email,
    normalize_phone,
    normalize_website,
)
from app.modules.system_admin.infrastructure.repositories.data_operation_dataset_repository import (
    DuplicateGroupParticipationDetail,
)

ScalarFieldKey = Literal["company_name", "legal_name", "trade_name", "city", "country"]
CommChannel = Literal["email", "phone", "website"]

SCALAR_FIELD_KEYS: tuple[ScalarFieldKey, ...] = (
    "company_name",
    "legal_name",
    "trade_name",
    "city",
    "country",
)

COMM_CHANNEL_KEYS: tuple[CommChannel, ...] = ("email", "phone", "website")


@dataclass(frozen=True)
class DuplicateGroupMergeSelection:
    surviving_customer_id: UUID
    scalar_selections: dict[ScalarFieldKey, UUID]
    selected_email_ids: tuple[UUID, ...]
    selected_phone_ids: tuple[UUID, ...]
    selected_website_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class DuplicateGroupMemberContext:
    customer: Customer
    participations: list[DuplicateGroupParticipationDetail]


@dataclass(frozen=True)
class CommunicationSourceRow:
    id: UUID
    customer_id: UUID
    customer_name: str
    channel: CommChannel
    value: str
    is_primary: bool
    created_at: datetime


@dataclass(frozen=True)
class MergePreviewScalarFields:
    company_name: str
    legal_name: str | None
    trade_name: str | None
    city: str | None
    country: str | None


@dataclass(frozen=True)
class MergePreviewCommunicationItem:
    value: str
    is_primary: bool
    source_customer_id: UUID
    source_customer_name: str
    source_row_id: UUID


@dataclass(frozen=True)
class MergePreviewParticipationSummary:
    total_participation_rows: int
    unique_fairs: int
    fair_names: list[str]


@dataclass(frozen=True)
class MergePreviewStatistics:
    customers_before: int
    customers_after: int
    emails_before: int
    emails_after: int
    phones_before: int
    phones_after: int
    websites_before: int
    websites_after: int


@dataclass(frozen=True)
class MergePreviewIssue:
    code: str
    message: str
    severity: Literal["error", "warning"]


def is_invalid_merge_selection_issue_code(code: str) -> bool:
    if code == "surviving_customer":
        return True
    if code.startswith(("missing_scalar_", "foreign_scalar_")):
        return True
    if code.startswith("missing_") and code.endswith("_id"):
        return True
    if code.startswith(("foreign_", "invalid_")) and code.endswith("_id"):
        return True
    return False


def invalid_merge_selection_issues(
    validation_errors: list[MergePreviewIssue],
) -> list[MergePreviewIssue]:
    return [
        issue
        for issue in validation_errors
        if issue.severity == "error" and is_invalid_merge_selection_issue_code(issue.code)
    ]


def raise_for_invalid_merge_selection(validation_errors: list[MergePreviewIssue]) -> None:
    invalid_issues = invalid_merge_selection_issues(validation_errors)
    if invalid_issues:
        raise ValueError(invalid_issues[0].message)


@dataclass(frozen=True)
class DuplicateGroupMergePreviewResult:
    group_key: str
    group_by: str
    surviving_customer_id: UUID
    merged_customer: Customer
    scalar_fields: MergePreviewScalarFields
    emails: list[MergePreviewCommunicationItem]
    phones: list[MergePreviewCommunicationItem]
    websites: list[MergePreviewCommunicationItem]
    participation_summary: MergePreviewParticipationSummary
    customers_to_archive: list[UUID]
    validation_errors: list[MergePreviewIssue]
    warnings: list[MergePreviewIssue]
    statistics: MergePreviewStatistics
    is_valid: bool


def _scalar_value(customer: Customer, field: ScalarFieldKey) -> str | None:
    if field == "company_name":
        return customer.display_name.strip() or None
    if field == "legal_name":
        return customer.legal_name.strip() if customer.legal_name else None
    if field == "trade_name":
        return customer.trade_name.strip() if customer.trade_name else None
    if field == "city":
        return customer.city.strip() if customer.city else None
    if field == "country":
        return customer.country.strip() if customer.country else None
    return None


def _group_has_scalar_value(members: list[DuplicateGroupMemberContext], field: ScalarFieldKey) -> bool:
    return any(_scalar_value(member.customer, field) for member in members)


def _normalize_comm_value(channel: CommChannel, value: str) -> str:
    if channel == "email":
        return normalize_email(value)
    if channel == "phone":
        return normalize_phone(value)
    return normalize_website(value)


def build_communication_index(
    members: list[DuplicateGroupMemberContext],
    communications_by_customer: dict[UUID, CustomerCommunications],
) -> dict[UUID, CommunicationSourceRow]:
    index: dict[UUID, CommunicationSourceRow] = {}
    for member in members:
        communications = communications_by_customer.get(member.customer.id)
        if communications is None:
            continue
        for email in communications.emails:
            index[email.id] = CommunicationSourceRow(
                id=email.id,
                customer_id=member.customer.id,
                customer_name=member.customer.display_name,
                channel="email",
                value=email.email,
                is_primary=email.is_primary,
                created_at=email.created_at,
            )
        for phone in communications.phones:
            index[phone.id] = CommunicationSourceRow(
                id=phone.id,
                customer_id=member.customer.id,
                customer_name=member.customer.display_name,
                channel="phone",
                value=phone.phone,
                is_primary=phone.is_primary,
                created_at=phone.created_at,
            )
        for website in communications.websites:
            index[website.id] = CommunicationSourceRow(
                id=website.id,
                customer_id=member.customer.id,
                customer_name=member.customer.display_name,
                channel="website",
                value=website.website,
                is_primary=website.is_primary,
                created_at=website.created_at,
            )
    return index


def _group_has_channel_from_index(
    members: list[DuplicateGroupMemberContext],
    communications_by_customer: dict[UUID, CustomerCommunications],
    channel: CommChannel,
) -> bool:
    for member in members:
        communications = communications_by_customer.get(member.customer.id)
        if communications is None:
            continue
        if channel == "email" and communications.emails:
            return True
        if channel == "phone" and communications.phones:
            return True
        if channel == "website" and communications.websites:
            return True
    return False


def _resolve_selected_rows(
    selected_ids: tuple[UUID, ...],
    index: dict[UUID, CommunicationSourceRow],
    *,
    channel: CommChannel,
    members: list[DuplicateGroupMemberContext],
) -> tuple[list[CommunicationSourceRow], list[MergePreviewIssue]]:
    issues: list[MergePreviewIssue] = []
    member_ids = {member.customer.id for member in members}
    rows: list[CommunicationSourceRow] = []

    for row_id in selected_ids:
        row = index.get(row_id)
        if row is None:
            issues.append(
                MergePreviewIssue(
                    code=f"missing_{channel}_id",
                    message=f"Selected {channel} id {row_id} was not found in this duplicate group.",
                    severity="error",
                )
            )
            continue
        if row.channel != channel:
            issues.append(
                MergePreviewIssue(
                    code=f"invalid_{channel}_id",
                    message=f"Selected id {row_id} is not a {channel} row.",
                    severity="error",
                )
            )
            continue
        if row.customer_id not in member_ids:
            issues.append(
                MergePreviewIssue(
                    code=f"foreign_{channel}_id",
                    message=f"Selected {channel} id {row_id} does not belong to this duplicate group.",
                    severity="error",
                )
            )
            continue
        rows.append(row)

    return rows, issues


def _dedupe_communications(rows: list[CommunicationSourceRow]) -> list[MergePreviewCommunicationItem]:
    seen: set[str] = set()
    deduped: list[MergePreviewCommunicationItem] = []
    for row in rows:
        normalized = _normalize_comm_value(row.channel, row.value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(
            MergePreviewCommunicationItem(
                value=row.value,
                is_primary=False,
                source_customer_id=row.customer_id,
                source_customer_name=row.customer_name,
                source_row_id=row.id,
            )
        )

    if not deduped:
        return deduped

    primary_source_ids = {row.id for row in rows if row.is_primary}
    primary_index = next(
        (index for index, item in enumerate(deduped) if item.source_row_id in primary_source_ids),
        0,
    )
    return [
        replace(item, is_primary=index == primary_index) for index, item in enumerate(deduped)
    ]


def _participation_summary(members: list[DuplicateGroupMemberContext]) -> MergePreviewParticipationSummary:
    fair_names: dict[str, None] = {}
    total_rows = 0
    for member in members:
        total_rows += len(member.participations)
        for participation in member.participations:
            fair_names[participation.fair_name] = None
    names = sorted(fair_names.keys())
    return MergePreviewParticipationSummary(
        total_participation_rows=total_rows,
        unique_fairs=len(names),
        fair_names=names,
    )


def _scalar_field_label(field: ScalarFieldKey) -> str:
    return {
        "company_name": "Company name",
        "legal_name": "Legal name",
        "trade_name": "Trade name",
        "city": "City",
        "country": "Country",
    }[field]


def build_duplicate_group_merge_preview(
    *,
    group_key: str,
    group_by: str,
    members: list[DuplicateGroupMemberContext],
    communications_by_customer: dict[UUID, CustomerCommunications],
    selection: DuplicateGroupMergeSelection,
) -> DuplicateGroupMergePreviewResult:
    if not members:
        raise ValueError("Duplicate group has no customers.")

    member_by_id = {member.customer.id: member for member in members}
    member_ids = set(member_by_id.keys())
    validation_errors: list[MergePreviewIssue] = []
    warnings: list[MergePreviewIssue] = []

    surviving_member = member_by_id.get(selection.surviving_customer_id)
    if surviving_member is None:
        validation_errors.append(
            MergePreviewIssue(
                code="surviving_customer",
                message="Surviving customer must be a member of this duplicate group.",
                severity="error",
            )
        )

    for field in SCALAR_FIELD_KEYS:
        source_id = selection.scalar_selections.get(field)
        if source_id is None:
            validation_errors.append(
                MergePreviewIssue(
                    code=f"missing_scalar_{field}",
                    message=f"Missing scalar selection for {_scalar_field_label(field).lower()}.",
                    severity="error",
                )
            )
            continue
        if source_id not in member_ids:
            validation_errors.append(
                MergePreviewIssue(
                    code=f"foreign_scalar_{field}",
                    message=f"Scalar selection for {_scalar_field_label(field).lower()} must reference a group member.",
                    severity="error",
                )
            )

    comm_index = build_communication_index(members, communications_by_customer)
    email_rows, email_issues = _resolve_selected_rows(
        selection.selected_email_ids,
        comm_index,
        channel="email",
        members=members,
    )
    phone_rows, phone_issues = _resolve_selected_rows(
        selection.selected_phone_ids,
        comm_index,
        channel="phone",
        members=members,
    )
    website_rows, website_issues = _resolve_selected_rows(
        selection.selected_website_ids,
        comm_index,
        channel="website",
        members=members,
    )
    validation_errors.extend(email_issues)
    validation_errors.extend(phone_issues)
    validation_errors.extend(website_issues)

    scalar_sources: dict[ScalarFieldKey, UUID] = {}
    resolved_scalars: dict[ScalarFieldKey, str | None] = {}
    for field in SCALAR_FIELD_KEYS:
        source_id = selection.scalar_selections.get(field)
        if source_id is None or source_id not in member_by_id:
            resolved_scalars[field] = None
            continue
        scalar_sources[field] = source_id
        resolved_scalars[field] = _scalar_value(member_by_id[source_id].customer, field)

    if not resolved_scalars.get("company_name"):
        validation_errors.append(
            MergePreviewIssue(
                code="company_name_required",
                message="Company name is required.",
                severity="error",
            )
        )

    for field in SCALAR_FIELD_KEYS:
        if field == "company_name":
            continue
        if not _group_has_scalar_value(members, field):
            continue
        if not resolved_scalars.get(field):
            validation_errors.append(
                MergePreviewIssue(
                    code=f"scalar_{field}_required",
                    message=(
                        f"{_scalar_field_label(field)} is required because at least one "
                        "customer in the group has a value."
                    ),
                    severity="error",
                )
            )

    for channel, selected_rows in (
        ("email", email_rows),
        ("phone", phone_rows),
        ("website", website_rows),
    ):
        if not _group_has_channel_from_index(members, communications_by_customer, channel):
            continue
        if not selected_rows:
            validation_errors.append(
                MergePreviewIssue(
                    code=f"{channel}_required",
                    message=f"Select at least one {channel}.",
                    severity="error",
                )
            )

    distinct_scalar_sources = set(scalar_sources.values())
    if len(distinct_scalar_sources) > 1:
        warnings.append(
            MergePreviewIssue(
                code="mixed_scalar_selection",
                message=(
                    "Mixed field selection — identity fields will be combined from "
                    f"{len(distinct_scalar_sources)} different customers."
                ),
                severity="warning",
            )
        )

    emails = _dedupe_communications(email_rows)
    phones = _dedupe_communications(phone_rows)
    websites = _dedupe_communications(website_rows)

    participation_summary = _participation_summary(members)

    surviving_customer = surviving_member.customer if surviving_member else members[0].customer
    merged_customer = replace(
        surviving_customer,
        display_name=resolved_scalars.get("company_name") or surviving_customer.display_name,
        legal_name=resolved_scalars.get("legal_name"),
        trade_name=resolved_scalars.get("trade_name"),
        city=resolved_scalars.get("city"),
        country=resolved_scalars.get("country"),
        normalized_name=compute_normalized_name(
            display_name=resolved_scalars.get("company_name") or surviving_customer.display_name,
            legal_name=resolved_scalars.get("legal_name"),
        ),
    )

    customers_to_archive = sorted(
        [member_id for member_id in member_ids if member_id != selection.surviving_customer_id],
        key=str,
    )

    statistics = MergePreviewStatistics(
        customers_before=len(members),
        customers_after=1,
        emails_before=len(email_rows),
        emails_after=len(emails),
        phones_before=len(phone_rows),
        phones_after=len(phones),
        websites_before=len(website_rows),
        websites_after=len(websites),
    )

    scalar_fields = MergePreviewScalarFields(
        company_name=merged_customer.display_name,
        legal_name=merged_customer.legal_name,
        trade_name=merged_customer.trade_name,
        city=merged_customer.city,
        country=merged_customer.country,
    )

    return DuplicateGroupMergePreviewResult(
        group_key=group_key,
        group_by=group_by,
        surviving_customer_id=selection.surviving_customer_id,
        merged_customer=merged_customer,
        scalar_fields=scalar_fields,
        emails=emails,
        phones=phones,
        websites=websites,
        participation_summary=participation_summary,
        customers_to_archive=customers_to_archive,
        validation_errors=validation_errors,
        warnings=warnings,
        statistics=statistics,
        is_valid=len(validation_errors) == 0,
    )
