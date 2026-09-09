from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleSnapshot,
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
from app.modules.email_accounts.infrastructure.persistence.models import (
    EmailAccountModel,
    EmailAccountProviderConfigModel,
    EmailAccountSmtpConfigModel,
)
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
from app.modules.organization_closure.application.closure_package import PACKAGE_SCHEMA_VERSION
from app.modules.organization_closure.application.credential_disposition import STATUS_DISPOSITION_COMPLETE
from app.modules.organization_closure.application.service import (
    STATUS_IN_PROGRESS,
    SYSTEM_CLOSURE_PERMISSION,
    ClosureAuthorizationUnavailableError,
    ClosureExecutionConflictError,
    ClosureExecutionNotFoundError,
    ClosureLifecyclePreconditionError,
    ClosureLifecycleUnavailableError,
    ClosurePermissionDeniedError,
    OrganizationClosureError,
)
from app.modules.organization_closure.infrastructure.models import OrganizationClosureArtifactInventoryModel
from app.modules.organization_closure.infrastructure.package_storage import (
    DEFAULT_CLOSURE_PACKAGE_ROOT,
    ClosurePackageStorageError,
    resolve_stored_locator,
    verify_package,
)
from app.modules.organization_closure.infrastructure.product_cleanup_models import (
    OrganizationClosureProductCleanupItemModel,
)
from app.modules.organization_closure.infrastructure.product_cleanup_repository import (
    SqlAlchemyOrganizationClosureProductCleanupRepository,
)
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.quote_templates.infrastructure.models import QuoteTemplateModel, QuoteTemplateVersionModel
from app.modules.quotes.infrastructure.models import QuoteModel
from app.modules.scraper.infrastructure.persistence.models import (
    CustomerEnrichmentStateModel,
    ScraperAdapterModel,
    ScraperRegistryAdapterHideModel,
    ScraperRunHistoryModel,
    ScraperRunLogModel,
)
from app.modules.system_admin.infrastructure.persistence.models import (
    DuplicateGroupMergeAuditLogModel,
    SystemDataOperationDatasetRowModel,
    SystemDataOperationRunModel,
)
from app.modules.template_contents.infrastructure.models import TemplateContentModel, TemplateContentTagModel
from app.modules.todos.infrastructure.persistence.models import (
    TodoModel,
    TodoOutcomeDefinitionModel,
    TodoStepModel,
    TodoWorklistStateModel,
)

PRODUCT_CLEANUP_POLICY_VERSION = "ol08.product-data-hard-delete.v1"
PRODUCT_GRACE_DAYS = 30


@dataclass(frozen=True, slots=True)
class ProductCleanupSpec:
    key: str
    sequence: int
    handler_name: str


PRODUCT_CLEANUP_PLAN: tuple[ProductCleanupSpec, ...] = (
    ProductCleanupSpec("communication_history", 10, "_delete_communication_history"),
    ProductCleanupSpec("operations", 20, "_delete_operations"),
    ProductCleanupSpec("scraper_relational_state", 30, "_delete_scraper_state"),
    ProductCleanupSpec("system_data_operations", 40, "_delete_system_data_operations"),
    ProductCleanupSpec("duplicate_merge_history", 50, "_delete_duplicate_merge_history"),
    ProductCleanupSpec("imports_data_integration", 60, "_delete_imports"),
    ProductCleanupSpec("quotes", 70, "_delete_quotes"),
    ProductCleanupSpec("todo_workflow", 80, "_delete_todo_workflow"),
    ProductCleanupSpec("activities", 90, "_delete_activities"),
    ProductCleanupSpec("participations", 100, "_delete_participations"),
    ProductCleanupSpec("contacts", 110, "_delete_contacts"),
    ProductCleanupSpec("customer_communications", 120, "_delete_customer_communications"),
    ProductCleanupSpec("customers", 130, "_delete_customers"),
    ProductCleanupSpec("fairs", 140, "_delete_fairs"),
    ProductCleanupSpec("quote_templates", 150, "_delete_quote_templates"),
    ProductCleanupSpec("template_contents", 160, "_delete_template_contents"),
    ProductCleanupSpec("cost_catalog", 170, "_delete_cost_catalog"),
    ProductCleanupSpec("mail_templates", 180, "_delete_mail_templates"),
    ProductCleanupSpec("email_accounts", 190, "_delete_email_accounts"),
)


class ClosureProductCleanupError(OrganizationClosureError):
    pass


class _CleanupBlocked(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


@dataclass(frozen=True, slots=True)
class ProductCleanupResult:
    items: tuple[OrganizationClosureProductCleanupItemModel, ...]
    processed_class_key: str | None
    completed: int
    blocked: int
    pending: int
    cleanup_complete: bool


class OrganizationClosureProductCleanupService:
    def __init__(
        self,
        repository: SqlAlchemyOrganizationClosureProductCleanupRepository,
        authorization: AuthorizationPort,
        lifecycle: OrganizationLifecycleGuard,
        audit: AuditPort,
        *,
        package_storage_root: Path | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._audit = audit
        self._package_storage_root = package_storage_root or DEFAULT_CLOSURE_PACKAGE_ROOT
        self._now_provider = now_provider or (lambda: datetime.now(tz=UTC))

    def reconcile(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> ProductCleanupResult:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_open_execution(organization_id, execution_id)
        snapshot = self._require_suspended_grace(organization_id)
        package, inventory = self._require_package_and_artifact_gates(organization_id, execution_id)
        self._require_credential_gate(organization_id, execution_id)

        items = self._repository.list_items(
            organization_id, execution_id, PRODUCT_CLEANUP_POLICY_VERSION
        )
        if not items:
            now = self._now()
            for spec in PRODUCT_CLEANUP_PLAN:
                self._repository.add_item(
                    OrganizationClosureProductCleanupItemModel(
                        id=uuid4(),
                        organization_id=organization_id,
                        closure_execution_id=execution_id,
                        policy_version=PRODUCT_CLEANUP_POLICY_VERSION,
                        suspension_episode_updated_at=snapshot.updated_at,
                        class_key=spec.key,
                        sequence=spec.sequence,
                        action="hard_delete",
                        status="pending",
                        attempt_count=0,
                        before_count=None,
                        deleted_count=None,
                        remaining_count=None,
                        failure_code=None,
                        failure_message=None,
                        actor_user_id=auth.user_id,
                        actor_session_id=auth.session_id,
                        created_at=now,
                        updated_at=now,
                        started_at=None,
                        completed_at=None,
                        last_attempt_at=None,
                    )
                )
            self._repository.flush()
            items = self._repository.list_items(
                organization_id, execution_id, PRODUCT_CLEANUP_POLICY_VERSION
            )

        self._validate_plan_and_episode(items, snapshot)
        current = next((item for item in items if item.status != "completed"), None)
        if current is None:
            return self._result(items, processed_class_key=None)

        spec = next(spec for spec in PRODUCT_CLEANUP_PLAN if spec.key == current.class_key)
        now = self._now()
        current.status = "pending"
        current.attempt_count += 1
        current.actor_user_id = auth.user_id
        current.actor_session_id = auth.session_id
        current.last_attempt_at = now
        current.updated_at = now
        current.started_at = current.started_at or now
        current.failure_code = None
        current.failure_message = None
        self._repository.flush()

        handler = getattr(self, spec.handler_name)
        try:
            with self._repository.nested():
                before_count, remaining_count = handler(
                    organization_id=organization_id,
                    execution_id=execution_id,
                    inventory=inventory,
                )
                if remaining_count != 0:
                    raise _CleanupBlocked(
                        "unexpected_residual_rows",
                        "Product-data class still has organization-owned rows after hard-delete attempt",
                    )
        except _CleanupBlocked as exc:
            self._mark_blocked(current, exc.code, exc.safe_message)
            self._record_class_audit(
                organization_id,
                execution_id,
                access_token,
                current,
                action="organization_closure.product_cleanup.blocked",
            )
            return self._result(
                self._repository.list_items(
                    organization_id, execution_id, PRODUCT_CLEANUP_POLICY_VERSION
                ),
                processed_class_key=current.class_key,
            )
        except IntegrityError:
            self._mark_blocked(
                current,
                "referential_integrity_blocked",
                "Product-data class hard delete was blocked by current referential integrity",
            )
            self._record_class_audit(
                organization_id,
                execution_id,
                access_token,
                current,
                action="organization_closure.product_cleanup.blocked",
            )
            return self._result(
                self._repository.list_items(
                    organization_id, execution_id, PRODUCT_CLEANUP_POLICY_VERSION
                ),
                processed_class_key=current.class_key,
            )

        current.status = "completed"
        current.before_count = before_count
        current.deleted_count = before_count - remaining_count
        current.remaining_count = remaining_count
        current.failure_code = None
        current.failure_message = None
        current.completed_at = self._now()
        current.updated_at = current.completed_at
        self._repository.flush()
        self._record_class_audit(
            organization_id,
            execution_id,
            access_token,
            current,
            action="organization_closure.product_cleanup.class_completed",
        )
        items = self._repository.list_items(
            organization_id, execution_id, PRODUCT_CLEANUP_POLICY_VERSION
        )
        return self._result(items, processed_class_key=current.class_key)

    def get(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> ProductCleanupResult:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_open_execution(organization_id, execution_id)
        items = self._repository.list_items(
            organization_id, execution_id, PRODUCT_CLEANUP_POLICY_VERSION
        )
        return self._result(items, processed_class_key=None)

    def _require_package_and_artifact_gates(
        self, organization_id: UUID, execution_id: UUID
    ):
        package = self._repository.get_package(
            organization_id, execution_id, PACKAGE_SCHEMA_VERSION
        )
        if package is None or package.integrity_verified_at is None or package.package_digest is None:
            raise ClosureExecutionConflictError(
                "Required canonical closure package lacks integrity verification evidence"
            )

        path = resolve_stored_locator(
            package.storage_locator, storage_root=self._package_storage_root
        )
        if package.status == "purged":
            if package.purged_at is None or path.exists() or path.is_symlink():
                raise ClosureExecutionConflictError(
                    "Purged closure package lacks positive non-existence evidence"
                )
        else:
            if package.status == "blocked" and package.failure_code not in {
                "package_purge_failed",
                "package_purge_integrity_mismatch",
            }:
                raise ClosureExecutionConflictError("Required closure package is blocked")
            if package.status not in {"integrity_verified", "expired", "blocked"}:
                raise ClosureExecutionConflictError(
                    "Required canonical closure package is not integrity verified"
                )
            try:
                verify_package(
                    path=path,
                    expected_package_digest=package.package_digest,
                    expected_manifest_digest=package.manifest_digest,
                )
            except ClosurePackageStorageError as exc:
                raise ClosureExecutionConflictError(
                    "Required canonical closure package integrity cannot be re-verified"
                ) from exc

        inventory = self._repository.list_inventory(
            organization_id, execution_id, package.id
        )
        for item in inventory:
            if item.ownership_class == "external_reference":
                accepted = item.cleanup_status == "not_applicable"
            elif item.ownership_class == "managed_product_artifact" and item.storage_kind == "managed_file":
                accepted = item.cleanup_status in {"purged", "already_absent"}
            elif item.ownership_class == "managed_product_artifact" and item.storage_kind == "embedded_database_bytes":
                accepted = item.cleanup_status in {
                    "relational_delete_required",
                    "already_absent",
                }
            else:
                accepted = False
            if not accepted:
                raise ClosureExecutionConflictError(
                    "OL08-E artifact cleanup evidence is incomplete or blocked"
                )
        return package, inventory

    def _require_credential_gate(self, organization_id: UUID, execution_id: UUID) -> None:
        dispositions = self._repository.list_credentials(organization_id, execution_id)
        if any(item.status != STATUS_DISPOSITION_COMPLETE for item in dispositions):
            raise ClosureExecutionConflictError(
                "OL08-C credential disposition is incomplete or blocked"
            )
        current_account_ids = set(self._repository.list_email_account_ids(organization_id))
        disposition_account_ids = {item.email_account_id for item in dispositions}
        if current_account_ids - disposition_account_ids:
            raise ClosureExecutionConflictError(
                "Current email-account product rows are missing closure credential disposition evidence"
            )

    def _validate_plan_and_episode(
        self,
        items: tuple[OrganizationClosureProductCleanupItemModel, ...],
        snapshot: OrganizationLifecycleSnapshot,
    ) -> None:
        expected = {(spec.key, spec.sequence) for spec in PRODUCT_CLEANUP_PLAN}
        actual = {(item.class_key, item.sequence) for item in items}
        if actual != expected or len(items) != len(PRODUCT_CLEANUP_PLAN):
            raise ClosureExecutionConflictError(
                "Durable product cleanup plan does not match the accepted policy version"
            )
        episode = self._aware(snapshot.updated_at)
        if any(self._aware(item.suspension_episode_updated_at) != episode for item in items):
            raise ClosureLifecyclePreconditionError(
                "Current Core suspension episode differs from the authorized destructive cleanup episode"
            )

    def _delete_communication_history(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        models = (MailSendOperationModel, FairEmailBatchModel)
        before = self._count_direct_models(models, organization_id)
        for model in models:
            self._repository.delete_direct(model, organization_id)
        self._repository.flush()
        return before, self._count_direct_models(models, organization_id)

    def _delete_operations(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        models = (OperationRunItemModel, OperationRunModel, OperationModel)
        before = self._count_direct_models(models, organization_id)
        for model in models:
            self._repository.delete_direct(model, organization_id)
        self._repository.flush()
        return before, self._count_direct_models(models, organization_id)

    def _delete_scraper_state(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        run_ids = self._repository.scoped_ids(ScraperRunHistoryModel, organization_id)
        log_before = (
            self._repository.count_where(ScraperRunLogModel, ScraperRunLogModel.run_id.in_(run_ids))
            if run_ids
            else 0
        )
        direct_models = (
            CustomerEnrichmentStateModel,
            ScraperRunHistoryModel,
            ScraperRegistryAdapterHideModel,
            ScraperAdapterModel,
        )
        before = log_before + self._count_direct_models(direct_models, organization_id)
        self._repository.delete_direct(CustomerEnrichmentStateModel, organization_id)
        if run_ids:
            self._repository.delete_where(ScraperRunLogModel, ScraperRunLogModel.run_id.in_(run_ids))
        self._repository.delete_direct(ScraperRunHistoryModel, organization_id)
        self._repository.delete_direct(ScraperRegistryAdapterHideModel, organization_id)
        self._repository.delete_direct(ScraperAdapterModel, organization_id)
        self._repository.flush()
        remaining_logs = (
            self._repository.count_where(ScraperRunLogModel, ScraperRunLogModel.run_id.in_(run_ids))
            if run_ids
            else 0
        )
        return before, remaining_logs + self._count_direct_models(direct_models, organization_id)

    def _delete_system_data_operations(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        runs = self._repository.list_direct(SystemDataOperationRunModel, organization_id)
        if any(run.output_files_json for run in runs):
            raise _CleanupBlocked(
                "unregistered_system_data_operation_artifact",
                "System data-operation rows reference persistent output files not registered by OL08-E",
            )
        models = (SystemDataOperationDatasetRowModel, SystemDataOperationRunModel)
        before = self._count_direct_models(models, organization_id)
        for model in models:
            self._repository.delete_direct(model, organization_id)
        self._repository.flush()
        return before, self._count_direct_models(models, organization_id)

    def _delete_duplicate_merge_history(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        before = self._repository.count_direct(DuplicateGroupMergeAuditLogModel, organization_id)
        self._repository.delete_direct(DuplicateGroupMergeAuditLogModel, organization_id)
        self._repository.flush()
        return before, self._repository.count_direct(DuplicateGroupMergeAuditLogModel, organization_id)

    def _delete_imports(
        self,
        *,
        organization_id: UUID,
        inventory: tuple[OrganizationClosureArtifactInventoryModel, ...],
        **_: object,
    ) -> tuple[int, int]:
        live_byte_batches = set(
            self._repository.ids_where(
                ImportBatchModel,
                ImportBatchModel.organization_id == organization_id,
                ImportBatchModel.stored_file_content.is_not(None),
            )
        )
        embedded = {
            item.owner_id: item
            for item in inventory
            if item.artifact_class == "import_upload"
            and item.owner_type == "import_batch"
            and item.storage_kind == "embedded_database_bytes"
        }
        for batch_id in live_byte_batches:
            item = embedded.get(str(batch_id))
            if item is None or item.cleanup_status != "relational_delete_required":
                raise _CleanupBlocked(
                    "import_artifact_evidence_missing",
                    "Import upload bytes lack matching OL08-E relational-delete authorization evidence",
                )

        models = (ImportJobModel, ImportRowModel, ImportBatchModel, ImportTemplateModel)
        before = self._count_direct_models(models, organization_id)
        for model in models:
            self._repository.delete_direct(model, organization_id)
        self._repository.flush()
        remaining = self._count_direct_models(models, organization_id)
        if remaining == 0:
            now = self._now()
            for item in embedded.values():
                if item.cleanup_status == "relational_delete_required":
                    item.cleanup_status = "already_absent"
                    item.nonexistence_verified_at = now
                    item.cleanup_failure_code = None
                    item.cleanup_failure_message = None
            self._repository.flush()
        return before, remaining

    def _delete_quotes(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        before = self._repository.count_direct(QuoteModel, organization_id)
        self._repository.delete_direct(QuoteModel, organization_id)
        self._repository.flush()
        return before, self._repository.count_direct(QuoteModel, organization_id)

    def _delete_todo_workflow(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        models = (TodoStepModel, TodoWorklistStateModel, TodoOutcomeDefinitionModel, TodoModel)
        before = self._count_direct_models(models, organization_id)
        todo_ids = self._repository.scoped_ids(TodoModel, organization_id)
        self._repository.delete_direct(TodoStepModel, organization_id)
        self._repository.delete_direct(TodoWorklistStateModel, organization_id)
        if todo_ids:
            # Production migration 0075 historically promoted old FKs to CASCADE.
            # Null the activity edge explicitly so todo deletion never silently
            # substitutes cascade for the later activity-class evidence step.
            self._repository.update_where(
                ActivityModel,
                {"todo_id": None},
                ActivityModel.organization_id == organization_id,
                ActivityModel.todo_id.in_(todo_ids),
            )
        self._repository.delete_direct(TodoModel, organization_id)
        self._repository.delete_direct(TodoOutcomeDefinitionModel, organization_id)
        self._repository.flush()
        return before, self._count_direct_models(models, organization_id)

    def _delete_activities(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        before = self._repository.count_direct(ActivityModel, organization_id)
        self._repository.delete_direct(ActivityModel, organization_id)
        self._repository.flush()
        return before, self._repository.count_direct(ActivityModel, organization_id)

    def _delete_participations(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        before = self._repository.count_direct(CustomerFairParticipationModel, organization_id)
        self._repository.delete_direct(CustomerFairParticipationModel, organization_id)
        self._repository.flush()
        return before, self._repository.count_direct(CustomerFairParticipationModel, organization_id)

    def _delete_contacts(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        before = self._repository.count_direct(ContactModel, organization_id)
        self._repository.delete_direct(ContactModel, organization_id)
        self._repository.flush()
        return before, self._repository.count_direct(ContactModel, organization_id)

    def _delete_customer_communications(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        models = (CustomerEmailModel, CustomerPhoneModel, CustomerWebsiteModel)
        before = self._count_direct_models(models, organization_id)
        for model in models:
            self._repository.delete_direct(model, organization_id)
        self._repository.flush()
        return before, self._count_direct_models(models, organization_id)

    def _delete_customers(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        before = self._repository.count_direct(CustomerModel, organization_id)
        self._repository.delete_direct(CustomerModel, organization_id)
        self._repository.flush()
        return before, self._repository.count_direct(CustomerModel, organization_id)

    def _delete_fairs(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        before = self._repository.count_direct(FairModel, organization_id)
        self._repository.delete_direct(FairModel, organization_id)
        self._repository.flush()
        return before, self._repository.count_direct(FairModel, organization_id)

    def _delete_quote_templates(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        template_ids = self._repository.scoped_ids(QuoteTemplateModel, organization_id)
        version_before = (
            self._repository.count_where(
                QuoteTemplateVersionModel,
                QuoteTemplateVersionModel.template_id.in_(template_ids),
            )
            if template_ids
            else 0
        )
        before = self._repository.count_direct(QuoteTemplateModel, organization_id) + version_before
        if template_ids:
            self._repository.update_where(
                QuoteTemplateModel,
                {"current_version_id": None},
                QuoteTemplateModel.organization_id == organization_id,
            )
            self._repository.delete_where(
                QuoteTemplateVersionModel,
                QuoteTemplateVersionModel.template_id.in_(template_ids),
            )
        self._repository.delete_direct(QuoteTemplateModel, organization_id)
        self._repository.flush()
        remaining_versions = (
            self._repository.count_where(
                QuoteTemplateVersionModel,
                QuoteTemplateVersionModel.template_id.in_(template_ids),
            )
            if template_ids
            else 0
        )
        return before, self._repository.count_direct(QuoteTemplateModel, organization_id) + remaining_versions

    def _delete_template_contents(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        models = (TemplateContentModel, TemplateContentTagModel)
        before = self._count_direct_models(models, organization_id)
        self._repository.delete_direct(TemplateContentModel, organization_id)
        self._repository.delete_direct(TemplateContentTagModel, organization_id)
        self._repository.flush()
        return before, self._count_direct_models(models, organization_id)

    def _delete_cost_catalog(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        models = (CostProductModel, CostCategoryModel)
        before = self._count_direct_models(models, organization_id)
        self._repository.delete_direct(CostProductModel, organization_id)
        self._repository.delete_direct(CostCategoryModel, organization_id)
        self._repository.flush()
        return before, self._count_direct_models(models, organization_id)

    def _delete_mail_templates(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        before = self._repository.count_direct(MailTemplateModel, organization_id)
        self._repository.delete_direct(MailTemplateModel, organization_id)
        self._repository.flush()
        return before, self._repository.count_direct(MailTemplateModel, organization_id)

    def _delete_email_accounts(self, *, organization_id: UUID, **_: object) -> tuple[int, int]:
        account_ids = self._repository.list_email_account_ids(organization_id)
        child_before = 0
        if account_ids:
            child_before = self._repository.count_where(
                EmailAccountSmtpConfigModel,
                EmailAccountSmtpConfigModel.email_account_id.in_(account_ids),
            ) + self._repository.count_where(
                EmailAccountProviderConfigModel,
                EmailAccountProviderConfigModel.email_account_id.in_(account_ids),
            )
        before = len(account_ids) + child_before
        if account_ids:
            self._repository.delete_where(
                EmailAccountSmtpConfigModel,
                EmailAccountSmtpConfigModel.email_account_id.in_(account_ids),
            )
            self._repository.delete_where(
                EmailAccountProviderConfigModel,
                EmailAccountProviderConfigModel.email_account_id.in_(account_ids),
            )
        self._repository.delete_direct(EmailAccountModel, organization_id)
        self._repository.flush()
        remaining_ids = self._repository.list_email_account_ids(organization_id)
        remaining = len(remaining_ids)
        if remaining_ids:
            remaining += self._repository.count_where(
                EmailAccountSmtpConfigModel,
                EmailAccountSmtpConfigModel.email_account_id.in_(remaining_ids),
            ) + self._repository.count_where(
                EmailAccountProviderConfigModel,
                EmailAccountProviderConfigModel.email_account_id.in_(remaining_ids),
            )
        return before, remaining

    def _require_open_execution(self, organization_id: UUID, execution_id: UUID) -> None:
        execution = self._repository.get_execution(organization_id, execution_id)
        if execution is None or execution.closed_at is not None or execution.status != STATUS_IN_PROGRESS:
            raise ClosureExecutionNotFoundError("Open in-progress closure execution not found")

    def _require_suspended_grace(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        try:
            snapshot = self._lifecycle.get_snapshot(organization_id)
        except OrganizationLifecycleUnavailableError as exc:
            raise ClosureLifecycleUnavailableError(
                "Organization lifecycle authority unavailable"
            ) from exc
        if snapshot.status != "suspended" or snapshot.is_deleted:
            raise ClosureLifecyclePreconditionError(
                f"Organization must remain suspended for product cleanup: {snapshot.status}"
            )
        if self._now() < self._aware(snapshot.updated_at) + timedelta(days=PRODUCT_GRACE_DAYS):
            raise ClosureLifecyclePreconditionError(
                "Organization suspension grace has not completed for product cleanup"
            )
        return snapshot

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
                "Product cleanup authorization authority unavailable"
            ) from exc
        if not allowed:
            raise ClosurePermissionDeniedError("Platform SuperAdmin authority required")

    def _mark_blocked(
        self,
        item: OrganizationClosureProductCleanupItemModel,
        code: str,
        message: str,
    ) -> None:
        item.status = "blocked"
        item.failure_code = code[:128]
        item.failure_message = message
        item.remaining_count = None
        item.completed_at = None
        item.updated_at = self._now()
        self._repository.flush()

    def _record_class_audit(
        self,
        organization_id: UUID,
        execution_id: UUID,
        access_token: str,
        item: OrganizationClosureProductCleanupItemModel,
        *,
        action: str,
    ) -> None:
        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action=action,
            resource_type="organization_closure_product_cleanup",
            resource_id=str(item.id),
            new_values={
                "policy_version": item.policy_version,
                "class_key": item.class_key,
                "status": item.status,
                "action": item.action,
                "attempt_count": item.attempt_count,
                "before_count": item.before_count,
                "deleted_count": item.deleted_count,
                "remaining_count": item.remaining_count,
                "failure_code": item.failure_code,
            },
            metadata={
                "authority": "system",
                "ol08_slice": "OL08-D",
                "closure_execution_id": str(execution_id),
                "suspension_episode_updated_at": self._aware(
                    item.suspension_episode_updated_at
                ).isoformat(),
            },
        )

    def _count_direct_models(self, models: tuple[type, ...], organization_id: UUID) -> int:
        return sum(self._repository.count_direct(model, organization_id) for model in models)

    @staticmethod
    def _result(
        items: tuple[OrganizationClosureProductCleanupItemModel, ...],
        *,
        processed_class_key: str | None,
    ) -> ProductCleanupResult:
        completed = sum(item.status == "completed" for item in items)
        blocked = sum(item.status == "blocked" for item in items)
        pending = sum(item.status == "pending" for item in items)
        return ProductCleanupResult(
            items=items,
            processed_class_key=processed_class_key,
            completed=completed,
            blocked=blocked,
            pending=pending,
            cleanup_complete=bool(items) and completed == len(PRODUCT_CLEANUP_PLAN),
        )

    def _now(self) -> datetime:
        return self._aware(self._now_provider())

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
