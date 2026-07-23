from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.operations.domain.value_objects import HandlerCapabilities
from app.modules.operations.infrastructure.persistence.models import OperationTypeModel

CAPABILITY_FIELD_NAMES = (
    "supports_pause",
    "supports_resume",
    "supports_retry",
    "supports_schedule",
    "supports_items",
)


def capabilities_from_model(row: OperationTypeModel) -> HandlerCapabilities:
    return HandlerCapabilities(
        supports_pause=bool(row.supports_pause),
        supports_resume=bool(row.supports_resume),
        supports_retry=bool(row.supports_retry),
        supports_schedule=bool(row.supports_schedule),
        supports_items=bool(row.supports_items),
    )


class SqlAlchemyOperationTypeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_types(self, *, active_only: bool = False) -> list[OperationTypeModel]:
        query = self._session.query(OperationTypeModel)
        if active_only:
            query = query.filter(OperationTypeModel.is_active.is_(True))
        return list(
            query.order_by(
                OperationTypeModel.sort_order.asc(),
                OperationTypeModel.name.asc(),
            ).all()
        )

    def get_by_key(self, key: str) -> OperationTypeModel | None:
        return (
            self._session.query(OperationTypeModel)
            .filter(OperationTypeModel.key == key)
            .one_or_none()
        )

    def get_capabilities(self, key: str) -> HandlerCapabilities | None:
        row = self.get_by_key(key)
        if row is None:
            return None
        return capabilities_from_model(row)

    def update_capabilities(
        self,
        key: str,
        capabilities: HandlerCapabilities,
        *,
        is_active: bool | None = None,
    ) -> OperationTypeModel | None:
        row = self.get_by_key(key)
        if row is None:
            return None
        row.supports_pause = capabilities.supports_pause
        row.supports_resume = capabilities.supports_resume
        row.supports_retry = capabilities.supports_retry
        row.supports_schedule = capabilities.supports_schedule
        row.supports_items = capabilities.supports_items
        if is_active is not None:
            row.is_active = is_active
        row.updated_at = datetime.now(tz=UTC)
        self._session.flush()
        self._session.refresh(row)
        return row
