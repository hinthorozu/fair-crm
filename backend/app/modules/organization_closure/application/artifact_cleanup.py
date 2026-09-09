from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Callable
from uuid import UUID

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleSnapshot,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.organization_closure.application.closure_package import PACKAGE_SCHEMA_VERSION
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
from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureArtifactInventoryModel,
    OrganizationClosurePackageModel,
)
from app.modules.organization_closure.infrastructure.package_repository import (
    SqlAlchemyOrganizationClosurePackageRepository,
)
from app.modules.organization_closure.infrastructure.package_storage import (
    DEFAULT_CLOSURE_PACKAGE_ROOT,
    ClosurePackageStorageError,
    resolve_stored_locator,
    verify_package,
)
from app.modules.quote_templates.infrastructure.logo_storage import (
    LOGO_STORAGE_ROOT,
    resolve_logo_file,
)
from app.modules.scraper.infrastructure.handoff_storage import (
    DEFAULT_HANDOFF_DIR,
    is_safe_handoff_artifact_path,
)

SOURCE_GRACE_DAYS = 30
TERMINAL_FILE_CLEANUP_STATUSES = {"purged", "already_absent"}


class ClosureArtifactCleanupError(OrganizationClosureError):
    pass


@dataclass(frozen=True, slots=True)
class SourceArtifactCleanupResult:
    package: OrganizationClosurePackageModel
    items: tuple[OrganizationClosureArtifactInventoryModel, ...]
    total: int
    purged: int
    already_absent: int
    not_applicable: int
    relational_delete_required: int
    blocked: int
    file_cleanup_complete: bool


