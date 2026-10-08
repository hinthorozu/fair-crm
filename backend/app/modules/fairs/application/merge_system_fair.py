"""User-directed merge of one duplicate System Fair into another.

The duplicate is archived after references move. It is not hard-deleted:
Fair removal in this catalog is archive, and a system fair cannot be restored.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.integrations.kyrox_core.client import HttpAuditAdapter
from app.modules.activities.infrastructure.persistence.models import ActivityModel
from app.modules.fair_emails.infrastructure.persistence.models import FairEmailBatchModel
from app.modules.fairs.domain.exceptions import (
    FairNotFoundError,
    SystemFairAlreadyMergedError,
    SystemFairMergeBlockedError,
)
from app.modules.fairs.domain.services.normalizers import (
    compute_identity_name,
    edition_key,
    fair_city_key,
)
from app.modules.fairs.infrastructure.persistence.models import (
    FairModel,
    SystemFairSeparationModel,
)
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.mail_send_operations.infrastructure.persistence.models import (
    MailSendOperationModel,
)
from app.modules.operations.infrastructure.persistence.models import OperationModel
from app.modules.participations.infrastructure.persistence.models import (
    CustomerFairParticipationModel,
)
from app.modules.quotes.infrastructure.models import QuoteModel
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel
from app.modules.todos.infrastructure.persistence.models import TodoModel

TOBB_SOURCE = "tobb"
_FAIR_SOURCE_KINDS = {"fair", "multiple_fairs"}


@dataclass(frozen=True)
class SystemFairMergeCommand:
    organization_id: UUID
    user_id: UUID
    access_token: str
    source_fair_id: UUID
    target_fair_id: UUID


@dataclass(frozen=True)
class MergeBlock:
    code: str
    message: str


@dataclass(frozen=True)
class MergeAnalysis:
    participations: int
    todos: int
    quotes: int
    activities: int
    imports: int
    scraper_runs: int
    email_batches: int
    mail_operations: int
    operations: int
    blocking_conflicts: tuple[MergeBlock, ...]


@dataclass(frozen=True)
class DuplicateFairSummary:
    id: UUID
    name: str
    city: str | None
    start_date: date | None
    end_date: date | None
    organizer: str | None
    website: str | None
    external_id: str | None
    source: str | None
    participations: int
    todos: int
    quotes: int
    imports: int
    scraper_runs: int
    has_scraper_config: bool


@dataclass(frozen=True)
class DuplicateGroup:
    identity_name: str
    city: str | None
    fairs: tuple[DuplicateFairSummary, ...]


def repoint_operation_documents(
    *,
    source_kind: str,
    source_config: dict[str, Any] | None,
    type_config: dict[str, Any] | None,
    source_id: UUID,
    target_id: UUID,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Rewrite only fair-reference keys. Other JSON values stay as stored."""
    source_text = str(source_id)
    target_text = str(target_id)
    config = dict(source_config or {})
    typed = dict(type_config or {})
    changed = False

    def replace_scalar(container: dict[str, Any], key: str) -> None:
        nonlocal changed
        if key not in container or container[key] is None:
            return
        if str(container[key]) == source_text:
            container[key] = target_text
            changed = True

    def replace_list(container: dict[str, Any], key: str) -> None:
        nonlocal changed
        raw = container.get(key)
        if not isinstance(raw, list):
            return
        if source_text not in {str(item) for item in raw}:
            return
        updated: list[str] = []
        seen: set[str] = set()
        for item in raw:
            value = target_text if str(item) == source_text else str(item)
            if value != str(item) or value in seen:
                changed = True
            if value in seen:
                continue
            seen.add(value)
            updated.append(value)
        if updated != [str(item) for item in raw]:
            changed = True
        container[key] = updated

    if source_kind in _FAIR_SOURCE_KINDS:
        replace_list(config, "source_ids")
    replace_scalar(config, "fair_id")
    replace_list(config, "fair_ids")
    replace_scalar(typed, "fair_id")
    replace_list(typed, "fair_ids")
    return config, typed, changed


def _filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return len(value) > 0
    return True


