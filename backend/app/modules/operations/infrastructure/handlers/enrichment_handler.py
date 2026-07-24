"""Enrichment Operation handler — reuses existing customer contact enrichment engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

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
from app.modules.scraper.domain.enrichment_adapter import (
    CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY,
    is_customer_contact_enrichment_adapter,
)
from app.shared.import_output_fields import IMPORT_OUTPUT_FIELD_DEFINITIONS

if TYPE_CHECKING:
    from app.modules.scraper.application.enrichment_run_job_runner import EnrichmentRunJobCommand
    from app.modules.scraper.application.run_enrichment import RunEnrichmentUseCase
    from app.modules.scraper.services.scraper_run_history_service import ScraperRunHistoryService

ENRICHMENT_OUTPUT_FIELD_KEYS = frozenset(
    item.output_key
    for item in IMPORT_OUTPUT_FIELD_DEFINITIONS
    if item.output_key
    in {
        "email",
        "phone",
        "address",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
    }
)
_VALID_COMPANY_NAME_MATCH = frozenset({"contains", "starts_with"})


def _parse_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _parse_optional_bool(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    raise ValueError("expected boolean")


def _parse_optional_uuid(value: Any) -> UUID | None:
    if value is None or value == "":
        return None
    return UUID(str(value))


class EnrichmentHandler:
    """Starts enrichment runs via RunEnrichmentUseCase + EnrichmentRunJobRunner."""

    operation_type = OperationType.ENRICHMENT

    def __init__(
        self,
        *,
        run_enrichment_use_case: RunEnrichmentUseCase | None = None,
        run_history_service: ScraperRunHistoryService | None = None,
        job_scheduler: Callable[[EnrichmentRunJobCommand], None] | None = None,
    ) -> None:
        self._run_enrichment_use_case = run_enrichment_use_case
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
        _ = run_settings, organization_id
        errors: list[str] = []

        if source_kind not in {SourceKind.FAIR, SourceKind.CUSTOMER}:
            errors.append("enrichment requires source_kind=fair or source_kind=customer")

        source_ids = extract_source_ids(source_config)
        if source_kind == SourceKind.FAIR and len(source_ids) < 1:
            errors.append("enrichment with source_kind=fair requires at least one fair in source_ids")

        adapter_key = str(type_config.get("adapter_key") or "").strip().lower()
        if not adapter_key:
            errors.append("type_config.adapter_key is required")
        elif not is_customer_contact_enrichment_adapter(adapter_key):
            errors.append(
                f"type_config.adapter_key must be {CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY}"
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
                if str(item).strip() not in ENRICHMENT_OUTPUT_FIELD_KEYS
            ]
            if invalid:
                errors.append(
                    "invalid requested_fields: " + ", ".join(sorted(set(invalid)))
                )
            elif len(requested_raw) == 0:
                errors.append("type_config.requested_fields must not be empty")

        if "limit" in type_config and type_config.get("limit") is not None:
            try:
                parsed_limit = _parse_optional_int(type_config.get("limit"))
                if parsed_limit is not None and (parsed_limit < 1 or parsed_limit > 500):
                    errors.append("type_config.limit must be between 1 and 500")
            except (TypeError, ValueError):
                errors.append("type_config.limit is invalid")

        if "include_existing_email" in type_config:
            try:
                _parse_optional_bool(type_config.get("include_existing_email"))
            except (TypeError, ValueError):
                errors.append("type_config.include_existing_email is invalid")

        if "company_name_match" in type_config and type_config.get("company_name_match") is not None:
            match = str(type_config.get("company_name_match") or "").strip()
            if match not in _VALID_COMPANY_NAME_MATCH:
                errors.append("type_config.company_name_match must be contains or starts_with")

        for key in ("company_name", "address_contains"):
            if key in type_config and type_config.get(key) is not None:
                if not isinstance(type_config.get(key), str):
                    errors.append(f"type_config.{key} must be a string")

        if "fair_id" in type_config and type_config.get("fair_id") is not None:
            try:
                _parse_optional_uuid(type_config.get("fair_id"))
            except (TypeError, ValueError):
                errors.append("type_config.fair_id is invalid")

        if "fair_ids" in type_config and type_config.get("fair_ids") is not None:
            raw_fair_ids = type_config.get("fair_ids")
            if not isinstance(raw_fair_ids, (list, tuple)):
                errors.append("type_config.fair_ids must be a list")
            else:
                for index, item in enumerate(raw_fair_ids):
                    try:
                        _parse_optional_uuid(item)
                    except (TypeError, ValueError):
                        errors.append(f"type_config.fair_ids[{index}] is invalid")
                        break

        if errors:
            return HandlerValidationResult.failure(*errors)
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
        return self._start_enrichment(operation=operation, run=run, context=context)

    def on_retry(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        return self._start_enrichment(operation=operation, run=run, context=context)

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

    def _start_enrichment(
        self,
        *,
        operation: Operation,
        run: OperationRun,
        context: HandlerExecutionContext,
    ) -> HandlerStartResult:
        from app.modules.scraper.application.enrichment_run_job_runner import (
            EnrichmentRunJobCommand,
        )
        from app.modules.scraper.application.run_enrichment import RunEnrichmentCommand

        if self._run_enrichment_use_case is None:
            raise InvalidOperationConfigError(
                "Enrichment use case is required to start enrichment operations"
            )
        if self._job_scheduler is None:
            raise InvalidOperationConfigError(
                "Background job scheduler is required for enrichment operations"
            )

        validation = self.validate_start(operation=operation)
        if not validation.ok:
            raise InvalidOperationConfigError("; ".join(validation.errors))

        type_config = dict(operation.type_config or {})
        adapter_key = str(
            type_config.get("adapter_key") or CUSTOMER_CONTACT_ENRICHMENT_ADAPTER_KEY
        ).strip().lower()
        fair_ids = self._resolve_fair_ids(operation, type_config)
        fair_id = fair_ids[0] if len(fair_ids) == 1 else None
        limit = _parse_optional_int(type_config.get("limit")) if "limit" in type_config else None
        include_existing_email = _parse_optional_bool(type_config.get("include_existing_email"))
        company_name = str(type_config.get("company_name") or "").strip() or None
        company_name_match = str(type_config.get("company_name_match") or "contains").strip()
        if company_name_match not in _VALID_COMPANY_NAME_MATCH:
            company_name_match = "contains"
        address_contains = str(type_config.get("address_contains") or "").strip() or None
        requested_fields = [
            str(item).strip()
            for item in (type_config.get("requested_fields") or [])
            if str(item).strip()
        ]
        dry_run = _parse_optional_bool(type_config.get("dry_run")) if "dry_run" in type_config else False
        max_pages = _parse_optional_int(type_config.get("max_pages")) or 10

        try:
            enrichment_run = self._run_enrichment_use_case.execute(
                RunEnrichmentCommand(
                    organization_id=operation.organization_id,
                    adapter_key=adapter_key,
                    limit=limit,
                    fair_id=fair_id if fair_ids else None,
                )
            )
        except Exception as exc:
            # OperationRun is already queued; mark failed so it never stays running.
            return HandlerStartResult(
                run_status=RunStatus.FAILED,
                total_items=0,
                message=str(exc) or "Enrichment run could not be started",
                result_payload={"adapter_key": adapter_key},
            )

        result_payload = {
            "scraper_run_id": str(enrichment_run.id),
            "adapter_key": enrichment_run.adapter_key,
            "fair_id": str(fair_id) if fair_id else None,
            "fair_ids": [str(item) for item in fair_ids],
            "import_batch_id": None,
            "total_rows": 0,
        }
        merge_result_payload(run, result_payload)

        self._job_scheduler(
            EnrichmentRunJobCommand(
                run_id=enrichment_run.id,
                organization_id=operation.organization_id,
                adapter_key=enrichment_run.adapter_key,
                user_id=context.user_id,
                access_token=context.access_token,
                limit=limit,
                requested_fields=requested_fields,
                dry_run=dry_run,
                max_pages=max_pages if max_pages is not None else 10,
                fair_id=fair_id if fair_ids else None,
                fair_ids=fair_ids or None,
                include_existing_email=include_existing_email,
                company_name=company_name,
                company_name_match=company_name_match,
                address_contains=address_contains,
                operation_id=operation.id,
                operation_run_id=run.id,
            )
        )

        return HandlerStartResult(
            run_status=RunStatus.RUNNING,
            total_items=0,
            message="Enrichment run started",
            result_payload=result_payload,
        )

    def _resolve_fair_ids(
        self, operation: Operation, type_config: dict[str, Any]
    ) -> list[UUID]:
        if operation.source_kind == SourceKind.FAIR:
            return extract_source_ids(operation.source_config)

        from app.modules.scraper.services.enrichment_candidate_service import (
            normalize_enrichment_fair_ids,
        )

        config_fair_ids: list[UUID] = []
        raw = type_config.get("fair_ids")
        if isinstance(raw, (list, tuple)):
            for item in raw:
                try:
                    parsed = _parse_optional_uuid(item)
                except (TypeError, ValueError):
                    continue
                if parsed is not None:
                    config_fair_ids.append(parsed)
        try:
            legacy = _parse_optional_uuid(type_config.get("fair_id"))
        except (TypeError, ValueError):
            legacy = None
        return normalize_enrichment_fair_ids(fair_id=legacy, fair_ids=config_fair_ids)