class _ArtifactBlocked(RuntimeError):
    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class OrganizationClosureArtifactCleanupService:
    def __init__(
        self,
        repository: SqlAlchemyOrganizationClosurePackageRepository,
        authorization: AuthorizationPort,
        lifecycle: OrganizationLifecycleGuard,
        audit: AuditPort,
        *,
        package_storage_root: Path | None = None,
        logo_storage_root: Path | None = None,
        handoff_storage_root: Path | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._audit = audit
        self._package_storage_root = package_storage_root or DEFAULT_CLOSURE_PACKAGE_ROOT
        self._logo_storage_root = logo_storage_root or LOGO_STORAGE_ROOT
        self._handoff_storage_root = handoff_storage_root or DEFAULT_HANDOFF_DIR
        self._now_provider = now_provider or (lambda: datetime.now(tz=UTC))

    def purge_source_artifacts(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> SourceArtifactCleanupResult:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_open_execution(organization_id, execution_id)
        snapshot = self._require_suspended_grace(organization_id)
        package = self._require_package_gate(organization_id, execution_id)
        items = self._repository.list_inventory(organization_id, execution_id, package.id)

        for item in items:
            self._reconcile_source_item(item, organization_id=organization_id)
        self._repository.flush()

        counts = self._counts(items)
        file_items = tuple(
            item
            for item in items
            if item.ownership_class == "managed_product_artifact"
            and item.storage_kind == "managed_file"
        )
        file_cleanup_complete = all(
            item.cleanup_status in TERMINAL_FILE_CLEANUP_STATUSES for item in file_items
        )

        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="organization_closure.artifacts.source_cleanup_reconciled",
            resource_type="organization_closure_package",
            resource_id=str(package.id),
            new_values={
                **counts,
                "file_cleanup_complete": file_cleanup_complete,
            },
            metadata={
                "authority": "system",
                "ol08_slice": "OL08-E2",
                "closure_execution_id": str(execution_id),
                "suspension_episode_updated_at": snapshot.updated_at.isoformat(),
                "source_grace_days": SOURCE_GRACE_DAYS,
            },
        )
        return SourceArtifactCleanupResult(
            package=package,
            items=items,
            total=len(items),
            file_cleanup_complete=file_cleanup_complete,
            **counts,
        )

    def purge_package(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosurePackageModel:
        self._require_system_authority(organization_id, auth, access_token)
        package = self._repository.get_package(
            organization_id,
            execution_id,
            PACKAGE_SCHEMA_VERSION,
        )
        if package is None:
            raise ClosureExecutionNotFoundError("Closure package not found")
        if package.status == "purged":
            self._verify_package_absent(package)
            return package
        if (
            package.integrity_verified_at is None
            or package.package_digest is None
            or package.ready_at is None
            or package.expires_at is None
        ):
            raise ClosureExecutionConflictError(
                "Closure package lacks accepted integrity/readiness evidence for purge"
            )

        now = self._now()
        reason = "retention_expired" if now >= self._aware(package.expires_at) else None
        if reason is None:
            snapshot = self._get_lifecycle_snapshot(organization_id)
            if snapshot.status == "active" and not snapshot.is_deleted:
                reason = "closure_cancelled_by_reactivation"
            else:
                raise ClosureExecutionConflictError(
                    "Closure package retention window has not expired"
                )

        if package.status not in {"integrity_verified", "expired", "blocked"}:
            raise ClosureExecutionConflictError("Closure package state is not purge eligible")
        if package.status == "blocked" and package.failure_code not in {
            "package_purge_failed",
            "package_purge_integrity_mismatch",
        }:
            raise ClosureExecutionConflictError("Blocked closure package is not purge-retry eligible")

        package.attempt_count += 1
        package.actor_user_id = auth.user_id
        package.actor_session_id = auth.session_id
        package.updated_at = now
        package.failure_code = None
        package.failure_message = None

        path = resolve_stored_locator(
            package.storage_locator,
            storage_root=self._package_storage_root,
        )
        try:
            if path.is_symlink():
                raise _ArtifactBlocked(
                    "package_purge_integrity_mismatch",
                    "Canonical closure package locator resolved to an unsafe symlink",
                )
            if path.exists():
                verify_package(
                    path=path,
                    expected_package_digest=package.package_digest,
                    expected_manifest_digest=package.manifest_digest,
                )
                path.unlink()
            if path.exists() or path.is_symlink():
                raise _ArtifactBlocked(
                    "package_purge_failed",
                    "Canonical closure package non-existence could not be verified",
                )
        except ClosurePackageStorageError as exc:
            _ = exc
            return self._block_package_purge(
                package,
                code="package_purge_integrity_mismatch",
                message="Canonical closure package integrity could not be verified before purge",
                organization_id=organization_id,
                access_token=access_token,
            )
        except OSError as exc:
            _ = exc
            return self._block_package_purge(
                package,
                code="package_purge_failed",
                message="Canonical closure package deletion or non-existence verification failed",
                organization_id=organization_id,
                access_token=access_token,
            )
        except _ArtifactBlocked as exc:
            return self._block_package_purge(
                package,
                code=exc.code,
                message=exc.safe_message,
                organization_id=organization_id,
                access_token=access_token,
            )

        package.status = "purged"
        package.purged_at = now
        package.updated_at = now
        package.failure_code = None
        package.failure_message = None
        self._repository.flush()
        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="organization_closure.package.purged",
            resource_type="organization_closure_package",
            resource_id=str(package.id),
            new_values={
                "status": "purged",
                "purged_at": now.isoformat(),
                "purge_reason": reason,
            },
            metadata={
                "authority": "system",
                "ol08_slice": "OL08-E2",
                "closure_execution_id": str(execution_id),
                "package_digest": package.package_digest,
            },
        )
        return package

    def _reconcile_source_item(
        self,
        item: OrganizationClosureArtifactInventoryModel,
        *,
        organization_id: UUID,
    ) -> None:
        if item.cleanup_status in TERMINAL_FILE_CLEANUP_STATUSES | {"not_applicable"}:
            return
        now = self._now()
        item.cleanup_attempt_count += 1
        item.cleanup_last_attempt_at = now
        item.cleanup_failure_code = None
        item.cleanup_failure_message = None

        if item.ownership_class == "external_reference":
            item.cleanup_status = "not_applicable"
            return
        if item.ownership_class != "managed_product_artifact":
            self._block_item(
                item,
                code="unknown_artifact_ownership_class",
                message="Artifact ownership class is not registered for closure cleanup",
            )
            return

        if item.storage_kind == "embedded_database_bytes":
            self._reconcile_embedded_bytes(item, organization_id=organization_id, now=now)
            return
        if item.storage_kind != "managed_file":
            self._block_item(
                item,
                code="unknown_artifact_storage_kind",
                message="Artifact storage kind is not registered for closure cleanup",
            )
            return

        try:
            path = self._resolve_managed_file(item, organization_id=organization_id)
            status = self._strict_delete_managed_file(path, item=item)
        except _ArtifactBlocked as exc:
            self._block_item(item, code=exc.code, message=exc.safe_message)
            return
        item.cleanup_status = status
        item.nonexistence_verified_at = now

    def _reconcile_embedded_bytes(
        self,
        item: OrganizationClosureArtifactInventoryModel,
        *,
        organization_id: UUID,
        now: datetime,
    ) -> None:
        if item.artifact_class != "import_upload" or item.owner_type != "import_batch":
            self._block_item(
                item,
                code="unknown_embedded_artifact",
                message="Embedded artifact class is not registered for closure cleanup",
            )
            return
        locator = item.locator_json
        batch_token = locator.get("batch_id")
        field = locator.get("field")
        try:
            batch_id = UUID(str(batch_token))
        except (TypeError, ValueError):
            self._block_item(
                item,
                code="invalid_import_artifact_locator",
                message="Import artifact locator is invalid",
            )
            return
        if str(batch_id) != item.owner_id or field != "stored_file_content":
            self._block_item(
                item,
                code="invalid_import_artifact_locator",
                message="Import artifact locator does not match durable inventory ownership",
            )
            return
        batch = self._repository.get_import_batch(organization_id, batch_id)
        if batch is None or batch.stored_file_content is None:
            item.cleanup_status = "already_absent"
            item.nonexistence_verified_at = now
            return
        item.cleanup_status = "relational_delete_required"
        item.nonexistence_verified_at = None

    def _resolve_managed_file(
        self,
        item: OrganizationClosureArtifactInventoryModel,
        *,
        organization_id: UUID,
    ) -> Path:
        if item.artifact_class == "quote_template_logo":
            filename = item.locator_json.get("filename")
            if not isinstance(filename, str):
                raise _ArtifactBlocked(
                    "invalid_managed_logo_locator",
                    "Managed logo locator is invalid",
                )
            organization_root = self._logo_storage_root / str(organization_id)
            if organization_root.is_symlink():
                raise _ArtifactBlocked(
                    "unsafe_managed_logo_root",
                    "Managed logo organization root is an unsafe symlink",
                )
            path = resolve_logo_file(
                organization_id,
                filename,
                storage_root=self._logo_storage_root,
            )
            if path is None:
                raise _ArtifactBlocked(
                    "invalid_managed_logo_locator",
                    "Managed logo locator escapes accepted organization ownership",
                )
            return path

        if item.artifact_class == "scraper_handoff":
            locator = item.locator_json
            run_token = locator.get("run_id")
            relative_path = locator.get("relative_path")
            try:
                run_id = UUID(str(run_token))
            except (TypeError, ValueError) as exc:
                raise _ArtifactBlocked(
                    "invalid_scraper_handoff_locator",
                    "Scraper handoff run ownership is invalid",
                ) from exc
            if str(run_id) != item.owner_id or not isinstance(relative_path, str):
                raise _ArtifactBlocked(
                    "invalid_scraper_handoff_locator",
                    "Scraper handoff locator does not match durable inventory ownership",
                )
            if self._handoff_storage_root.is_symlink():
                raise _ArtifactBlocked(
                    "unsafe_scraper_handoff_root",
                    "Scraper handoff storage root is an unsafe symlink",
                )
            candidate = self._handoff_storage_root / relative_path
            if not is_safe_handoff_artifact_path(
                candidate,
                run_id=run_id,
                base_dir=self._handoff_storage_root,
            ):
                raise _ArtifactBlocked(
                    "invalid_scraper_handoff_locator",
                    "Scraper handoff locator escapes accepted run ownership",
                )
            return candidate.resolve()

        raise _ArtifactBlocked(
            "unknown_managed_artifact_class",
            "Managed artifact class is not registered for closure cleanup",
        )

    def _strict_delete_managed_file(
        self,
        path: Path,
        *,
        item: OrganizationClosureArtifactInventoryModel,
    ) -> str:
        if path.is_symlink():
            raise _ArtifactBlocked(
                "unsafe_artifact_symlink",
                "Managed artifact locator resolved to an unsafe symlink",
            )
        if not path.exists():
            return "already_absent"
        if not path.is_file():
            raise _ArtifactBlocked(
                "unsafe_artifact_type",
                "Managed artifact locator is not a regular file",
            )
        if item.content_digest:
            try:
                current_digest = sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                raise _ArtifactBlocked(
                    "artifact_read_failed",
                    "Managed artifact cannot be verified before deletion",
                ) from exc
            if current_digest != item.content_digest:
                raise _ArtifactBlocked(
                    "artifact_content_changed",
                    "Managed artifact bytes changed after package inventory capture",
                )
        try:
            path.unlink()
        except OSError as exc:
            raise _ArtifactBlocked(
                "artifact_delete_failed",
                "Managed artifact deletion failed",
            ) from exc
        if path.exists() or path.is_symlink():
            raise _ArtifactBlocked(
                "artifact_nonexistence_unverified",
                "Managed artifact non-existence could not be verified",
            )
        return "purged"

    def _require_package_gate(
        self,
        organization_id: UUID,
        execution_id: UUID,
    ) -> OrganizationClosurePackageModel:
        package = self._repository.get_package(
            organization_id,
            execution_id,
            PACKAGE_SCHEMA_VERSION,
        )
        if package is None:
            raise ClosureExecutionConflictError(
                "Required canonical closure package does not exist"
            )
        if package.integrity_verified_at is None or package.package_digest is None:
            raise ClosureExecutionConflictError(
                "Required canonical closure package lacks integrity verification evidence"
            )
        if package.status == "purged":
            if package.purged_at is None:
                raise ClosureExecutionConflictError(
                    "Purged closure package lacks positive purge evidence"
                )
            self._verify_package_absent(package)
            return package
        if package.status == "blocked" and package.failure_code not in {
            "package_purge_failed",
            "package_purge_integrity_mismatch",
        }:
            raise ClosureExecutionConflictError(
                "Required canonical closure package is blocked"
            )
        if package.status not in {"integrity_verified", "expired", "blocked"}:
            raise ClosureExecutionConflictError(
                "Required canonical closure package is not integrity verified"
            )
        path = resolve_stored_locator(
            package.storage_locator,
            storage_root=self._package_storage_root,
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
        return package

    def _verify_package_absent(self, package: OrganizationClosurePackageModel) -> None:
        path = resolve_stored_locator(
            package.storage_locator,
            storage_root=self._package_storage_root,
        )
        if path.exists() or path.is_symlink():
            raise ClosureExecutionConflictError(
                "Purged closure package bytes unexpectedly still exist"
            )

    def _require_open_execution(self, organization_id: UUID, execution_id: UUID) -> None:
        execution = self._repository.get_execution(organization_id, execution_id)
        if (
            execution is None
            or execution.closed_at is not None
            or execution.status != STATUS_IN_PROGRESS
        ):
            raise ClosureExecutionNotFoundError("Open in-progress closure execution not found")

    def _require_suspended_grace(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        snapshot = self._get_lifecycle_snapshot(organization_id)
        if snapshot.status != "suspended" or snapshot.is_deleted:
            raise ClosureLifecyclePreconditionError(
                f"Organization must remain suspended for source artifact cleanup: {snapshot.status}"
            )
        grace_deadline = self._aware(snapshot.updated_at) + timedelta(days=SOURCE_GRACE_DAYS)
        if self._now() < grace_deadline:
            raise ClosureLifecyclePreconditionError(
                "Organization suspension grace has not completed for source artifact cleanup"
            )
        return snapshot

    def _get_lifecycle_snapshot(self, organization_id: UUID) -> OrganizationLifecycleSnapshot:
        try:
            return self._lifecycle.get_snapshot(organization_id)
        except OrganizationLifecycleUnavailableError as exc:
            raise ClosureLifecycleUnavailableError(
                "Organization lifecycle authority unavailable"
            ) from exc

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
                "Closure artifact cleanup authorization authority unavailable"
            ) from exc
        if not allowed:
            raise ClosurePermissionDeniedError("Platform SuperAdmin authority required")

    def _block_item(
        self,
        item: OrganizationClosureArtifactInventoryModel,
        *,
        code: str,
        message: str,
    ) -> None:
        item.cleanup_status = "blocked"
        item.cleanup_failure_code = code[:128]
        item.cleanup_failure_message = message
        item.nonexistence_verified_at = None

    def _block_package_purge(
        self,
        package: OrganizationClosurePackageModel,
        *,
        code: str,
        message: str,
        organization_id: UUID,
        access_token: str,
    ) -> OrganizationClosurePackageModel:
        package.status = "blocked"
        package.failure_code = code[:128]
        package.failure_message = message
        package.updated_at = self._now()
        self._repository.flush()
        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="organization_closure.package.purge_blocked",
            resource_type="organization_closure_package",
            resource_id=str(package.id),
            new_values={
                "status": "blocked",
                "failure_code": package.failure_code,
                "attempt_count": package.attempt_count,
            },
            metadata={
                "authority": "system",
                "ol08_slice": "OL08-E2",
                "closure_execution_id": str(package.closure_execution_id),
            },
        )
        return package

    @staticmethod
    def _counts(
        items: tuple[OrganizationClosureArtifactInventoryModel, ...],
    ) -> dict[str, int]:
        return {
            "purged": sum(item.cleanup_status == "purged" for item in items),
            "already_absent": sum(
                item.cleanup_status == "already_absent" for item in items
            ),
            "not_applicable": sum(
                item.cleanup_status == "not_applicable" for item in items
            ),
            "relational_delete_required": sum(
                item.cleanup_status == "relational_delete_required" for item in items
            ),
            "blocked": sum(item.cleanup_status == "blocked" for item in items),
        }

    def _now(self) -> datetime:
        return self._aware(self._now_provider())

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
