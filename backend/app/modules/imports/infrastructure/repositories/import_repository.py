from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.imports.domain.entities import ImportBatch, ImportRow
from app.modules.imports.infrastructure.persistence.mappers import (
    batch_entity_to_model,
    batch_model_to_entity,
    row_entity_to_model,
    row_model_to_entity,
    update_batch_model_from_entity,
    update_row_model_from_entity,
)
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel, ImportRowModel


class SqlAlchemyImportBatchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, batch: ImportBatch) -> ImportBatch:
        model = batch_entity_to_model(batch)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return batch_model_to_entity(model)

    def get_by_id(self, organization_id: UUID, batch_id: UUID) -> ImportBatch | None:
        model = (
            self._session.query(ImportBatchModel)
            .filter(
                ImportBatchModel.organization_id == organization_id,
                ImportBatchModel.id == batch_id,
            )
            .one_or_none()
        )
        return batch_model_to_entity(model) if model else None

    def update(self, batch: ImportBatch) -> ImportBatch:
        model = (
            self._session.query(ImportBatchModel)
            .filter(
                ImportBatchModel.organization_id == batch.organization_id,
                ImportBatchModel.id == batch.id,
            )
            .one()
        )
        update_batch_model_from_entity(model, batch)
        self._session.flush()
        self._session.refresh(model)
        return batch_model_to_entity(model)


class SqlAlchemyImportRowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_many(self, rows: list[ImportRow]) -> list[ImportRow]:
        models = [row_entity_to_model(row) for row in rows]
        self._session.add_all(models)
        self._session.flush()
        for model in models:
            self._session.refresh(model)
        return [row_model_to_entity(model) for model in models]

    def list_by_batch(self, organization_id: UUID, batch_id: UUID) -> list[ImportRow]:
        models = (
            self._session.query(ImportRowModel)
            .filter(
                ImportRowModel.organization_id == organization_id,
                ImportRowModel.batch_id == batch_id,
            )
            .order_by(ImportRowModel.row_number.asc())
            .all()
        )
        return [row_model_to_entity(model) for model in models]

    def get_by_id(
        self, organization_id: UUID, batch_id: UUID, row_id: UUID
    ) -> ImportRow | None:
        model = (
            self._session.query(ImportRowModel)
            .filter(
                ImportRowModel.organization_id == organization_id,
                ImportRowModel.batch_id == batch_id,
                ImportRowModel.id == row_id,
            )
            .one_or_none()
        )
        return row_model_to_entity(model) if model else None

    def update(self, row: ImportRow) -> ImportRow:
        model = (
            self._session.query(ImportRowModel)
            .filter(
                ImportRowModel.organization_id == row.organization_id,
                ImportRowModel.id == row.id,
            )
            .one()
        )
        update_row_model_from_entity(model, row)
        self._session.flush()
        self._session.refresh(model)
        return row_model_to_entity(model)

    def update_many(self, rows: list[ImportRow]) -> None:
        for row in rows:
            model = (
                self._session.query(ImportRowModel)
                .filter(
                    ImportRowModel.organization_id == row.organization_id,
                    ImportRowModel.id == row.id,
                )
                .one()
            )
            update_row_model_from_entity(model, row)
        self._session.flush()

    def delete_by_batch(self, organization_id: UUID, batch_id: UUID) -> None:
        (
            self._session.query(ImportRowModel)
            .filter(
                ImportRowModel.organization_id == organization_id,
                ImportRowModel.batch_id == batch_id,
            )
            .delete(synchronize_session=False)
        )
        self._session.flush()
