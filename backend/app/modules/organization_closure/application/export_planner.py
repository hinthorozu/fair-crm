from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.contacts.infrastructure.persistence.models import ContactModel
from app.modules.cost_catalog.infrastructure.models import CostCategoryModel, CostProductModel
from app.modules.customers.infrastructure.persistence.communication_models import (
    CustomerEmailModel,
    CustomerPhoneModel,
    CustomerWebsiteModel,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.data_integration.infrastructure.persistence.models import ImportJobModel, ImportTemplateModel
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailBatchModel
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel, ImportRowModel
from app.modules.mail_send_operations.infrastructure.persistence.models import MailSendOperationModel
from app.modules.mail_templates.infrastructure.persistence.models import MailTemplateModel
from app.modules.operations.infrastructure.persistence.models import (
    OperationModel,
    OperationRunItemModel,
    OperationRunModel,
)
from app.modules.organization_closure.application.service import (
    ClosureAuthorizationUnavailableError,
    ClosureExecutionConflictError,
    ClosureExecutionNotFoundError,
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
    ClosurePermissionDeniedError,
    OrganizationClosureError,
    STATUS_IN_PROGRESS,
    SYSTEM_CLOSURE_PERMISSION,
)
from app.modules.organization_closure.infrastructure.export_plan_repository import (
    SqlAlchemyOrganizationClosureExportPlanRepository,
)
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureEventModel,
    OrganizationClosureExportPlanModel,
)
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.quote_templates.infrastructure.models import QuoteTemplateModel, QuoteTemplateVersionModel
from app.modules.quotes.infrastructure.models import QuoteModel
from app.modules.scraper.infrastructure.persistence.models import (
    CustomerEnrichmentStateModel,
    ScraperAdapterModel,
    ScraperRunHistoryModel,
)
from app.modules.template_contents.infrastructure.models import TemplateContentModel, TemplateContentTagModel
from app.modules.todos.infrastructure.persistence.models import (
    TodoModel,
    TodoOutcomeDefinitionModel,
    TodoStepModel,
    TodoWorklistStateModel,
)

EXPORT_SCHEMA_VERSION = "ol08.export-manifest.v1"
EXPORT_DISPOSITION_REQUIRED = "required"
EXPORT_STATUS_PLANNED = "planned"
INCLUDED = "included"
EXCLUDED = "excluded"
DEFERRED = "deferred"

PORTABLE_SCOPE_REASON = "portable_structured_scope_certified_v1"
FORBIDDEN_EXPORT_SOURCE_TABLES = frozenset(
    {
        "email_account_smtp_configs",
        "email_account_provider_configs",
        "smtp_accounts",
    }
)


class ClosureExportPlanningError(OrganizationClosureError):
    pass


class ClosureExportPlanNotFoundError(ClosureExecutionNotFoundError):
    pass


@dataclass(frozen=True)
class SourceSpec:
    key: str
    model: type
    scope_model: type
    join_on: Any | None = None
    field_exclusions: tuple[str, ...] = ()

    @property
    def table_name(self) -> str:
        return str(self.model.__tablename__)

    @property
    def scope_table_name(self) -> str:
        return str(self.scope_model.__tablename__)


@dataclass(frozen=True)
class DataClassSpec:
    key: str
    classification: str
    reason_code: str
    sources: tuple[SourceSpec, ...] = ()


def _direct(
    key: str,
    model: type,
    *,
    field_exclusions: tuple[str, ...] = (),
) -> SourceSpec:
    return SourceSpec(
        key=key,
        model=model,
        scope_model=model,
        field_exclusions=field_exclusions,
    )


def _joined(
    key: str,
    model: type,
    scope_model: type,
    join_on: Any,
) -> SourceSpec:
    return SourceSpec(
        key=key,
        model=model,
        scope_model=scope_model,
        join_on=join_on,
    )


