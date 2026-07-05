from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

from openpyxl import Workbook

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.customers.application.list_customers import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
    customer_name_sort_api_field,
    resolve_customer_list_sort,
)
from app.modules.customers.application.communication_parsing import api_scalar_fields_from_communications
from app.modules.customers.domain.value_objects import CustomerStatus, CustomerType
from app.modules.customers.application.duplicate_group_merge_execute import (
    DuplicateGroupMergeExecuteError,
    DuplicateGroupMergeExecuteResult,
    execute_duplicate_group_merge,
)
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from sqlalchemy.orm import Session
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.participations.application.validators import ensure_fair_for_participation
from app.modules.system_admin.application.data_operation_assign_fair import (
    ANALYZE_CUSTOMERS_WITHOUT_FAIR_OPERATION_KEY,
    ASSIGN_CUSTOMERS_TO_FAIR_OPERATION_KEY,
)
from app.modules.system_admin.application.data_operation_delete_customers import (
    DELETE_SELECTED_CUSTOMERS_OPERATION_KEY,
)
from app.modules.customers.application.customer_field_grouping import GROUP_BY_FIELDS
from app.modules.system_admin.application.data_operation_registry import (
    DATA_OPERATIONS,
    get_operation_definition,
)

DUPLICATE_CUSTOMER_ANALYSIS_OPERATION_KEY = "duplicate_customer_analysis"
from app.modules.system_admin.domain.data_operation_entities import DataOperationRun
from app.modules.system_admin.infrastructure.repositories.data_operation_dataset_repository import (
    SqlAlchemyDataOperationDatasetRepository,
)
from app.modules.system_admin.infrastructure.repositories.data_operation_run_repository import (
    SqlAlchemyDataOperationRunRepository,
)

PERMISSION_READ = "fair_crm.admin.data_operations.read"
PERMISSION_RUN = "fair_crm.admin.data_operations.run"

DATASET_CUSTOMER_ALLOWED_SORT_FIELDS = frozenset(
    ALLOWED_SORT_FIELDS | {"legal_name", "trade_name", "website", "company_name"}
)

DATASET_DUPLICATE_CUSTOMER_ALLOWED_SORT_FIELDS = frozenset(
    DATASET_CUSTOMER_ALLOWED_SORT_FIELDS
    | {
        "group_key",
        "duplicate_group_key",
        "duplicate_group",
        "group_by",
        "fair_count",
        "first_fair_name",
        "first_fair",
    }
)

DUPLICATE_DATASET_ONLY_SORT_FIELDS = frozenset(
    {
        "group_key",
        "duplicate_group_key",
        "duplicate_group",
        "group_by",
        "fair_count",
        "first_fair_name",
        "first_fair",
    }
)


def resolve_duplicate_dataset_sort(sort_by: str) -> str:
    if sort_by in DUPLICATE_DATASET_ONLY_SORT_FIELDS:
        if sort_by in ("duplicate_group", "group_key"):
            return "duplicate_group_key"
        if sort_by == "first_fair":
            return "first_fair_name"
        return sort_by
    return resolve_customer_list_sort(sort_by)


def duplicate_dataset_sort_api_field(resolved_sort: str) -> str:
    if resolved_sort == "duplicate_group_key":
        return "group_key"
    if resolved_sort == "first_fair_name":
        return "first_fair"
    if resolved_sort in DUPLICATE_DATASET_ONLY_SORT_FIELDS:
        return resolved_sort
    return customer_name_sort_api_field(resolved_sort)


class ListDataOperationsUseCase:
    def __init__(self, repository: SqlAlchemyDataOperationRunRepository, authorization: AuthorizationPort) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> list[dict]:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        latest_runs = self._repository.latest_run_by_operation_key(organization_id)
        active_runs = self._repository.active_runs_by_operation_key(organization_id)
        return [
            {
                "definition": operation,
                "last_run": latest_runs.get(operation.key),
                "active_run": active_runs.get(operation.key),
            }
            for operation in DATA_OPERATIONS
        ]


