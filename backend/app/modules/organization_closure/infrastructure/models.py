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
            "status IN ('in_progress', 'blocked', 'completed')",
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
    # Retained scalar evidence identity. OL08-D intentionally does not keep a
    # live FK to the product email_accounts row during the 12-month evidence window.
    email_account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
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


class OrganizationClosurePackageModel(Base):
    __tablename__ = "crm_organization_closure_packages"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'generating', 'ready', 'integrity_verified', 'expired', 'purged', 'blocked')",
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

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
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
    inventory_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_locator: Mapped[str] = mapped_column(String(1024), nullable=False)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    package_digest: Mapped[str | None] = mapped_column(String(64))
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    failure_message: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    integrity_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationClosureArtifactInventoryModel(Base):
    __tablename__ = "crm_organization_closure_artifact_inventory"
    __table_args__ = (
        CheckConstraint(
            "ownership_class IN ('managed_product_artifact', 'external_reference')",
            name="ck_org_closure_artifact_ownership_class",
        ),
        CheckConstraint(
            "cleanup_status IN ('pending', 'not_applicable', 'relational_delete_required', 'purged', 'already_absent', 'blocked')",
            name="ck_org_closure_artifact_cleanup_status",
        ),
        UniqueConstraint(
            "package_id",
            "artifact_key",
            name="uq_org_closure_artifact_package_key",
        ),
        Index("ix_closure_artifact_package", "package_id"),
        Index("ix_closure_artifact_org", "organization_id"),
        Index("ix_closure_artifact_exec", "closure_execution_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    package_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    closure_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    inventory_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_key: Mapped[str] = mapped_column(String(512), nullable=False)
    artifact_class: Mapped[str] = mapped_column(String(96), nullable=False)
    ownership_class: Mapped[str] = mapped_column(String(48), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(200), nullable=False)
    storage_kind: Mapped[str] = mapped_column(String(48), nullable=False)
    package_disposition: Mapped[str] = mapped_column(String(64), nullable=False)
    cleanup_action: Mapped[str] = mapped_column(String(64), nullable=False)
    locator_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    package_entry: Mapped[str | None] = mapped_column(String(1024))
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    content_digest: Mapped[str | None] = mapped_column(String(64))
    cleanup_status: Mapped[str] = mapped_column(String(48), nullable=False, default="pending")
    cleanup_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleanup_failure_code: Mapped[str | None] = mapped_column(String(128))
    cleanup_failure_message: Mapped[str | None] = mapped_column(Text)
    cleanup_last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nonexistence_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
