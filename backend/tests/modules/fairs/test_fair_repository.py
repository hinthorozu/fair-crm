from datetime import UTC, datetime

from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.infrastructure.repositories.fair_repository import SqlAlchemyFairRepository


def _seed_fair(session, organization_id, name: str) -> Fair:
    now = datetime.now(tz=UTC)
    fair = Fair.create(
        organization_id=organization_id,
        name=name,
        venue="Test Hall 1",
        city="Ankara",
        now=now,
    )
    repo = SqlAlchemyFairRepository(session)
    return repo.add(fair)


def test_org_isolation(db_session, organization_id, other_organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    saved = _seed_fair(db_session, organization_id, "Org A Fair")

    assert repo.get_by_id(organization_id, saved.id) is not None
    assert repo.get_by_id(other_organization_id, saved.id) is None


def test_search_includes_venue(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    _seed_fair(db_session, organization_id, "Hidden Name Fair")

    result = repo.list_by_organization(organization_id, search="Test Hall")
    assert len(result.items) == 1
    assert result.items[0].venue == "Test Hall 1"


def test_list_page_pagination(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    for index in range(3):
        _seed_fair(db_session, organization_id, f"Fair {index}")

    first_page = repo.list_by_organization(organization_id, page=1, page_size=2)
    assert len(first_page.items) == 2
    assert first_page.page == 1
    assert first_page.page_size == 2
    assert first_page.total == 3
    assert first_page.total_pages == 2

    second_page = repo.list_by_organization(organization_id, page=2, page_size=2)
    assert len(second_page.items) == 1
    assert second_page.page == 2


def test_list_archived_fairs(db_session, organization_id):
    from datetime import UTC, datetime

    from app.modules.fairs.domain.value_objects import FairStatus

    repo = SqlAlchemyFairRepository(db_session)
    active = _seed_fair(db_session, organization_id, "Active Fair")
    archived = _seed_fair(db_session, organization_id, "Archived Fair")
    archived.archive(now=datetime.now(tz=UTC))
    repo.update(archived)

    default_list = repo.list_by_organization(organization_id)
    assert len(default_list.items) == 2
    default_ids = {item.id for item in default_list.items}
    assert active.id in default_ids
    assert archived.id in default_ids

    archived_list = repo.list_by_organization(
        organization_id, status=FairStatus.ARCHIVED
    )
    assert len(archived_list.items) == 1
    assert archived_list.items[0].id == archived.id
    assert archived_list.items[0].status == FairStatus.ARCHIVED


def test_sort_by_start_date(db_session, organization_id):
    from datetime import date

    repo = SqlAlchemyFairRepository(db_session)
    now = datetime.now(tz=UTC)

    fair_late = Fair.create(
        organization_id=organization_id,
        name="Late Fair",
        start_date=date(2026, 12, 1),
        now=now,
    )
    fair_early = Fair.create(
        organization_id=organization_id,
        name="Early Fair",
        start_date=date(2026, 1, 1),
        now=now,
    )
    repo.add(fair_late)
    repo.add(fair_early)

    result = repo.list_by_organization(
        organization_id, sort_by="start_date", sort_dir="asc"
    )
    names = [item.name for item in result.items]
    assert names.index("Early Fair") < names.index("Late Fair")
