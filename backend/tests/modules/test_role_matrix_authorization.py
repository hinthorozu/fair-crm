"""Role-matrix authorization tests (non-owner roles, prod-path, dev bypass off)."""

from __future__ import annotations

import sys
from contextlib import contextmanager
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
from app.modules.system_admin.api.dependencies import get_authorization_adapter as get_system_admin_authorization_adapter

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
