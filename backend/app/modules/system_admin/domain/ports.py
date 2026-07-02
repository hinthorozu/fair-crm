from typing import Protocol
from uuid import UUID

from app.modules.system_admin.domain.entities import SystemBackup


class SystemBackupRepository(Protocol):
    def add(self, backup: SystemBackup) -> SystemBackup: ...

    def update(self, backup: SystemBackup) -> SystemBackup: ...

    def get_by_id(self, organization_id: UUID, backup_id: UUID) -> SystemBackup | None: ...

    def list_recent(
        self,
        organization_id: UUID,
        *,
        page: int,
        page_size: int,
        sort_by: str = "started_at",
        sort_dir: str = "desc",
    ) -> tuple[list[SystemBackup], int]: ...
