"""Resolve CRM fairs linked to an adapter via scraper run history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.modules.fairs.domain.services.normalizers import compute_normalized_name
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.imports.infrastructure.persistence.models import ImportBatchModel
from app.modules.scraper.core.manifest_registry import ManifestRegistry, get_manifest_registry
from app.modules.scraper.domain.adapter_linked_fair import AdapterLinkedFair
from app.modules.scraper.infrastructure.persistence.models import ScraperRunHistoryModel


@dataclass
class _RunFairAggregate:
    display_name: str
    source_url: str | None
    last_run_at: datetime | None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AdapterLinkedFairService:
    def __init__(
        self,
        session: Session,
        manifest_registry: ManifestRegistry | None = None,
    ) -> None:
        self._session = session
        self._manifest_registry = manifest_registry or get_manifest_registry()

    def list_linked_fairs(self, organization_id: UUID, adapter_key: str) -> list[AdapterLinkedFair]:
        self._manifest_registry.get(adapter_key)

        aggregates = self._aggregate_runs_by_fair_name(adapter_key)
        if not aggregates:
            return []

        fair_models = self._session.scalars(
            select(FairModel).where(
                FairModel.organization_id == organization_id,
                FairModel.deleted_at.is_(None),
            )
        ).all()
        fair_by_normalized = {model.normalized_name: model for model in fair_models}

        matched_fair_ids: list[UUID] = []
        results: list[AdapterLinkedFair] = []
        matched_keys: set[str] = set()

        for normalized_name, aggregate in aggregates.items():
            fair_model = fair_by_normalized.get(normalized_name)
            if fair_model is None:
                continue
            matched_keys.add(normalized_name)
            matched_fair_ids.append(fair_model.id)
            results.append(
                AdapterLinkedFair(
                    id=fair_model.id,
                    name=fair_model.name,
                    venue=fair_model.venue,
                    city=fair_model.city,
                    status=fair_model.status,
                    source_url=aggregate.source_url,
                    last_import_at=aggregate.last_run_at,
                )
            )

        for normalized_name, aggregate in aggregates.items():
            if normalized_name in matched_keys:
                continue
            results.append(
                AdapterLinkedFair(
                    id=None,
                    name=aggregate.display_name,
                    venue=None,
                    city=None,
                    status=None,
                    source_url=aggregate.source_url,
                    last_import_at=aggregate.last_run_at,
                )
            )

        import_times = self._latest_import_times(organization_id, matched_fair_ids)
        enriched: list[AdapterLinkedFair] = []
        for item in results:
            batch_at = import_times.get(item.id) if item.id is not None else None
            last_import_at = item.last_import_at
            if batch_at is not None:
                batch_at = _ensure_utc(batch_at)
            if last_import_at is not None:
                last_import_at = _ensure_utc(last_import_at)
            if batch_at is not None and (last_import_at is None or batch_at > last_import_at):
                last_import_at = batch_at
            enriched.append(
                AdapterLinkedFair(
                    id=item.id,
                    name=item.name,
                    venue=item.venue,
                    city=item.city,
                    status=item.status,
                    source_url=item.source_url,
                    last_import_at=last_import_at,
                )
            )

        enriched.sort(
            key=lambda row: row.last_import_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return enriched

    def _aggregate_runs_by_fair_name(self, adapter_key: str) -> dict[str, _RunFairAggregate]:
        stmt = (
            select(ScraperRunHistoryModel)
            .where(
                ScraperRunHistoryModel.adapter_key == adapter_key,
                ScraperRunHistoryModel.fair_name.is_not(None),
                ScraperRunHistoryModel.fair_name != "",
            )
            .order_by(desc(ScraperRunHistoryModel.started_at))
        )
        aggregates: dict[str, _RunFairAggregate] = {}
        for model in self._session.scalars(stmt).all():
            fair_name = str(model.fair_name).strip()
            if not fair_name:
                continue
            normalized_name = compute_normalized_name(name=fair_name)
            if not normalized_name:
                continue

            finished_at = model.finished_at or model.started_at
            existing = aggregates.get(normalized_name)
            if existing is None:
                aggregates[normalized_name] = _RunFairAggregate(
                    display_name=fair_name,
                    source_url=model.input_url,
                    last_run_at=finished_at,
                )
                continue

            if existing.last_run_at is None or (
                finished_at is not None and finished_at > existing.last_run_at
            ):
                aggregates[normalized_name] = _RunFairAggregate(
                    display_name=fair_name,
                    source_url=model.input_url or existing.source_url,
                    last_run_at=finished_at,
                )
        return aggregates

    def _latest_import_times(
        self,
        organization_id: UUID,
        fair_ids: list[UUID],
    ) -> dict[UUID, datetime]:
        if not fair_ids:
            return {}
        stmt = (
            select(
                ImportBatchModel.fair_id,
                func.max(ImportBatchModel.created_at),
            )
            .where(
                ImportBatchModel.organization_id == organization_id,
                ImportBatchModel.fair_id.in_(fair_ids),
            )
            .group_by(ImportBatchModel.fair_id)
        )
        return {
            fair_id: created_at
            for fair_id, created_at in self._session.execute(stmt).all()
            if fair_id is not None and created_at is not None
        }


def create_adapter_linked_fair_service(session: Session) -> AdapterLinkedFairService:
    return AdapterLinkedFairService(session)