class RunDataOperationUseCase:
    def __init__(self, repository: SqlAlchemyDataOperationRunRepository, authorization: AuthorizationPort) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        user_email: str | None,
        access_token: str,
        operation_key: str,
        group_by: str | None = None,
    ) -> DataOperationRun:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_RUN,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        definition = get_operation_definition(operation_key)
        if definition is None:
            raise LookupError("Unknown data operation")

        active = self._repository.get_active_for_operation(organization_id, operation_key)
        if active is not None:
            raise ValueError("Operation is already running")

        if operation_key == DUPLICATE_CUSTOMER_ANALYSIS_OPERATION_KEY:
            if not group_by or group_by not in GROUP_BY_FIELDS:
                raise ValueError(
                    "group_by is required for duplicate customer analysis "
                    "(company_name, email, website, or phone)"
                )

        now = datetime.now(tz=UTC)
        run = DataOperationRun.create(
            organization_id=organization_id,
            operation_key=operation_key,
            started_by=user_id,
            started_by_email=user_email,
            now=now,
        )
        if operation_key == DUPLICATE_CUSTOMER_ANALYSIS_OPERATION_KEY and group_by:
            run.summary_json = {"group_by": group_by}
        return self._repository.add(run)


class GetDataOperationRunUseCase:
    def __init__(self, repository: SqlAlchemyDataOperationRunRepository, authorization: AuthorizationPort) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
    ) -> DataOperationRun:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        run = self._repository.get_by_id(organization_id, run_id)
        if run is None:
            raise LookupError("Data operation run not found")
        return run


class ListDataOperationDatasetCustomersUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = DEFAULT_SORT_FIELD,
        sort_dir: str = DEFAULT_SORT_DIRECTION,
    ):
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        run = self._run_repository.get_by_id(organization_id, run_id)
        if run is None:
            raise LookupError("Data operation run not found")
        if run.result is None:
            raise ValueError("Data operation run is not completed")
        dataset_kind = (run.summary_json or {}).get("dataset_kind")
        if dataset_kind != "customers_without_fair":
            raise ValueError("Run does not expose a customer dataset")

        resolved_sort = resolve_customer_list_sort(sort_by)
        result = self._dataset_repository.list_customers(
            run_id=run_id,
            organization_id=organization_id,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=resolved_sort,
            sort_dir=sort_dir,
        )
        api_sort_field = customer_name_sort_api_field(resolved_sort)
        return result, api_sort_field, sort_dir


class ExportDataOperationDatasetCustomersUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        sort_by: str = DEFAULT_SORT_FIELD,
        sort_dir: str = DEFAULT_SORT_DIRECTION,
    ) -> tuple[str, BytesIO]:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        run = self._run_repository.get_by_id(organization_id, run_id)
        if run is None:
            raise LookupError("Data operation run not found")
        if run.result is None:
            raise ValueError("Data operation run is not completed")
        dataset_kind = (run.summary_json or {}).get("dataset_kind")
        if dataset_kind != "customers_without_fair":
            raise ValueError("Run does not expose a customer dataset")

        resolved_sort = resolve_customer_list_sort(sort_by)
        customers = self._dataset_repository.list_all_customers(
            run_id=run_id,
            organization_id=organization_id,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
            sort_by=resolved_sort,
            sort_dir=sort_dir,
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "customers_without_fair"
        sheet.append(
            [
                "customer_id",
                "company_name",
                "legal_name",
                "trade_name",
                "customer_type",
                "status",
                "phone",
                "email",
                "website",
                "city",
                "country",
                "created_at",
                "updated_at",
            ]
        )
        comm_repo = SqlAlchemyCustomerCommunicationRepository(self._dataset_repository._session)
        communications_by_customer = comm_repo.load_for_customers([customer.id for customer in customers])
        for customer in customers:
            phone, email, website, _, _, _ = api_scalar_fields_from_communications(
                communications_by_customer.get(customer.id)
            )
            sheet.append(
                [
                    str(customer.id),
                    customer.display_name,
                    customer.legal_name,
                    customer.trade_name,
                    customer.customer_type.value,
                    customer.status.value,
                    phone,
                    email,
                    website,
                    customer.city,
                    customer.country,
                    customer.created_at.replace(tzinfo=None) if customer.created_at.tzinfo else customer.created_at,
                    customer.updated_at.replace(tzinfo=None) if customer.updated_at.tzinfo else customer.updated_at,
                ]
            )

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        stamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        return f"customers_without_fair_{stamp}.xlsx", buffer


DATASET_DUPLICATE_GROUP_ALLOWED_SORT_FIELDS = frozenset(
    {
        "group_key",
        "duplicate_group_key",
        "duplicate_group",
        "group_by",
        "customer_count",
        "fair_count",
        "created_at_min",
        "created_at_max",
        "created_at",
        "suggested_winner_company_name",
        "suggested_winner",
    }
)


def _require_duplicate_customer_dataset_run(run) -> None:
    if run.result is None:
        raise ValueError("Data operation run is not completed")
    dataset_kind = (run.summary_json or {}).get("dataset_kind")
    if dataset_kind != "duplicate_customer_groups":
        raise ValueError("Run does not expose a duplicate customer dataset")


class ListDataOperationDuplicateGroupsUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "group_key",
        sort_dir: str = DEFAULT_SORT_DIRECTION,
    ):
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        run = self._run_repository.get_by_id(organization_id, run_id)
        if run is None:
            raise LookupError("Data operation run not found")
        _require_duplicate_customer_dataset_run(run)

        resolved_sort = sort_by if sort_by in DATASET_DUPLICATE_GROUP_ALLOWED_SORT_FIELDS else "group_key"
        if resolved_sort in ("duplicate_group", "group_key"):
            resolved_sort = "group_key"
        if resolved_sort == "suggested_winner":
            resolved_sort = "suggested_winner_company_name"

        result = self._dataset_repository.list_duplicate_groups(
            run_id=run_id,
            organization_id=organization_id,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=resolved_sort,
            sort_dir=sort_dir,
        )
        api_sort_field = resolved_sort
        if api_sort_field == "duplicate_group_key":
            api_sort_field = "group_key"
        return result, api_sort_field, sort_dir


class GetDataOperationDuplicateGroupDetailUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        group_key: str,
    ):
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        run = self._run_repository.get_by_id(organization_id, run_id)
        if run is None:
            raise LookupError("Data operation run not found")
        _require_duplicate_customer_dataset_run(run)

        detail = self._dataset_repository.get_duplicate_group_detail(
            run_id=run_id,
            organization_id=organization_id,
            group_key=group_key.strip(),
        )
        if detail is None:
            raise LookupError("Duplicate group not found")
        return detail


def _build_duplicate_group_merge_preview(
    *,
    run_repository: SqlAlchemyDataOperationRunRepository,
    dataset_repository: SqlAlchemyDataOperationDatasetRepository,
    communication_repository: SqlAlchemyCustomerCommunicationRepository,
    organization_id: UUID,
    run_id: UUID,
    group_key: str,
    surviving_customer_id: UUID,
    scalar_selections: dict[str, UUID],
    selected_email_ids: list[UUID],
    selected_phone_ids: list[UUID],
    selected_website_ids: list[UUID],
):
    from app.modules.customers.application.duplicate_group_merge import (
        DuplicateGroupMemberContext,
        DuplicateGroupMergeSelection,
        SCALAR_FIELD_KEYS,
        build_duplicate_group_merge_preview,
        raise_for_invalid_merge_selection,
    )

    run = run_repository.get_by_id(organization_id, run_id)
    if run is None:
        raise LookupError("Data operation run not found")
    _require_duplicate_customer_dataset_run(run)

    detail = dataset_repository.get_duplicate_group_detail(
        run_id=run_id,
        organization_id=organization_id,
        group_key=group_key.strip(),
    )
    if detail is None:
        raise LookupError("Duplicate group not found")

    members = [
        DuplicateGroupMemberContext(
            customer=group_customer.customer,
            participations=group_customer.participations,
        )
        for group_customer in detail.customers
    ]
    customer_ids = [member.customer.id for member in members]
    communications_by_customer = communication_repository.load_for_customers(customer_ids)

    if not members:
        raise ValueError("Duplicate group has no customers.")

    selection = DuplicateGroupMergeSelection(
        surviving_customer_id=surviving_customer_id,
        scalar_selections={
            field: scalar_selections[field]
            for field in SCALAR_FIELD_KEYS
        },
        selected_email_ids=tuple(selected_email_ids),
        selected_phone_ids=tuple(selected_phone_ids),
        selected_website_ids=tuple(selected_website_ids),
    )

    preview = build_duplicate_group_merge_preview(
        group_key=detail.group_key,
        group_by=detail.group_by,
        members=members,
        communications_by_customer=communications_by_customer,
        selection=selection,
    )
    return preview, detail


