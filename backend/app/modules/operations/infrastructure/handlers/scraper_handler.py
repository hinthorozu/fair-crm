"""Scraper Operation handler — orchestrates existing fair scraper pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

from app.modules.fairs.domain.ports import FairRepository
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.operations.domain.entities import Operation, OperationRun
from app.modules.operations.domain.exceptions import InvalidOperationConfigError
from app.modules.operations.domain.handler import (
    HandlerExecutionContext,
    HandlerStartResult,
    HandlerValidationResult,
)
from app.modules.operations.domain.source_normalization import extract_source_ids
from app.modules.operations.domain.value_objects import (
    HandlerCapabilities,
    OperationType,
    RunStatus,
    SourceKind,
)
from app.modules.operations.infrastructure.handlers.scraper_operation_sync import (
    extract_scraper_run_id,
    merge_result_payload,
)
from app.modules.scraper.domain.enrichment_adapter import is_customer_contact_enrichment_adapter
from app.modules.scraper.domain.scraper_adapter_exceptions import AdapterNotFoundError
from app.modules.scraper.domain.scraper_run_source import ScraperRunSource
from app.shared.import_output_fields import IMPORT_OUTPUT_FIELD_DEFINITIONS

if TYPE_CHECKING:
    from app.modules.scraper.application.fair_scraper_job_runner import FairScraperJobCommand
    from app.modules.scraper.services.scraper_adapter_service import ScraperAdapterService
    from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService

REQUESTED_OUTPUT_FIELD_KEYS = tuple(
    item.output_key for item in IMPORT_OUTPUT_FIELD_DEFINITIONS
)


def _parse_optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    raise ValueError("expected boolean")


def _parse_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


class ScraperHandler:
    """Starts fair scraper runs via existing scraper infrastructure."""

    operation_type = OperationType.SCRAPER

    def __init__(
        self,
        *,
        fair_repository: FairRepository | None = None,
        adapter_service: ScraperAdapterService | None = None,
        run_history_service: ScraperRunHistoryService | None = None,
        job_scheduler: Callable[[FairScraperJobCommand], None] | None = None,
    ) -> None:
        self._fair_repository = fair_repository
        self._adapter_service = adapter_service
        self._run_history_service = run_history_service
        self._job_scheduler = job_scheduler

    @property
    def capabilities(self) -> HandlerCapabilities:
        return HandlerCapabilities(
            supports_pause=False,
            supports_resume=False,
            supports_retry=True,
            supports_schedule=False,
            supports_items=False,
        )

    def validate_create(
        self,
        *,
        source_kind: str,
        source_config: dict[str, Any],
        type_config: dict[str, Any],
        run_settings: dict[str, Any],
        organization_id: UUID | None = None,
    ) -> HandlerValidationResult:
        _ = run_settings
        errors: list[str] = []

        if source_kind != SourceKind.FAIR:
            errors.append("scraper requires source_kind=fair")

        source_ids = extract_source_ids(source_config)
        if len(source_ids) != 1:
            errors.append("scraper requires exactly one fair in source_ids")

        adapter_key = str(type_config.get("adapter_key") or "").strip()
        if not adapter_key:
            errors.append("type_config.adapter_key is required")
        elif is_customer_contact_enrichment_adapter(adapter_key):
            errors.append(
                "customer_contact_enrichment is not a scraper automation adapter"
            )

        requested_raw = type_config.get("requested_fields")
        if requested_raw is None:
            errors.append("type_config.requested_fields is required")
        elif not isinstance(requested_raw, (list, tuple)):
            errors.append("type_config.requested_fields must be a list")
        else:
            invalid = [
                str(item)
                for item in requested_raw
                if str(item).strip() not in REQUESTED_OUTPUT_FIELD_KEYS
            ]
            if invalid:
                errors.append(
                    "invalid requested_fields: " + ", ".join(sorted(set(invalid)))
                )
            elif len(requested_raw) == 0:
                errors.append("type_config.requested_fields must not be empty")

        for key in ("max_pages", "use_http", "scrape_detail"):
            if key not in type_config:
                continue
            try:
                if key == "max_pages":
                    parsed = _parse_optional_int(type_config.get(key))
                    if parsed is not None and parsed < 1:
                        errors.append("type_config.max_pages must be >= 1")
                else:
                    _parse_optional_bool(type_config.get(key))
            except (TypeError, ValueError):
                errors.append(f"type_config.{key} is invalid")

        if "source_url" in type_config and type_config.get("source_url") is not None:
            if not isinstance(type_config.get("source_url"), str):
                errors.append("type_config.source_url must be a string")
            elif not str(type_config.get("source_url") or "").strip():
                errors.append("type_config.source_url must not be empty")

        if "scraper_config" in type_config and type_config.get("scraper_config") is not None:
            if not isinstance(type_config.get("scraper_config"), dict):
                errors.append("type_config.scraper_config must be an object")

        if errors:
            return HandlerValidationResult.failure(*errors)

        if (
            organization_id is not None
            and self._fair_repository is not None
            and self._adapter_service is not None
            and source_ids
            and adapter_key
        ):
            deep_errors = self._validate_against_domain(
                organization_id=organization_id,
                fair_id=source_ids[0],
                adapter_key=adapter_key,
                requested_fields=list(requested_raw or []),
                source_url_override=str(type_config.get("source_url") or "").strip() or None,
            )
            if deep_errors:
                return HandlerValidationResult.failure(*deep_errors)

        return HandlerValidationResult.success()

    def validate_start(self, *, operation: Operation) -> HandlerValidationResult:
        return self.validate_create(
            source_kind=operation.source_kind,
            source_config=operation.source_config,
            type_config=operation.type_config,
            run_settings=operation.run_settings,
            organization_id=operation.organization_id,
        )

    def on_start(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        return self._start_scraper(operation=operation, run=run, context=context)

    def on_retry(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        return self._start_scraper(operation=operation, run=run, context=context)

    def on_cancel(
        self,
        *,
        operation: Operation,
        run: OperationRun | None,
        context: HandlerExecutionContext | None = None,
    ) -> None:
        if run is None or self._run_history_service is None or context is None:
            return
        scraper_run_id = extract_scraper_run_id(run)
        if scraper_run_id is None:
            return
        try:
            self._run_history_service.request_cancel(
                scraper_run_id,
                organization_id=operation.organization_id,
                requested_by=context.user_id,
            )
        except KeyError:
            return

    def _start_scraper(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        from app.modules.scraper.application.fair_scraper_job_runner import (
            FairScraperJobCommand,
        )
        from app.modules.scraper.domain.requested_output_fields import (
            normalize_requested_fields,
        )

        if (
            self._fair_repository is None
            or self._adapter_service is None
            or self._run_history_service is None
        ):
            raise InvalidOperationConfigError(
                "Scraper repositories are required to start scraper operations"
            )

        validation = self.validate_start(operation=operation)
        if not validation.ok:
            raise InvalidOperationConfigError("; ".join(validation.errors))

        fair_id = extract_source_ids(operation.source_config)[0]
        fair = self._fair_repository.get_by_id(operation.organization_id, fair_id)
        if fair is None:
            raise InvalidOperationConfigError("Fair not found")

        type_config = dict(operation.type_config or {})
        adapter_key = str(type_config.get("adapter_key") or "").strip()
        source_url_override = str(type_config.get("source_url") or "").strip() or None
        effective_source_url = source_url_override or (fair.source_url or "").strip() or None
        scraper_config_override = (
            dict(type_config["scraper_config"])
            if isinstance(type_config.get("scraper_config"), dict)
            else None
        )
        requested_fields = normalize_requested_fields(
            list(type_config.get("requested_fields") or []),
            capabilities=self._capabilities_for_adapter(
                operation.organization_id, adapter_key
            ),
        )
        option_overrides = self._build_option_overrides(type_config)

        fair_year = fair.start_date.year if fair.start_date is not None else None
        scraper_run = self._run_history_service.start_run(
            adapter_key=adapter_key,
            input_url=effective_source_url,
            fair_name=fair.name,
            fair_year=fair_year,
            organization_id=fair.organization_id,
            fair_id=fair.id,
            run_source=ScraperRunSource.FAIR_AUTOMATION,
        )

        result_payload = {
            "scraper_run_id": str(scraper_run.id),
            "adapter_key": adapter_key,
            "fair_id": str(fair.id),
            "input_url": effective_source_url,
            "requested_fields": requested_fields,
            "import_batch_id": None,
            "total_rows": 0,
        }
        merge_result_payload(run, result_payload)

        command = FairScraperJobCommand(
            run_id=scraper_run.id,
            organization_id=operation.organization_id,
            fair_id=fair.id,
            user_id=context.user_id,
            access_token=context.access_token,
            operation_id=operation.id,
            operation_run_id=run.id,
            requested_fields=requested_fields,
            option_overrides=option_overrides or None,
            adapter_key=adapter_key,
            source_url=effective_source_url,
            scraper_config=scraper_config_override,
        )

        if self._job_scheduler is None:
            raise InvalidOperationConfigError(
                "Background job scheduler is required for scraper operations"
            )
        self._job_scheduler(command)

        return HandlerStartResult(
            run_status=RunStatus.RUNNING,
            total_items=0,
            message="Scraper run started",
            result_payload=result_payload,
        )

    def _validate_against_domain(
        self,
        *,
        organization_id: UUID,
        fair_id: UUID,
        adapter_key: str,
        requested_fields: list[str],
        source_url_override: str | None = None,
    ) -> list[str]:
        from app.modules.scraper.domain.requested_output_fields import (
            filter_requested_fields_by_capabilities,
        )

        assert self._fair_repository is not None
        assert self._adapter_service is not None
        errors: list[str] = []

        try:
            adapter = self._adapter_service.get_adapter(organization_id, adapter_key)
        except AdapterNotFoundError:
            return [f"adapter not found: {adapter_key}"]

        if not adapter.is_active:
            errors.append(f"adapter is not active: {adapter_key}")

        fair = self._fair_repository.get_by_id(organization_id, fair_id)
        if fair is None:
            errors.append("fair not found")
            return errors

        if fair.deleted_at is not None or fair.status == FairStatus.ARCHIVED:
            errors.append("fair is archived or deleted")

        effective_source_url = source_url_override or (fair.source_url or "").strip()
        if not effective_source_url:
            errors.append("source_url is not configured")

        capabilities = self._capabilities_for_adapter(organization_id, adapter_key)
        unsupported = [
            field
            for field in requested_fields
            if field in REQUESTED_OUTPUT_FIELD_KEYS
            and field
            not in filter_requested_fields_by_capabilities([field], capabilities)
        ]
        if unsupported:
            errors.append(
                "requested_fields not supported by adapter: "
                + ", ".join(unsupported)
            )

        return errors

    def _capabilities_for_adapter(
        self, organization_id: UUID, adapter_key: str
    ) -> dict[str, bool] | None:
        from app.modules.scraper.domain.requested_output_fields import (
            output_field_capabilities_from_supports,
        )

        if self._adapter_service is None:
            return None
        try:
            self._adapter_service.get_adapter(organization_id, adapter_key)
            merged = self._adapter_service.get_merged_manifest(organization_id, adapter_key)
        except AdapterNotFoundError:
            return None
        if merged is not None:
            return output_field_capabilities_from_supports(merged.supports)
        return None

    def _build_option_overrides(self, type_config: dict[str, Any]) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        if "max_pages" in type_config:
            value = _parse_optional_int(type_config.get("max_pages"))
            if value is not None:
                overrides["max_pages"] = value
        if "use_http" in type_config:
            value = _parse_optional_bool(type_config.get("use_http"))
            if value is not None:
                overrides["use_http"] = value
        if "scrape_detail" in type_config:
            value = _parse_optional_bool(type_config.get("scrape_detail"))
            if value is not None:
                overrides["scrape_detail"] = value
        return overrides
