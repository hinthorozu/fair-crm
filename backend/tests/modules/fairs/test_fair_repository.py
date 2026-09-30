from datetime import UTC, date, datetime
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
    assert names.index("Early Fair") < names.index("Late Fair")


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


_LIST_TODAY = date(2026, 10, 1)


def _dated_fair(
    repo: SqlAlchemyFairRepository,
    organization_id,
    name: str,
    start: date,
    *,
    system: bool = False,
):
    now = datetime(2026, 10, 1, tzinfo=UTC)
    if system:
        fair = Fair(
            id=uuid4(),
            organization_id=None,
            name=name,
            organizer=None,
            venue=None,
            city=None,
            country=None,
            start_date=start,
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
    else:
        fair = Fair.create(
            organization_id=organization_id,
            name=name,
            start_date=start,
            now=now,
        )
    return repo.add(fair)


def _default_names(repo, organization_id, **kwargs) -> list[str]:
    result = repo.list_visible(
        organization_id,
        default_date_order=True,
        today=_LIST_TODAY,
        page_size=100,
        **kwargs,
    )
    return [item.name for item in result.items]


def test_default_list_orders_upcoming_then_past(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    _dated_fair(repo, organization_id, "Past Late", date(2026, 9, 30))
    _dated_fair(repo, organization_id, "Future Far", date(2026, 12, 1))
    _dated_fair(repo, organization_id, "Future Near", date(2026, 10, 5))
    _dated_fair(repo, organization_id, "Past Early", date(2026, 9, 20))
    _dated_fair(repo, organization_id, "Future Mid", date(2026, 10, 15))

    assert _default_names(repo, organization_id) == [
        "Future Near",
        "Future Mid",
        "Future Far",
        "Past Late",
        "Past Early",
    ]


def test_default_list_keeps_today_with_upcoming(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    _dated_fair(repo, organization_id, "Tomorrow", date(2026, 10, 2))
    _dated_fair(repo, organization_id, "Yesterday", date(2026, 9, 30))
    _dated_fair(repo, organization_id, "Today", date(2026, 10, 1))

    assert _default_names(repo, organization_id) == ["Today", "Tomorrow", "Yesterday"]


def test_default_list_tie_breaks_same_date_by_id(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    _dated_fair(repo, organization_id, "Same A", date(2026, 10, 5))
    _dated_fair(repo, organization_id, "Same B", date(2026, 10, 5))

    first = repo.list_visible(
        organization_id, default_date_order=True, today=_LIST_TODAY, page_size=1, page=1
    )
    second = repo.list_visible(
        organization_id, default_date_order=True, today=_LIST_TODAY, page_size=1, page=2
    )
    full = repo.list_visible(
        organization_id, default_date_order=True, today=_LIST_TODAY, page_size=10
    )
    again = repo.list_visible(
        organization_id, default_date_order=True, today=_LIST_TODAY, page_size=10
    )
    assert [item.id for item in again.items] == [item.id for item in full.items]
    assert [first.items[0].id, second.items[0].id] == [item.id for item in full.items]


def test_default_list_mixes_organization_and_system_fairs(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    _dated_fair(repo, organization_id, "Org Future", date(2026, 10, 15))
    _dated_fair(repo, organization_id, "System Near", date(2026, 10, 5), system=True)
    _dated_fair(repo, organization_id, "Org Past", date(2026, 9, 1))

    assert _default_names(repo, organization_id) == ["System Near", "Org Future", "Org Past"]


def test_explicit_start_date_sort_is_not_the_default_order(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    _dated_fair(repo, organization_id, "Past", date(2026, 9, 30))
    _dated_fair(repo, organization_id, "Future", date(2026, 10, 15))

    result = repo.list_visible(
        organization_id, sort_by="start_date", sort_dir="desc", today=_LIST_TODAY
    )
    assert [item.name for item in result.items] == ["Future", "Past"]


def test_default_list_keeps_search_filter(db_session, organization_id):
    repo = SqlAlchemyFairRepository(db_session)
    _dated_fair(repo, organization_id, "Needle Future", date(2026, 12, 1))
    _dated_fair(repo, organization_id, "Needle Past", date(2026, 9, 1))
    _dated_fair(repo, organization_id, "Other Future", date(2026, 10, 5))

    assert _default_names(repo, organization_id, search="Needle") == [
        "Needle Future",
        "Needle Past",
    ]
