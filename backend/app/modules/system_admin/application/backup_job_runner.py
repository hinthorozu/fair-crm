from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.system_admin.domain.value_objects import SystemBackupStage
from app.modules.system_admin.infrastructure.repositories.backup_repository import (
    SqlAlchemySystemBackupRepository,
)
from app.shared.database_backup.engine import DatabaseBackupError, pg_dump_custom
from app.shared.database_backup.paths import resolve_backup_path


@dataclass(frozen=True)
class BackupJobCommand:
    organization_id: UUID
    backup_id: UUID


class BackupJobRunner:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def run_backup(self, command: BackupJobCommand) -> None:
        db = self._session_factory()
        try:
            repo = SqlAlchemySystemBackupRepository(db)
            backup = repo.get_by_id(command.organization_id, command.backup_id)
            if backup is None:
                return

            settings = get_settings()
            now = datetime.now(tz=UTC)
            backup.mark_stage(SystemBackupStage.PREPARING, now=now)
            repo.update(backup)
            db.commit()

            output_path = resolve_backup_path(backup.file_name)

            def on_stage(stage: str) -> None:
                nonlocal backup
                mapped = {
                    "preparing": SystemBackupStage.PREPARING,
                    "dumping": SystemBackupStage.DUMPING,
                    "compressing": SystemBackupStage.COMPRESSING,
                }.get(stage)
                if mapped is None:
                    return
                now_stage = datetime.now(tz=UTC)
                backup = repo.get_by_id(command.organization_id, command.backup_id)
                if backup is None:
                    return
                backup.mark_stage(mapped, now=now_stage)
                repo.update(backup)
                db.commit()

            try:
                result = pg_dump_custom(
                    database_url=settings.database_url,
                    output_path=output_path,
                    on_stage=on_stage,
                )
                finished = datetime.now(tz=UTC)
                backup = repo.get_by_id(command.organization_id, command.backup_id)
                if backup is None:
                    return
                duration = max(0, int((finished - backup.started_at).total_seconds()))
                backup.mark_completed(
                    file_size=result.size_bytes,
                    checksum=result.checksum_sha256,
                    duration_seconds=duration,
                    now=finished,
                )
                repo.update(backup)
                db.commit()
            except (DatabaseBackupError, OSError) as exc:
                db.rollback()
                backup = repo.get_by_id(command.organization_id, command.backup_id)
                if backup:
                    backup.mark_failed(error_message=str(exc), now=datetime.now(tz=UTC))
                    repo.update(backup)
                    db.commit()
        finally:
            db.close()
