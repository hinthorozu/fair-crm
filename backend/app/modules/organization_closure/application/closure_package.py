from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.integrations.kyrox_core.lifecycle import (
    OrganizationLifecycleGuard,
    OrganizationLifecycleUnavailableError,
)
from app.integrations.kyrox_core.ports import AuditPort, AuthContext, AuthorizationPort
from app.modules.organization_closure.application.export_planner import (
    DATA_CLASS_REGISTRY,
    EXPORT_DISPOSITION_REQUIRED,
    EXPORT_SCHEMA_VERSION,
    EXPORT_STATUS_PLANNED,
    INCLUDED,
    SourceSpec,
    validate_secret_exclusion_registry,
)
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
    PackageMember,
    canonical_manifest_bytes,
    inspect_package,
    resolve_package_path,
    resolve_stored_locator,
    verify_package,
    write_immutable_package,
)
from app.modules.quote_templates.infrastructure.logo_storage import (
    LOGO_API_PREFIX,
    LOGO_MEDIA_TYPES,
    LOGO_STORAGE_ROOT,
    normalize_logo_url,
    resolve_logo_file,
)
from app.modules.scraper.infrastructure.handoff_storage import (
    DEFAULT_HANDOFF_DIR,
    is_safe_handoff_artifact_path,
    resolve_handoff_excel_path,
    resolve_handoff_path,
)

PACKAGE_SCHEMA_VERSION = "ol08.closure-package.v1"
INVENTORY_SCHEMA_VERSION = "ol08.artifact-inventory.v1"
PACKAGE_RETENTION_DAYS = 30
STATUS_PLANNED = "planned"
STATUS_GENERATING = "generating"
STATUS_READY = "ready"
STATUS_INTEGRITY_VERIFIED = "integrity_verified"
STATUS_BLOCKED = "blocked"


class ClosurePackageError(OrganizationClosureError):
    pass


class ClosurePackageNotFoundError(ClosureExecutionNotFoundError):
    pass


@dataclass(frozen=True, slots=True)
class ArtifactBlueprint:
    artifact_key: str
    artifact_class: str
    ownership_class: str
    owner_type: str
    owner_id: str
    storage_kind: str
    package_disposition: str
    cleanup_action: str
    locator_json: dict[str, Any]
    package_entry: str | None
    byte_size: int | None
    content_digest: str | None


class _PackageBuildBlocked(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        + b"\n"
    )


def _canonical_identity_digest(values: list[str]) -> str:
    return sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise _PackageBuildBlocked(
            "unregistered_binary_field",
            "Portable structured export encountered binary bytes outside the accepted artifact registry",
        )
    raise _PackageBuildBlocked(
        "unsupported_portable_value",
        "Portable structured export encountered an unsupported value type",
    )


def _row_payload(row: Any, source: SourceSpec) -> dict[str, Any]:
    excluded = set(source.field_exclusions)
    return {
        column.name: _json_value(getattr(row, column.name))
        for column in row.__table__.columns
        if column.name not in excluded
    }


def _member_registry(members: list[PackageMember]) -> list[dict[str, Any]]:
    return [
        {
            "path": member.path,
            "sha256": sha256(member.content).hexdigest(),
            "byte_size": len(member.content),
        }
        for member in sorted(members, key=lambda item: item.path)
    ]