DATA_CLASS_REGISTRY: tuple[DataClassSpec, ...] = (
    DataClassSpec(
        "customers",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (_direct("customers", CustomerModel),),
    ),
    DataClassSpec(
        "customer_communications",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct("customer_phones", CustomerPhoneModel),
            _direct("customer_emails", CustomerEmailModel),
            _direct("customer_websites", CustomerWebsiteModel),
        ),
    ),
    DataClassSpec(
        "contacts",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (_direct("contacts", ContactModel),),
    ),
    DataClassSpec(
        "fairs",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (_direct("fairs", FairModel),),
    ),
    DataClassSpec(
        "participations",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (_direct("participations", CustomerFairParticipationModel),),
    ),
    DataClassSpec(
        "activities_followups",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (_direct("activities", ActivityModel),),
    ),
    DataClassSpec(
        "todos_workflow",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct("todos", TodoModel),
            _direct("todo_steps", TodoStepModel),
            _direct("todo_outcome_definitions", TodoOutcomeDefinitionModel),
            _direct("todo_worklist_states", TodoWorklistStateModel),
        ),
    ),
    DataClassSpec(
        "quotes",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (_direct("quotes", QuoteModel),),
    ),
    DataClassSpec(
        "quote_template_sources",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct("quote_templates", QuoteTemplateModel),
            _joined(
                "quote_template_versions",
                QuoteTemplateVersionModel,
                QuoteTemplateModel,
                QuoteTemplateVersionModel.template_id == QuoteTemplateModel.id,
            ),
        ),
    ),
    DataClassSpec(
        "template_content_sources",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct("template_content_tags", TemplateContentTagModel),
            _direct("template_contents", TemplateContentModel),
        ),
    ),
    DataClassSpec(
        "cost_catalog",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct("cost_categories", CostCategoryModel),
            _direct("cost_products", CostProductModel),
        ),
    ),
    DataClassSpec(
        "imports_data_integration",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct(
                "import_batches",
                ImportBatchModel,
                field_exclusions=("stored_file_content",),
            ),
            _direct("import_rows", ImportRowModel),
            _direct("import_jobs", ImportJobModel),
            _direct("import_templates", ImportTemplateModel),
        ),
    ),
    DataClassSpec(
        "scraper_enrichment_structured",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct("scraper_run_history", ScraperRunHistoryModel),
            _direct("scraper_adapters", ScraperAdapterModel),
            _direct("customer_enrichment_states", CustomerEnrichmentStateModel),
        ),
    ),
    DataClassSpec(
        "operations_automation_structured",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct("operations", OperationModel),
            _direct("operation_runs", OperationRunModel),
            _direct("operation_run_items", OperationRunItemModel),
        ),
    ),
    DataClassSpec(
        "mail_templates",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (_direct("mail_templates", MailTemplateModel),),
    ),
    DataClassSpec(
        "mail_send_history",
        INCLUDED,
        PORTABLE_SCOPE_REASON,
        (
            _direct("fair_email_batches", FairEmailBatchModel),
            _direct("mail_send_operations", MailSendOperationModel),
        ),
    ),
    DataClassSpec(
        "generated_binary_files_artifacts",
        DEFERRED,
        "binary_artifact_lifecycle_deferred_ol08_e",
    ),
    DataClassSpec(
        "scraper_operation_raw_artifacts",
        DEFERRED,
        "raw_artifact_lifecycle_deferred_ol08_e",
    ),
    DataClassSpec(
        "managed_quote_logo_binary_assets",
        DEFERRED,
        "binary_artifact_lifecycle_deferred_ol08_e",
    ),
    DataClassSpec(
        "scraper_internal_logs",
        EXCLUDED,
        "internal_diagnostic_not_portable_v1",
    ),
    DataClassSpec(
        "provider_account_descriptors",
        DEFERRED,
        "provider_descriptor_policy_deferred_ol08_c",
    ),
    DataClassSpec(
        "reusable_provider_smtp_credentials",
        EXCLUDED,
        "reusable_secret_material_forbidden",
    ),
    DataClassSpec(
        "provider_side_credential_lifecycle",
        DEFERRED,
        "provider_credential_lifecycle_deferred_ol08_c",
    ),
    DataClassSpec(
        "raw_provider_webhooks_signatures_diagnostics",
        EXCLUDED,
        "raw_provider_payload_not_portable_v1",
    ),
    DataClassSpec(
        "core_identity_credentials",
        EXCLUDED,
        "outside_fair_crm_ownership",
    ),
    DataClassSpec(
        "system_admin_backups_restores",
        DEFERRED,
        "backup_restore_policy_deferred_ol10",
    ),
    DataClassSpec(
        "derived_dashboard_views",
        EXCLUDED,
        "derived_reproducible_view",
    ),
    DataClassSpec(
        "internal_closure_orchestration_events",
        EXCLUDED,
        "internal_orchestration_not_portable_v1",
    ),
)


