from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrganizationClosureExecutionModel(Base):
    __tablename__ = "crm_organization_closure_executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'blocked')",
            name="ck_org_closure_execution_status",
        ),
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_org_closure_execution_idempotency",
        ),
        Index(
            "uq_org_closure_execution_open_org",
            "organization_id",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
            sqlite_where=text("closed_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_phase: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    failure_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lifecycle_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationClosureEventModel(Base):
    __tablename__ = "crm_organization_closure_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_executions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganizationClosureExportPlanModel(Base):
    __tablename__ = "crm_organization_closure_export_plans"
    __table_args__ = (
        CheckConstraint(
            "disposition = 'required'",
            name="ck_org_closure_export_plan_disposition",
        ),
        CheckConstraint(
            "status = 'planned'",
            name="ck_org_closure_export_plan_status",
        ),
        UniqueConstraint(
            "organization_id",
            "closure_execution_id",
            "schema_version",
            name="uq_org_closure_export_plan_execution_schema",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    closure_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_executions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganizationClosurePackageModel(Base):
    __tablename__ = "crm_organization_closure_packages"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'generating', 'ready', 'integrity_verified', 'blocked', 'expired', 'purged')",
            name="ck_org_closure_package_status",
        ),
        UniqueConstraint(
            "organization_id",
            "closure_execution_id",
            "schema_version",
            name="uq_org_closure_package_execution_schema",
        ),
        Index("ix_closure_package_org", "organization_id"),
        Index("ix_closure_package_exec", "closure_execution_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    closure_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    export_plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_export_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    package_locator: Mapped[str | None] = mapped_column(String(512))
    package_sha256: Mapped[str | None] = mapped_column(String(64))
    package_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    member_count: Mapped[int | None] = mapped_column(Integer)
    manifest_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    failure_message: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    integrity_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationClosureArtifactInventoryModel(Base):
    __tablename__ = "crm_organization_closure_artifact_inventory"
    __table_args__ = (
        CheckConstraint(
            "storage_class IN ('managed_file', 'embedded_bytes', 'external_reference')",
            name="ck_org_closure_artifact_storage_class",
        ),
        CheckConstraint(
            "status IN ('certified', 'external_reference')",
            name="ck_org_closure_artifact_status",
        ),
        CheckConstraint(
            "cleanup_action IN ('delete_managed_file', 'delete_with_owner_row', 'retain_external_reference')",
            name="ck_org_closure_artifact_cleanup_action",
        ),
        UniqueConstraint(
            "package_id",
            "owner_type",
            "owner_id",
            "owner_field",
            "locator",
            name="uq_org_closure_artifact_owner_locator",
        ),
        Index("ix_closure_artifact_org", "organization_id"),
        Index("ix_closure_artifact_exec", "closure_execution_id"),
        Index("ix_closure_artifact_package", "package_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    package_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    closure_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_class: Mapped[str] = mapped_column(String(96), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    owner_field: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_class: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    package_included: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cleanup_action: Mapped[str] = mapped_column(String(48), nullable=False)
    locator: Mapped[str] = mapped_column(String(255), nullable=False)
    package_member: Mapped[str | None] = mapped_column(String(512))
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganizationClosureCredentialDispositionModel(Base):
    __tablename__ = "crm_organization_closure_credential_dispositions"
    __table_args__ = (
        CheckConstraint(
            "capability_class IN ('supported_unidentifiable', 'operator_required', 'not_applicable')",
            name="ck_org_closure_credential_capability_class",
        ),
        CheckConstraint(
            "external_invalidation_state IN ('blocked_supported_unidentifiable', 'operator_required', 'not_applicable', 'confirmed')",
            name="ck_org_closure_credential_external_state",
        ),
        CheckConstraint(
            "target_verification_state IN ('missing', 'unverified', 'not_required')",
            name="ck_org_closure_credential_target_state",
        ),
        CheckConstraint(
            "status IN ('outbound_disabled', 'operator_required', 'blocked_supported_unidentifiable', 'local_send_secrets_purged', 'receive_only_pending', 'disposition_complete')",
            name="ck_org_closure_credential_status",
        ),
        UniqueConstraint(
            "organization_id",
            "closure_execution_id",
            "email_account_id",
            name="uq_org_closure_credential_execution_account",
        ),
        Index("ix_closure_cred_org", "organization_id"),
        Index("ix_closure_cred_exec", "closure_execution_id"),
        Index("ix_closure_cred_account", "email_account_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    closure_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    email_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("email_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_key: Mapped[str | None] = mapped_column(String(64))
    capability_class: Mapped[str] = mapped_column(String(48), nullable=False)
    external_invalidation_state: Mapped[str] = mapped_column(String(48), nullable=False)
    target_verification_state: Mapped[str] = mapped_column(String(32), nullable=False)
    external_credential_id: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(48), nullable=False)
    signing_secret_retained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    failure_message: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    outbound_disabled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    external_invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    send_secret_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationClosureCredentialEventModel(Base):
    __tablename__ = "crm_organization_closure_credential_events"
    __table_args__ = (
        Index("ix_closure_cred_evt_disp", "disposition_id"),
        Index("ix_closure_cred_evt_exec", "closure_execution_id"),
        Index("ix_closure_cred_evt_org", "organization_id"),
        Index("ix_closure_cred_evt_account", "email_account_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    disposition_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_credential_dispositions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    closure_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    email_account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(48))
    to_status: Mapped[str] = mapped_column(String(48), nullable=False)
    evidence_code: Mapped[str | None] = mapped_column(String(128))
    evidence_reference: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
