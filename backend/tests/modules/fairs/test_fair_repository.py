from datetime import UTC, datetime
from uuid import uuid4

from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.value_objects import FairStatus
from app.modules.fairs.infrastructure.persistence.models import FairModel
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
    assert names.index("EARLY FAİR") < names.index("LATE FAİR")


def _system_fair(name: str = "System Fair") -> Fair:
    now = datetime.now(tz=UTC)
    return Fair(
        id=uuid4(),
        organization_id=None,
        name=name,
        organizer=None,
        venue="System Hall",
        city="Ankara",
        country=None,
        start_date=None,
        end_date=None,
        website=None,
        status=FairStatus.PLANNED,
        description=None,
        normalized_name=name.lower(),
        created_at=now,
        updated_at=now,
        deleted_at=None,
        origin="system",
        source="tobb",
        external_id=str(uuid4()),
    )


def test_visible_reads_include_own_and_system_fairs(
    db_session, organization_id, other_organization_id
):
    repo = SqlAlchemyFairRepository(db_session)
    own = _seed_fair(db_session, organization_id, "Own Fair")
    other = _seed_fair(db_session, other_organization_id, "Other Fair")
    system = repo.add(_system_fair())

    assert repo.get_by_id(organization_id, system.id) is None
    assert repo.get_by_id(organization_id, other.id) is None
    assert repo.get_visible(organization_id, own.id) is not None
    assert repo.get_visible(organization_id, system.id) is not None
    assert repo.get_visible(organization_id, other.id) is None

    org_only = repo.list_by_organization(organization_id)
    org_only_ids = {item.id for item in org_only.items}
    assert own.id in org_only_ids
    assert system.id not in org_only_ids
    assert other.id not in org_only_ids

    visible = repo.list_visible(organization_id)
    visible_ids = {item.id for item in visible.items}
    assert own.id in visible_ids
    assert system.id in visible_ids
    assert other.id not in visible_ids


def test_visible_detail_hides_archived_system_fair(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    system = repo.add(_system_fair("Archived System Fair"))
    model = db_session.get(FairModel, system.id)
    model.deleted_at = datetime.now(tz=UTC)
    db_session.flush()

    assert repo.get_visible(organization_id, system.id) is None
    loaded = repo.get_visible_including_archived(organization_id, system.id)
    assert loaded is not None
    assert loaded.origin == "system"
    assert loaded.deleted_at is not None
