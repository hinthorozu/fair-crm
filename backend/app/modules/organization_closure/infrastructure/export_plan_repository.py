from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureEventModel,
    OrganizationClosureExecutionModel,
    OrganizationClosureExportPlanModel,
)


class SqlAlchemyOrganizationClosureExportPlanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_execution(
        self,
        organization_id: UUID,
        execution_id: UUID,
    ) -> OrganizationClosureExecutionModel | None:
        stmt = select(OrganizationClosureExecutionModel).where(
            OrganizationClosureExecutionModel.organization_id == organization_id,
            OrganizationClosureExecutionModel.id == execution_id,
        )
        return self._session.scalar(stmt)

    def get_plan(
        self,
        organization_id: UUID,
        execution_id: UUID,
        schema_version: str,
    ) -> OrganizationClosureExportPlanModel | None:
        stmt = select(OrganizationClosureExportPlanModel).where(
            OrganizationClosureExportPlanModel.organization_id == organization_id,
            OrganizationClosureExportPlanModel.closure_execution_id == execution_id,
            OrganizationClosureExportPlanModel.schema_version == schema_version,
        )
        return self._session.scalar(stmt)

    def list_scoped_ids(
        self,
        *,
        model: type,
        scope_model: type,
        organization_id: UUID,
        join_on: Any | None = None,
    ) -> tuple[Any, ...]:
        stmt = select(model.id)
        if join_on is not None:
            stmt = stmt.join(scope_model, join_on)
        stmt = stmt.where(scope_model.organization_id == organization_id).order_by(model.id)
        return tuple(self._session.scalars(stmt).all())

    def add_plan(self, plan: OrganizationClosureExportPlanModel) -> None:
        self._session.add(plan)

    def add_event(self, event: OrganizationClosureEventModel) -> None:
        self._session.add(event)

    def flush(self) -> None:
        self._session.flush()

    def rollback(self) -> None:
        self._session.rollback()
