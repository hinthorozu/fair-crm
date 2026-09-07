from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureEventModel,
    OrganizationClosureExecutionModel,
)


class SqlAlchemyOrganizationClosureRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        organization_id: UUID,
        execution_id: UUID,
    ) -> OrganizationClosureExecutionModel | None:
        stmt = select(OrganizationClosureExecutionModel).where(
            OrganizationClosureExecutionModel.organization_id == organization_id,
            OrganizationClosureExecutionModel.id == execution_id,
        )
        return self._session.scalar(stmt)

    def get_by_idempotency(
        self,
        organization_id: UUID,
        idempotency_key: str,
    ) -> OrganizationClosureExecutionModel | None:
        stmt = select(OrganizationClosureExecutionModel).where(
            OrganizationClosureExecutionModel.organization_id == organization_id,
            OrganizationClosureExecutionModel.idempotency_key == idempotency_key,
        )
        return self._session.scalar(stmt)

    def get_open_for_organization(
        self,
        organization_id: UUID,
    ) -> OrganizationClosureExecutionModel | None:
        stmt = select(OrganizationClosureExecutionModel).where(
            OrganizationClosureExecutionModel.organization_id == organization_id,
            OrganizationClosureExecutionModel.closed_at.is_(None),
        )
        return self._session.scalar(stmt)

    def add_execution(self, execution: OrganizationClosureExecutionModel) -> None:
        self._session.add(execution)

    def add_event(self, event: OrganizationClosureEventModel) -> None:
        self._session.add(event)

    def flush(self) -> None:
        self._session.flush()

    def rollback(self) -> None:
        self._session.rollback()
