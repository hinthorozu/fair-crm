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
from app.modules.customers.application.customer_communication_sync import CustomerCommunicationSyncService
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository
from app.modules.data_integration.application.engine.import_executor import ImportExecutor
from app.modules.data_integration.domain.entities import ImportJob
from app.modules.data_integration.infrastructure.repositories.job_repository import SqlAlchemyImportJobRepository
from app.modules.imports.application.analyze_canonical_import import AnalyzeCanonicalImportUseCase
from app.modules.imports.application.analyze_import import AnalyzeImportUseCase
from app.modules.imports.application.apply_import import ApplyImportUseCase
from app.modules.imports.application.commands import AnalyzeImportCommand, ApplyImportCommand
from app.modules.imports.domain.value_objects import ImportJobStatus, ImportSourceType
from app.modules.imports.infrastructure.repositories.import_repository import (
    SqlAlchemyImportBatchRepository,
    SqlAlchemyImportRowRepository,
)
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)


def _communication_sync(db: Session) -> CustomerCommunicationSyncService:
    return CustomerCommunicationSyncService(SqlAlchemyCustomerCommunicationRepository(db))


@dataclass(frozen=True)
class ApplyJobCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    job_id: UUID


@dataclass(frozen=True)
class BulkDecisionJobCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    job_id: UUID
    action_type: str


@dataclass(frozen=True)
class AnalyzeJobCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    batch_id: UUID
    job_id: UUID


