from dataclasses import dataclass

from app.core.pagination import build_paginated_meta, normalize_page_params, normalize_sort_direction
from app.modules.fairs.domain.ports import FairRepository
from app.modules.imports.application.batch_display_metadata import build_fair_name_lookup
from app.modules.imports.application.commands import ListImportBatchesQuery
from app.modules.imports.application.mappers import batch_to_result
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository

ALLOWED_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "file_name", "status", "total_rows", "completed_at"}
)
DEFAULT_SORT_FIELD = "created_at"
DEFAULT_SORT_DIRECTION = "desc"


@dataclass
class ListImportBatchesResult:
    items: list
    page: int
    page_size: int
    total: int
    total_pages: int


class ListImportBatchesUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        fair_repository: FairRepository,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._fair_repository = fair_repository

    def execute(self, query: ListImportBatchesQuery) -> ListImportBatchesResult:
        params = normalize_page_params(query.page, query.page_size)
        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)
        batches, total = self._batch_repository.list_paginated(
            query.organization_id,
            page=params.page,
            page_size=params.page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        fair_ids = {batch.fair_id for batch in batches if batch.fair_id is not None}
        fair_names = build_fair_name_lookup(
            self._fair_repository,
            organization_id=query.organization_id,
            fair_ids=fair_ids,
        )
        items = []
        for batch in batches:
            rows = self._row_repository.list_by_batch(query.organization_id, batch.id)
            fair_name = fair_names.get(batch.fair_id) if batch.fair_id is not None else None
            items.append(batch_to_result(batch, rows, fair_name=fair_name))
        meta = build_paginated_meta(page=params.page, page_size=params.page_size, total=total)
        return ListImportBatchesResult(
            items=items,
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )
