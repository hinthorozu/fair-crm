from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.value_objects import TodoCategory, TodoPriority, TodoStatus
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository


def _seed_todo(session, organization_id, *, title: str, status: str = "todo") -> Todo:
    now = datetime.now(tz=UTC)
    todo = Todo.create(
        organization_id=organization_id,
        title=title,
        created_by=uuid4(),
        status=status,
        now=now,
    )
    repo = SqlAlchemyTodoRepository(session)
    return repo.add(todo)


def test_org_isolation(db_session, organization_id, other_organization_id):
    repo = SqlAlchemyTodoRepository(db_session)
    saved = _seed_todo(db_session, organization_id, title="Org A Todo")

    assert repo.get_by_id(organization_id, saved.id) is not None
    assert repo.get_by_id(other_organization_id, saved.id) is None


def test_list_excludes_archived_by_default(db_session, organization_id):
    repo = SqlAlchemyTodoRepository(db_session)
    _seed_todo(db_session, organization_id, title="Active todo")
    _seed_todo(db_session, organization_id, title="Archived todo", status=TodoStatus.ARCHIVED)

    result = repo.list_by_organization(organization_id, page_size=100)
    titles = [item.title for item in result.items]

    assert result.total == 1
    assert titles == ["Active todo"]


def test_list_search_matches_description(db_session, organization_id):
    repo = SqlAlchemyTodoRepository(db_session)
    now = datetime.now(tz=UTC)
    todo = Todo.create(
        organization_id=organization_id,
        title="Hidden title",
        description="Unique search phrase",
        created_by=uuid4(),
        now=now,
    )
    repo.add(todo)

    result = repo.list_by_organization(organization_id, search="Unique search")
    assert len(result.items) == 1
    assert result.items[0].description == "Unique search phrase"


def test_list_pagination(db_session, organization_id):
    repo = SqlAlchemyTodoRepository(db_session)
    for index in range(3):
        _seed_todo(db_session, organization_id, title=f"Todo {index}")

    first_page = repo.list_by_organization(organization_id, page=1, page_size=2)
    assert len(first_page.items) == 2
    assert first_page.total == 3
    assert first_page.total_pages == 2

    second_page = repo.list_by_organization(organization_id, page=2, page_size=2)
    assert len(second_page.items) == 1


def test_delete_by_id_removes_todo(db_session, organization_id):
    repo = SqlAlchemyTodoRepository(db_session)
    saved = _seed_todo(db_session, organization_id, title="Delete me")
    assert repo.delete_by_id(organization_id, saved.id) is True
    assert repo.get_by_id(organization_id, saved.id) is None


def test_list_filters_status_priority_category(db_session, organization_id):
    repo = SqlAlchemyTodoRepository(db_session)
    now = datetime.now(tz=UTC)
    todo = Todo.create(
        organization_id=organization_id,
        title="Filtered",
        created_by=uuid4(),
        status=TodoStatus.IN_PROGRESS,
        priority=TodoPriority.HIGH,
        category=TodoCategory.ARAMA,
        now=now,
    )
    repo.add(todo)

    result = repo.list_by_organization(
        organization_id,
        status=TodoStatus.IN_PROGRESS,
        priority=TodoPriority.HIGH,
        category=TodoCategory.ARAMA,
        page_size=100,
    )
    assert result.total == 1
    assert result.items[0].title == "Filtered"


def test_list_include_archived(db_session, organization_id):
    repo = SqlAlchemyTodoRepository(db_session)
    _seed_todo(db_session, organization_id, title="Active")
    _seed_todo(db_session, organization_id, title="Archived", status=TodoStatus.ARCHIVED)

    result = repo.list_by_organization(organization_id, include_archived=True, page_size=100)
    assert result.total == 2


def test_list_is_overdue_filter(db_session, organization_id):
    repo = SqlAlchemyTodoRepository(db_session)
    now = datetime.now(tz=UTC)
    overdue = Todo.create(
        organization_id=organization_id,
        title="Overdue",
        created_by=uuid4(),
        deadline=now - timedelta(days=1),
        now=now,
    )
    repo.add(overdue)
    _seed_todo(db_session, organization_id, title="On time")

    overdue_result = repo.list_by_organization(
        organization_id,
        is_overdue=True,
        now=now,
        page_size=100,
    )
    assert overdue_result.total == 1
    assert overdue_result.items[0].title == "Overdue"