def included_source_table_names() -> frozenset[str]:
    return frozenset(
        source.table_name
        for data_class in DATA_CLASS_REGISTRY
        if data_class.classification == INCLUDED
        for source in data_class.sources
    )


def validate_secret_exclusion_registry() -> None:
    included_tables = included_source_table_names()
    forbidden = included_tables.intersection(FORBIDDEN_EXPORT_SOURCE_TABLES)
    if forbidden:
        raise ClosureExportPlanningError(
            "Secret-bearing tables cannot participate in closure export planning: "
            + ", ".join(sorted(forbidden))
        )

    for data_class in DATA_CLASS_REGISTRY:
        if data_class.classification == INCLUDED and not data_class.sources:
            raise ClosureExportPlanningError(
                f"Included export data class has no explicit source: {data_class.key}"
            )
        if data_class.classification != INCLUDED and data_class.sources:
            raise ClosureExportPlanningError(
                f"Non-included export data class cannot have count sources: {data_class.key}"
            )


def _canonical_digest(values: list[str]) -> str:
    payload = "\n".join(sorted(values)).encode("utf-8")
    return sha256(payload).hexdigest()


def _manifest_digest(manifest: dict[str, Any]) -> str:
    payload = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


class OrganizationClosureExportPlanner:
    def __init__(
        self,
        repository: SqlAlchemyOrganizationClosureExportPlanRepository,
        authorization: AuthorizationPort,
        lifecycle: OrganizationLifecycleGuard,
        audit: AuditPort,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._audit = audit

    def plan(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureExportPlanModel:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_suspended(organization_id)

        execution = self._repository.get_execution(organization_id, execution_id)
        if execution is None or execution.closed_at is not None:
            raise ClosureExecutionNotFoundError("Open closure execution not found")
        if execution.status != STATUS_IN_PROGRESS:
            raise ClosureExecutionConflictError(
                "Closure execution must be in progress for export planning"
            )

        existing = self._repository.get_plan(
            organization_id,
            execution_id,
            EXPORT_SCHEMA_VERSION,
        )
        if existing is not None:
            return existing

        validate_secret_exclusion_registry()
        plan_id = uuid4()
        now = datetime.now(tz=UTC)
        try:
            manifest = self._build_manifest(
                plan_id=plan_id,
                organization_id=organization_id,
                execution_id=execution_id,
                planned_at=now,
            )
        except OrganizationClosureError:
            raise
        except Exception as exc:
            raise ClosureExportPlanningError(
                "Closure export planning failed before durable plan creation"
            ) from exc

        plan = OrganizationClosureExportPlanModel(
            id=plan_id,
            organization_id=organization_id,
            closure_execution_id=execution_id,
            schema_version=EXPORT_SCHEMA_VERSION,
            disposition=EXPORT_DISPOSITION_REQUIRED,
            status=EXPORT_STATUS_PLANNED,
            manifest_json=manifest,
            manifest_digest=_manifest_digest(manifest),
            actor_user_id=auth.user_id,
            actor_session_id=auth.session_id,
            created_at=now,
            updated_at=now,
        )
        event = OrganizationClosureEventModel(
            id=uuid4(),
            execution_id=execution.id,
            organization_id=organization_id,
            actor_user_id=auth.user_id,
            actor_session_id=auth.session_id,
            action="export_plan_planned",
            from_status=execution.status,
            to_status=execution.status,
            phase=execution.current_phase,
            created_at=now,
        )
        self._repository.add_plan(plan)
        self._repository.add_event(event)

        try:
            self._repository.flush()
        except IntegrityError as exc:
            self._repository.rollback()
            duplicate = self._repository.get_plan(
                organization_id,
                execution_id,
                EXPORT_SCHEMA_VERSION,
            )
            if duplicate is not None:
                return duplicate
            raise ClosureExportPlanningError(
                "Closure export plan persistence failed"
            ) from exc

        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="organization_closure.export_plan.planned",
            resource_type="organization_closure_export_plan",
            resource_id=str(plan.id),
            new_values={
                "status": plan.status,
                "disposition": plan.disposition,
                "schema_version": plan.schema_version,
            },
            metadata={
                "authority": "system",
                "ol08_slice": "OL08-03A",
                "closure_execution_id": str(execution_id),
                "manifest_digest": plan.manifest_digest,
                "digest_semantics": "planning_metadata_only_not_package_integrity",
            },
        )
        return plan

    def get(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosureExportPlanModel:
        self._require_system_authority(organization_id, auth, access_token)
        plan = self._repository.get_plan(
            organization_id,
            execution_id,
            EXPORT_SCHEMA_VERSION,
        )
        if plan is None:
            raise ClosureExportPlanNotFoundError("Closure export plan not found")
        return plan

    def _build_manifest(
        self,
        *,
        plan_id: UUID,
        organization_id: UUID,
        execution_id: UUID,
        planned_at: datetime,
    ) -> dict[str, Any]:
        data_classes = [
            self._plan_data_class(spec, organization_id)
            for spec in DATA_CLASS_REGISTRY
        ]
        return {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "export_id": str(plan_id),
            "organization_id": str(organization_id),
            "closure_execution_id": str(execution_id),
            "disposition": EXPORT_DISPOSITION_REQUIRED,
            "planning_state": EXPORT_STATUS_PLANNED,
            "planning_timestamp": planned_at.isoformat(),
            "data_classes": data_classes,
            "secret_exclusion": {
                "status": "enforced",
                "fingerprint_input": "record_id_only",
                "reusable_secret_material": "excluded",
                "secret_derived_fingerprints": "forbidden",
            },
            "digest_semantics": "planning_metadata_only_not_package_integrity",
        }

    def _plan_data_class(
        self,
        spec: DataClassSpec,
        organization_id: UUID,
    ) -> dict[str, Any]:
        if spec.classification != INCLUDED:
            return {
                "key": spec.key,
                "classification": spec.classification,
                "reason_code": spec.reason_code,
                "record_count": None,
                "record_identity_digest": None,
                "sources": [],
            }

        sources: list[dict[str, Any]] = []
        class_fingerprint_values: list[str] = []
        total_count = 0
        for source in spec.sources:
            ids = self._repository.list_scoped_ids(
                model=source.model,
                scope_model=source.scope_model,
                organization_id=organization_id,
                join_on=source.join_on,
            )
            identity_digest = _canonical_digest([str(record_id) for record_id in ids])
            count = len(ids)
            total_count += count
            class_fingerprint_values.append(
                f"{source.key}:{count}:{identity_digest}"
            )
            source_entry: dict[str, Any] = {
                "key": source.key,
                "table": source.table_name,
                "scope_table": source.scope_table_name,
                "scope_mode": "direct" if source.join_on is None else "parent_join",
                "record_count": count,
                "record_identity_digest": identity_digest,
                "fingerprint_input": "record_id_only",
            }
            if source.field_exclusions:
                source_entry["field_exclusions"] = list(source.field_exclusions)
            sources.append(source_entry)

        return {
            "key": spec.key,
            "classification": INCLUDED,
            "reason_code": spec.reason_code,
            "record_count": total_count,
            "record_identity_digest": _canonical_digest(class_fingerprint_values),
            "sources": sources,
        }

    def _require_system_authority(
        self,
        organization_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> None:
        try:
            allowed = self._authorization.check_permission(
                organization_id=organization_id,
                user_id=auth.user_id,
                permission_code=SYSTEM_CLOSURE_PERMISSION,
                access_token=access_token,
            )
        except Exception as exc:
            raise ClosureAuthorizationUnavailableError(
                "Closure export authorization authority unavailable"
            ) from exc
        if not allowed:
            raise ClosurePermissionDeniedError("Platform SuperAdmin authority required")

    def _require_suspended(self, organization_id: UUID) -> None:
        try:
            snapshot = self._lifecycle.get_snapshot(organization_id)
        except OrganizationLifecycleUnavailableError as exc:
            raise ClosureLifecycleUnavailableError(
                "Organization lifecycle authority unavailable"
            ) from exc
        if snapshot.status != "suspended":
            raise ClosureLifecyclePreconditionError(
                f"Organization must be suspended before export planning: {snapshot.status}"
            )