class ImportJobRunner:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    @staticmethod
    def _uses_canonical_analyze(batch) -> bool:
        if batch.source_type == ImportSourceType.SCRAPER:
            return True
        preview = batch.raw_preview_json or {}
        return isinstance(preview, dict) and "canonical_source" in preview

    def run_apply(self, command: ApplyJobCommand) -> None:
        """Run apply job synchronously (call from FastAPI BackgroundTasks after DB commit)."""
        self._run_apply(command)

    def run_bulk_decision(self, command: BulkDecisionJobCommand) -> None:
        """Run bulk decision job synchronously (call from FastAPI BackgroundTasks after DB commit)."""
        self._run_bulk_decision(command)

    def run_analyze(self, command: AnalyzeJobCommand) -> None:
        """Run analyze job synchronously (call from FastAPI BackgroundTasks after DB commit)."""
        self._run_analyze(command)

    def _run_analyze(self, command: AnalyzeJobCommand) -> None:
        db = self._session_factory()
        try:
            job_repo = SqlAlchemyImportJobRepository(db)
            batch_repo = SqlAlchemyImportBatchRepository(db)
            job = job_repo.get_by_id(command.organization_id, command.job_id)
            if job is None:
                return

            now = datetime.now(tz=UTC)
            batch = batch_repo.get_by_id(command.organization_id, command.batch_id)
            if batch is not None:
                batch.mark_analyzing(now=now)
                batch_repo.update(batch)
            job.mark_running(now=now)
            job_repo.update(job)
            db.commit()

            authorization: AuthorizationPort = AllowAllAuthorizationAdapter()
            audit = NoOpAuditAdapter() if dev_bypass_enabled() else HttpAuditAdapter()
            if batch is not None and self._uses_canonical_analyze(batch):
                analyze_use_case = AnalyzeCanonicalImportUseCase(
                    batch_repo,
                    SqlAlchemyImportRowRepository(db),
                    SqlAlchemyCustomerRepository(db),
                    SqlAlchemyParticipationRepository(db),
                    authorization,
                    audit,
                )
                result = analyze_use_case.execute(
                    organization_id=command.organization_id,
                    batch_id=command.batch_id,
                    user_id=command.user_id,
                    access_token=command.access_token,
                    skip_permission_check=True,
                    from_background_job=True,
                )
            else:
                analyze_use_case = AnalyzeImportUseCase(
                    batch_repo,
                    SqlAlchemyImportRowRepository(db),
                    SqlAlchemyCustomerRepository(db),
                    SqlAlchemyParticipationRepository(db),
                    authorization,
                    audit,
                )
                result = analyze_use_case.execute(
                    AnalyzeImportCommand(
                        organization_id=command.organization_id,
                        user_id=command.user_id,
                        access_token=command.access_token,
                        batch_id=command.batch_id,
                        from_background_job=True,
                    )
                )

            job = job_repo.get_by_id(command.organization_id, command.job_id)
            if job:
                job.mark_completed(
                    result={"total_rows": result.total_rows, "batch_status": result.batch.status.value},
                    now=datetime.now(tz=UTC),
                )
                job_repo.update(job)
            db.commit()
        except Exception as exc:
            db.rollback()
            try:
                job_repo = SqlAlchemyImportJobRepository(db)
                batch_repo = SqlAlchemyImportBatchRepository(db)
                job = job_repo.get_by_id(command.organization_id, command.job_id)
                if job:
                    job.mark_failed(error_message=str(exc), now=datetime.now(tz=UTC))
                    job_repo.update(job)
                batch = batch_repo.get_by_id(command.organization_id, command.batch_id)
                if batch:
                    batch.mark_analysis_failed(notes=str(exc), now=datetime.now(tz=UTC))
                    batch_repo.update(batch)
                db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()

    def _run_bulk_decision(self, command: BulkDecisionJobCommand) -> None:
        db = self._session_factory()
        try:
            job_repo = SqlAlchemyImportJobRepository(db)
            batch_repo = SqlAlchemyImportBatchRepository(db)
            row_repo = SqlAlchemyImportRowRepository(db)
            job = job_repo.get_by_id(command.organization_id, command.job_id)
            if job is None:
                return

            now = datetime.now(tz=UTC)
            job.mark_running(now=now)
            job_repo.update(job)
            db.commit()

            rows = row_repo.list_by_batch(command.organization_id, command.batch_id)
            batch = batch_repo.get_by_id(command.organization_id, command.batch_id)
            if batch is None:
                raise RuntimeError("Import batch not found")

            authorization: AuthorizationPort = AllowAllAuthorizationAdapter()
            audit = NoOpAuditAdapter() if dev_bypass_enabled() else HttpAuditAdapter()
            apply_use_case = ApplyImportUseCase(
                batch_repo,
                row_repo,
                SqlAlchemyCustomerRepository(db),
                _communication_sync(db),
                SqlAlchemyContactRepository(db),
                SqlAlchemyActivityRepository(db),
                SqlAlchemyParticipationRepository(db),
                authorization,
                audit,
            )

            to_update: list = []
            rows_to_delete: list = []

            if command.action_type == "link_all_existing":
                from app.modules.imports.domain.services.bulk_link_existing_to_fair import (
                    LinkExistingRowCategory,
                    apply_link_existing_to_fair_row,
                )

                participation_repo = SqlAlchemyParticipationRepository(db)
                customer_repo = SqlAlchemyCustomerRepository(db)
                processed = 0
                skipped = 0
                errors = 0
                for row in rows:
                    try:
                        result = apply_link_existing_to_fair_row(
                            row,
                            batch=batch,
                            participation_lookup=participation_repo,
                            customer_lookup=customer_repo,
                            now=now,
                        )
                        if result == LinkExistingRowCategory.TO_LINK:
                            rows_to_delete.append(row.id)
                            batch.increment_apply_counts(
                                updated_rows=1,
                                created_participations=1,
                                now=now,
                            )
                            processed += 1
                        elif result == LinkExistingRowCategory.ALREADY_LINKED:
                            rows_to_delete.append(row.id)
                            batch.increment_apply_counts(skipped_rows=1, now=now)
                            skipped += 1
                        elif result is None:
                            continue
                    except Exception:
                        errors += 1
            else:
                from app.modules.imports.domain.services.bulk_decision_actions import apply_bulk_decision_to_row

                processed = 0
                skipped = 0
                errors = 0
                for row in rows:
                    try:
                        if apply_bulk_decision_to_row(row, command.action_type):
                            to_update.append(row)
                            processed += 1
                        else:
                            skipped += 1
                    except Exception:
                        errors += 1

                if to_update:
                    row_repo.update_many(to_update)

                apply_cmd = ApplyImportCommand(
                    organization_id=command.organization_id,
                    user_id=command.user_id,
                    access_token=command.access_token,
                    batch_id=command.batch_id,
                )
                for row in to_update:
                    try:
                        apply_use_case.finalize_applied_row(batch, row, apply_cmd, now)
                    except Exception:
                        errors += 1

            if rows_to_delete:
                row_repo.delete_many(
                    command.organization_id,
                    command.batch_id,
                    rows_to_delete,
                )

            all_rows = row_repo.list_by_batch(command.organization_id, command.batch_id)
            batch = apply_use_case.sync_batch_progress(batch, all_rows, now=now)
            batch_repo.update(batch)

            job = job_repo.get_by_id(command.organization_id, command.job_id)
            if job:
                job.mark_completed(
                    result={
                        "action_type": command.action_type,
                        "processed_rows": processed,
                        "skipped_rows": skipped,
                        "error_rows": errors,
                    },
                    now=datetime.now(tz=UTC),
                )
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
            batch = batch_repo.get_by_id(command.organization_id, command.batch_id)
            if batch is not None:
                batch.mark_applying(now=datetime.now(tz=UTC))
                batch_repo.update(batch)
                db.commit()
            # Apply permission was verified when the job was queued.
            authorization: AuthorizationPort = AllowAllAuthorizationAdapter()
            audit = NoOpAuditAdapter() if dev_bypass_enabled() else HttpAuditAdapter()

            apply_use_case = ApplyImportUseCase(
                batch_repo,
                row_repo,
                SqlAlchemyCustomerRepository(db),
                _communication_sync(db),
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
