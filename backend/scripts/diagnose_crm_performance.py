"""Measure CRM query and endpoint performance against the active database."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, event, func, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.modules.customers.application.list_customers import ListCustomersUseCase
from app.modules.customers.application.commands import ListCustomersQuery
from app.modules.customers.infrastructure.repositories.customer_communication_repository import (
    SqlAlchemyCustomerCommunicationRepository,
)
from app.modules.customers.infrastructure.repositories.customer_repository import SqlAlchemyCustomerRepository


ORG_ID = UUID("00000000-0000-4000-8000-000000000010")


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    slow_sql: list[tuple[float, str]] = []

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start = conn.info["query_start_time"].pop(-1)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms >= 50:
            slow_sql.append((elapsed_ms, statement.replace("\n", " ")[:200]))

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    print("=== DB connectivity ===")
    t0 = time.perf_counter()
    session.execute(text("SELECT 1")).scalar()
    print(f"SELECT 1: {_ms(t0)} ms")

    print("\n=== Table stats ===")
    for table in (
        "crm_customers",
        "crm_customer_emails",
        "crm_customer_phones",
        "crm_customer_websites",
        "system_data_operation_runs",
    ):
        count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"{table}: {count}")

    print("\n=== Running / queued data operations ===")
    rows = session.execute(
        text(
            """
            SELECT id, operation_key, status, started_at
            FROM system_data_operation_runs
            WHERE status IN ('queued', 'running')
            ORDER BY started_at DESC
            LIMIT 5
            """
        )
    ).all()
    if rows:
        for row in rows:
            print(row)
    else:
        print("none")

    print("\n=== crm_customers indexes ===")
    index_rows = session.execute(
        text(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'crm_customers'
            ORDER BY indexname
            """
        )
    ).all()
    for name, definition in index_rows:
        print(f"{name}: {definition}")

    print("\n=== Customer list use case (page 1, sort name asc) ===")
    repo = SqlAlchemyCustomerRepository(session)
    comm_repo = SqlAlchemyCustomerCommunicationRepository(session)
    use_case = ListCustomersUseCase(repo, comm_repo)

    timings: dict[str, float] = {}
    t_list = time.perf_counter()
    result = use_case.execute(
        ListCustomersQuery(
            organization_id=ORG_ID,
            status=None,
            include_archived=False,
            customer_type=None,
            country=None,
            search=None,
            page=1,
            page_size=25,
            sort_by="display_name",
            sort_dir="asc",
        )
    )
    timings["list_use_case_total"] = _ms(t_list)
    timings["items_returned"] = len(result.items)
    timings["total_count"] = result.total
    print(timings)

    print("\n=== Isolated repository timings ===")
    t_count = time.perf_counter()
    repo.list_by_organization(ORG_ID, page=1, page_size=25, sort_by="display_name", sort_dir="asc")
    timings["list_by_organization"] = _ms(t_count)
    print(f"list_by_organization (includes count+page): {timings['list_by_organization']} ms")

    customer_ids = [item.id for item in result.items]
    t_comm = time.perf_counter()
    comm_repo.load_list_summaries(customer_ids)
    print(f"load_list_summaries(25 ids): {_ms(t_comm)} ms")

    print("\n=== EXPLAIN (count filter status != deleted) ===")
    plan = session.execute(
        text(
            """
            EXPLAIN ANALYZE
            SELECT COUNT(crm_customers.id)
            FROM crm_customers
            WHERE organization_id = :org
              AND status != 'deleted'
            """
        ),
        {"org": str(ORG_ID)},
    ).all()
    for line, in plan:
        print(line)

    print("\n=== EXPLAIN (list page sort display_name) ===")
    plan = session.execute(
        text(
            """
            EXPLAIN ANALYZE
            SELECT id
            FROM crm_customers
            WHERE organization_id = :org
              AND status != 'deleted'
            ORDER BY lower(display_name) ASC, id ASC
            LIMIT 25 OFFSET 0
            """
        ),
        {"org": str(ORG_ID)},
    ).all()
    for line, in plan:
        print(line)

    if slow_sql:
        print(f"\n=== SQL queries >= 50ms ({len(slow_sql)}) ===")
        for elapsed_ms, statement in sorted(slow_sql, reverse=True)[:15]:
            print(f"{elapsed_ms:.1f} ms | {statement}")

    print("\n=== Timed compare: separate count+page vs window count (no search) ===")
    from app.modules.customers.infrastructure.persistence.models import CustomerModel
    from app.modules.customers.domain.value_objects import CustomerStatus

    base = session.query(CustomerModel).filter(
        CustomerModel.organization_id == ORG_ID,
        CustomerModel.status != CustomerStatus.DELETED.value,
    )
    t_count = time.perf_counter()
    base.with_entities(func.count(CustomerModel.id)).order_by(None).scalar()
    count_only_ms = _ms(t_count)

    t_page = time.perf_counter()
    base.order_by(func.lower(CustomerModel.display_name).asc(), CustomerModel.id.asc()).limit(25).all()
    page_only_ms = _ms(t_page)

    t_window = time.perf_counter()
    total_count = func.count(CustomerModel.id).over().label("_total_count")
    base.with_entities(CustomerModel, total_count).order_by(
        func.lower(CustomerModel.display_name).asc(),
        CustomerModel.id.asc(),
    ).limit(25).all()
    window_ms = _ms(t_window)

    print(
        {
            "count_only_ms": count_only_ms,
            "page_only_ms": page_only_ms,
            "count_plus_page_ms": round(count_only_ms + page_only_ms, 2),
            "window_count_page_ms": window_ms,
        }
    )

    session.close()
    engine.dispose()


if __name__ == "__main__":
    main()
