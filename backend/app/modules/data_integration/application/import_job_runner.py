"""Background import job runner (Sprint 09.1)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.integrations.kyrox_core.dev_bypass import AllowAllAuthorizationAdapter, NoOpAuditAdapter, dev_bypass_enabled
from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.infrastructure.repositories.activity_repository import SqlAlchemyActivityRepository
from app.modules.contacts.infrastructure.repositories.contact_repository import SqlAlchemyContactRepository
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.data_integration.application.engine.import_executor import ImportExecutor
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.infrastructure.repositories.job_repository import SqlAlchemyImportJobRepository
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.commands import ApplyImportCommand
from app.modules.imports.domain.value_objects import ImportJobStatus
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)


@dataclass(frozen=True)
class ApplyJobCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    job_id: UUID


class ImportJobRunner:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def run_apply(self, command: ApplyJobCommand) -> None:
        """Run apply job synchronously (call from FastAPI BackgroundTasks after DB commit)."""
        self._run_apply(command)

    def _run_apply(self, command: ApplyJobCommand) -> None:
        db = self._session_factory()
        try:
            job_repo = SqlAlchemyImportJobRepository(db)
            job = job_repo.get_by_id(command.organization_id, command.job_id)
            if job is None:
                return

            now = datetime.now(tz=UTC)
            job.mark_running(now=now)
            job_repo.update(job)
            db.commit()

            batch_repo = SqlAlchemyImportBatchRepository(db)
            row_repo = SqlAlchemyImportRowRepository(db)
            # Apply permission was verified when the job was queued.
            authorization: AuthorizationPort = AllowAllAuthorizationAdapter()
            audit = NoOpAuditAdapter() if dev_bypass_enabled() else HttpAuditAdapter()

            apply_use_case = ApplyImportUseCase(
                batch_repo,
                row_repo,
                SqlAlchemyCustomerRepository(db),
                SqlAlchemyContactRepository(db),
                SqlAlchemyActivityRepository(db),
                SqlAlchemyParticipationRepository(db),
                authorization,
                audit,
            )
            executor = ImportExecutor(apply_use_case)
            result = executor.execute(
                ApplyImportCommand(
                    organization_id=command.organization_id,
                    user_id=command.user_id,
                    access_token=command.access_token,
                    batch_id=command.batch_id,
                )
            )

            job = job_repo.get_by_id(command.organization_id, command.job_id)
            if job:
                job.mark_completed(result=result.to_dict(), now=datetime.now(tz=UTC))
                job_repo.update(job)
            db.commit()
        except Exception as exc:
            db.rollback()
            try:
                job_repo = SqlAlchemyImportJobRepository(db)
                job = job_repo.get_by_id(command.organization_id, command.job_id)
                if job:
                    job.mark_failed(error_message=str(exc), now=datetime.now(tz=UTC))
                    job_repo.update(job)
                db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()