def _same_year_distinct_editions(fairs: list[FairModel]) -> bool:
    years: set[int] = set()
    editions: list[tuple[str, ...]] = []
    for fair in fairs:
        if not fair.external_id or ":" not in fair.external_id:
            return False
        prefix = fair.external_id.split(":", 1)[0]
        if not prefix.isdigit():
            return False
        years.add(int(prefix))
        key = edition_key(fair.name)
        if not key:
            return False
        editions.append(key)
    return len(years) == 1 and len(set(editions)) == len(editions)


class SystemFairDuplicateService:
    def __init__(
        self,
        session: Session,
        repository: SqlAlchemyFairRepository,
        audit: HttpAuditAdapter,
    ) -> None:
        self._session = session
        self._repository = repository
        self._audit = audit
        self._failpoint: str | None = None

    def list_groups(self) -> list[DuplicateGroup]:
        fairs = (
            self._session.query(FairModel)
            .filter(
                FairModel.origin == "system",
                FairModel.source == TOBB_SOURCE,
                FairModel.deleted_at.is_(None),
            )
            .all()
        )
        separated = self._repository.list_system_fair_separation_ids(source=TOBB_SOURCE)
        grouped: dict[tuple[str, str], list[FairModel]] = defaultdict(list)
        for fair in fairs:
            grouped[(compute_identity_name(name=fair.name), fair_city_key(fair.city))].append(fair)

        groups: list[DuplicateGroup] = []
        for (identity_name, _city_key), members in grouped.items():
            if len(members) < 2 or _same_year_distinct_editions(members):
                continue
            if all(member.id in separated for member in members):
                continue
            groups.append(
                DuplicateGroup(
                    identity_name=identity_name,
                    city=members[0].city,
                    fairs=tuple(self._summaries(members)),
                )
            )
        groups.sort(key=lambda group: (group.identity_name, group.city or ""))
        return groups

    def preview(self, source_fair_id: UUID, target_fair_id: UUID) -> MergeAnalysis:
        source, target = self._load_pair(source_fair_id, target_fair_id)
        return self._analyze(source, target)

    def merge(self, command: SystemFairMergeCommand) -> MergeAnalysis:
        source, target = self._load_pair(command.source_fair_id, command.target_fair_id)
        analysis = self._analyze(source, target)
        if analysis.blocking_conflicts:
            raise SystemFairMergeBlockedError(
                [
                    {"code": block.code, "message": block.message}
                    for block in analysis.blocking_conflicts
                ]
            )
        self._apply(source, target)
        self._audit.record_event(
            organization_id=command.organization_id,
            access_token=command.access_token,
            action="fair_crm.system_fair.merged",
            resource_type="fair",
            resource_id=str(target.id),
            metadata={
                "user_id": str(command.user_id),
                "source_fair_id": str(source.id),
                "target_fair_id": str(target.id),
                "participations": analysis.participations,
                "todos": analysis.todos,
                "quotes": analysis.quotes,
                "activities": analysis.activities,
                "imports": analysis.imports,
                "scraper_runs": analysis.scraper_runs,
                "email_batches": analysis.email_batches,
                "mail_operations": analysis.mail_operations,
                "operations": analysis.operations,
            },
        )
        return analysis

    def keep_separate(self, fair_ids: list[UUID]) -> int:
        if len(set(fair_ids)) < 2:
            raise SystemFairMergeBlockedError(
                [{"code": "too_few", "message": "Ayrı tutmak için en az iki fuar seçilmelidir."}]
            )
        fairs = [self._require_active_system_fair(fair_id) for fair_id in fair_ids]
        identity = compute_identity_name(name=fairs[0].name)
        city = fair_city_key(fairs[0].city)
        if any(
            compute_identity_name(name=fair.name) != identity or fair_city_key(fair.city) != city
            for fair in fairs[1:]
        ):
            raise SystemFairMergeBlockedError(
                [
                    {
                        "code": "different_identity",
                        "message": "Seçilen fuarlar aynı mükerrer gruba ait değil.",
                    }
                ]
            )
        existing = self._repository.list_system_fair_separation_ids(source=TOBB_SOURCE)
        now = datetime.now(tz=UTC)
        created = 0
        for fair in fairs:
            if fair.id in existing:
                continue
            self._session.add(
                SystemFairSeparationModel(
                    id=uuid4(),
                    source=TOBB_SOURCE,
                    identity_name=identity,
                    city_key=city,
                    fair_id=fair.id,
                    created_at=now,
                )
            )
            created += 1
        self._session.flush()
        return created

    def _apply(self, source: FairModel, target: FairModel) -> None:
        with self._session.begin_nested():
            self._repoint(source.id, target.id)
            self._copy_empty_scraper_fields(source, target)
            if self._failpoint == "after_repoint":
                raise RuntimeError("forced merge failure")
            now = datetime.now(tz=UTC)
            source.external_id = None
            source.archived_from_status = source.status
            source.status = "archived"
            source.deleted_at = now
            source.updated_at = now
            self._session.flush()
        self._session.expire_all()

    def _repoint(self, source_id: UUID, target_id: UUID) -> None:
        for model, column in (
            (CustomerFairParticipationModel, CustomerFairParticipationModel.fair_id),
            (QuoteModel, QuoteModel.fair_id),
            (TodoModel, TodoModel.source_fair_id),
            (ActivityModel, ActivityModel.fair_id),
            (ScraperRunHistoryModel, ScraperRunHistoryModel.fair_id),
            (ImportBatchModel, ImportBatchModel.fair_id),
            (FairEmailBatchModel, FairEmailBatchModel.fair_id),
            (MailSendOperationModel, MailSendOperationModel.fair_id),
        ):
            self._session.query(model).filter(column == source_id).update(
                {column.key: target_id},
                synchronize_session=False,
            )
        operations = self._operations_mentioning(source_id)
        for operation in operations:
            config, typed, changed = repoint_operation_documents(
                source_kind=operation.source_kind,
                source_config=operation.source_config,
                type_config=operation.type_config,
                source_id=source_id,
                target_id=target_id,
            )
            if changed:
                operation.source_config = config
                operation.type_config = typed
                operation.updated_at = datetime.now(tz=UTC)

    def _copy_empty_scraper_fields(self, source: FairModel, target: FairModel) -> None:
        if not _filled(target.adapter_key) and _filled(source.adapter_key):
            target.adapter_key = source.adapter_key
        if not _filled(target.source_url) and _filled(source.source_url):
            target.source_url = source.source_url
        if not _filled(target.scraper_config) and _filled(source.scraper_config):
            target.scraper_config = dict(source.scraper_config or {})
        target.updated_at = datetime.now(tz=UTC)

    def _analyze(self, source: FairModel, target: FairModel) -> MergeAnalysis:
        blocks: list[MergeBlock] = []
        source_participations = (
            self._session.query(CustomerFairParticipationModel)
            .filter(
                CustomerFairParticipationModel.fair_id == source.id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .all()
        )
        target_keys = {
            (row.organization_id, row.customer_id)
            for row in self._session.query(CustomerFairParticipationModel)
            .filter(
                CustomerFairParticipationModel.fair_id == target.id,
                CustomerFairParticipationModel.deleted_at.is_(None),
            )
            .all()
        }
        collisions = [
            row
            for row in source_participations
            if (row.organization_id, row.customer_id) in target_keys
        ]
        if collisions:
            blocks.append(
                MergeBlock(
                    code="participation_collision",
                    message="Aynı müşteri her iki fuarda da kayıtlı. Birleştirme durduruldu.",
                )
            )
        for field, label in (
            ("adapter_key", "adapter"),
            ("source_url", "kaynak adresi"),
            ("scraper_config", "scraper ayarı"),
        ):
            source_value = getattr(source, field)
            target_value = getattr(target, field)
            if _filled(source_value) and _filled(target_value) and source_value != target_value:
                blocks.append(
                    MergeBlock(
                        code="scraper_conflict",
                        message=f"İki fuarın {label} değeri farklı. Birleştirme durduruldu.",
                    )
                )
        operation_count = 0
        for operation in self._operations_mentioning(source.id):
            _config, _typed, changed = repoint_operation_documents(
                source_kind=operation.source_kind,
                source_config=operation.source_config,
                type_config=operation.type_config,
                source_id=source.id,
                target_id=target.id,
            )
            if changed:
                operation_count += 1
        return MergeAnalysis(
            participations=self._count(CustomerFairParticipationModel.fair_id, source.id),
            todos=self._count(TodoModel.source_fair_id, source.id),
            quotes=self._count(QuoteModel.fair_id, source.id),
            activities=self._count(ActivityModel.fair_id, source.id),
            imports=self._count(ImportBatchModel.fair_id, source.id),
            scraper_runs=self._count(ScraperRunHistoryModel.fair_id, source.id),
            email_batches=self._count(FairEmailBatchModel.fair_id, source.id),
            mail_operations=self._count(MailSendOperationModel.fair_id, source.id),
            operations=operation_count,
            blocking_conflicts=tuple(blocks),
        )

    def _operations_mentioning(self, fair_id: UUID) -> list[OperationModel]:
        needle = str(fair_id)
        return (
            self._session.query(OperationModel)
            .filter(
                or_(
                    cast(OperationModel.source_config, String).contains(needle),
                    cast(OperationModel.type_config, String).contains(needle),
                )
            )
            .all()
        )

    def _count(self, column: Any, fair_id: UUID) -> int:
        return self._session.query(column).filter(column == fair_id).count()

    def _load_pair(self, source_fair_id: UUID, target_fair_id: UUID) -> tuple[FairModel, FairModel]:
        if source_fair_id == target_fair_id:
            raise SystemFairMergeBlockedError(
                [{"code": "same_fair", "message": "Korunacak fuar ile birleştirilecek fuar aynı."}]
            )
        return (
            self._require_merge_source(source_fair_id),
            self._require_active_system_fair(target_fair_id),
        )

    def _require_merge_source(self, fair_id: UUID) -> FairModel:
        fair = self._session.get(FairModel, fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")
        if fair.origin != "system":
            raise ForbiddenError("Organization fairs cannot be merged")
        if fair.deleted_at is not None or fair.status == "archived":
            raise SystemFairAlreadyMergedError("System fair is already merged")
        return fair

    def _require_active_system_fair(self, fair_id: UUID) -> FairModel:
        fair = self._session.get(FairModel, fair_id)
        if fair is None:
            raise FairNotFoundError("Fair not found")
        if fair.origin != "system":
            raise ForbiddenError("Organization fairs cannot be merged")
        if fair.deleted_at is not None or fair.status == "archived":
            raise SystemFairMergeBlockedError(
                [
                    {
                        "code": "archived_target",
                        "message": "Arşivlenmiş bir fuar korunacak kayıt olamaz.",
                    }
                ]
            )
        return fair

    def _summaries(self, fairs: list[FairModel]) -> list[DuplicateFairSummary]:
        ids = [fair.id for fair in fairs]
        participation_counts = self._counts_by_fair(CustomerFairParticipationModel.fair_id, ids)
        todo_counts = self._counts_by_fair(TodoModel.source_fair_id, ids)
        quote_counts = self._counts_by_fair(QuoteModel.fair_id, ids)
        import_counts = self._counts_by_fair(ImportBatchModel.fair_id, ids)
        run_counts = self._counts_by_fair(ScraperRunHistoryModel.fair_id, ids)
        return [
            DuplicateFairSummary(
                id=fair.id,
                name=fair.name,
                city=fair.city,
                start_date=fair.start_date,
                end_date=fair.end_date,
                organizer=fair.organizer,
                website=fair.website,
                external_id=fair.external_id,
                source=fair.source,
                participations=participation_counts.get(fair.id, 0),
                todos=todo_counts.get(fair.id, 0),
                quotes=quote_counts.get(fair.id, 0),
                imports=import_counts.get(fair.id, 0),
                scraper_runs=run_counts.get(fair.id, 0),
                has_scraper_config=_filled(fair.adapter_key)
                or _filled(fair.source_url)
                or _filled(fair.scraper_config),
            )
            for fair in sorted(fairs, key=lambda item: (item.start_date or item.created_at, str(item.id)))
        ]

    def _counts_by_fair(self, column: Any, fair_ids: list[UUID]) -> dict[UUID, int]:
        if not fair_ids:
            return {}
        rows = (
            self._session.query(column, func.count())
            .filter(column.in_(fair_ids))
            .group_by(column)
            .all()
        )
        return {fair_id: int(count) for fair_id, count in rows if fair_id is not None}
