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
from app.modules.activities.domain.value_objects import ActivitySource
from app.modules.activities.infrastructure.persistence.models import ActivityModel

FAIR_BULK_EMAIL_ACTIVITY_SOURCE = "fair_bulk_email"

ACTIVITY_SORT_FIELDS = {
    "created_at": ActivityModel.created_at,
    "updated_at": ActivityModel.updated_at,
    "activity_date": ActivityModel.activity_date,
    "follow_up_date": ActivityModel.follow_up_date,
    "subject": ActivityModel.subject,
    "status": ActivityModel.status,
    "activity_type": ActivityModel.activity_type,
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
