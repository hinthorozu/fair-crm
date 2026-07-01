from uuid import UUID

from app.core.pagination import build_paginated_meta, normalize_page_params, normalize_sort_direction
from app.modules.contacts.infrastructure.repositories.contact_repository import SqlAlchemyContactRepository
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.imports.application.commands import ImportRowListResult, ListImportRowsQuery
from app.modules.imports.application.mappers import row_to_result
from app.modules.imports.application.merge_preview_builder import MergePreviewBuilder
from app.modules.imports.domain.exceptions import ImportBatchNotFoundError
from app.modules.imports.domain.ports import ImportBatchRepository, ImportRowRepository
from app.modules.imports.domain.services.merge_preview import row_matches_filter, sort_rows
from app.modules.participations.infrastructure.repositories.participation_repository import (
    SqlAlchemyParticipationRepository,
)

ALLOWED_SORT_FIELDS = frozenset({"row_number", "company_name", "confidence", "status"})
DEFAULT_SORT_FIELD = "row_number"
DEFAULT_SORT_DIRECTION = "asc"


class ListImportRowsUseCase:
    def __init__(
        self,
        batch_repository: ImportBatchRepository,
        row_repository: ImportRowRepository,
        customer_repository: CustomerRepository,
        participation_repository: SqlAlchemyParticipationRepository,
        contact_repository: SqlAlchemyContactRepository,
    ) -> None:
        self._batch_repository = batch_repository
        self._row_repository = row_repository
        self._customer_repository = customer_repository
        self._preview_builder = MergePreviewBuilder(
            customer_repository,
            participation_repository,
            contact_repository,
        )

    def execute(self, query: ListImportRowsQuery) -> ImportRowListResult:
        batch = self._batch_repository.get_by_id(query.organization_id, query.batch_id)
        if batch is None:
            raise ImportBatchNotFoundError("Import batch not found")

        rows = self._row_repository.list_by_batch(query.organization_id, query.batch_id)

        if query.search:
            term = query.search.strip().lower()
            rows = [
                row
                for row in rows
                if term in str((row.normalized_data_json or {}).get("company_name") or "").lower()
            ]

        if query.filter:
            rows = [row for row in rows if row_matches_filter(row, query.filter)]

        sort_by = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)
        if sort_by == DEFAULT_SORT_FIELD:
            sort_by = None
        rows = sort_rows(rows, sort_by=sort_by, sort_dir=sort_dir)

        page_params = normalize_page_params(query.page, query.page_size)
        total = len(rows)
        page_rows = rows[page_params.offset : page_params.offset + page_params.page_size]

        customer_names: dict[UUID, str] = {}
        items = []
        for row in page_rows:
            if row.match_customer_id and row.match_customer_id not in customer_names:
                customer = self._customer_repository.get_by_id(
                    query.organization_id, row.match_customer_id
                )
                if customer:
                    customer_names[row.match_customer_id] = customer.display_name

            merge_preview = self._preview_builder.build_for_row(query.organization_id, batch, row)
            items.append(
                row_to_result(
                    row,
                    match_customer_name=customer_names.get(row.match_customer_id)
                    if row.match_customer_id
                    else None,
                    merge_preview=merge_preview,
                )
            )

        meta = build_paginated_meta(page_params.page, page_params.page_size, total)
        return ImportRowListResult(
            items=items,
            page=meta.page,
            page_size=meta.page_size,
            total=meta.total,
            total_pages=meta.total_pages,
        )
