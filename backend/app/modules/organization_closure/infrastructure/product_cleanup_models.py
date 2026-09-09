from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrganizationClosureProductCleanupItemModel(Base):
    __tablename__ = "crm_organization_closure_product_cleanup_items"
    __table_args__ = (
        CheckConstraint("action = 'hard_delete'", name="ck_org_closure_product_cleanup_action"),
        CheckConstraint(
            "status IN ('pending', 'completed', 'blocked')",
            name="ck_org_closure_product_cleanup_status",
        ),
        UniqueConstraint(
            "organization_id",
            "closure_execution_id",
            "policy_version",
            "class_key",
            name="uq_org_closure_product_cleanup_class",
        ),
        Index("ix_closure_product_cleanup_org", "organization_id"),
        Index("ix_closure_product_cleanup_exec", "closure_execution_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    closure_execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_organization_closure_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    suspension_episode_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    class_key: Mapped[str] = mapped_column(String(96), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="hard_delete")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    before_count: Mapped[int | None] = mapped_column(Integer)
    deleted_count: Mapped[int | None] = mapped_column(Integer)
    remaining_count: Mapped[int | None] = mapped_column(Integer)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    failure_message: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