def _append_duplicate_match_review_warnings(preview, detail):
    from dataclasses import replace

    from app.modules.customers.application.duplicate_group_merge import MergePreviewIssue
    from app.modules.customers.application.duplicate_merge_classification import (
        GroupMatchSummary,
        manual_review_warning_message,
    )

    if not detail.requires_manual_review:
        return preview
    summary = GroupMatchSummary(
        min_match_score=detail.min_match_score,
        max_match_score=detail.max_match_score,
        merge_classification=detail.merge_classification or "manual_review",
        review_tier=detail.review_tier or "needs_review",
        requires_manual_review=True,
        match_explanation_summary=detail.match_explanation_summary or "",
    )
    message = manual_review_warning_message(summary)
    if message is None:
        return preview
    if any(issue.code == "manual_review_required" for issue in preview.warnings):
        return preview
    return replace(
        preview,
        warnings=[
            *preview.warnings,
            MergePreviewIssue(
                code="manual_review_required",
                message=message,
                severity="warning",
            ),
        ],
    )


def _finalize_duplicate_group_merge_preview(preview, *, detail=None):
    from app.modules.customers.application.duplicate_group_merge import (
        raise_for_invalid_merge_selection,
    )

    if detail is not None:
        preview = _append_duplicate_match_review_warnings(preview, detail)
    raise_for_invalid_merge_selection(preview.validation_errors)
    return preview


class PreviewDuplicateGroupMergeUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
        communication_repository: SqlAlchemyCustomerCommunicationRepository,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization
        self._communication_repository = communication_repository

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        group_key: str,
        surviving_customer_id: UUID,
        scalar_selections: dict[str, UUID],
        selected_email_ids: list[UUID],
        selected_phone_ids: list[UUID],
        selected_website_ids: list[UUID],
    ):
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        preview, detail = _build_duplicate_group_merge_preview(
                run_repository=self._run_repository,
                dataset_repository=self._dataset_repository,
                communication_repository=self._communication_repository,
                organization_id=organization_id,
                run_id=run_id,
                group_key=group_key,
                surviving_customer_id=surviving_customer_id,
                scalar_selections=scalar_selections,
                selected_email_ids=selected_email_ids,
                selected_phone_ids=selected_phone_ids,
                selected_website_ids=selected_website_ids,
            )
        return _finalize_duplicate_group_merge_preview(preview, detail=detail)


class ExecuteDuplicateGroupMergeUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
        communication_repository: SqlAlchemyCustomerCommunicationRepository,
        session: Session,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization
        self._communication_repository = communication_repository
        self._session = session

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        group_key: str,
        surviving_customer_id: UUID,
        scalar_selections: dict[str, UUID],
        selected_email_ids: list[UUID],
        selected_phone_ids: list[UUID],
        selected_website_ids: list[UUID],
    ) -> DuplicateGroupMergeExecuteResult:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_RUN,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        from app.modules.customers.application.duplicate_group_merge_idempotency import (
            try_get_idempotent_merge_execute_result,
        )

        existing = try_get_idempotent_merge_execute_result(
            self._session,
            organization_id=organization_id,
            run_id=run_id,
            group_key=group_key,
            surviving_customer_id=surviving_customer_id,
        )
        if existing is not None:
            return existing

        preview, detail = _build_duplicate_group_merge_preview(
            run_repository=self._run_repository,
            dataset_repository=self._dataset_repository,
            communication_repository=self._communication_repository,
            organization_id=organization_id,
            run_id=run_id,
            group_key=group_key,
            surviving_customer_id=surviving_customer_id,
            scalar_selections=scalar_selections,
            selected_email_ids=selected_email_ids,
            selected_phone_ids=selected_phone_ids,
            selected_website_ids=selected_website_ids,
        )
        preview = _append_duplicate_match_review_warnings(preview, detail)

        from app.modules.customers.application.duplicate_group_merge import (
            raise_for_invalid_merge_selection,
        )

        raise_for_invalid_merge_selection(preview.validation_errors)
        if not preview.is_valid:
            message = (
                preview.validation_errors[0].message
                if preview.validation_errors
                else "Merge selection is invalid"
            )
            raise ValueError(message)

        member_customer_ids = [preview.surviving_customer_id, *preview.customers_to_archive]
        try:
            result = execute_duplicate_group_merge(
                self._session,
                organization_id=organization_id,
                preview=preview,
                member_customer_ids=member_customer_ids,
            )
        except DuplicateGroupMergeExecuteError as exc:
            raise ValueError(str(exc)) from exc

        self._dataset_repository.remove_customer_rows(
            run_id=run_id,
            organization_id=organization_id,
            customer_ids=result.customers_deleted,
        )
        return result


class ListDataOperationDuplicateCustomersUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "group_key",
        sort_dir: str = DEFAULT_SORT_DIRECTION,
    ):
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        run = self._run_repository.get_by_id(organization_id, run_id)
        if run is None:
            raise LookupError("Data operation run not found")
        if run.result is None:
            raise ValueError("Data operation run is not completed")
        dataset_kind = (run.summary_json or {}).get("dataset_kind")
        if dataset_kind != "duplicate_customer_groups":
            raise ValueError("Run does not expose a duplicate customer dataset")

        resolved_sort = resolve_duplicate_dataset_sort(sort_by)
        result = self._dataset_repository.list_duplicate_customers(
            run_id=run_id,
            organization_id=organization_id,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=resolved_sort,
            sort_dir=sort_dir,
        )
        api_sort_field = duplicate_dataset_sort_api_field(resolved_sort)
        return result, api_sort_field, sort_dir


class ExportDataOperationDuplicateCustomersUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        status: CustomerStatus | None = None,
        customer_type: CustomerType | None = None,
        country: str | None = None,
        search: str | None = None,
        sort_by: str = "group_key",
        sort_dir: str = DEFAULT_SORT_DIRECTION,
    ) -> tuple[str, BytesIO]:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        run = self._run_repository.get_by_id(organization_id, run_id)
        if run is None:
            raise LookupError("Data operation run not found")
        if run.result is None:
            raise ValueError("Data operation run is not completed")
        dataset_kind = (run.summary_json or {}).get("dataset_kind")
        if dataset_kind != "duplicate_customer_groups":
            raise ValueError("Run does not expose a duplicate customer dataset")

        resolved_sort = resolve_duplicate_dataset_sort(sort_by)
        items = self._dataset_repository.list_all_duplicate_customers(
            run_id=run_id,
            organization_id=organization_id,
            status=status,
            customer_type=customer_type,
            country=country,
            search=search,
            sort_by=resolved_sort,
            sort_dir=sort_dir,
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "customer_duplicates"
        sheet.append(
            [
                "group_key",
                "group_by",
                "customer_id",
                "company_name",
                "legal_name",
                "trade_name",
                "phone",
                "email",
                "website",
                "city",
                "country",
                "status",
                "fair_count",
                "first_fair_name",
                "created_at",
                "updated_at",
            ]
        )
        comm_repo = SqlAlchemyCustomerCommunicationRepository(self._dataset_repository._session)
        communications_by_customer = comm_repo.load_for_customers(
            [item.customer.id for item in items]
        )
        for item in items:
            customer = item.customer
            phone, email, website, _, _, _ = api_scalar_fields_from_communications(
                communications_by_customer.get(customer.id)
            )
            sheet.append(
                [
                    item.group_key,
                    item.group_by,
                    str(customer.id),
                    customer.display_name,
                    customer.legal_name,
                    customer.trade_name,
                    phone,
                    email,
                    website,
                    customer.city,
                    customer.country,
                    customer.status.value,
                    item.fair_count,
                    item.first_fair_name,
                    customer.created_at.replace(tzinfo=None)
                    if customer.created_at.tzinfo
                    else customer.created_at,
                    customer.updated_at.replace(tzinfo=None)
                    if customer.updated_at.tzinfo
                    else customer.updated_at,
                ]
            )

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        stamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        return f"customer_duplicates_{stamp}.xlsx", buffer


class DownloadDataOperationFileUseCase:
    def __init__(self, repository: SqlAlchemyDataOperationRunRepository, authorization: AuthorizationPort) -> None:
        self._repository = repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        access_token: str,
        run_id: UUID,
        file_id: UUID,
    ) -> tuple[DataOperationRun, str, Path]:
        from app.modules.system_admin.application.data_operation_job_runner import resolve_run_output_file

        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_READ,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        run = self._repository.get_by_id(organization_id, run_id)
        if run is None:
            raise LookupError("Data operation run not found")
        if run.result is None:
            raise ValueError("Data operation run is not completed")

        path = resolve_run_output_file(run, file_id)
        if not path.is_file():
            raise FileNotFoundError("Output file not found on disk")
        return run, path.name, path


class AssignCustomersToFairUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        fair_repository: SqlAlchemyFairRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._fair_repository = fair_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        user_email: str | None,
        access_token: str,
        parent_run_id: UUID,
        fair_id: UUID,
        customer_ids: list[UUID],
    ) -> DataOperationRun:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_RUN,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        if not customer_ids:
            raise ValueError("At least one customer must be selected")

        parent_run = self._run_repository.get_by_id(organization_id, parent_run_id)
        if parent_run is None:
            raise LookupError("Data operation run not found")
        if parent_run.operation_key != ANALYZE_CUSTOMERS_WITHOUT_FAIR_OPERATION_KEY:
            raise ValueError("Assign to fair is only supported for analyze customers without fair runs")
        if parent_run.result is None:
            raise ValueError("Analysis run is not completed")

        dataset_kind = (parent_run.summary_json or {}).get("dataset_kind")
        if dataset_kind != "customers_without_fair":
            raise ValueError("Run does not expose a customer dataset")

        fair = ensure_fair_for_participation(self._fair_repository, organization_id, fair_id)

        unique_customer_ids = list(dict.fromkeys(customer_ids))
        in_dataset = self._dataset_repository.customer_ids_in_dataset(
            run_id=parent_run_id,
            organization_id=organization_id,
            customer_ids=unique_customer_ids,
        )
        if not in_dataset:
            raise ValueError("None of the selected customers belong to this analysis dataset")

        now = datetime.now(tz=UTC)
        run = DataOperationRun.create(
            organization_id=organization_id,
            operation_key=ASSIGN_CUSTOMERS_TO_FAIR_OPERATION_KEY,
            started_by=user_id,
            started_by_email=user_email,
            now=now,
        )
        run.summary_json = {
            "action": ASSIGN_CUSTOMERS_TO_FAIR_OPERATION_KEY,
            "parent_run_id": str(parent_run_id),
            "fair_id": str(fair_id),
            "fair_name": fair.name,
            "customer_ids": [str(customer_id) for customer_id in unique_customer_ids],
            "selected_count": len(unique_customer_ids),
        }
        return self._run_repository.add(run)


class DeleteSelectedCustomersUseCase:
    def __init__(
        self,
        run_repository: SqlAlchemyDataOperationRunRepository,
        dataset_repository: SqlAlchemyDataOperationDatasetRepository,
        authorization: AuthorizationPort,
    ) -> None:
        self._run_repository = run_repository
        self._dataset_repository = dataset_repository
        self._authorization = authorization

    def execute(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        user_email: str | None,
        access_token: str,
        parent_run_id: UUID,
        customer_ids: list[UUID],
    ) -> DataOperationRun:
        if not self._authorization.check_permission(
            organization_id=organization_id,
            user_id=user_id,
            permission_code=PERMISSION_RUN,
            access_token=access_token,
        ):
            raise ForbiddenError("Admin permission required")

        if not customer_ids:
            raise ValueError("At least one customer must be selected")

        parent_run = self._run_repository.get_by_id(organization_id, parent_run_id)
        if parent_run is None:
            raise LookupError("Data operation run not found")
        if parent_run.operation_key != ANALYZE_CUSTOMERS_WITHOUT_FAIR_OPERATION_KEY:
            raise ValueError("Delete selected is only supported for analyze customers without fair runs")
        if parent_run.result is None:
            raise ValueError("Analysis run is not completed")

        dataset_kind = (parent_run.summary_json or {}).get("dataset_kind")
        if dataset_kind != "customers_without_fair":
            raise ValueError("Run does not expose a customer dataset")

        unique_customer_ids = list(dict.fromkeys(customer_ids))
        in_dataset = self._dataset_repository.customer_ids_in_dataset(
            run_id=parent_run_id,
            organization_id=organization_id,
            customer_ids=unique_customer_ids,
        )
        if not in_dataset:
            raise ValueError("None of the selected customers belong to this analysis dataset")

        now = datetime.now(tz=UTC)
        run = DataOperationRun.create(
            organization_id=organization_id,
            operation_key=DELETE_SELECTED_CUSTOMERS_OPERATION_KEY,
            started_by=user_id,
            started_by_email=user_email,
            now=now,
        )
        run.summary_json = {
            "action": DELETE_SELECTED_CUSTOMERS_OPERATION_KEY,
            "parent_run_id": str(parent_run_id),
            "customer_ids": [str(customer_id) for customer_id in unique_customer_ids],
            "selected_count": len(unique_customer_ids),
        }
        return self._run_repository.add(run)
