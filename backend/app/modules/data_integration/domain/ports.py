from typing import Protocol
from uuid import UUID

from app.modules.data_integration.domain.entities import ImportJob


class ImportJobRepository(Protocol):
    def add(self, job: ImportJob) -> ImportJob: ...

    def get_by_id(self, organization_id: UUID, job_id: UUID) -> ImportJob | None: ...

    def update(self, job: ImportJob) -> ImportJob: ...

    def list_by_batch(self, organization_id: UUID, batch_id: UUID) -> list[ImportJob]: ...

    def list_recent(
        self,
        organization_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[ImportJob], int]: ...