def _parse_utc_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise _PackageBuildBlocked(
            "canonical_package_manifest_invalid",
            f"Canonical package {field} is missing or invalid",
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise _PackageBuildBlocked(
            "canonical_package_manifest_invalid",
            f"Canonical package {field} is missing or invalid",
        ) from exc
    if parsed.tzinfo is None:
        raise _PackageBuildBlocked(
            "canonical_package_manifest_invalid",
            f"Canonical package {field} is missing or invalid",
        )
    return parsed.astimezone(UTC)


class OrganizationClosurePackageService:
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
    ) -> None:
        self._repository = repository
        self._authorization = authorization
        self._lifecycle = lifecycle
        self._audit = audit
        self._package_storage_root = package_storage_root or DEFAULT_CLOSURE_PACKAGE_ROOT
        self._logo_storage_root = logo_storage_root or LOGO_STORAGE_ROOT
        self._handoff_storage_root = handoff_storage_root or DEFAULT_HANDOFF_DIR

    def generate(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> OrganizationClosurePackageModel:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_suspended(organization_id)
        execution = self._require_open_execution(organization_id, execution_id)
        plan = self._repository.get_export_plan(
            organization_id,
            execution_id,
            EXPORT_SCHEMA_VERSION,
        )
        if plan is None:
            raise ClosureExecutionConflictError(
                "Required closure export plan must exist before package generation"
            )
        if plan.disposition != EXPORT_DISPOSITION_REQUIRED or plan.status != EXPORT_STATUS_PLANNED:
            raise ClosureExecutionConflictError("Closure export plan is not eligible for package generation")

        existing = self._repository.get_package(
            organization_id,
            execution_id,
            PACKAGE_SCHEMA_VERSION,
        )
        if existing is not None and existing.status == STATUS_INTEGRITY_VERIFIED:
            return existing
        if existing is not None and existing.status in {"expired", "purged"}:
            raise ClosureExecutionConflictError(
                "Expired or purged canonical closure package cannot be regenerated"
            )

        now = datetime.now(tz=UTC)
        package_id = uuid5(
            NAMESPACE_URL,
            f"fair-crm:closure-package:{organization_id}:{execution_id}:{PACKAGE_SCHEMA_VERSION}",
        )
        _, storage_locator = resolve_package_path(
            organization_id,
            execution_id,
            package_id,
            storage_root=self._package_storage_root,
        )
        is_new = existing is None
        package = existing or OrganizationClosurePackageModel(
            id=package_id,
            organization_id=organization_id,
            closure_execution_id=execution_id,
            export_plan_id=plan.id,
            schema_version=PACKAGE_SCHEMA_VERSION,
            inventory_schema_version=INVENTORY_SCHEMA_VERSION,
            status=STATUS_PLANNED,
            storage_locator=storage_locator,
            manifest_json={},
            manifest_digest=sha256(canonical_manifest_bytes({})).hexdigest(),
            package_digest=None,
            byte_size=None,
            attempt_count=1,
            failure_code=None,
            failure_message=None,
            actor_user_id=auth.user_id,
            actor_session_id=auth.session_id,
            created_at=now,
            updated_at=now,
            ready_at=None,
            integrity_verified_at=None,
            expires_at=None,
        )
        if is_new:
            self._repository.add_package(package)
        else:
            package.attempt_count += 1
            package.actor_user_id = auth.user_id
            package.actor_session_id = auth.session_id
            package.updated_at = now
        package.status = STATUS_GENERATING
        package.failure_code = None
        package.failure_message = None
        self._repository.clear_inventory(package.id)

        try:
            validate_secret_exclusion_registry()
            members, data_class_manifest = self._build_structured_members(
                organization_id=organization_id,
                plan_manifest=plan.manifest_json,
            )
            artifacts = self._build_artifact_inventory(
                organization_id=organization_id,
                execution_id=execution_id,
                package_id=package.id,
                members=members,
            )
            for artifact in artifacts:
                self._repository.add_inventory(
                    OrganizationClosureArtifactInventoryModel(
                        id=uuid4(),
                        package_id=package.id,
                        closure_execution_id=execution_id,
                        organization_id=organization_id,
                        inventory_schema_version=INVENTORY_SCHEMA_VERSION,
                        artifact_key=artifact.artifact_key,
                        artifact_class=artifact.artifact_class,
                        ownership_class=artifact.ownership_class,
                        owner_type=artifact.owner_type,
                        owner_id=artifact.owner_id,
                        storage_kind=artifact.storage_kind,
                        package_disposition=artifact.package_disposition,
                        cleanup_action=artifact.cleanup_action,
                        locator_json=artifact.locator_json,
                        package_entry=artifact.package_entry,
                        byte_size=artifact.byte_size,
                        content_digest=artifact.content_digest,
                        created_at=now,
                    )
                )

            registry = _member_registry(members)
            artifact_manifest = [
                {
                    "artifact_key": artifact.artifact_key,
                    "artifact_class": artifact.artifact_class,
                    "ownership_class": artifact.ownership_class,
                    "owner_type": artifact.owner_type,
                    "owner_id": artifact.owner_id,
                    "package_disposition": artifact.package_disposition,
                    "cleanup_action": artifact.cleanup_action,
                    "package_entry": artifact.package_entry,
                    "byte_size": artifact.byte_size if artifact.package_entry else None,
                    "sha256": artifact.content_digest if artifact.package_entry else None,
                }
                for artifact in sorted(artifacts, key=lambda item: item.artifact_key)
            ]
            manifest_base = {
                "schema_version": PACKAGE_SCHEMA_VERSION,
                "inventory_schema_version": INVENTORY_SCHEMA_VERSION,
                "export_schema_version": plan.schema_version,
                "package_id": str(package.id),
                "organization_id": str(organization_id),
                "closure_execution_id": str(execution_id),
                "export_plan_id": str(plan.id),
                "data_classes": data_class_manifest,
                "artifacts": artifact_manifest,
                "members": registry,
                "integrity": {
                    "algorithm": "sha256",
                    "manifest_membership": "explicit_exact_set",
                    "secret_exclusion": "enforced",
                },
            }

            target = resolve_stored_locator(
                package.storage_locator,
                storage_root=self._package_storage_root,
            )
            if target.exists():
                inspected = inspect_package(target)
                existing_manifest = dict(inspected.manifest)
                created_at = _parse_utc_timestamp(
                    existing_manifest.pop("package_created_at", None),
                    field="package_created_at",
                )
                ready_at = _parse_utc_timestamp(
                    existing_manifest.pop("ready_at", None),
                    field="ready_at",
                )
                if existing_manifest != manifest_base:
                    raise _PackageBuildBlocked(
                        "canonical_package_reconciliation_mismatch",
                        "Existing canonical package does not match the current accepted export/artifact membership",
                    )
                if not is_new and package.created_at != created_at:
                    raise _PackageBuildBlocked(
                        "canonical_package_identity_mismatch",
                        "Existing canonical package creation identity does not match durable package state",
                    )
                if is_new:
                    package.created_at = created_at
                manifest = inspected.manifest
                package_digest = inspected.package_digest
                package_size = inspected.byte_size
                manifest_digest = inspected.manifest_digest
            else:
                ready_at = datetime.now(tz=UTC)
                manifest = {
                    **manifest_base,
                    "package_created_at": package.created_at.isoformat(),
                    "ready_at": ready_at.isoformat(),
                }
                stored = write_immutable_package(
                    organization_id=organization_id,
                    execution_id=execution_id,
                    package_id=package.id,
                    manifest=manifest,
                    members=members,
                    storage_root=self._package_storage_root,
                )
                package_digest = stored.digest
                package_size = stored.byte_size
                manifest_digest = sha256(canonical_manifest_bytes(manifest)).hexdigest()
                target = stored.path

            package.status = STATUS_READY
            package.manifest_json = manifest
            package.manifest_digest = manifest_digest
            package.package_digest = package_digest
            package.byte_size = package_size
            package.ready_at = ready_at
            package.expires_at = ready_at + timedelta(days=PACKAGE_RETENTION_DAYS)
            package.updated_at = datetime.now(tz=UTC)

            verify_package(
                path=target,
                expected_package_digest=package_digest,
                expected_manifest_digest=manifest_digest,
            )
            package.status = STATUS_INTEGRITY_VERIFIED
            package.integrity_verified_at = datetime.now(tz=UTC)
            package.updated_at = package.integrity_verified_at
            package.failure_code = None
            package.failure_message = None
            self._repository.flush()
        except _PackageBuildBlocked as exc:
            return self._block(
                package=package,
                code=exc.code,
                message=exc.safe_message,
                organization_id=organization_id,
                access_token=access_token,
            )
        except (ClosurePackageStorageError, OSError) as exc:
            _ = exc
            return self._block(
                package=package,
                code="package_storage_or_integrity_failure",
                message="Closure package storage or integrity reconciliation failed",
                organization_id=organization_id,
                access_token=access_token,
            )

        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="organization_closure.package.integrity_verified",
            resource_type="organization_closure_package",
            resource_id=str(package.id),
            new_values={
                "status": package.status,
                "schema_version": package.schema_version,
                "inventory_schema_version": package.inventory_schema_version,
                "byte_size": package.byte_size,
                "ready_at": package.ready_at.isoformat() if package.ready_at else None,
                "integrity_verified_at": (
                    package.integrity_verified_at.isoformat()
                    if package.integrity_verified_at
                    else None
                ),
                "expires_at": package.expires_at.isoformat() if package.expires_at else None,
            },
            metadata={
                "authority": "system",
                "ol08_slice": "OL08-E1",
                "closure_execution_id": str(execution.id),
                "package_digest": package.package_digest,
                "manifest_digest": package.manifest_digest,
            },
        )
        return package

    def get(
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
            raise ClosurePackageNotFoundError("Closure package not found")
        return package

    def resolve_download(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        auth: AuthContext,
        access_token: str,
    ) -> tuple[OrganizationClosurePackageModel, Path]:
        self._require_system_authority(organization_id, auth, access_token)
        self._require_suspended(organization_id)
        self._require_open_execution(organization_id, execution_id)
        package = self._repository.get_package(
            organization_id,
            execution_id,
            PACKAGE_SCHEMA_VERSION,
        )
        if package is None:
            raise ClosurePackageNotFoundError("Closure package not found")
        if package.status != STATUS_INTEGRITY_VERIFIED:
            raise ClosureExecutionConflictError(
                "Closure package is not integrity verified for retrieval"
            )
        now = datetime.now(tz=UTC)
        if package.expires_at is None or now >= package.expires_at:
            raise ClosureExecutionConflictError("Closure package retrieval window has expired")
        if package.package_digest is None:
            raise ClosureExecutionConflictError("Closure package digest evidence is unavailable")
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
                "Closure package integrity cannot be verified for retrieval"
            ) from exc
        return package, path

    def _build_structured_members(
        self,
        *,
        organization_id: UUID,
        plan_manifest: dict[str, Any],
    ) -> tuple[list[PackageMember], list[dict[str, Any]]]:
        planned_classes = {
            item.get("key"): item
            for item in plan_manifest.get("data_classes", [])
            if isinstance(item, dict) and isinstance(item.get("key"), str)
        }
        members: list[PackageMember] = []
        manifest_classes: list[dict[str, Any]] = []

        for data_class in DATA_CLASS_REGISTRY:
            planned = planned_classes.get(data_class.key)
            if planned is None or planned.get("classification") != data_class.classification:
                raise _PackageBuildBlocked(
                    "export_plan_registry_mismatch",
                    "Closure export plan does not match the accepted portable registry",
                )
            class_entry: dict[str, Any] = {
                "key": data_class.key,
                "classification": data_class.classification,
                "reason_code": data_class.reason_code,
                "record_count": planned.get("record_count"),
                "sources": [],
            }
            if data_class.classification != INCLUDED:
                manifest_classes.append(class_entry)
                continue

            planned_sources = {
                item.get("key"): item
                for item in planned.get("sources", [])
                if isinstance(item, dict) and isinstance(item.get("key"), str)
            }
            total_count = 0
            for source in data_class.sources:
                planned_source = planned_sources.get(source.key)
                if planned_source is None:
                    raise _PackageBuildBlocked(
                        "export_plan_registry_mismatch",
                        "Closure export plan source registry is incomplete",
                    )
                ids = self._repository.list_scoped_ids(
                    model=source.model,
                    scope_model=source.scope_model,
                    organization_id=organization_id,
                    join_on=source.join_on,
                )
                identity_digest = _canonical_identity_digest([str(record_id) for record_id in ids])
                if (
                    planned_source.get("record_count") != len(ids)
                    or planned_source.get("record_identity_digest") != identity_digest
                ):
                    raise _PackageBuildBlocked(
                        "export_plan_stale",
                        "Closure export source identity changed after planning; package generation is blocked",
                    )
                rows = self._repository.list_scoped_rows(
                    model=source.model,
                    scope_model=source.scope_model,
                    organization_id=organization_id,
                    join_on=source.join_on,
                )
                if [str(row.id) for row in rows] != [str(record_id) for record_id in ids]:
                    raise _PackageBuildBlocked(
                        "export_snapshot_ambiguous",
                        "Closure export rows changed during package materialization",
                    )
                records = [_row_payload(row, source) for row in rows]
                member_path = f"structured/{data_class.key}/{source.key}.json"
                payload = _canonical_json_bytes(
                    {
                        "schema_version": PACKAGE_SCHEMA_VERSION,
                        "data_class": data_class.key,
                        "source": source.key,
                        "records": records,
                    }
                )
                members.append(PackageMember(member_path, payload))
                total_count += len(rows)
                class_entry["sources"].append(
                    {
                        "key": source.key,
                        "record_count": len(rows),
                        "package_entry": member_path,
                    }
                )
            if total_count != planned.get("record_count"):
                raise _PackageBuildBlocked(
                    "export_plan_stale",
                    "Closure export class count changed after planning; package generation is blocked",
                )
            class_entry["record_count"] = total_count
            manifest_classes.append(class_entry)
        return members, manifest_classes

    def _build_artifact_inventory(
        self,
        *,
        organization_id: UUID,
        execution_id: UUID,
        package_id: UUID,
        members: list[PackageMember],
    ) -> list[ArtifactBlueprint]:
        _ = (execution_id, package_id)
        artifacts: list[ArtifactBlueprint] = []
        member_by_path = {member.path: member for member in members}

        def include_member(path: str, content: bytes) -> tuple[int, str]:
            existing = member_by_path.get(path)
            if existing is not None and existing.content != content:
                raise _PackageBuildBlocked(
                    "artifact_package_entry_collision",
                    "Two different artifacts resolved to the same canonical package entry",
                )
            if existing is None:
                member = PackageMember(path, content)
                members.append(member)
                member_by_path[path] = member
            return len(content), sha256(content).hexdigest()

        referenced_logo_filenames: set[str] = set()
        logo_root = self._logo_storage_root
        organization_logo_dir = logo_root / str(organization_id)
        if organization_logo_dir.exists() and organization_logo_dir.is_symlink():
            raise _PackageBuildBlocked(
                "unsafe_managed_logo_root",
                "Managed quote-template logo ownership root is a symlink",
            )

        for version in self._repository.list_quote_template_versions(organization_id):
            normalized = normalize_logo_url(version.logo_url)
            if not normalized:
                continue
            if not normalized.startswith(LOGO_API_PREFIX):
                artifacts.append(
                    ArtifactBlueprint(
                        artifact_key=f"quote_template_logo_external:{version.id}",
                        artifact_class="quote_template_logo",
                        ownership_class="external_reference",
                        owner_type="quote_template_version",
                        owner_id=str(version.id),
                        storage_kind="external_reference",
                        package_disposition="structured_reference_only",
                        cleanup_action="relational_pointer_only",
                        locator_json={"reference_kind": "quote_template_logo_url"},
                        package_entry=None,
                        byte_size=None,
                        content_digest=None,
                    )
                )
                continue

            relative = normalized[len(LOGO_API_PREFIX) :]
            organization_token, separator, filename = relative.partition("/")
            if not separator or organization_token != str(organization_id):
                raise _PackageBuildBlocked(
                    "unsafe_managed_logo_locator",
                    "Managed quote-template logo locator does not belong to the closing organization",
                )
            unresolved = logo_root / str(organization_id) / filename
            if unresolved.exists() and unresolved.is_symlink():
                raise _PackageBuildBlocked(
                    "unsafe_managed_logo_locator",
                    "Managed quote-template logo locator is a symlink",
                )
            resolved = resolve_logo_file(
                organization_id,
                filename,
                storage_root=logo_root,
            )
            if resolved is None or not resolved.is_file():
                raise _PackageBuildBlocked(
                    "managed_logo_missing",
                    "A referenced managed quote-template logo is unavailable for the required package",
                )
            try:
                content = resolved.read_bytes()
            except OSError as exc:
                raise _PackageBuildBlocked(
                    "managed_logo_read_failed",
                    "A referenced managed quote-template logo cannot be read for the required package",
                ) from exc
            referenced_logo_filenames.add(filename)
            package_entry = f"artifacts/quote-template-logos/{filename}"
            byte_size, digest = include_member(package_entry, content)
            artifacts.append(
                ArtifactBlueprint(
                    artifact_key=f"quote_template_logo:{version.id}",
                    artifact_class="quote_template_logo",
                    ownership_class="managed_product_artifact",
                    owner_type="quote_template_version",
                    owner_id=str(version.id),
                    storage_kind="managed_file",
                    package_disposition="included",
                    cleanup_action="package_then_hard_delete",
                    locator_json={"filename": filename},
                    package_entry=package_entry,
                    byte_size=byte_size,
                    content_digest=digest,
                )
            )

        if organization_logo_dir.exists():
            if not organization_logo_dir.is_dir():
                raise _PackageBuildBlocked(
                    "unsafe_managed_logo_root",
                    "Managed quote-template logo ownership root is not a directory",
                )
            try:
                logo_entries = sorted(organization_logo_dir.iterdir(), key=lambda path: path.name)
            except OSError as exc:
                raise _PackageBuildBlocked(
                    "managed_logo_inventory_failed",
                    "Managed quote-template logo inventory cannot be enumerated",
                ) from exc
            for candidate in logo_entries:
                if candidate.is_symlink() or not candidate.is_file():
                    raise _PackageBuildBlocked(
                        "unknown_managed_logo_artifact",
                        "Managed quote-template logo root contains an unsafe or unknown artifact",
                    )
                if candidate.suffix.lower() not in LOGO_MEDIA_TYPES:
                    raise _PackageBuildBlocked(
                        "unknown_managed_logo_artifact",
                        "Managed quote-template logo root contains an unregistered artifact type",
                    )
                if candidate.name in referenced_logo_filenames:
                    continue
                artifacts.append(
                    ArtifactBlueprint(
                        artifact_key=f"quote_template_logo_orphan:{candidate.name}",
                        artifact_class="quote_template_logo",
                        ownership_class="managed_product_artifact",
                        owner_type="organization",
                        owner_id=str(organization_id),
                        storage_kind="managed_file",
                        package_disposition="not_included_unreferenced_orphan",
                        cleanup_action="hard_delete_after_gate",
                        locator_json={"filename": candidate.name},
                        package_entry=None,
                        byte_size=None,
                        content_digest=None,
                    )
                )

        for batch in self._repository.list_import_batches_with_stored_bytes(organization_id):
            content = bytes(batch.stored_file_content or b"")
            package_entry = f"artifacts/import-uploads/{batch.id}/original-upload.bin"
            byte_size, digest = include_member(package_entry, content)
            artifacts.append(
                ArtifactBlueprint(
                    artifact_key=f"import_upload:{batch.id}",
                    artifact_class="import_upload",
                    ownership_class="managed_product_artifact",
                    owner_type="import_batch",
                    owner_id=str(batch.id),
                    storage_kind="embedded_database_bytes",
                    package_disposition="included",
                    cleanup_action="package_then_hard_delete",
                    locator_json={"batch_id": str(batch.id), "field": "stored_file_content"},
                    package_entry=package_entry,
                    byte_size=byte_size,
                    content_digest=digest,
                )
            )

        handoff_root = self._handoff_storage_root
        if handoff_root.exists() and handoff_root.is_symlink():
            raise _PackageBuildBlocked(
                "unsafe_scraper_handoff_root",
                "Scraper handoff storage root cannot be a symlink for closure inventory",
            )
        handoff_root_resolved = handoff_root.resolve()
        for run in self._repository.list_scraper_runs(organization_id):
            candidates: list[tuple[str, Path, bool, str]] = [
                ("json", resolve_handoff_path(run.id, base_dir=handoff_root), False, ".json"),
                ("xlsx", resolve_handoff_excel_path(run.id, base_dir=handoff_root), False, ".xlsx"),
            ]
            if run.output_json_path:
                candidates.append(("json", Path(run.output_json_path), True, ".json"))
            if run.output_excel_path:
                candidates.append(("xlsx", Path(run.output_excel_path), True, ".xlsx"))

            discovered: dict[Path, tuple[str, Path]] = {}
            for kind, candidate, required_if_recorded, suffix in candidates:
                if candidate.suffix.lower() != suffix:
                    if required_if_recorded:
                        raise _PackageBuildBlocked(
                            "unsafe_scraper_handoff_locator",
                            "Recorded scraper handoff artifact has an unexpected file type",
                        )
                    continue
                if not is_safe_handoff_artifact_path(
                    candidate,
                    run_id=run.id,
                    base_dir=handoff_root,
                ):
                    if required_if_recorded:
                        raise _PackageBuildBlocked(
                            "unsafe_scraper_handoff_locator",
                            "Recorded scraper handoff artifact is outside accepted run ownership",
                        )
                    continue
                if candidate.exists() and candidate.is_symlink():
                    raise _PackageBuildBlocked(
                        "unsafe_scraper_handoff_locator",
                        "Scraper handoff artifact cannot be a symlink",
                    )
                resolved = candidate.resolve()
                if not resolved.exists():
                    if required_if_recorded:
                        raise _PackageBuildBlocked(
                            "scraper_handoff_missing",
                            "A recorded scraper handoff artifact is unavailable for the required package",
                        )
                    continue
                if not resolved.is_file():
                    raise _PackageBuildBlocked(
                        "unsafe_scraper_handoff_locator",
                        "Scraper handoff artifact is not a regular file",
                    )
                relative = resolved.relative_to(handoff_root_resolved)
                discovered[resolved] = (kind, relative)

            for index, (resolved, (kind, relative)) in enumerate(
                sorted(discovered.items(), key=lambda item: item[1][1].as_posix()),
                start=1,
            ):
                try:
                    content = resolved.read_bytes()
                except OSError as exc:
                    raise _PackageBuildBlocked(
                        "scraper_handoff_read_failed",
                        "A scraper handoff artifact cannot be read for the required package",
                    ) from exc
                suffix = resolved.suffix.lower()
                package_entry = (
                    f"artifacts/scraper-handoff/{run.id}/{kind}-{index}{suffix}"
                )
                byte_size, digest = include_member(package_entry, content)
                relative_token = relative.as_posix()
                locator_digest = sha256(relative_token.encode("utf-8")).hexdigest()[:16]
                artifacts.append(
                    ArtifactBlueprint(
                        artifact_key=f"scraper_handoff:{run.id}:{kind}:{locator_digest}",
                        artifact_class="scraper_handoff",
                        ownership_class="managed_product_artifact",
                        owner_type="scraper_run",
                        owner_id=str(run.id),
                        storage_kind="managed_file",
                        package_disposition="included",
                        cleanup_action="package_then_hard_delete",
                        locator_json={
                            "run_id": str(run.id),
                            "kind": kind,
                            "relative_path": relative_token,
                        },
                        package_entry=package_entry,
                        byte_size=byte_size,
                        content_digest=digest,
                    )
                )
        return artifacts

    def _block(
        self,
        *,
        package: OrganizationClosurePackageModel,
        code: str,
        message: str,
        organization_id: UUID,
        access_token: str,
    ) -> OrganizationClosurePackageModel:
        now = datetime.now(tz=UTC)
        package.status = STATUS_BLOCKED
        package.failure_code = code[:128]
        package.failure_message = message
        package.updated_at = now
        package.integrity_verified_at = None
        self._repository.flush()
        self._audit.record_event(
            organization_id=organization_id,
            access_token=access_token,
            action="organization_closure.package.blocked",
            resource_type="organization_closure_package",
            resource_id=str(package.id),
            new_values={
                "status": package.status,
                "failure_code": package.failure_code,
                "attempt_count": package.attempt_count,
            },
            metadata={
                "authority": "system",
                "ol08_slice": "OL08-E1",
                "closure_execution_id": str(package.closure_execution_id),
            },
        )
        return package

    def _require_open_execution(self, organization_id: UUID, execution_id: UUID):
        execution = self._repository.get_execution(organization_id, execution_id)
        if (
            execution is None
            or execution.closed_at is not None
            or execution.status != STATUS_IN_PROGRESS
        ):
            raise ClosureExecutionNotFoundError("Open in-progress closure execution not found")
        return execution

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
                "Closure package authorization authority unavailable"
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
                f"Organization must be suspended for closure package work: {snapshot.status}"
            )
