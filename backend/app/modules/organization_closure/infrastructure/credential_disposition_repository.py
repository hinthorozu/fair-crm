from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organization_closure.infrastructure.models import (
    OrganizationClosureCredentialDispositionModel,
    OrganizationClosureCredentialEventModel,
)


class SqlAlchemyOrganizationClosureCredentialDispositionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_disposition(
        self,
        disposition: OrganizationClosureCredentialDispositionModel,
    ) -> None:
        self._session.add(disposition)

    def add_event(self, event: OrganizationClosureCredentialEventModel) -> None:
        self._session.add(event)

    def get_by_id(
        self,
        organization_id: UUID,
        closure_execution_id: UUID,
        disposition_id: UUID,
    ) -> OrganizationClosureCredentialDispositionModel | None:
        stmt = select(OrganizationClosureCredentialDispositionModel).where(
            OrganizationClosureCredentialDispositionModel.organization_id == organization_id,
            OrganizationClosureCredentialDispositionModel.closure_execution_id
            == closure_execution_id,
            OrganizationClosureCredentialDispositionModel.id == disposition_id,
        )
        return self._session.scalars(stmt).one_or_none()

    def get_by_account(
        self,
        organization_id: UUID,
        closure_execution_id: UUID,
        email_account_id: UUID,
    ) -> OrganizationClosureCredentialDispositionModel | None:
        stmt = select(OrganizationClosureCredentialDispositionModel).where(
            OrganizationClosureCredentialDispositionModel.organization_id == organization_id,
            OrganizationClosureCredentialDispositionModel.closure_execution_id
            == closure_execution_id,
            OrganizationClosureCredentialDispositionModel.email_account_id == email_account_id,
        )
        return self._session.scalars(stmt).one_or_none()

    def list_for_execution(
        self,
        organization_id: UUID,
        closure_execution_id: UUID,
    ) -> list[OrganizationClosureCredentialDispositionModel]:
        stmt = (
            select(OrganizationClosureCredentialDispositionModel)
            .where(
                OrganizationClosureCredentialDispositionModel.organization_id
                == organization_id,
                OrganizationClosureCredentialDispositionModel.closure_execution_id
                == closure_execution_id,
            )
            .order_by(
                OrganizationClosureCredentialDispositionModel.email_account_id.asc()
            )
        )
        return list(self._session.scalars(stmt).all())

    def flush(self) -> None:
        self._session.flush()
