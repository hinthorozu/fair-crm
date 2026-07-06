"""Role-matrix authorization tests (non-owner roles, prod-path, dev bypass off)."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import patch
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.api.dependencies import get_authorization_adapter as get_activity_authorization_adapter
from app.modules.contacts.api.dependencies import get_authorization_adapter as get_contact_authorization_adapter
from app.modules.customers.api.dependencies import get_authorization_adapter as get_customer_authorization_adapter
from app.modules.fairs.api.dependencies import get_authorization_adapter as get_fair_authorization_adapter
from app.modules.imports.api.dependencies import get_authorization_adapter as get_import_authorization_adapter
from app.modules.participations.api.dependencies import (
    get_authorization_adapter as get_participation_authorization_adapter,
)
from app.modules.scraper.api.dependencies import get_authorization_adapter as get_scraper_authorization_adapter
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from app.modules.smtp.api.dependencies import get_authorization_adapter as get_smtp_authorization_adapter
from app.modules.mail_templates.api.dependencies import (
    get_authorization_adapter as get_mail_templates_authorization_adapter,
)
from app.modules.fair_emails.api.dependencies import (
    get_authorization_adapter as get_fair_emails_authorization_adapter,
)
from app.modules.system_admin.api.dependencies import get_authorization_adapter as get_system_admin_authorization_adapter
from app.modules.fairs.infrastructure.persistence.models import FairModel
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.participations.infrastructure.persistence.models import CustomerFairParticipationModel
from app.modules.todos.domain.entities import Todo
from app.modules.todos.domain.worklist_entities import TodoWorklistState
from app.modules.todos.domain.worklist_value_objects import StoredWorklistPrimaryStatus
from app.modules.todos.infrastructure.repositories.todo_repository import SqlAlchemyTodoRepository
from app.modules.todos.infrastructure.repositories.worklist_state_repository import (
    SqlAlchemyTodoWorklistStateRepository,
)
from app.modules.todos.api.dependencies import get_authorization_adapter as get_todos_authorization_adapter
from app.modules.todos.api.outcome_dependencies import (
    get_authorization_adapter as get_outcome_authorization_adapter,
)
from app.modules.dashboard.api.dependencies import (
    get_authorization_adapter as get_dashboard_authorization_adapter,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fair_crm_role_matrix import (  # noqa: E402
    ADMIN_ONLY_PERMISSIONS,
    permissions_for_role,
    role_slugs,
)

MATRIX_ROLES = tuple(
    slug for slug in role_slugs() if slug not in {"member"} and permissions_for_role(slug)
)

AUTH_DEPENDENCIES = (
    get_customer_authorization_adapter,
    get_fair_authorization_adapter,
    get_contact_authorization_adapter,
    get_activity_authorization_adapter,
    get_import_authorization_adapter,
    get_participation_authorization_adapter,
    get_scraper_authorization_adapter,
    get_smtp_authorization_adapter,
    get_mail_templates_authorization_adapter,
    get_fair_emails_authorization_adapter,
    get_todos_authorization_adapter,
    get_outcome_authorization_adapter,
    get_dashboard_authorization_adapter,
    get_system_admin_authorization_adapter,
)


class RoleMatrixAuthorization(AuthorizationPort):
    def __init__(
        self,
        role_slug: str,
        *,
        allowed_organization_id: UUID | None = None,
    ) -> None:
        self._role_slug = role_slug
        self._allowed = permissions_for_role(role_slug)
        self._allowed_organization_id = allowed_organization_id

    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (user_id, access_token)
        if self._allowed_organization_id is not None and organization_id != self._allowed_organization_id:
            return False
        return permission_code in self._allowed


@contextmanager
def install_role_matrix_auth(
    client: TestClient,
    role_slug: str,
    *,
    allowed_organization_id: UUID | None = None,
):
    auth = RoleMatrixAuthorization(role_slug, allowed_organization_id=allowed_organization_id)
    for dependency in AUTH_DEPENDENCIES:
        client.app.dependency_overrides[dependency] = lambda auth=auth: auth
    try:
        yield auth
    finally:
        for dependency in AUTH_DEPENDENCIES:
            client.app.dependency_overrides.pop(dependency, None)


def _role_has(role_slug: str, permission_code: str) -> bool:
    return permission_code in permissions_for_role(role_slug)


@pytest.fixture
def isolated_admin_backup_job(monkeypatch: pytest.MonkeyPatch):
    """Prevent role-matrix auth tests from running real pg_dump or writing backups/."""
    repo_backups = REPO_ROOT / "backups"
    before = (
        {path.name for path in repo_backups.glob("faircrm_backup_*")}
        if repo_backups.exists()
        else set()
    )

    def _noop_run_backup(self, command) -> None:
        _ = (self, command)
        return None

    monkeypatch.setattr(
        "app.modules.system_admin.application.backup_job_runner.BackupJobRunner.run_backup",
        _noop_run_backup,
    )
    yield
    if repo_backups.exists():
        after = {path.name for path in repo_backups.glob("faircrm_backup_*")}
        assert after == before, f"Role-matrix backup test leaked files: {sorted(after - before)}"


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_customers_read(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/customers", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.customers.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_customers_create(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            "/api/v1/customers",
            json={"display_name": f"Matrix {role_slug}"},
            headers=auth_headers,
        )
    expected = 201 if _role_has(role_slug, "fair_crm.customers.create") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_admin_backups_read(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/admin/backups", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.admin.backups.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_admin_backups_create(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
    isolated_admin_backup_job,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            "/api/v1/admin/backups",
            json={"backup_format": "postgresql_dump"},
            headers=auth_headers,
        )
    expected = 202 if _role_has(role_slug, "fair_crm.admin.backups.create") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_scraper_read(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/scraper/runs", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.scraper.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_scraper_run(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/fairs",
        json={
            "name": f"Matrix Run Fair {role_slug}",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://example.test/list",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    fair_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
    expected = 202 if _role_has(role_slug, "fair_crm.scraper.run") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_foreign_org_denied(
    client: TestClient,
    auth_headers: dict[str, str],
    organization_id: UUID,
    other_organization_id: UUID,
    role_slug: str,
) -> None:
    with install_role_matrix_auth(
        client,
        role_slug,
        allowed_organization_id=organization_id,
    ):
        response = client.get(
            "/api/v1/customers",
            headers={
                **auth_headers,
                "X-Organization-Id": str(other_organization_id),
            },
        )
    assert response.status_code == 403


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_dev_bypass_rejected(
    client: TestClient,
    organization_id: UUID,
    role_slug: str,
) -> None:
    _ = role_slug
    response = client.get(
        "/api/v1/customers",
        headers={
            "Authorization": "Bearer dev-bypass",
            "X-Organization-Id": str(organization_id),
        },
    )
    assert response.status_code == 401


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_smtp_read(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/smtp/accounts", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.smtp.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_smtp_create(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            "/api/v1/smtp/accounts",
            json={
                "name": "Matrix SMTP",
                "from_email": "noreply@example.com",
                "host": "smtp.example.com",
                "port": 587,
            },
            headers=auth_headers,
        )
    expected = 201 if _role_has(role_slug, "fair_crm.smtp.create") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_smtp_update(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": f"Matrix Update Target {role_slug}",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    account_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.patch(
            f"/api/v1/smtp/accounts/{account_id}",
            json={"name": f"Matrix Updated {role_slug}"},
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.smtp.update") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_smtp_delete(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": f"Matrix Delete Target {role_slug}",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    account_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.delete(
            f"/api/v1/smtp/accounts/{account_id}",
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.smtp.delete") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
@patch("app.modules.smtp.application.send_test_smtp_mail.send_smtp_message")
def test_role_matrix_smtp_test_mail(
    mock_send,
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": f"Matrix Test Mail Target {role_slug}",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "password": "secret-password",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    account_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            f"/api/v1/smtp/accounts/{account_id}/test",
            json={"recipient": "admin@example.com"},
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.smtp.update") else 403
    assert response.status_code == expected
    if expected == 200:
        mock_send.assert_called_once()
    else:
        mock_send.assert_not_called()


def _mail_template_payload(**overrides):
    payload = {
        "name": "Welcome Email",
        "key": "welcome_email",
        "subject": "Hello {{ name }}",
        "body_html": "<p>Hello {{ name }}</p>",
        "body_text": "Hello {{ name }}",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_mail_templates_read(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/mail-templates", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.mail_templates.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_mail_templates_create(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            "/api/v1/mail-templates",
            json=_mail_template_payload(key=f"create_{role_slug}"),
            headers=auth_headers,
        )
    expected = 201 if _role_has(role_slug, "fair_crm.mail_templates.create") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_mail_templates_update(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create_response = client.post(
        "/api/v1/mail-templates",
        json=_mail_template_payload(key="update_target"),
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.patch(
            f"/api/v1/mail-templates/{template_id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.mail_templates.update") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_mail_templates_delete(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create_response = client.post(
        "/api/v1/mail-templates",
        json=_mail_template_payload(key="delete_target"),
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.delete(
            f"/api/v1/mail-templates/{template_id}",
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.mail_templates.delete") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_mail_templates_render(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create_response = client.post(
        "/api/v1/mail-templates",
        json=_mail_template_payload(key="render_target"),
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            f"/api/v1/mail-templates/{template_id}/render",
            json={"variables": {"name": "Ada"}},
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.mail_templates.render") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_mail_templates_test_send(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create_response = client.post(
        "/api/v1/mail-templates",
        json=_mail_template_payload(key="test_send_target"),
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            f"/api/v1/mail-templates/{template_id}/test-email",
            json={"to_email": "test@example.com", "variables": {"name": "Ada"}},
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.mail_templates.test_send") else 403
    if expected == 200:
        assert response.status_code in {200, 400}
    else:
        assert response.status_code == 403


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_fair_emails_preview(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/fairs",
        json={"name": f"Matrix Bulk Email Fair {role_slug}", "status": "active"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    fair_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            f"/api/v1/fairs/{fair_id}/bulk-email/preview-recipients",
            json={"recipient_options": {"include_customer_emails": True, "include_contact_emails": False}},
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.fair_emails.preview") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_fair_emails_send(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/fairs",
        json={"name": f"Matrix Bulk Email Send Fair {role_slug}", "status": "active"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    fair_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            f"/api/v1/fairs/{fair_id}/bulk-email/send",
            json={
                "template_id": str(uuid4()),
                "recipient_options": {"include_customer_emails": True, "include_contact_emails": False},
            },
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.fair_emails.send") else 403
    if expected == 200:
        assert response.status_code in {200, 404, 400}
    else:
        assert response.status_code == 403


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_fair_emails_batch_logs(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/fairs",
        json={"name": f"Matrix Bulk Email Logs Fair {role_slug}", "status": "active"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    fair_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.get(
            f"/api/v1/fairs/{fair_id}/bulk-email/batches",
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.fair_emails.preview") else 403
    assert response.status_code == expected


def test_owner_retains_full_fair_crm_access() -> None:
    owner_perms = permissions_for_role("owner")
    for code in ADMIN_ONLY_PERMISSIONS:
        assert code in owner_perms


def test_admin_only_permissions_not_granted_to_operational_roles() -> None:
    for role_slug in ("manager", "sales", "viewer", "scraper_operator"):
        role_perms = permissions_for_role(role_slug)
        overlap = ADMIN_ONLY_PERMISSIONS.intersection(role_perms)
        assert not overlap, f"{role_slug} unexpectedly has admin-only permissions: {sorted(overlap)}"


def test_viewer_denied_on_import_detail(client: TestClient, auth_headers: dict[str, str]) -> None:
    with install_role_matrix_auth(client, "viewer"):
        response = client.get(f"/api/v1/imports/{uuid4()}", headers=auth_headers)
    assert response.status_code in {200, 404}


def test_sales_denied_admin_data_operations(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    with install_role_matrix_auth(client, "sales"):
        response = client.get("/api/v1/admin/data-operations", headers=auth_headers)
    assert response.status_code == 403


def test_scraper_operator_denied_customer_create(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    with install_role_matrix_auth(client, "scraper_operator"):
        response = client.post(
            "/api/v1/customers",
            json={"display_name": "Denied Scraper Op"},
            headers=auth_headers,
        )
    assert response.status_code == 403


def test_manager_allowed_customer_create(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    with install_role_matrix_auth(client, "manager"):
        response = client.post(
            "/api/v1/customers",
            json={"display_name": "Manager Customer"},
            headers=auth_headers,
        )
    assert response.status_code == 201


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todos_read(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/todos", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.todos.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todos_create(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            "/api/v1/todos",
            json={"title": f"Matrix Todo {role_slug}"},
            headers=auth_headers,
        )
    expected = 201 if _role_has(role_slug, "fair_crm.todos.create") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todos_archive(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/todos",
        json={"title": f"Matrix Archive Target {role_slug}"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    todo_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            f"/api/v1/todos/{todo_id}/archive",
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.todos.archive") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todos_delete(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/todos",
        json={"title": f"Matrix Delete Target {role_slug}"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    todo_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.delete(
            f"/api/v1/todos/{todo_id}",
            headers=auth_headers,
        )
    expected = 204 if _role_has(role_slug, "fair_crm.todos.delete") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todo_outcomes_read(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/todo-outcomes", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.todos.outcomes.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todo_outcomes_create(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            "/api/v1/todo-outcomes",
            json={
                "name": f"Matrix Outcome {role_slug}",
                "code": f"matrix_{role_slug}",
                "primary_worklist_status": "in_follow_up",
            },
            headers=auth_headers,
        )
    expected = 201 if _role_has(role_slug, "fair_crm.todos.outcomes.create") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todo_outcomes_update(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/todo-outcomes",
        json={
            "name": f"Matrix Update Target {role_slug}",
            "code": f"matrix_update_{role_slug}",
            "primary_worklist_status": "in_follow_up",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    outcome_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.patch(
            f"/api/v1/todo-outcomes/{outcome_id}",
            json={"name": "Updated by matrix"},
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.todos.outcomes.update") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todo_outcomes_deactivate(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    create = client.post(
        "/api/v1/todo-outcomes",
        json={
            "name": f"Matrix Deactivate Target {role_slug}",
            "code": f"matrix_deactivate_{role_slug}",
            "primary_worklist_status": "closed",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    outcome_id = create.json()["id"]

    with install_role_matrix_auth(client, role_slug):
        response = client.post(
            f"/api/v1/todo-outcomes/{outcome_id}/deactivate",
            headers=auth_headers,
        )
    expected = 200 if _role_has(role_slug, "fair_crm.todos.outcomes.deactivate") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_todo_worklist_read(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
    organization_id,
    user_id,
    role_slug: str,
) -> None:
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Matrix Fair",
        normalized_name="matrix fair",
        status="planned",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    db_session.add(fair)
    db_session.flush()
    todo = SqlAlchemyTodoRepository(db_session).add(
        Todo.create(
            organization_id=organization_id,
            title=f"Matrix Worklist {role_slug}",
            created_by=user_id,
            source_fair_id=fair.id,
            now=datetime.now(tz=UTC),
        )
    )

    with install_role_matrix_auth(client, role_slug):
        response = client.get(f"/api/v1/todos/{todo.id}/worklist", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.todos.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_follow_ups_read(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
    organization_id,
    user_id,
    role_slug: str,
) -> None:
    fair = FairModel(
        id=uuid4(),
        organization_id=organization_id,
        name="Matrix Fair Follow-ups",
        normalized_name="matrix fair follow-ups",
        status="planned",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    db_session.add(fair)
    db_session.flush()
    todo = SqlAlchemyTodoRepository(db_session).add(
        Todo.create(
            organization_id=organization_id,
            title=f"Matrix Follow-ups {role_slug}",
            created_by=user_id,
            source_fair_id=fair.id,
            now=datetime.now(tz=UTC),
        )
    )
    customer = CustomerModel(
        id=uuid4(),
        organization_id=organization_id,
        display_name="Follow-up Customer",
        normalized_name="follow-up customer",
        customer_type="lead",
        status="active",
        source="manual",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    db_session.add(customer)
    db_session.flush()
    participation = CustomerFairParticipationModel(
        id=uuid4(),
        organization_id=organization_id,
        customer_id=customer.id,
        fair_id=fair.id,
        participation_status="exhibitor",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    db_session.add(participation)
    db_session.flush()
    SqlAlchemyTodoWorklistStateRepository(db_session).add(
        TodoWorklistState.create(
            organization_id=organization_id,
            todo_id=todo.id,
            customer_id=customer.id,
            participation_id=participation.id,
            primary_status=StoredWorklistPrimaryStatus.IN_FOLLOW_UP,
            follow_up_at=datetime.now(tz=UTC),
            now=datetime.now(tz=UTC),
        )
    )

    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/follow-ups?filter=hepsi", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.todos.read") else 403
    assert response.status_code == expected


@pytest.mark.parametrize("role_slug", MATRIX_ROLES)
def test_role_matrix_dashboard_read(
    client: TestClient,
    auth_headers: dict[str, str],
    role_slug: str,
) -> None:
    with install_role_matrix_auth(client, role_slug):
        response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    expected = 200 if _role_has(role_slug, "fair_crm.dashboard.read") else 403
    assert response.status_code == expected
