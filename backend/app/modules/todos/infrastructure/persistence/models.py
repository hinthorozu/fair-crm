from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TodoModel(Base):
    __tablename__ = "crm_todos"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="todo")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, server_default="normal")
    category: Mapped[str] = mapped_column(String(32), nullable=False, server_default="genel_gorev")
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignee_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    customer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_fair_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_fairs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TodoOutcomeDefinitionModel(Base):
    __tablename__ = "crm_todo_outcome_definitions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "code",
            name="uq_crm_todo_outcome_definitions_org_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primary_worklist_status: Mapped[str] = mapped_column(String(32), nullable=False)
    requires_action: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    marks_data_problem: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TodoWorklistStateModel(Base):
    __tablename__ = "crm_todo_worklist_states"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "todo_id",
            "customer_id",
            name="uq_crm_todo_worklist_states_org_todo_customer",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    todo_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_todos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_customer_fair_participations.id", ondelete="SET NULL"),
        nullable=True,
    )
    primary_status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_activity_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_activities.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_outcome_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("crm_todo_outcome_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_note_summary: Mapped[str | None] = mapped_column(String(500))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_actor_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    action_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_problem: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
