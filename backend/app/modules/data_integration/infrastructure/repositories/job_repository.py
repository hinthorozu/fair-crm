from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.infrastructure.persistence.models import ImportJobModel
from app.modules.imports.domain.value_objects import ImportJobStatus, ImportJobType


def _to_entity(model: ImportJobModel) -> ImportJob:
    return ImportJob(
        id=model.id,
        organization_id=model.organization_id,
        batch_id=model.batch_id,
        job_type=ImportJobType(model.job_type),
        status=ImportJobStatus(model.status),
        progress_processed=model.progress_processed,
        progress_total=model.progress_total,
        result_json=model.result_json,
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
    )


def _to_model(entity: ImportJob) -> ImportJobModel:
    return ImportJobModel(
        id=entity.id,
        organization_id=entity.organization_id,
        batch_id=entity.batch_id,
        job_type=entity.job_type.value,
        status=entity.status.value,
        progress_processed=entity.progress_processed,
        progress_total=entity.progress_total,
        result_json=entity.result_json,
        error_message=entity.error_message,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        started_at=entity.started_at,
        completed_at=entity.completed_at,
    )


def _update_model(model: ImportJobModel, entity: ImportJob) -> None:
    model.status = entity.status.value
    model.progress_processed = entity.progress_processed
    model.progress_total = entity.progress_total
    model.result_json = entity.result_json
    model.error_message = entity.error_message
    model.updated_at = entity.updated_at
    model.started_at = entity.started_at
    model.completed_at = entity.completed_at


class SqlAlchemyImportJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: ImportJob) -> ImportJob:
        model = _to_model(job)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _to_entity(model)

    def get_by_id(self, organization_id: UUID, job_id: UUID) -> ImportJob | None:
        model = (
            self._session.query(ImportJobModel)
            .filter(
                ImportJobModel.organization_id == organization_id,
                ImportJobModel.id == job_id,
            )
            .one_or_none()
        )
        return _to_entity(model) if model else None

    def update(self, job: ImportJob) -> ImportJob:
        model = (
            self._session.query(ImportJobModel)
            .filter(
                ImportJobModel.organization_id == job.organization_id,
                ImportJobModel.id == job.id,
            )
            .one()
        )
        _update_model(model, job)
        self._session.flush()
        self._session.refresh(model)
        return _to_entity(model)

    def list_by_batch(self, organization_id: UUID, batch_id: UUID) -> list[ImportJob]:
        models = (
            self._session.query(ImportJobModel)
            .filter(
                ImportJobModel.organization_id == organization_id,
                ImportJobModel.batch_id == batch_id,
            )
            .order_by(ImportJobModel.created_at.desc())
            .all()
        )
        return [_to_entity(m) for m in models]

    def list_recent(
        self,
        organization_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[ImportJob], int]:
        query = self._session.query(ImportJobModel).filter(
            ImportJobModel.organization_id == organization_id
        )
        total = query.count()
        models = (
            query.order_by(ImportJobModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [_to_entity(m) for m in models], total

    def has_active_analyze_job(self, organization_id: UUID) -> bool:
        model = (
            self._session.query(ImportJobModel)
            .filter(
                ImportJobModel.organization_id == organization_id,
                ImportJobModel.job_type == ImportJobType.ANALYZE.value,
                ImportJobModel.status.in_(
                    [ImportJobStatus.QUEUED.value, ImportJobStatus.RUNNING.value]
                ),
            )
            .first()
        )
        return model is not None

    def get_active_analyze_job_for_batch(
        self, organization_id: UUID, batch_id: UUID
    ) -> ImportJob | None:
        model = (
            self._session.query(ImportJobModel)
            .filter(
                ImportJobModel.organization_id == organization_id,
                ImportJobModel.batch_id == batch_id,
                ImportJobModel.job_type == ImportJobType.ANALYZE.value,
                ImportJobModel.status.in_(
                    [ImportJobStatus.QUEUED.value, ImportJobStatus.RUNNING.value]
                ),
            )
            .order_by(ImportJobModel.created_at.desc())
            .first()
        )
        return _to_entity(model) if model else None

    def has_active_bulk_or_apply_job_for_batch(
        self, organization_id: UUID, batch_id: UUID
    ) -> bool:
        return self.get_active_bulk_or_apply_job_for_batch(organization_id, batch_id) is not None

    def get_active_bulk_or_apply_job_for_batch(
        self, organization_id: UUID, batch_id: UUID
    ) -> ImportJob | None:
        model = (
            self._session.query(ImportJobModel)
            .filter(
                ImportJobModel.organization_id == organization_id,
                ImportJobModel.batch_id == batch_id,
                ImportJobModel.job_type.in_(
                    [ImportJobType.APPLY.value, ImportJobType.BULK_DECISION.value]
                ),
                ImportJobModel.status.in_(
                    [ImportJobStatus.QUEUED.value, ImportJobStatus.RUNNING.value]
                ),
            )
            .order_by(ImportJobModel.created_at.desc())
            .first()
        )
        return _to_entity(model) if model else None

    def has_any_active_job_for_batch(self, organization_id: UUID, batch_id: UUID) -> bool:
        if self.get_active_analyze_job_for_batch(organization_id, batch_id) is not None:
            return True
        return self.get_active_bulk_or_apply_job_for_batch(organization_id, batch_id) is not None
