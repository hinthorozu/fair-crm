import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository
from app.modules.imports.application.analyze_canonical_import import AnalyzeCanonicalImportUseCase
from app.modules.imports.application.commands import CreateImportBatchFromCanonicalCommand
from app.modules.imports.application.create_import_batch_from_canonical import (
    CreateImportBatchFromCanonicalUseCase,
)
from app.modules.imports.domain.exceptions import InvalidCanonicalImportError
from app.modules.scraper.infrastructure.handoff_storage import is_safe_handoff_artifact_path
from app.modules.scraper.infrastructure.repositories.scraper_run_history_repository import (
    LatestCompletedSystemRun,
    ScraperRunHistoryRepository,
)


@dataclass(frozen=True)
class CompareSystemFairImportCommand:
    organization_id: UUID
    fair_id: UUID
    user_id: UUID
    access_token: str


@dataclass(frozen=True)
class CompareSystemFairImportResult:
    batch_id: UUID


class CompareSystemFairImportUseCase:
    def __init__(
        self,
        fair_repository: FairRepository,
        run_history_repository: ScraperRunHistoryRepository,
        create_batch: CreateImportBatchFromCanonicalUseCase,
        analyze_batch: AnalyzeCanonicalImportUseCase,
    ) -> None:
        self._fair_repository = fair_repository
        self._run_history_repository = run_history_repository
        self._create_batch = create_batch
        self._analyze_batch = analyze_batch

    def execute(self, command: CompareSystemFairImportCommand) -> CompareSystemFairImportResult:
        fair = self._fair_repository.get_visible(command.organization_id, command.fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")
        if fair.origin != "system":
            raise ForbiddenError("Only system fairs can be compared with CRM")

        latest = self._run_history_repository.list_latest_completed_system_runs([fair.id]).get(fair.id)
        document = _load_completed_handoff(latest)
        created = self._create_batch.execute(
            CreateImportBatchFromCanonicalCommand(
                organization_id=command.organization_id,
                user_id=command.user_id,
                access_token=command.access_token,
                document=document,
                fair_id=fair.id,
            ),
            resolved_fair=fair,
        )
        self._analyze_batch.execute(
            organization_id=command.organization_id,
            batch_id=created.batch.id,
            user_id=command.user_id,
            access_token=command.access_token,
        )
        return CompareSystemFairImportResult(batch_id=created.batch.id)


def _load_completed_handoff(run: LatestCompletedSystemRun | None) -> dict:
    path_text = "" if run is None else (run.output_json_path or "").strip()
    if run is None or not path_text:
        raise InvalidCanonicalImportError("Completed scraper handoff is not available")
    if not is_safe_handoff_artifact_path(path_text, run_id=run.run_id):
        raise InvalidCanonicalImportError("Completed scraper handoff is not available")
    try:
        document = json.loads(Path(path_text).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidCanonicalImportError("Completed scraper handoff is not available") from exc
    if not isinstance(document, dict) or not document:
        raise InvalidCanonicalImportError("Completed scraper handoff is not available")
    return document
