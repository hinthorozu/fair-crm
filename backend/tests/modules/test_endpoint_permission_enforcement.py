"""Cross-module endpoint permission enforcement audit tests (prod-path, dev bypass off)."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.integrations.kyrox_core.ports import AuthorizationPort
from app.modules.activities.api.dependencies import get_authorization_adapter as get_activity_authorization_adapter
from app.modules.contacts.api.dependencies import get_authorization_adapter as get_contact_authorization_adapter
from app.modules.customers.api.dependencies import get_authorization_adapter as get_customer_authorization_adapter
from app.modules.fairs.api.dependencies import (
    PERMISSION_SCRAPER_RUN,
    get_authorization_adapter as get_fair_authorization_adapter,
)
from app.modules.imports.api.dependencies import get_authorization_adapter as get_import_authorization_adapter
from app.modules.participations.api.dependencies import (
    get_authorization_adapter as get_participation_authorization_adapter,
)
from app.modules.scraper.api.dependencies import (
    PERMISSION_READ as SCRAPER_READ,
    get_authorization_adapter as get_scraper_authorization_adapter,
)
from app.modules.smtp.api.dependencies import get_authorization_adapter as get_smtp_authorization_adapter
from app.modules.system_admin.api.dependencies import get_authorization_adapter as get_system_admin_authorization_adapter
from app.modules.scraper.types.scraper_site import ScraperSiteKey


class SelectiveAuthorization(AuthorizationPort):
    def __init__(self, *, denied: set[str] | None = None) -> None:
        self._denied = denied or set()

    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (organization_id, user_id, access_token)
        return permission_code not in self._denied


class SingleOrgAuthorization(AuthorizationPort):
    """Simulates Core RBAC: permission checks succeed only for one organization."""

    def __init__(self, allowed_organization_id: UUID) -> None:
        self._allowed_organization_id = allowed_organization_id

    def check_permission(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        permission_code: str,
        access_token: str,
    ) -> bool:
        _ = (user_id, permission_code, access_token)
        return organization_id == self._allowed_organization_id


@pytest.fixture
def deny_customers_read(client: TestClient):
    client.app.dependency_overrides[get_customer_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.customers.read"}
    )
    yield
    client.app.dependency_overrides.pop(get_customer_authorization_adapter, None)


@pytest.fixture
def deny_customers_create(client: TestClient):
    client.app.dependency_overrides[get_customer_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.customers.create"}
    )
    yield
    client.app.dependency_overrides.pop(get_customer_authorization_adapter, None)


def test_dev_bypass_token_rejected_on_customers_list(client: TestClient, organization_id: UUID) -> None:
    response = client.get(
        "/api/v1/customers",
        headers={
            "Authorization": "Bearer dev-bypass",
            "X-Organization-Id": str(organization_id),
        },
    )
    assert response.status_code == 401


def test_foreign_org_header_denied_on_customers_list(
    client: TestClient,
    auth_headers: dict[str, str],
    organization_id: UUID,
    other_organization_id: UUID,
) -> None:
    client.app.dependency_overrides[get_customer_authorization_adapter] = lambda: SingleOrgAuthorization(
        organization_id
    )
    try:
        response = client.get(
            "/api/v1/customers",
            headers={
                **auth_headers,
                "X-Organization-Id": str(other_organization_id),
            },
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_customer_authorization_adapter, None)


def test_customers_read_allowed(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/customers", headers=auth_headers)
    assert response.status_code == 200


def test_customers_read_denied_returns_403(
    client: TestClient,
    auth_headers: dict[str, str],
    deny_customers_read: None,
) -> None:
    response = client.get("/api/v1/customers", headers=auth_headers)
    assert response.status_code == 403


def test_customers_create_denied_returns_403(
    client: TestClient,
    auth_headers: dict[str, str],
    deny_customers_create: None,
) -> None:
    response = client.post(
        "/api/v1/customers",
        json={"display_name": "Denied Customer"},
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_fairs_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_fair_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.fairs.read"}
    )
    try:
        response = client.get("/api/v1/fairs", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_fair_authorization_adapter, None)


def test_fair_scraper_run_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    create = client.post(
        "/api/v1/fairs",
        json={
            "name": "Perm Test Fair",
            "adapter_key": ScraperSiteKey.TUYAP_NEW,
            "source_url": "https://example.test/list",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    fair_id = create.json()["id"]

    client.app.dependency_overrides[get_fair_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={PERMISSION_SCRAPER_RUN}
    )
    try:
        response = client.post(f"/api/v1/fairs/{fair_id}/run", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_fair_authorization_adapter, None)


def test_imports_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_import_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.imports.read"}
    )
    try:
        response = client.get(f"/api/v1/imports/{uuid4()}", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_import_authorization_adapter, None)


def test_deprecated_import_analyze_requires_auth(client: TestClient, organization_id: UUID) -> None:
    response = client.post(
        f"/api/v1/imports/{uuid4()}/analyze",
        headers={"X-Organization-Id": str(organization_id)},
    )
    assert response.status_code == 401


def test_contacts_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_contact_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.contacts.read"}
    )
    try:
        response = client.get(f"/api/v1/contacts/{uuid4()}", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_contact_authorization_adapter, None)


def test_participations_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_participation_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.participations.read"}
    )
    try:
        response = client.get(f"/api/v1/fair-participations/{uuid4()}", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_participation_authorization_adapter, None)


def test_activities_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_activity_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.activities.read"}
    )
    try:
        response = client.get(f"/api/v1/activities/{uuid4()}", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_activity_authorization_adapter, None)


def test_scraper_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_scraper_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={SCRAPER_READ}
    )
    try:
        response = client.get("/api/v1/scraper/runs", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_scraper_authorization_adapter, None)


def test_smtp_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_smtp_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.smtp.read"}
    )
    try:
        response = client.get("/api/v1/smtp/accounts", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_smtp_authorization_adapter, None)


def test_smtp_create_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_smtp_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.smtp.create"}
    )
    try:
        response = client.post(
            "/api/v1/smtp/accounts",
            json={
                "name": "Denied SMTP",
                "from_email": "noreply@example.com",
                "host": "smtp.example.com",
                "port": 587,
            },
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_smtp_authorization_adapter, None)


def test_smtp_update_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Patch Target",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    account_id = create.json()["id"]

    client.app.dependency_overrides[get_smtp_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.smtp.update"}
    )
    try:
        response = client.patch(
            f"/api/v1/smtp/accounts/{account_id}",
            json={"name": "Denied Rename"},
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_smtp_authorization_adapter, None)


def test_smtp_delete_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Delete Target",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
        },
        headers=auth_headers,
    )
    account_id = create.json()["id"]

    client.app.dependency_overrides[get_smtp_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.smtp.delete"}
    )
    try:
        response = client.delete(f"/api/v1/smtp/accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_smtp_authorization_adapter, None)


def test_smtp_test_mail_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    create = client.post(
        "/api/v1/smtp/accounts",
        json={
            "name": "Test Target",
            "from_email": "noreply@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "password": "secret",
        },
        headers=auth_headers,
    )
    account_id = create.json()["id"]

    client.app.dependency_overrides[get_smtp_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.smtp.update"}
    )
    try:
        response = client.post(
            f"/api/v1/smtp/accounts/{account_id}/test",
            json={"recipient": "admin@example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_smtp_authorization_adapter, None)


def test_dev_bypass_token_rejected_on_smtp_list(client: TestClient, organization_id: UUID) -> None:
    response = client.get(
        "/api/v1/smtp/accounts",
        headers={
            "Authorization": "Bearer dev-bypass",
            "X-Organization-Id": str(organization_id),
        },
    )
    assert response.status_code == 401


def test_admin_backups_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_system_admin_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.admin.backups.read"}
    )
    try:
        response = client.get("/api/v1/admin/backups", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_system_admin_authorization_adapter, None)


def test_admin_backups_create_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_system_admin_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.admin.backups.create"}
    )
    try:
        response = client.post(
            "/api/v1/admin/backups",
            json={"backup_format": "postgresql_dump"},
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_system_admin_authorization_adapter, None)


def test_admin_backups_download_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_system_admin_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.admin.backups.download"}
    )
    try:
        response = client.get(
            f"/api/v1/admin/backups/{uuid4()}/download",
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_system_admin_authorization_adapter, None)


def test_admin_data_operations_read_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_system_admin_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.admin.data_operations.read"}
    )
    try:
        response = client.get("/api/v1/admin/data-operations", headers=auth_headers)
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_system_admin_authorization_adapter, None)


def test_admin_data_operations_run_denied_returns_403(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.app.dependency_overrides[get_system_admin_authorization_adapter] = lambda: SelectiveAuthorization(
        denied={"fair_crm.admin.data_operations.run"}
    )
    try:
        response = client.post(
            "/api/v1/admin/data-operations/analyze_customers_without_fair/run",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_system_admin_authorization_adapter, None)
