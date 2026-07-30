"""Excel export for the Customers screen — same filters as list, no pagination."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core.pagination import normalize_sort_direction
from app.modules.customers.application.commands import ExportCustomersQuery
from app.modules.customers.application.list_customers import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_DIRECTION,
    DEFAULT_SORT_FIELD,
    resolve_customer_list_sort,
)
from app.modules.customers.domain.ports import CustomerRepository
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.participations.infrastructure.persistence.models import (
    CustomerFairParticipationModel,
)

EXPORT_HEADERS = [
    "Müşteri Adı",
    "Yasal Ünvan",
    "Ticari Ünvan",
    "Tip",
    "Durum",
    "Şehir",
    "Ülke",
    "Web Sitesi",
    "Fuarlar",
    "E-posta",
    "Telefon",
]


def _join_values(values: list[str]) -> str:
    return ", ".join(value for value in values if value and value.strip())


def _load_fair_names_by_customer(
    session: Session,
    customer_ids: list[UUID],
) -> dict[UUID, list[str]]:
    if not customer_ids:
        return {}
    rows = (
        session.query(
            CustomerFairParticipationModel.customer_id,
            CustomerFairParticipationModel.fair_id,
            FairModel.name,
        )
        .join(FairModel, FairModel.id == CustomerFairParticipationModel.fair_id)
        .filter(
            CustomerFairParticipationModel.customer_id.in_(customer_ids),
            CustomerFairParticipationModel.deleted_at.is_(None),
        )
        .order_by(FairModel.name.asc(), CustomerFairParticipationModel.fair_id.asc())
        .all()
    )
    grouped: dict[UUID, list[str]] = defaultdict(list)
    seen_names: dict[UUID, set[str]] = defaultdict(set)
    seen_fair_ids: dict[UUID, set[UUID]] = defaultdict(set)
    for customer_id, fair_id, fair_name in rows:
        if not fair_name or not fair_name.strip():
            continue
        name = fair_name.strip()
        # Same fair_id or duplicate display name must appear only once.
        if fair_id in seen_fair_ids[customer_id] or name in seen_names[customer_id]:
            continue
        seen_fair_ids[customer_id].add(fair_id)
        seen_names[customer_id].add(name)
        grouped[customer_id].append(name)
    return grouped


class ExportCustomersUseCase:
    def __init__(
        self,
        repository: CustomerRepository,
        communication_repository: SqlAlchemyCustomerCommunicationRepository,
        session: Session,
    ) -> None:
        self._repository = repository
        self._communication_repository = communication_repository
        self._session = session

    def execute(self, query: ExportCustomersQuery) -> tuple[str, BytesIO]:
        requested = query.sort_by if query.sort_by in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
        sort_by = resolve_customer_list_sort(requested)
        sort_dir = normalize_sort_direction(query.sort_dir or DEFAULT_SORT_DIRECTION)

        customers = self._repository.list_all_matching(
            query.organization_id,
            status=query.status,
            include_archived=query.include_archived,
            customer_type=query.customer_type,
            country=query.country,
            search=query.search,
            missing_info=query.missing_info,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        customer_ids = [customer.id for customer in customers]
        communications = self._communication_repository.load_for_customers(customer_ids)
        fair_names = _load_fair_names_by_customer(self._session, customer_ids)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "customers"
        sheet.append(EXPORT_HEADERS)

        for customer in customers:
            comm = communications.get(customer.id)
            websites = [item.website for item in (comm.websites if comm else [])]
            emails = [item.email for item in (comm.emails if comm else [])]
            phones = [item.phone for item in (comm.phones if comm else [])]
            sheet.append(
                [
                    customer.display_name,
                    customer.legal_name or "",
                    customer.trade_name or "",
                    customer.customer_type.value,
                    customer.status.value,
                    customer.city or "",
                    customer.country or "",
                    _join_values(websites),
                    _join_values(fair_names.get(customer.id, [])),
                    _join_values(emails),
                    _join_values(phones),
                ]
            )

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        stamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        return f"customers_{stamp}.xlsx", buffer
