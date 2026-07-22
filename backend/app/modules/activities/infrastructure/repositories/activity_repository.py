from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.pagination import build_order_clause, build_paginated_meta, normalize_page_params
from app.modules.activities.domain.entities import Activity
from app.modules.activities.domain.ports import ActivityListResult
from app.modules.activities.infrastructure.persistence.mappers import (
    entity_to_model,
    model_to_entity,
    update_model_from_entity,
)
from app.modules.activities.domain.value_objects import ActivitySource, ActivityType
from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel

FAIR_BULK_EMAIL_ACTIVITY_SOURCE = "fair_bulk_email"

ACTIVITY_SORT_FIELDS = {
    "created_at": ActivityModel.created_at,
    "updated_at": ActivityModel.updated_at,
    "activity_date": ActivityModel.activity_date,
    "follow_up_date": ActivityModel.follow_up_date,
    "subject": ActivityModel.subject,
    "status": ActivityModel.status,
    "activity_type": ActivityModel.activity_type,
    "customer_name": CustomerModel.display_name,
}

SEARCH_FIELDS = (
    ActivityModel.subject,
    ActivityModel.description,
    ActivityModel.activity_type,
    ActivityModel.status,
)


class SqlAlchemyActivityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, activity: Activity) -> Activity:
        model = entity_to_model(activity)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def exists_fair_bulk_email_outbox(self, organization_id: UUID, outbox_id: UUID) -> bool:
        outbox_id_text = str(outbox_id)
        models = (
            self._session.query(ActivityModel)
            .filter(
                ActivityModel.organization_id == organization_id,
                ActivityModel.source == ActivitySource.EMAIL_AUTOMATION,
                ActivityModel.deleted_at.is_(None),
                ActivityModel.metadata_json.isnot(None),
            )
            .all()
        )
        for model in models:
            metadata = model.metadata_json or {}
            if metadata.get("source") != FAIR_BULK_EMAIL_ACTIVITY_SOURCE:
                continue
            if metadata.get("outbox_id") == outbox_id_text:
                return True
        return False

    def get_by_id(self, organization_id: UUID, activity_id: UUID) -> Activity | None:
        model = (
            self._session.query(ActivityModel)
            .filter(
                ActivityModel.organization_id == organization_id,
                ActivityModel.id == activity_id,
                ActivityModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def get_task_completed_by_todo_id(
        self, organization_id: UUID, todo_id: UUID
    ) -> Activity | None:
        model = (
            self._session.query(ActivityModel)
            .filter(
                ActivityModel.organization_id == organization_id,
                ActivityModel.todo_id == todo_id,
                ActivityModel.activity_type == ActivityType.TASK_COMPLETED,
                ActivityModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return model_to_entity(model) if model else None

    def update(self, activity: Activity) -> Activity:
        model = (
            self._session.query(ActivityModel)
            .filter(
                ActivityModel.organization_id == activity.organization_id,
                ActivityModel.id == activity.id,
            )
            .one()
        )
        update_model_from_entity(model, activity)
        self._session.flush()
        self._session.refresh(model)
        return model_to_entity(model)

    def hard_delete(self, organization_id: UUID, activity_id: UUID) -> bool:
        model = (
            self._session.query(ActivityModel)
            .filter(
                ActivityModel.organization_id == organization_id,
                ActivityModel.id == activity_id,
                ActivityModel.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True

    def hard_delete_many(self, organization_id: UUID, activity_ids: list[UUID]) -> int:
        if not activity_ids:
            return 0
        models = (
            self._session.query(ActivityModel)
            .filter(
                ActivityModel.organization_id == organization_id,
                ActivityModel.id.in_(activity_ids),
                ActivityModel.deleted_at.is_(None),
            )
            .all()
        )
        for model in models:
            self._session.delete(model)
        self._session.flush()
        return len(models)

    def get_existing_ids(
        self, organization_id: UUID, activity_ids: list[UUID]
    ) -> list[UUID]:
        if not activity_ids:
            return []
        rows = (
            self._session.query(ActivityModel.id)
            .filter(
                ActivityModel.organization_id == organization_id,
                ActivityModel.id.in_(activity_ids),
                ActivityModel.deleted_at.is_(None),
            )
            .all()
        )
        return [row.id for row in rows]

    def list_by_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        search: str | None = None,
        activity_type: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "activity_date",
        sort_dir: str = "desc",
        include_deleted: bool = False,
    ) -> ActivityListResult:
        page_params = normalize_page_params(page, page_size)
        query = self._session.query(ActivityModel).filter(
            ActivityModel.organization_id == organization_id,
            ActivityModel.customer_id == customer_id,
        )
        if not include_deleted:
            query = query.filter(ActivityModel.deleted_at.is_(None))
        if activity_type:
            query = query.filter(ActivityModel.activity_type == activity_type.strip())
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(*[field.ilike(pattern) for field in SEARCH_FIELDS]))

        total = query.count()
        sort_column = ACTIVITY_SORT_FIELDS.get(sort_by, ActivityModel.activity_date)
        if sort_by == "customer_name":
            sort_column = ActivityModel.activity_date
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "desc",
            tie_breaker=ActivityModel.id,
        )

        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return ActivityListResult(
            items=[model_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )

    def list_all(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        customer_id: UUID | None = None,
        fair_id: UUID | None = None,
        activity_type: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "activity_date",
        sort_dir: str = "desc",
        include_deleted: bool = False,
    ) -> ActivityListResult:
        page_params = normalize_page_params(page, page_size)
        query = (
            self._session.query(ActivityModel)
            .outerjoin(CustomerModel, CustomerModel.id == ActivityModel.customer_id)
            .filter(ActivityModel.organization_id == organization_id)
        )
        if not include_deleted:
            query = query.filter(ActivityModel.deleted_at.is_(None))
        if customer_id is not None:
            query = query.filter(ActivityModel.customer_id == customer_id)
        if fair_id is not None:
            query = query.filter(ActivityModel.fair_id == fair_id)
        if activity_type:
            query = query.filter(ActivityModel.activity_type == activity_type.strip())
        if status:
            query = query.filter(ActivityModel.status == status.strip())
        if date_from is not None:
            query = query.filter(ActivityModel.activity_date >= date_from)
        if date_to is not None:
            query = query.filter(ActivityModel.activity_date <= date_to)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    *[field.ilike(pattern) for field in SEARCH_FIELDS],
                    CustomerModel.display_name.ilike(pattern),
                )
            )

        total = query.count()
        sort_column = ACTIVITY_SORT_FIELDS.get(sort_by, ActivityModel.activity_date)
        order = build_order_clause(
            sort_column,
            sort_dir if sort_dir in ("asc", "desc") else "desc",
            tie_breaker=ActivityModel.id,
        )

        models = (
            query.order_by(*order)
            .offset(page_params.offset)
            .limit(page_params.page_size)
            .all()
        )
        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return ActivityListResult(
            items=[model_to_entity(model) for model in models],
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )
